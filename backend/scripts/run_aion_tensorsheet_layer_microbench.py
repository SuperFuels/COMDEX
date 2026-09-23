#!/usr/bin/env python3
"""Test CPU/Metal TensorSheet placement on one real Granite MoE decode route."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
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


CONDITIONS = ("metal_8", "cpu_8", "hybrid_cpu_2", "hybrid_cpu_4")


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)]


def _expert_forward(
    value: torch.Tensor,
    weights: tuple[torch.Tensor, torch.Tensor],
) -> torch.Tensor:
    hidden = functional.linear(value, weights[0])
    gate, projected = hidden.chunk(2, dim=-1)
    return functional.linear(functional.silu(gate) * projected, weights[1])


def _run_cpu_group(
    value: torch.Tensor,
    weights: list[tuple[torch.Tensor, torch.Tensor]],
    indexes: tuple[int, ...],
) -> dict[int, torch.Tensor]:
    return {index: _expert_forward(value, weights[index]) for index in indexes}


def _execute(
    condition: str,
    value_cpu: torch.Tensor,
    value_mps: torch.Tensor,
    gates_mps: torch.Tensor,
    cpu_weights: list[tuple[torch.Tensor, torch.Tensor]],
    mps_weights: list[tuple[torch.Tensor, torch.Tensor]],
    executor: ThreadPoolExecutor,
) -> tuple[torch.Tensor, dict[str, float]]:
    cpu_count = {
        "metal_8": 0, "cpu_8": 8, "hybrid_cpu_2": 2, "hybrid_cpu_4": 4,
    }[condition]
    cpu_indexes = tuple(range(cpu_count))
    metal_indexes = tuple(range(cpu_count, 8))
    stage = {"cpu_compute": 0.0, "metal_compute": 0.0, "result_transfer_and_reduce": 0.0}

    future = None
    cpu_started = time.perf_counter()
    if cpu_indexes:
        future = executor.submit(_run_cpu_group, value_cpu, cpu_weights, cpu_indexes)

    metal_started = time.perf_counter()
    outputs = {
        index: _expert_forward(value_mps, mps_weights[index])
        for index in metal_indexes
    }
    if metal_indexes:
        torch.mps.synchronize()
    stage["metal_compute"] = time.perf_counter() - metal_started

    if future is not None:
        cpu_outputs = future.result()
        stage["cpu_compute"] = time.perf_counter() - cpu_started
    else:
        cpu_outputs = {}

    reduce_started = time.perf_counter()
    for index, output in cpu_outputs.items():
        outputs[index] = output.to("mps")
    combined = outputs[0] * gates_mps[0]
    for index in range(1, 8):
        combined = combined + outputs[index] * gates_mps[index]
    torch.mps.synchronize()
    stage["result_transfer_and_reduce"] = time.perf_counter() - reduce_started
    return combined.detach().cpu(), stage


def _execute_faulted(
    condition: str,
    value_cpu: torch.Tensor,
    value_mps: torch.Tensor,
    gates_mps: torch.Tensor,
    cpu_weights: list[tuple[torch.Tensor, torch.Tensor]],
    executor: ThreadPoolExecutor,
) -> tuple[torch.Tensor, dict[str, float]]:
    """Execute after a CPU-resident miss, including required Metal placement."""
    cpu_count = {
        "metal_8": 0, "cpu_8": 8, "hybrid_cpu_2": 2, "hybrid_cpu_4": 4,
    }[condition]
    cpu_indexes = tuple(range(cpu_count))
    metal_indexes = tuple(range(cpu_count, 8))
    stage = {
        "cpu_compute": 0.0, "metal_weight_placement": 0.0,
        "metal_compute": 0.0, "result_transfer_and_reduce": 0.0,
    }
    total_started = time.perf_counter()
    future = (
        executor.submit(_run_cpu_group, value_cpu, cpu_weights, cpu_indexes)
        if cpu_indexes else None
    )
    cpu_started = total_started

    placement_started = time.perf_counter()
    placed = {
        index: (
            cpu_weights[index][0].to("mps"), cpu_weights[index][1].to("mps")
        )
        for index in metal_indexes
    }
    if metal_indexes:
        torch.mps.synchronize()
    stage["metal_weight_placement"] = time.perf_counter() - placement_started

    metal_started = time.perf_counter()
    outputs = {
        index: _expert_forward(value_mps, placed[index]) for index in metal_indexes
    }
    if metal_indexes:
        torch.mps.synchronize()
    stage["metal_compute"] = time.perf_counter() - metal_started
    if future is not None:
        cpu_outputs = future.result()
        stage["cpu_compute"] = time.perf_counter() - cpu_started
    else:
        cpu_outputs = {}

    reduce_started = time.perf_counter()
    for index, result in cpu_outputs.items():
        outputs[index] = result.to("mps")
    combined = outputs[0] * gates_mps[0]
    for index in range(1, 8):
        combined = combined + outputs[index] * gates_mps[index]
    torch.mps.synchronize()
    stage["result_transfer_and_reduce"] = time.perf_counter() - reduce_started
    return combined.detach().cpu(), stage


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--shard-manifest", type=Path, required=True)
    parser.add_argument("--route-observation", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=16)
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--warmups", type=int, default=8)
    parser.add_argument("--seed", type=int, default=7092026)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {
        "shard_manifest": args.shard_manifest.resolve(),
        "route_observation": args.route_observation.resolve(),
    }
    output = args.output.resolve()
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("all model inputs and evidence must remain on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    if not 0 <= args.layer < 32 or args.samples < 2 or args.warmups < 1:
        raise SystemExit("invalid layer, sample or warmup count")
    if not torch.backends.mps.is_available():
        raise SystemExit("Apple Metal/MPS is required")

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
    route = tuple(
        int(value)
        for value in observation["route_batches_by_layer"][args.layer][-1][-1]
    )
    if len(route) != 8 or len(set(route)) != 8:
        raise RuntimeError(f"expected one real eight-expert decode route, got {route}")

    load_started = time.perf_counter()
    cpu_weights = []
    logical_bytes = 0
    expert_hashes = {}
    for expert in route:
        entry = by_expert[expert]
        path = Path(entry["path"]).resolve()
        if root not in path.parents or _sha256(path) != entry["sha256"]:
            raise RuntimeError(f"expert integrity failed: {expert}")
        tensors = load_file(path, device="cpu")
        cpu_weights.append(tuple(
            tensors[name].to(torch.float16)
            for name in ("input_linear.weight", "output_linear.weight")
        ))
        logical_bytes += int(entry["bytes"])
        expert_hashes[str(expert)] = entry["sha256"]
    cpu_load_and_cast_seconds = time.perf_counter() - load_started

    transfer_started = time.perf_counter()
    mps_weights = [
        (input_weight.to("mps"), output_weight.to("mps"))
        for input_weight, output_weight in cpu_weights
    ]
    torch.mps.synchronize()
    initial_metal_transfer_seconds = time.perf_counter() - transfer_started
    generator = torch.Generator(device="cpu").manual_seed(args.seed)
    value_cpu = torch.randn((1, 1536), generator=generator, dtype=torch.float16)
    gates_cpu = torch.rand((8,), generator=generator, dtype=torch.float16)
    gates_cpu = gates_cpu / gates_cpu.sum()
    value_mps, gates_mps = value_cpu.to("mps"), gates_cpu.to("mps")

    trials = []
    fault_trials = []
    outputs: dict[str, torch.Tensor] = {}
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="aion-tensorsheet-cpu") as executor:
        for condition in CONDITIONS:
            for _ in range(args.warmups):
                _execute(
                    condition, value_cpu, value_mps, gates_mps,
                    cpu_weights, mps_weights, executor,
                )
        for sample in range(args.samples):
            # Rotate the order every sample to balance drift and thermal effects.
            offset = sample % len(CONDITIONS)
            order = CONDITIONS[offset:] + CONDITIONS[:offset]
            for sequence, condition in enumerate(order):
                started = time.perf_counter()
                observed, stages = _execute(
                    condition, value_cpu, value_mps, gates_mps,
                    cpu_weights, mps_weights, executor,
                )
                elapsed = time.perf_counter() - started
                outputs[condition] = observed
                trials.append({
                    "sample": sample, "sequence": sequence, "condition": condition,
                    "seconds": elapsed, "stage_seconds": stages,
                })
        for sample in range(args.samples):
            offset = sample % len(CONDITIONS)
            order = CONDITIONS[offset:] + CONDITIONS[:offset]
            for sequence, condition in enumerate(order):
                started = time.perf_counter()
                observed, stages = _execute_faulted(
                    condition, value_cpu, value_mps, gates_mps,
                    cpu_weights, executor,
                )
                elapsed = time.perf_counter() - started
                outputs[f"faulted_{condition}"] = observed
                fault_trials.append({
                    "sample": sample, "sequence": sequence, "condition": condition,
                    "seconds": elapsed, "stage_seconds": stages,
                })

    reference = outputs["metal_8"]
    aggregates = {}
    for condition in CONDITIONS:
        group = [trial for trial in trials if trial["condition"] == condition]
        seconds = [trial["seconds"] for trial in group]
        difference = (outputs[condition].float() - reference.float()).abs()
        aggregates[condition] = {
            "samples": len(group),
            "p50_seconds": statistics.median(seconds),
            "p95_seconds_nearest_rank": _p95(seconds),
            "relative_to_metal_p50_percent": 100 * (
                statistics.median(seconds)
                / statistics.median(
                    trial["seconds"] for trial in trials
                    if trial["condition"] == "metal_8"
                ) - 1
            ),
            "output_bit_exact_to_metal": torch.equal(outputs[condition], reference),
            "maximum_absolute_error_to_metal": float(difference.max().item()),
            "nonzero_elements_to_metal": int(torch.count_nonzero(difference).item()),
            "median_stage_seconds": {
                stage: statistics.median(
                    trial["stage_seconds"][stage] for trial in group
                )
                for stage in (
                    "cpu_compute", "metal_compute", "result_transfer_and_reduce"
                )
            },
        }

    fastest = min(CONDITIONS, key=lambda name: aggregates[name]["p50_seconds"])
    exact_candidates = [
        name for name in CONDITIONS
        if name != "metal_8" and aggregates[name]["output_bit_exact_to_metal"]
    ]
    fault_aggregates = {}
    for condition in CONDITIONS:
        group = [trial for trial in fault_trials if trial["condition"] == condition]
        seconds = [trial["seconds"] for trial in group]
        difference = (
            outputs[f"faulted_{condition}"].float() - reference.float()
        ).abs()
        fault_aggregates[condition] = {
            "samples": len(group),
            "p50_seconds": statistics.median(seconds),
            "p95_seconds_nearest_rank": _p95(seconds),
            "relative_to_faulted_metal_p50_percent": 100 * (
                statistics.median(seconds)
                / statistics.median(
                    trial["seconds"] for trial in fault_trials
                    if trial["condition"] == "metal_8"
                ) - 1
            ),
            "output_bit_exact_to_resident_metal": torch.equal(
                outputs[f"faulted_{condition}"], reference
            ),
            "maximum_absolute_error_to_resident_metal": float(difference.max().item()),
            "nonzero_elements_to_resident_metal": int(torch.count_nonzero(difference).item()),
            "median_stage_seconds": {
                stage: statistics.median(
                    trial["stage_seconds"][stage] for trial in group
                )
                for stage in (
                    "cpu_compute", "metal_weight_placement", "metal_compute",
                    "result_transfer_and_reduce",
                )
            },
        }
    fastest_fault = min(
        CONDITIONS, key=lambda name: fault_aggregates[name]["p50_seconds"]
    )
    acceptance = {
        "real_sd_backed_experts_and_route": True,
        "all_artifact_hashes_verified": True,
        "balanced_order_and_equal_samples": all(
            aggregates[name]["samples"] == args.samples for name in CONDITIONS
        ),
        "an_assisted_candidate_is_faster_than_metal": fastest != "metal_8",
        "a_faster_assisted_candidate_is_bit_exact": any(
            aggregates[name]["p50_seconds"] < aggregates["metal_8"]["p50_seconds"]
            for name in exact_candidates
        ),
        "a_cpu_assisted_fault_path_is_faster_than_metal": (
            fastest_fault != "metal_8"
        ),
        "fastest_fault_path_is_bit_exact": fault_aggregates[fastest_fault][
            "output_bit_exact_to_resident_metal"
        ],
    }
    report = {
        "schema_version": "aion.tensorsheet_layer_microbench.v1",
        "paths": {key: str(value) for key, value in paths.items()},
        "hashes": {
            "shard_manifest": _sha256(paths["shard_manifest"]),
            "route_observation": _sha256(paths["route_observation"]),
            "layer_index": _sha256(index_path), "experts": expert_hashes,
        },
        "method": {
            "layer": args.layer, "decode_route": route, "samples": args.samples,
            "warmups_per_condition": args.warmups, "seed": args.seed,
            "dtype": "float16", "input_shape": [1, 1536],
            "logical_expert_bytes": logical_bytes,
            "cpu_load_and_cast_seconds": cpu_load_and_cast_seconds,
            "initial_metal_transfer_seconds": initial_metal_transfer_seconds,
            "cpu_worker_threads": 1,
            "condition_order_rotated_each_sample": True,
            "weights_resident_during_timed_compute": True,
        },
        "aggregates": aggregates,
        "cpu_resident_fault_aggregates": fault_aggregates,
        "fastest_condition": fastest,
        "fastest_cpu_resident_fault_condition": fastest_fault,
        "acceptance": acceptance,
        "result": "PROMOTABLE_EXACT" if all(acceptance.values()) else "QUALITY_GATED_ONLY",
        "claim_boundary": (
            "Single-layer decode-sized kernel experiment using a real recorded route and "
            "verified SD-backed weights. Synthetic activation; no full-token or full-model "
            "speed claim. The fault-path comparison starts from CPU-resident weights and "
            "isolates Metal placement; it does not include SD read/decode. CPU or hybrid "
            "output must be bit exact to enter the exact track."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "output": str(output), "result": report["result"],
        "fastest_condition": fastest, "aggregates": aggregates,
        "fastest_cpu_resident_fault_condition": fastest_fault,
        "cpu_resident_fault_aggregates": fault_aggregates,
        "acceptance": acceptance, "report_sha256": report["report_sha256"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
