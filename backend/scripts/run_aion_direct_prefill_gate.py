#!/usr/bin/env python3
"""Gate direct token-major Metal prefill without host-visible expert counts."""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
import statistics
import time

import torch

from backend.modules.aion_inference.int8_dynamic_bank_moe import (
    Int8DynamicBankMoE, _library, load_bank_entry,
)
from backend.scripts.run_aion_int8_glyph_full_model import _canonical_sha256
from backend.scripts.run_aion_int8pack_expert_microbench import _p95
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256
from backend.scripts.run_aion_storage_first_boot import _load_storage_first_model


def _summary(values: list[float]) -> dict[str, float]:
    return {"p50_seconds": statistics.median(values),
            "p95_seconds_nearest_rank": _p95(values),
            "mean_seconds": statistics.mean(values)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--bank-manifest", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=16)
    parser.add_argument("--tokens", type=int, default=64)
    parser.add_argument("--accuracy-samples", type=int, default=16)
    parser.add_argument("--timing-samples", type=int, default=100)
    parser.add_argument("--warmups", type=int, default=5)
    parser.add_argument("--seed", type=int, default=8091843)
    parser.add_argument("--maximum-output-error", type=float, default=0.002)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, model_path = args.storage_root.resolve(), args.model_path.resolve()
    bank_path, output = args.bank_manifest.resolve(), args.output.resolve()
    if any(root not in path.parents for path in (model_path, bank_path, output)) or output.exists():
        raise SystemExit("scope invalid or output already exists")
    if not 1 <= args.tokens <= 128:
        raise SystemExit("direct-prefill narrow gate requires 1--128 tokens")
    manifest = json.loads(bank_path.read_text())
    checkpoint = model_path / "model.safetensors.index.json"
    model, shared = _load_storage_first_model(model_path, json.loads(checkpoint.read_text()))
    source = model.model.layers[args.layer].block_sparse_moe
    moe = Int8DynamicBankMoE(
        source, load_bank_entry(manifest, args.layer, root, _sha256), root, _sha256, "mps",
    ).eval()
    del model
    gc.collect()
    library = _library()
    generator = torch.Generator().manual_seed(args.seed)
    samples = torch.randn(
        (args.accuracy_samples, args.tokens, moe.input_size), generator=generator,
        dtype=torch.float16,
    ).to("mps")
    activated = torch.empty(
        (args.tokens * 8, moe.input_bank.shape[1] // 2),
        dtype=torch.float16, device="mps",
    )
    candidate_output = torch.empty(
        (args.tokens, moe.output_bank.shape[1]), dtype=torch.float16, device="mps",
    )

    def candidate(value: torch.Tensor):
        logits = moe.router.layer(value).float()
        top_logits, top_indices = logits.topk(8, dim=1)
        top_gates = torch.softmax(top_logits, dim=1).type_as(value)
        top_indices, order = top_indices.sort(dim=1)
        top_gates = top_gates.gather(1, order)
        assignments = args.tokens * 8
        library.prefill_input_silu(
            value, moe.input_bank, moe.input_scale_bank, top_indices.flatten(), activated,
            moe.input_bank.shape[2], moe.input_bank.shape[1],
            threads=((moe.input_bank.shape[1] // 2) * 32, assignments, 1),
            group_size=(32, 1, 1),
        )
        library.prefill_output(
            activated, moe.output_bank, moe.output_scale_bank, top_indices.flatten(),
            top_gates.flatten(), candidate_output, moe.output_bank.shape[2],
            moe.output_bank.shape[1], threads=(moe.output_bank.shape[1] * 32, args.tokens, 1),
            group_size=(32, 1, 1),
        )
        return candidate_output

    exact = 0
    maximum_error = 0.0
    with torch.inference_mode():
        for value in samples:
            control = moe(value.unsqueeze(0))[0]
            observed = candidate(value)
            torch.mps.synchronize()
            exact += bool(torch.equal(control.cpu(), observed.cpu()))
            maximum_error = max(maximum_error, float(
                (control.float() - observed.float()).abs().max().cpu()))
        fixed = samples[0]
        for _ in range(args.warmups):
            moe(fixed.unsqueeze(0)); candidate(fixed)
        timings = {"grouped_host_synchronized_prefill": [], "direct_metal_prefill": []}
        for sample in range(args.timing_samples):
            order_names = tuple(timings) if sample % 2 == 0 else tuple(reversed(tuple(timings)))
            for condition in order_names:
                started = time.perf_counter()
                (moe(fixed.unsqueeze(0)) if condition == "grouped_host_synchronized_prefill"
                 else candidate(fixed))
                torch.mps.synchronize()
                timings[condition].append(time.perf_counter() - started)
    control_summary = _summary(timings["grouped_host_synchronized_prefill"])
    candidate_summary = _summary(timings["direct_metal_prefill"])
    p50 = 100 * (1 - candidate_summary["p50_seconds"] / control_summary["p50_seconds"])
    p95 = 100 * (1 - candidate_summary["p95_seconds_nearest_rank"] /
                 control_summary["p95_seconds_nearest_rank"])
    acceptance = {
        "maximum_output_error_within_0_002": maximum_error <= args.maximum_output_error,
        "p50_improved_at_least_15_percent": p50 >= 15.0,
        "p95_not_regressed": p95 >= 0.0,
        "no_host_visible_expert_counts_in_candidate": True,
    }
    report = {
        "schema_version": "aion.direct_prefill_gate.v1",
        "track": "quality_gated_changed_kernel_not_bit_exact",
        "paths": {"model": str(model_path), "bank_manifest": str(bank_path)},
        "hashes": {"checkpoint_index": _sha256(checkpoint),
                   "bank_manifest": _sha256(bank_path)},
        "layer": args.layer, "tokens": args.tokens,
        "accuracy_samples": args.accuracy_samples, "timing_samples": args.timing_samples,
        "seed": args.seed, "bit_exact_fraction": exact / args.accuracy_samples,
        "maximum_output_error": maximum_error, "control": control_summary,
        "candidate": candidate_summary, "p50_improvement_percent": p50,
        "p95_improvement_percent": p95, "shared_load": shared,
        "candidate_temporary_buffer_bytes": int(activated.numel() * activated.element_size() +
                                                 candidate_output.numel() * candidate_output.element_size()),
        "acceptance": acceptance,
        "decision": ("ADVANCE_DIRECT_PREFILL_TO_FULL_MODEL_GATE"
                     if all(acceptance.values()) else "STOP_DIRECT_PREFILL_V1"),
        "claim_boundary": (
            "One real Granite layer-16 INT8 bank and synthetic 64-token FP16 batches. "
            "Full-model prompt speed and semantic preservation remain unproved."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "output": str(output), "decision": report["decision"],
        "bit_exact_fraction": report["bit_exact_fraction"],
        "maximum_output_error": maximum_error, "control": control_summary,
        "candidate": candidate_summary, "p50_improvement_percent": p50,
        "p95_improvement_percent": p95, "acceptance": acceptance,
        "report_sha256": report["report_sha256"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
