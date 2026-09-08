#!/usr/bin/env python3
"""Sweep native Metal INT4 group sizes on one real Granite expert route."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import time
from typing import Any

from safetensors.torch import load_file
import torch
import torch.nn.functional as functional

from backend.scripts.run_aion_int8pack_expert_microbench import (
    _canonical_sha256, _fp16_forward, _p95, _quantize_rows,
)
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256


def _quantize_int4_groups(weight: torch.Tensor, group_size: int, clip_ratio: float = 1.0
                          ) -> tuple[torch.Tensor, torch.Tensor]:
    """Affine UINT4 groups in the format consumed by Metal tinygemm."""
    rows, columns = weight.shape
    if columns % group_size or columns % 2:
        raise ValueError("weight width must be divisible by group size and two")
    grouped = weight.float().reshape(rows, columns // group_size, group_size)
    if not 0 < clip_ratio <= 1:
        raise ValueError("clip ratio must be in (0, 1]")
    maximum = grouped.amax(dim=2, keepdim=True)
    minimum = grouped.amin(dim=2, keepdim=True)
    midpoint = (maximum + minimum) / 2
    half_range = (maximum - minimum) * (clip_ratio / 2)
    maximum = midpoint + half_range
    minimum = midpoint - half_range
    scales = (maximum - minimum).clamp_min(1e-6) / 15.0
    zeros = minimum + scales * 8.0
    quantized = ((grouped - minimum) / scales).round().clamp(0, 15)
    quantized = quantized.to(torch.uint8).reshape(rows, columns)
    # Metal expects the earlier K value in the high nibble.
    nibbles = ((quantized[:, ::2] << 4) | quantized[:, 1::2]).contiguous()
    scales_and_zeros = torch.stack(
        (scales.squeeze(-1), zeros.squeeze(-1)), dim=-1,
    ).transpose(0, 1).to(torch.float16).contiguous()
    return nibbles, scales_and_zeros


def _dequantize_int4_groups(nibbles: torch.Tensor, scales_and_zeros: torch.Tensor,
                            group_size: int) -> torch.Tensor:
    """Reference unpacker used only by focused tests."""
    values = torch.empty((nibbles.shape[0], nibbles.shape[1] * 2), dtype=torch.float32)
    values[:, ::2] = (nibbles >> 4).float()
    values[:, 1::2] = (nibbles & 15).float()
    scales = scales_and_zeros[..., 0].transpose(0, 1).float()
    zeros = scales_and_zeros[..., 1].transpose(0, 1).float()
    return ((values.reshape(values.shape[0], -1, group_size) - 8.0) * scales[..., None]
            + zeros[..., None]).reshape(values.shape)


def _pack_for_metal(nibbles: torch.Tensor, scales_and_zeros: torch.Tensor,
                    inner_k_tiles: int = 8) -> tuple[torch.Tensor, torch.Tensor]:
    packed = torch._convert_weight_to_int4pack(nibbles.to("mps"), inner_k_tiles)
    return packed, scales_and_zeros.to("mps")


def _int4_forward(value: torch.Tensor,
                  weights: list[tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]],
                  gates: torch.Tensor, group_size: int) -> torch.Tensor:
    outputs = []
    for input_packed, input_qparams, output_packed, output_qparams in weights:
        hidden = torch._weight_int4pack_mm(value, input_packed, group_size, input_qparams)
        gate, projected = hidden.chunk(2, dim=-1)
        outputs.append(torch._weight_int4pack_mm(
            functional.silu(gate) * projected, output_packed, group_size, output_qparams,
        ))
    result = outputs[0] * gates[0]
    for index in range(1, len(outputs)):
        result = result + outputs[index] * gates[index]
    return result


def _int8_forward(value: torch.Tensor,
                  weights: list[tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]],
                  gates: torch.Tensor) -> torch.Tensor:
    outputs = []
    for input_packed, input_scale, output_packed, output_scale in weights:
        hidden = torch._weight_int8pack_mm(value, input_packed, input_scale)
        gate, projected = hidden.chunk(2, dim=-1)
        outputs.append(torch._weight_int8pack_mm(
            functional.silu(gate) * projected, output_packed, output_scale,
        ))
    result = outputs[0] * gates[0]
    for index in range(1, len(outputs)):
        result = result + outputs[index] * gates[index]
    return result


def _summary(values: list[float]) -> dict[str, float]:
    return {"p50_seconds": statistics.median(values),
            "p95_seconds_nearest_rank": _p95(values),
            "mean_seconds": statistics.mean(values)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--shard-manifest", type=Path, required=True)
    parser.add_argument("--route-observation", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=16)
    parser.add_argument("--group-sizes", type=int, nargs="+", default=[32, 64, 128])
    parser.add_argument("--samples", type=int, default=200)
    parser.add_argument("--warmups", type=int, default=8)
    parser.add_argument("--seed", type=int, default=8090326)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    inputs = {"shard_manifest": args.shard_manifest.resolve(),
              "route_observation": args.route_observation.resolve()}
    output = args.output.resolve()
    if any(root not in path.parents for path in (*inputs.values(), output)):
        raise SystemExit("all model inputs and evidence must remain on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    if not torch.backends.mps.is_available():
        raise SystemExit("Metal is required")

    manifest = json.loads(inputs["shard_manifest"].read_text())
    observation = json.loads(inputs["route_observation"].read_text())
    layer_entry = manifest["layers"][args.layer]
    index_path = Path(layer_entry["index_path"]).resolve()
    if root not in index_path.parents or _sha256(index_path) != layer_entry["index_sha256"]:
        raise RuntimeError("layer index integrity gate failed")
    index = json.loads(index_path.read_text())
    by_expert = {int(item["expert"]): item for item in index["experts"]}
    route = tuple(int(value) for value in
                  observation["route_batches_by_layer"][args.layer][-1][-1])
    if len(route) != 8 or len(set(route)) != 8:
        raise RuntimeError(f"expected a real eight-expert route, got {route}")

    fp16_cpu = []
    for expert in route:
        entry = by_expert[expert]
        path = Path(entry["path"]).resolve()
        if root not in path.parents or _sha256(path) != entry["sha256"]:
            raise RuntimeError(f"expert integrity failed: {expert}")
        tensors = load_file(path, device="cpu")
        fp16_cpu.append(tuple(tensors[name].to(torch.float16).contiguous()
                              for name in ("input_linear.weight", "output_linear.weight")))
    fp16_bytes = sum(t.numel() * t.element_size() for pair in fp16_cpu for t in pair)
    fp16_mps = [(a.to("mps"), b.to("mps")) for a, b in fp16_cpu]
    int8_cpu = []
    for first, second in fp16_cpu:
        first_q, first_s = _quantize_rows(first)
        second_q, second_s = _quantize_rows(second)
        int8_cpu.append((first_q, first_s, second_q, second_s))
    int8_mps = [tuple(item.to("mps") for item in group) for group in int8_cpu]

    int4_cpu: dict[int, list[tuple[torch.Tensor, ...]]] = {}
    int4_mps: dict[int, list[tuple[torch.Tensor, ...]]] = {}
    for group_size in args.group_sizes:
        groups = []
        placed = []
        for first, second in fp16_cpu:
            first_n, first_q = _quantize_int4_groups(first, group_size)
            second_n, second_q = _quantize_int4_groups(second, group_size)
            groups.append((first_n, first_q, second_n, second_q))
            first_p, first_q_mps = _pack_for_metal(first_n, first_q)
            second_p, second_q_mps = _pack_for_metal(second_n, second_q)
            placed.append((first_p, first_q_mps, second_p, second_q_mps))
        int4_cpu[group_size] = groups
        int4_mps[group_size] = placed

    generator = torch.Generator().manual_seed(args.seed)
    value = torch.randn((1, fp16_cpu[0][0].shape[1]), generator=generator,
                        dtype=torch.float16).to("mps")
    gates = torch.rand((8,), generator=generator, dtype=torch.float16).to("mps")
    gates = gates / gates.sum()
    names = ["fp16", "int8"] + [f"int4_g{size}" for size in args.group_sizes]

    def calculate(name: str) -> torch.Tensor:
        if name == "fp16":
            return _fp16_forward(value, fp16_mps, gates)
        if name == "int8":
            return _int8_forward(value, int8_mps, gates)
        size = int(name.split("g", 1)[1])
        return _int4_forward(value, int4_mps[size], gates, size)

    for _ in range(args.warmups):
        for name in names:
            calculate(name)
    torch.mps.synchronize()
    timings = {name: [] for name in names}
    outputs: dict[str, torch.Tensor] = {}
    for sample in range(args.samples):
        order = names if sample % 2 == 0 else list(reversed(names))
        for name in order:
            started = time.perf_counter()
            result = calculate(name)
            torch.mps.synchronize()
            timings[name].append(time.perf_counter() - started)
            outputs[name] = result.detach().cpu().float()

    reference = outputs["fp16"]
    conditions: dict[str, Any] = {}
    for name in names:
        if name == "fp16":
            logical_bytes = fp16_bytes
        elif name == "int8":
            logical_bytes = sum(t.numel() * t.element_size()
                                for group in int8_cpu for t in group)
        else:
            size = int(name.split("g", 1)[1])
            logical_bytes = sum(t.numel() * t.element_size()
                                for group in int4_cpu[size] for t in group)
        error = (outputs[name] - reference).abs()
        timing = _summary(timings[name])
        conditions[name] = {**timing, "logical_bytes": logical_bytes,
                            "byte_reduction_percent": 100 * (1 - logical_bytes / fp16_bytes),
                            "p50_compute_improvement_vs_fp16_percent": 100 * (
                                1 - timing["p50_seconds"] / _summary(timings["fp16"])["p50_seconds"]),
                            "maximum_layer_output_error": float(error.max()),
                            "mean_layer_output_error": float(error.mean())}
    int8_error = conditions["int8"]["maximum_layer_output_error"]
    viable = [name for name in names if name.startswith("int4_")
              and conditions[name]["p50_compute_improvement_vs_fp16_percent"] >= 10
              and conditions[name]["maximum_layer_output_error"] <= int8_error * 4]
    report = {"schema_version": "aion.int4pack_expert_sweep.v1",
              "paths": {name: str(path) for name, path in inputs.items()},
              "hashes": {name: _sha256(path) for name, path in inputs.items()},
              "layer": args.layer, "route": list(route), "samples": args.samples,
              "warmups": args.warmups, "seed": args.seed, "backend": "mps",
              "group_sizes": args.group_sizes, "conditions": conditions,
              "acceptance": {"requires_at_least_10_percent_compute_improvement": True,
                             "maximum_error_must_be_at_most_four_times_int8": True,
                             "viable_conditions": viable},
              "decision": "ADVANCE_BEST_INT4_TO_MODEL_GATE" if viable else "STOP_INT4_DIRECT_PATH",
              "claim_boundary": ("One real eight-expert Granite layer/decode route. INT4 and INT8 "
                                 "are lossy quality-gated representations. Quantization and initial "
                                 "Metal packing are offline and excluded; full-model speed and "
                                 "semantic quality are not established.")}
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), "decision": report["decision"],
                      "conditions": conditions, "report_sha256": report["report_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
