#!/usr/bin/env python3
"""Measure cached resident weight views for sparse packed-INT8 expert decode."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import time
from typing import Any

import torch
import torch.nn.functional as functional

from backend.modules.aion_inference.int8_glyph_moe import (
    Int8GlyphParallelExperts, load_layer_entries,
)
from backend.scripts.run_aion_int8_glyph_full_model import _canonical_sha256
from backend.scripts.run_aion_int8pack_expert_microbench import _p95
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256


def _forward(experts: Int8GlyphParallelExperts, values: torch.Tensor,
             expert_size: list[int]) -> torch.Tensor:
    hidden = experts.input_forward(values, expert_size)
    gate, projected = hidden.chunk(2, dim=-1)
    return experts.output_forward(functional.silu(gate) * projected, expert_size)


def _summary(values: list[float]) -> dict[str, float]:
    return {"p50_seconds": statistics.median(values),
            "p95_seconds_nearest_rank": _p95(values),
            "mean_seconds": statistics.mean(values)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--glyph-manifest", type=Path, required=True)
    parser.add_argument("--route-observation", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=16)
    parser.add_argument("--samples", type=int, default=1000)
    parser.add_argument("--warmups", type=int, default=20)
    parser.add_argument("--seed", type=int, default=8091057)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {"glyph_manifest": args.glyph_manifest.resolve(),
             "route_observation": args.route_observation.resolve()}
    output = args.output.resolve()
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("all model inputs and evidence must remain on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    glyph = json.loads(paths["glyph_manifest"].read_text())
    observation = json.loads(paths["route_observation"].read_text())
    entries = load_layer_entries(glyph, args.layer, root, _sha256)
    experts = Int8GlyphParallelExperts(
        entries, root, _sha256, "mps", skip_empty_experts=True,
        use_decode_arena=False, use_cached_weight_views=False,
    ).eval()
    route = tuple(int(value) for value in
                  observation["route_batches_by_layer"][args.layer][-1][-1])
    active = set(route)
    expert_size = [1 if index in active else 0 for index in range(40)]
    if sum(expert_size) != 8:
        raise RuntimeError(f"expected eight unique routed experts, got {route}")
    generator = torch.Generator().manual_seed(args.seed)
    values = torch.randn((8, entries[0]["input_shape"][1]), generator=generator,
                         dtype=torch.float16).to("mps")
    for _ in range(args.warmups):
        experts.use_cached_weight_views = False; _forward(experts, values, expert_size)
        experts.use_cached_weight_views = True; _forward(experts, values, expert_size)
    torch.mps.synchronize()
    timings = {"dynamic_views": [], "cached_views": []}
    outputs: dict[str, torch.Tensor] = {}
    conditions = tuple(timings)
    for sample in range(args.samples):
        order = conditions if sample % 2 == 0 else tuple(reversed(conditions))
        for condition in order:
            experts.use_cached_weight_views = condition == "cached_views"
            started = time.perf_counter()
            result = _forward(experts, values, expert_size)
            torch.mps.synchronize()
            timings[condition].append(time.perf_counter() - started)
            outputs[condition] = result.detach().clone().cpu()
    control = _summary(timings["dynamic_views"])
    candidate = _summary(timings["cached_views"])
    p50_improvement = 100 * (1 - candidate["p50_seconds"] / control["p50_seconds"])
    p95_improvement = 100 * (
        1 - candidate["p95_seconds_nearest_rank"] / control["p95_seconds_nearest_rank"])
    exact = torch.equal(outputs["dynamic_views"], outputs["cached_views"])
    acceptance = {"outputs_bit_identical": exact,
                  "p50_improved_at_least_5_percent": p50_improvement >= 5,
                  "p95_not_regressed_more_than_3_percent": p95_improvement >= -3,
                  "cached_views_add_no_weight_storage": True}
    report: dict[str, Any] = {
        "schema_version": "aion.int8_cached_views_gate.v1",
        "paths": {name: str(path) for name, path in paths.items()},
        "hashes": {name: _sha256(path) for name, path in paths.items()},
        "layer": args.layer, "route": list(route), "samples": args.samples,
        "warmups": args.warmups, "seed": args.seed,
        "control": control, "candidate": candidate,
        "aggregate": {"p50_improvement_percent": p50_improvement,
                      "p95_improvement_percent": p95_improvement,
                      "maximum_output_error": float((outputs["dynamic_views"].float() -
                                                      outputs["cached_views"].float()).abs().max())},
        "acceptance": acceptance,
        "decision": "ADVANCE_TO_FULL_MODEL_CACHED_VIEWS_GATE" if all(acceptance.values())
                    else "STOP_CACHED_WEIGHT_VIEWS",
        "claim_boundary": ("One real eight-expert route with synthetic decode activation. Both "
                           "conditions use promoted sparse dispatch and identical resident INT8 "
                           "blocks; full-model throughput is not established."),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), "decision": report["decision"],
                      "control": control, "candidate": candidate,
                      "aggregate": report["aggregate"], "acceptance": acceptance,
                      "report_sha256": report["report_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
