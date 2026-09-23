#!/usr/bin/env python3
"""Gate a Metal input-projection plus SiLU fusion on a real Granite bank."""

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
    parser.add_argument("--accuracy-samples", type=int, default=128)
    parser.add_argument("--timing-samples", type=int, default=1000)
    parser.add_argument("--warmups", type=int, default=20)
    parser.add_argument("--seed", type=int, default=8091842)
    parser.add_argument("--maximum-output-error", type=float, default=0.001)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, model_path = args.storage_root.resolve(), args.model_path.resolve()
    bank_path, output = args.bank_manifest.resolve(), args.output.resolve()
    if any(root not in path.parents for path in (model_path, bank_path, output)) or output.exists():
        raise SystemExit("scope invalid or output already exists")
    manifest = json.loads(bank_path.read_text())
    checkpoint = model_path / "model.safetensors.index.json"
    model, shared = _load_storage_first_model(model_path, json.loads(checkpoint.read_text()))
    source = model.model.layers[args.layer].block_sparse_moe
    moe = Int8DynamicBankMoE(
        source, load_bank_entry(manifest, args.layer, root, _sha256), root, _sha256, "mps", True,
    ).eval()
    del model
    gc.collect()
    library = _library()
    generator = torch.Generator().manual_seed(args.seed)
    values = torch.randn(
        (args.accuracy_samples, moe.input_size), generator=generator, dtype=torch.float16,
    ).to("mps")
    route_scores = torch.randn(
        (args.accuracy_samples, 40), generator=generator, dtype=torch.float32,
    ).to("mps")
    gate_scores = torch.randn(
        (args.accuracy_samples, 8), generator=generator, dtype=torch.float32,
    ).to("mps")
    routes = route_scores.topk(8, dim=1).indices.sort(dim=1).values.to(torch.int32)
    gates = torch.softmax(gate_scores, dim=1).to(torch.float16)
    candidate_activated = torch.empty(
        (8, moe.input_bank.shape[1] // 2), dtype=torch.float16, device="mps",
    )
    control_output = torch.empty_like(moe.dynamic_output)
    candidate_output = torch.empty_like(moe.dynamic_output)

    def control(index: int):
        flat = values[index:index + 1]
        library.dyn_input(
            flat, moe.input_bank, moe.input_scale_bank, routes[index], moe.dynamic_hidden,
            moe.input_bank.shape[2], moe.input_bank.shape[1],
            threads=(moe.input_bank.shape[1] * 32, 8, 1), group_size=(32, 1, 1),
        )
        gate, projected = moe.dynamic_hidden.chunk(2, dim=-1)
        activated = moe.activation(gate) * projected
        library.dyn_output(
            activated, moe.output_bank, moe.output_scale_bank, routes[index], gates[index],
            control_output, moe.output_bank.shape[2], moe.output_bank.shape[1],
            threads=(moe.output_bank.shape[1] * 32, 1, 1), group_size=(32, 1, 1),
        )

    def candidate(index: int):
        flat = values[index:index + 1]
        library.dyn_input_silu2(
            flat, moe.input_bank, moe.input_scale_bank, routes[index], candidate_activated,
            moe.input_bank.shape[2], moe.input_bank.shape[1],
            threads=((moe.input_bank.shape[1] // 2) * 32, 16, 1), group_size=(32, 2, 1),
        )
        library.dyn_output_parallel(
            candidate_activated, moe.output_bank, moe.output_scale_bank, routes[index],
            gates[index], candidate_output, moe.output_bank.shape[2], moe.output_bank.shape[1],
            threads=(moe.output_bank.shape[1] * 32, 8, 1), group_size=(32, 8, 1),
        )

    exact = 0
    maximum_error = 0.0
    with torch.inference_mode():
        for index in range(args.accuracy_samples):
            control(index); candidate(index); torch.mps.synchronize()
            exact += bool(torch.equal(control_output.cpu(), candidate_output.cpu()))
            maximum_error = max(maximum_error, float(
                (control_output.float() - candidate_output.float()).abs().max().cpu()))
        for _ in range(args.warmups):
            control(0); candidate(0)
        timings = {"serial_projection_pipeline": [], "fused_parallel_projection_pipeline": []}
        for sample in range(args.timing_samples):
            order = tuple(timings) if sample % 2 == 0 else tuple(reversed(tuple(timings)))
            for condition in order:
                started = time.perf_counter()
                control(0) if condition == "serial_projection_pipeline" else candidate(0)
                torch.mps.synchronize()
                timings[condition].append(time.perf_counter() - started)
    control_summary = _summary(timings["serial_projection_pipeline"])
    candidate_summary = _summary(timings["fused_parallel_projection_pipeline"])
    p50 = 100 * (1 - candidate_summary["p50_seconds"] / control_summary["p50_seconds"])
    p95 = 100 * (1 - candidate_summary["p95_seconds_nearest_rank"] /
                 control_summary["p95_seconds_nearest_rank"])
    acceptance = {
        "maximum_output_error_within_0_001": maximum_error <= args.maximum_output_error,
        "p50_improved_at_least_15_percent": p50 >= 15.0,
        "p95_not_regressed": p95 >= 0.0,
    }
    report = {
        "schema_version": "aion.dual_projection_fast_silu_pipeline_gate.v5",
        "track": "quality_gated_changed_kernel_not_bit_exact",
        "paths": {"model": str(model_path), "bank_manifest": str(bank_path)},
        "hashes": {"checkpoint_index": _sha256(checkpoint),
                   "bank_manifest": _sha256(bank_path)},
        "layer": args.layer, "accuracy_samples": args.accuracy_samples,
        "timing_samples": args.timing_samples, "seed": args.seed,
        "bit_exact_fraction": exact / args.accuracy_samples,
        "maximum_output_error": maximum_error, "control": control_summary,
        "candidate": candidate_summary, "p50_improvement_percent": p50,
        "p95_improvement_percent": p95, "shared_load": shared,
        "acceptance": acceptance,
        "decision": ("ADVANCE_DUAL_PROJECTION_FAST_SILU_TO_FULL_MODEL_GATE"
                     if all(acceptance.values()) else "STOP_DUAL_PROJECTION_FAST_SILU_V5"),
        "claim_boundary": (
            "One real Granite layer-16 INT8 bank with synthetic one-token FP16 inputs, "
            "routes and gates. Fast-SiLU input fusion and eight-way output projection are combined."
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
