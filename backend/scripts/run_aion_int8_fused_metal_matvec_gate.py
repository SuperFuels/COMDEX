#!/usr/bin/env python3
"""Quality-gate a fused eight-expert Metal INT8 decode matvec."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import time

import torch
import torch.nn.functional as functional

from backend.modules.aion_inference.int8_glyph_moe import (
    Int8GlyphParallelExperts, fused_metal_shader_source, load_layer_entries,
)
from backend.scripts.run_aion_int8_glyph_full_model import _canonical_sha256
from backend.scripts.run_aion_int8pack_expert_microbench import _p95
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256


def _shader_source() -> str:
    return fused_metal_shader_source()


def _launch(kernel, values, pairs, output) -> None:
    arguments = []
    for weight, scale in pairs:
        arguments.extend((weight, scale))
    rows, width = pairs[0][0].shape
    kernel(values, *arguments, output, width, rows,
           threads=(rows * 32, 8, 1), group_size=(32, 1, 1))


def _builtin(values, input_pairs, output_pairs):
    hidden = torch.cat([
        torch._weight_int8pack_mm(values[index:index + 1], weight, scale)
        for index, (weight, scale) in enumerate(input_pairs)
    ], dim=0)
    gate, projected = hidden.chunk(2, dim=-1)
    activated = functional.silu(gate) * projected
    return torch.cat([
        torch._weight_int8pack_mm(activated[index:index + 1], weight, scale)
        for index, (weight, scale) in enumerate(output_pairs)
    ], dim=0)


def _fused(kernel, values, input_pairs, output_pairs, hidden, output):
    _launch(kernel, values, input_pairs, hidden)
    gate, projected = hidden.chunk(2, dim=-1)
    activated = functional.silu(gate) * projected
    _launch(kernel, activated, output_pairs, output)
    return output


def _summary(values):
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
    parser.add_argument("--seed", type=int, default=8091357)
    parser.add_argument("--maximum-extra-error", type=float, default=0.00075)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {"glyph_manifest": args.glyph_manifest.resolve(),
             "route_observation": args.route_observation.resolve()}
    output_path = args.output.resolve()
    if any(root not in path.parents for path in (*paths.values(), output_path)):
        raise SystemExit("all model inputs and evidence must remain on external storage")
    if output_path.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output_path}")
    glyph = json.loads(paths["glyph_manifest"].read_text())
    observation = json.loads(paths["route_observation"].read_text())
    entries = load_layer_entries(glyph, args.layer, root, _sha256)
    experts = Int8GlyphParallelExperts(entries, root, _sha256, "mps",
                                       skip_empty_experts=True).eval()
    route = sorted(set(int(value) for value in
                       observation["route_batches_by_layer"][args.layer][-1][-1]))
    if len(route) != 8:
        raise RuntimeError(f"expected eight routed experts, got {route}")
    input_pairs = []
    output_pairs = []
    for expert in route:
        input_weight, input_scale, output_weight, output_scale = experts._weights(expert)
        input_pairs.append((input_weight, input_scale))
        output_pairs.append((output_weight, output_scale))
    generator = torch.Generator().manual_seed(args.seed)
    values = torch.randn((8, input_pairs[0][0].shape[1]), generator=generator,
                         dtype=torch.float16).to("mps")
    hidden = torch.empty((8, input_pairs[0][0].shape[0]), dtype=torch.float16, device="mps")
    output = torch.empty((8, output_pairs[0][0].shape[0]), dtype=torch.float16, device="mps")
    kernel = torch.mps.compile_shader(_shader_source()).fused8
    for _ in range(args.warmups):
        _builtin(values, input_pairs, output_pairs)
        _fused(kernel, values, input_pairs, output_pairs, hidden, output)
    torch.mps.synchronize()
    timings = {"builtin_16_launches": [], "fused_2_launches": []}
    outputs = {}
    conditions = tuple(timings)
    for sample in range(args.samples):
        order = conditions if sample % 2 == 0 else tuple(reversed(conditions))
        for condition in order:
            started = time.perf_counter()
            result = (_builtin(values, input_pairs, output_pairs)
                      if condition == "builtin_16_launches" else
                      _fused(kernel, values, input_pairs, output_pairs, hidden, output))
            torch.mps.synchronize()
            timings[condition].append(time.perf_counter() - started)
            outputs[condition] = result.detach().clone().cpu()
    control = _summary(timings["builtin_16_launches"])
    candidate = _summary(timings["fused_2_launches"])
    p50_gain = 100 * (1 - candidate["p50_seconds"] / control["p50_seconds"])
    p95_gain = 100 * (1 - candidate["p95_seconds_nearest_rank"] /
                      control["p95_seconds_nearest_rank"])
    difference = (outputs["builtin_16_launches"].float() -
                  outputs["fused_2_launches"].float()).abs()
    maximum_error = float(difference.max())
    rmse = float(torch.sqrt(torch.mean(difference.square())))
    acceptance = {"p50_improved_at_least_10_percent": p50_gain >= 10,
                  "p95_not_regressed_more_than_3_percent": p95_gain >= -3,
                  "extra_maximum_error_within_ceiling": maximum_error <= args.maximum_extra_error,
                  "fused_kernel_adds_no_weight_storage": True}
    report = {"schema_version": "aion.int8_fused_metal_matvec_gate.v1",
              "track": "quality_gated_changed_kernel_not_bit_exact",
              "paths": {name: str(path) for name, path in paths.items()},
              "hashes": {name: _sha256(path) for name, path in paths.items()},
              "layer": args.layer, "route": route, "samples": args.samples,
              "warmups": args.warmups, "seed": args.seed,
              "control_metal_launches_per_layer_token": 16,
              "candidate_metal_launches_per_layer_token": 2,
              "maximum_extra_error_ceiling": args.maximum_extra_error,
              "control": control, "candidate": candidate,
              "aggregate": {"p50_improvement_percent": p50_gain,
                            "p95_improvement_percent": p95_gain,
                            "maximum_output_error": maximum_error,
                            "output_rmse": rmse},
              "acceptance": acceptance,
              "decision": ("ADVANCE_FUSED_METAL_MATVEC_TO_MODEL_INTEGRATION"
                           if all(acceptance.values()) else "STOP_FUSED_METAL_MATVEC_V1"),
              "claim_boundary": ("One real layer-16 eight-expert decode route with synthetic "
                                 "activation. This changed kernel is not bit-exact and is separate "
                                 "from the exact INT8 track; full-model quality is not established.")}
    report["report_sha256"] = _canonical_sha256(report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output_path), "decision": report["decision"],
                      "control": control, "candidate": candidate,
                      "aggregate": report["aggregate"], "acceptance": acceptance,
                      "report_sha256": report["report_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
