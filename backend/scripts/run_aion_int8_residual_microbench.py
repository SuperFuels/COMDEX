#!/usr/bin/env python3
"""Test sparse FP16 residual shelves over native INT8 Granite experts."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import time
from typing import Any

from safetensors.torch import load_file
import torch
import torch.nn.functional as functional

from backend.scripts.run_aion_int8pack_expert_microbench import (
    _fp16_forward, _int8_forward, _p95, _quantize_rows,
)
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def _residual_shelf(weight: torch.Tensor, packed: torch.Tensor, scale: torch.Tensor,
                    fraction: float) -> tuple[torch.Tensor, torch.Tensor]:
    reconstructed = packed.float() * scale.float()[:, None]
    residual = weight.float() - reconstructed
    column_count = max(1, math.ceil(weight.shape[1] * fraction))
    indexes = residual.square().sum(dim=0).topk(column_count).indices.sort().values
    return indexes.to(torch.int64), residual[:, indexes].to(torch.float16).contiguous()


def _residual_forward(value: torch.Tensor, weights: list[tuple[torch.Tensor, ...]],
                      gates: torch.Tensor) -> torch.Tensor:
    outputs = []
    for (input_q, input_scale, output_q, output_scale,
         input_indexes, input_residual, output_indexes, output_residual) in weights:
        hidden = torch._weight_int8pack_mm(value, input_q, input_scale)
        hidden = hidden + functional.linear(value.index_select(-1, input_indexes), input_residual)
        gate, projected = hidden.chunk(2, dim=-1)
        activated = functional.silu(gate) * projected
        output = torch._weight_int8pack_mm(activated, output_q, output_scale)
        output = output + functional.linear(
            activated.index_select(-1, output_indexes), output_residual,
        )
        outputs.append(output)
    result = outputs[0] * gates[0]
    for index in range(1, len(outputs)):
        result = result + outputs[index] * gates[index]
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--shard-manifest", type=Path, required=True)
    parser.add_argument("--route-observation", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=16)
    parser.add_argument("--residual-fraction", type=float, default=0.03)
    parser.add_argument("--samples", type=int, default=200)
    parser.add_argument("--warmups", type=int, default=12)
    parser.add_argument("--seed", type=int, default=80920261)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {"shard_manifest": args.shard_manifest.resolve(),
             "route_observation": args.route_observation.resolve()}
    output = args.output.resolve()
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("all inputs and evidence must remain on external storage")
    if output.exists() or not 0 < args.residual_fraction < 0.1:
        raise SystemExit("refusing overwrite or invalid residual fraction")
    manifest = json.loads(paths["shard_manifest"].read_text())
    observation = json.loads(paths["route_observation"].read_text())
    layer_entry = manifest["layers"][args.layer]
    index_path = Path(layer_entry["index_path"]).resolve()
    if _sha256(index_path) != layer_entry["index_sha256"]:
        raise RuntimeError("layer index integrity failed")
    index = json.loads(index_path.read_text())
    by_expert = {int(item["expert"]): item for item in index["experts"]}
    route = tuple(int(value) for value in
                  observation["route_batches_by_layer"][args.layer][-1][-1])
    fp16_cpu, int8_cpu, residual_cpu = [], [], []
    source_hashes = {}
    for expert in route:
        entry = by_expert[expert]
        path = Path(entry["path"]).resolve()
        if root not in path.parents or _sha256(path) != entry["sha256"]:
            raise RuntimeError(f"expert integrity failed: {expert}")
        tensors = load_file(path, device="cpu")
        input_weight = tensors["input_linear.weight"].to(torch.float16).contiguous()
        output_weight = tensors["output_linear.weight"].to(torch.float16).contiguous()
        input_q, input_scale = _quantize_rows(input_weight)
        output_q, output_scale = _quantize_rows(output_weight)
        input_indexes, input_residual = _residual_shelf(
            input_weight, input_q, input_scale, args.residual_fraction,
        )
        output_indexes, output_residual = _residual_shelf(
            output_weight, output_q, output_scale, args.residual_fraction,
        )
        fp16_cpu.append((input_weight, output_weight))
        int8_cpu.append((input_q, input_scale, output_q, output_scale))
        residual_cpu.append((input_q, input_scale, output_q, output_scale,
                             input_indexes, input_residual,
                             output_indexes, output_residual))
        source_hashes[str(expert)] = entry["sha256"]
    fp16 = [tuple(t.to("mps") for t in group) for group in fp16_cpu]
    int8 = [tuple(t.to("mps") for t in group) for group in int8_cpu]
    residual = [tuple(t.to("mps") for t in group) for group in residual_cpu]
    generator = torch.Generator().manual_seed(args.seed)
    value = torch.randn((1, 1536), generator=generator, dtype=torch.float16).to("mps")
    gates = torch.rand((8,), generator=generator, dtype=torch.float16).to("mps")
    gates = gates / gates.sum()
    conditions = ("fp16", "int8", "int8_residual")
    functions = {"fp16": lambda: _fp16_forward(value, fp16, gates),
                 "int8": lambda: _int8_forward(value, int8, gates),
                 "int8_residual": lambda: _residual_forward(value, residual, gates)}
    for _ in range(args.warmups):
        for condition in conditions:
            functions[condition]()
    torch.mps.synchronize()
    trials = []
    outputs = {}
    for sample in range(args.samples):
        offset = sample % 3
        order = conditions[offset:] + conditions[:offset]
        for sequence, condition in enumerate(order):
            started = time.perf_counter()
            result = functions[condition]()
            torch.mps.synchronize()
            trials.append({"sample": sample, "sequence": sequence,
                           "condition": condition, "seconds": time.perf_counter() - started})
            outputs[condition] = result.detach().float().cpu()
    aggregate = {}
    for condition in conditions:
        values = [trial["seconds"] for trial in trials if trial["condition"] == condition]
        aggregate[condition] = {"p50_seconds": statistics.median(values),
                                "p95_seconds_nearest_rank": _p95(values)}
    fp16_bytes = sum(t.numel() * t.element_size() for group in fp16_cpu for t in group)
    int8_bytes = sum(t.numel() * t.element_size() for group in int8_cpu for t in group)
    residual_bytes = sum(t.numel() * t.element_size() for group in residual_cpu for t in group)
    plain_error = float((outputs["int8"] - outputs["fp16"]).abs().max())
    residual_error = float((outputs["int8_residual"] - outputs["fp16"]).abs().max())
    projected_gib = residual_bytes / len(route) * 1280 / 1024**3
    residual_slowdown = 100 * (aggregate["int8_residual"]["p50_seconds"] /
                               aggregate["int8"]["p50_seconds"] - 1)
    error_reduction = 100 * (1 - residual_error / plain_error)
    acceptance = {"projected_library_within_3_gib": projected_gib <= 3,
                  "maximum_error_reduced_at_least_40_percent": error_reduction >= 40,
                  "resident_slowdown_vs_plain_int8_at_most_15_percent": residual_slowdown <= 15}
    report = {
        "schema_version": "aion.int8_residual_microbench.v1",
        "paths": {name: str(path) for name, path in paths.items()},
        "hashes": {name: _sha256(path) for name, path in paths.items()},
        "layer": args.layer, "route": list(route), "source_hashes": source_hashes,
        "samples": args.samples, "warmups": args.warmups,
        "residual_fraction": args.residual_fraction,
        "bytes": {"fp16_route": fp16_bytes, "plain_int8_route": int8_bytes,
                  "int8_residual_route": residual_bytes,
                  "projected_full_library_gibibytes": projected_gib},
        "timing": aggregate,
        "aggregate": {"plain_int8_maximum_error": plain_error,
                      "residual_maximum_error": residual_error,
                      "maximum_error_reduction_percent": error_reduction,
                      "residual_p50_slowdown_percent_vs_plain_int8": residual_slowdown},
        "acceptance": acceptance,
        "decision": "ADVANCE_TO_CALIBRATION_GATE" if all(acceptance.values())
                    else "NOT_PROMOTED",
        "claim_boundary": (
            "One real eight-expert layer route with synthetic activation. The sparse residual "
            "selection uses weight error only; full-model quality and speed are unproven."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), "decision": report["decision"],
                      "bytes": report["bytes"], "aggregate": report["aggregate"],
                      "report_sha256": report["report_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
