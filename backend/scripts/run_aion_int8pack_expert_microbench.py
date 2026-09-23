#!/usr/bin/env python3
"""Benchmark native Metal INT8-packed execution on one real Granite route."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import time
from typing import Any

from safetensors.torch import load_file
import torch
import torch.nn.functional as functional

from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)]


def _quantize_rows(weight: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Symmetric per-output-channel INT8 weight-only quantization."""
    source = weight.float()
    scales = source.abs().amax(dim=1).clamp_min(1e-12) / 127.0
    packed = torch.round(source / scales[:, None]).clamp(-127, 127).to(torch.int8)
    return packed.contiguous(), scales.to(torch.float16).contiguous()


def _fp16_forward(value: torch.Tensor, weights: list[tuple[torch.Tensor, torch.Tensor]],
                  gates: torch.Tensor) -> torch.Tensor:
    outputs = []
    for input_weight, output_weight in weights:
        hidden = functional.linear(value, input_weight)
        gate, projected = hidden.chunk(2, dim=-1)
        outputs.append(functional.linear(functional.silu(gate) * projected, output_weight))
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


def _summarize(trials: list[dict[str, Any]], condition: str) -> dict[str, float]:
    group = [trial for trial in trials if trial["condition"] == condition]
    seconds = [trial["seconds"] for trial in group]
    return {
        "p50_seconds": statistics.median(seconds),
        "p95_seconds_nearest_rank": _p95(seconds),
        "mean_seconds": statistics.mean(seconds),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--shard-manifest", type=Path, required=True)
    parser.add_argument("--route-observation", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=16)
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--warmups", type=int, default=8)
    parser.add_argument("--seed", type=int, default=8092026)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {"shard_manifest": args.shard_manifest.resolve(),
             "route_observation": args.route_observation.resolve()}
    output = args.output.resolve()
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("all model inputs and evidence must remain on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    if not torch.backends.mps.is_available() or not hasattr(torch, "_weight_int8pack_mm"):
        raise SystemExit("native Metal weight-only INT8 operation is required")

    manifest = json.loads(paths["shard_manifest"].read_text())
    observation = json.loads(paths["route_observation"].read_text())
    if not all(manifest["integrity"].values()):
        raise RuntimeError("expert-shard integrity gate failed")
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
    packed_cpu = []
    expert_hashes = {}
    for expert in route:
        entry = by_expert[expert]
        path = Path(entry["path"]).resolve()
        if root not in path.parents or _sha256(path) != entry["sha256"]:
            raise RuntimeError(f"expert integrity failed: {expert}")
        tensors = load_file(path, device="cpu")
        input_weight, output_weight = (tensors[name].to(torch.float16).contiguous()
                                       for name in ("input_linear.weight",
                                                    "output_linear.weight"))
        fp16_cpu.append((input_weight, output_weight))
        input_q, input_scale = _quantize_rows(input_weight)
        output_q, output_scale = _quantize_rows(output_weight)
        packed_cpu.append((input_q, input_scale, output_q, output_scale))
        expert_hashes[str(expert)] = entry["sha256"]

    fp16_bytes = sum(t.numel() * t.element_size() for pair in fp16_cpu for t in pair)
    packed_bytes = sum(t.numel() * t.element_size() for group in packed_cpu for t in group)
    fp16_mps = [(a.to("mps"), b.to("mps")) for a, b in fp16_cpu]
    packed_mps = [tuple(t.to("mps") for t in group) for group in packed_cpu]
    packed_blocks_cpu = [torch.cat((group[0].reshape(-1), group[2].reshape(-1)))
                         for group in packed_cpu]
    packed_scales_mps = [(group[1].to("mps"), group[3].to("mps"))
                         for group in packed_cpu]
    generator = torch.Generator().manual_seed(args.seed)
    value = torch.randn((1, fp16_cpu[0][0].shape[1]), generator=generator,
                        dtype=torch.float16).to("mps")
    gates = torch.rand((8,), generator=generator, dtype=torch.float16).to("mps")
    gates = gates / gates.sum()

    for _ in range(args.warmups):
        _fp16_forward(value, fp16_mps, gates)
        _int8_forward(value, packed_mps, gates)
    torch.mps.synchronize()

    trials = []
    outputs = {}
    conditions = ("fp16_resident", "int8pack_resident")
    for sample in range(args.samples):
        order = conditions if sample % 2 == 0 else tuple(reversed(conditions))
        for sequence, condition in enumerate(order):
            started = time.perf_counter()
            result = (_fp16_forward(value, fp16_mps, gates) if condition == "fp16_resident"
                      else _int8_forward(value, packed_mps, gates))
            torch.mps.synchronize()
            elapsed = time.perf_counter() - started
            outputs[condition] = result.detach().cpu()
            trials.append({"sample": sample, "sequence": sequence,
                           "condition": condition, "seconds": elapsed})

    # Fault-path comparison includes CPU-to-Metal placement and direct execution.
    fault_trials = []
    for sample in range(args.samples):
        order = conditions if sample % 2 == 0 else tuple(reversed(conditions))
        for sequence, condition in enumerate(order):
            started = time.perf_counter()
            if condition == "fp16_resident":
                placed = [(a.to("mps"), b.to("mps")) for a, b in fp16_cpu]
                result = _fp16_forward(value, placed, gates)
            else:
                placed = [tuple(t.to("mps") for t in group) for group in packed_cpu]
                result = _int8_forward(value, placed, gates)
            torch.mps.synchronize()
            elapsed = time.perf_counter() - started
            outputs[f"fault_{condition}"] = result.detach().cpu()
            fault_trials.append({"sample": sample, "sequence": sequence,
                                 "condition": condition, "seconds": elapsed})
            del placed

    block_fault_trials = []
    for sample in range(args.samples):
        order = ("fp16_fault", "int8_block_fault") if sample % 2 == 0 else (
            "int8_block_fault", "fp16_fault",
        )
        for sequence, condition in enumerate(order):
            started = time.perf_counter()
            if condition == "fp16_fault":
                placed_fp16 = [(a.to("mps"), b.to("mps")) for a, b in fp16_cpu]
                result = _fp16_forward(value, placed_fp16, gates)
                del placed_fp16
            else:
                placed_packed = []
                for block, source, scales in zip(
                    packed_blocks_cpu, packed_cpu, packed_scales_mps, strict=True,
                ):
                    input_count = source[0].numel()
                    block_mps = block.to("mps")
                    placed_packed.append((
                        block_mps[:input_count].view(source[0].shape), scales[0],
                        block_mps[input_count:].view(source[2].shape), scales[1],
                    ))
                result = _int8_forward(value, placed_packed, gates)
                del placed_packed
            torch.mps.synchronize()
            block_fault_trials.append({"sample": sample, "sequence": sequence,
                                       "condition": condition,
                                       "seconds": time.perf_counter() - started})

    resident = {condition: _summarize(trials, condition) for condition in conditions}
    fault = {condition: _summarize(fault_trials, condition) for condition in conditions}
    block_fault = {condition: _summarize(block_fault_trials, condition)
                   for condition in ("fp16_fault", "int8_block_fault")}
    reference = outputs["fp16_resident"].float()
    candidate = outputs["int8pack_resident"].float()
    max_error = float((candidate - reference).abs().max().item())
    mean_error = float((candidate - reference).abs().mean().item())
    resident_improvement = 100 * (1 - resident["int8pack_resident"]["p50_seconds"] /
                                  resident["fp16_resident"]["p50_seconds"])
    fault_improvement = 100 * (1 - fault["int8pack_resident"]["p50_seconds"] /
                               fault["fp16_resident"]["p50_seconds"])
    block_fault_improvement = 100 * (
        1 - block_fault["int8_block_fault"]["p50_seconds"] /
        block_fault["fp16_fault"]["p50_seconds"]
    )
    acceptance = {
        "packed_bytes_reduced_at_least_40_percent": packed_bytes <= fp16_bytes * 0.6,
        "resident_compute_improved_at_least_10_percent": resident_improvement >= 10,
        "glyph_block_fault_path_improved_at_least_10_percent": block_fault_improvement >= 10,
        "finite_output": bool(torch.isfinite(candidate).all().item()),
        "quality_requires_full_model_validation": True,
    }
    report = {
        "schema_version": "aion.int8pack_expert_microbench.v1",
        "paths": {name: str(path) for name, path in paths.items()},
        "hashes": {name: _sha256(path) for name, path in paths.items()},
        "layer": args.layer, "route": list(route), "expert_hashes": expert_hashes,
        "samples": args.samples, "warmups": args.warmups, "seed": args.seed,
        "torch_version": torch.__version__, "backend": "mps",
        "representation": {
            "control": "FP16",
            "candidate": "symmetric per-output-channel INT8 plus FP16 scales",
            "fp16_bytes": fp16_bytes, "int8pack_bytes": packed_bytes,
            "byte_reduction_percent": 100 * (1 - packed_bytes / fp16_bytes),
            "candidate_uses_native_weight_int8pack_mm_without_fp16_weight_materialization": True,
        },
        "resident": resident, "naive_fault_path": fault,
        "glyph_block_fault_path_with_resident_scales": block_fault,
        "aggregate": {"resident_p50_improvement_percent": resident_improvement,
                      "naive_fault_p50_improvement_percent": fault_improvement,
                      "glyph_block_fault_p50_improvement_percent": block_fault_improvement,
                      "maximum_layer_output_error": max_error,
                      "mean_layer_output_error": mean_error},
        "acceptance": acceptance,
        "decision": "ADVANCE_TO_FULL_MODEL_QUALITY_GATE" if all(acceptance.values())
                    else "NOT_PROMOTED",
        "claim_boundary": (
            "One real eight-expert Granite layer/decode-route microbenchmark. INT8 is a "
            "lossy, quality-gated representation and is not exact. Timing does not yet prove "
            "full-model token throughput or quality. Quantization is offline and excluded."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), "decision": report["decision"],
                      "representation": report["representation"],
                      "aggregate": report["aggregate"],
                      "report_sha256": report["report_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
