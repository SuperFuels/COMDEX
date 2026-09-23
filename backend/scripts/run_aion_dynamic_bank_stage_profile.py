#!/usr/bin/env python3
"""Profile the resident dynamic-bank decode path by synchronized Metal stage."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
import statistics
import time
from typing import Any, Callable

import torch

from backend.modules.aion_inference.int8_dynamic_bank_moe import (
    Int8DynamicBankMoE,
    _library,
    load_bank_entry,
)
from backend.scripts.run_aion_int8_glyph_full_model import _canonical_sha256, _memory
from backend.scripts.run_aion_int8pack_expert_microbench import _p95
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256
from backend.scripts.run_aion_storage_first_boot import _load_storage_first_model


def _summary(values: list[float]) -> dict[str, float]:
    return {"p50_seconds": statistics.median(values),
            "p95_seconds_nearest_rank": _p95(values),
            "mean_seconds": statistics.mean(values)}


def _measure(function: Callable[[], Any], warmups: int, samples: int) -> dict[str, float]:
    for _ in range(warmups):
        function()
    torch.mps.synchronize()
    values = []
    for _ in range(samples):
        started = time.perf_counter()
        function()
        torch.mps.synchronize()
        values.append(time.perf_counter() - started)
    return _summary(values)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--bank-manifest", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=16)
    parser.add_argument("--samples", type=int, default=500)
    parser.add_argument("--warmups", type=int, default=20)
    parser.add_argument("--seed", type=int, default=8091824)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    model_path = args.model_path.resolve()
    bank_path = args.bank_manifest.resolve()
    output_path = args.output.resolve()
    if any(root not in path.parents for path in (model_path, bank_path, output_path)):
        raise SystemExit("model, bank and evidence must remain on external storage")
    if output_path.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output_path}")
    manifest = json.loads(bank_path.read_text())
    if not all(manifest["integrity"].values()):
        raise RuntimeError("bank manifest integrity failed")
    index = json.loads((model_path / "model.safetensors.index.json").read_text())
    model, shared_load = _load_storage_first_model(model_path, index)
    source = model.model.layers[args.layer].block_sparse_moe
    entry = load_bank_entry(manifest, args.layer, root, _sha256)
    moe = Int8DynamicBankMoE(source, entry, root, _sha256, "mps", True).eval()
    del model
    gc.collect()
    generator = torch.Generator().manual_seed(args.seed)
    flattened = torch.randn((1, moe.input_size), generator=generator,
                            dtype=torch.float16).to("mps")
    library = _library()

    def route():
        logits = moe.router.layer(flattened).float()
        top_logits, top_indices = logits.topk(8, dim=1)
        gates = torch.softmax(top_logits, dim=1).type_as(flattened)
        top_indices, order = top_indices.sort(dim=1)
        return top_indices[0].to(torch.int32), gates.gather(1, order)[0]

    expert_indices, gates = route()
    library.dyn_input(
        flattened, moe.input_bank, moe.input_scale_bank, expert_indices,
        moe.dynamic_hidden, moe.input_bank.shape[2], moe.input_bank.shape[1],
        threads=(moe.input_bank.shape[1] * 32, 8, 1), group_size=(32, 1, 1),
    )
    gate, projected = moe.dynamic_hidden.chunk(2, dim=-1)
    activated = moe.activation(gate) * projected
    torch.mps.synchronize()

    def input_projection():
        return library.dyn_input(
            flattened, moe.input_bank, moe.input_scale_bank, expert_indices,
            moe.dynamic_hidden, moe.input_bank.shape[2], moe.input_bank.shape[1],
            threads=(moe.input_bank.shape[1] * 32, 8, 1), group_size=(32, 1, 1),
        )

    def activation():
        local_gate, local_projected = moe.dynamic_hidden.chunk(2, dim=-1)
        return moe.activation(local_gate) * local_projected

    def output_projection():
        return library.dyn_output(
            activated, moe.output_bank, moe.output_scale_bank, expert_indices, gates,
            moe.dynamic_output, moe.output_bank.shape[2], moe.output_bank.shape[1],
            threads=(moe.output_bank.shape[1] * 32, 1, 1), group_size=(32, 1, 1),
        )

    stages = {
        "route_topk_softmax_sort": _measure(route, args.warmups, args.samples),
        "input_projection": _measure(input_projection, args.warmups, args.samples),
        "activation": _measure(activation, args.warmups, args.samples),
        "output_projection": _measure(output_projection, args.warmups, args.samples),
        "complete_dynamic_moe": _measure(
            lambda: moe._dynamic(flattened), args.warmups, args.samples),
    }
    component_total = sum(stages[name]["p50_seconds"] for name in (
        "route_topk_softmax_sort", "input_projection", "activation", "output_projection"))
    shares = {name: stages[name]["p50_seconds"] / component_total
              for name in ("route_topk_softmax_sort", "input_projection", "activation",
                           "output_projection")}
    largest = max(shares, key=shares.get)
    report = {
        "schema_version": "aion.dynamic_bank_stage_profile.v1",
        "track": "diagnostic_no_runtime_change",
        "paths": {"model": str(model_path), "bank_manifest": str(bank_path)},
        "hashes": {"bank_manifest": _sha256(bank_path),
                   "checkpoint_index": _sha256(model_path / "model.safetensors.index.json")},
        "layer": args.layer, "samples_per_stage": args.samples,
        "warmups_per_stage": args.warmups, "seed": args.seed,
        "shared_load": shared_load, "memory": _memory("dynamic_bank_stage_profile"),
        "stages": stages, "synchronized_component_p50_sum_seconds": component_total,
        "component_p50_shares": shares, "largest_synchronized_component": largest,
        "decision": f"PROFILE_NEXT_{largest.upper()}",
        "claim_boundary": (
            "One real Granite layer and one synthetic decode activation. Each component is "
            "synchronized independently, so shares include per-stage synchronization and do not "
            "sum to asynchronous full-model latency. Use only to select the next narrow candidate."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output_path), "stages": stages,
                      "component_p50_shares": shares,
                      "largest": largest, "decision": report["decision"],
                      "report_sha256": report["report_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
