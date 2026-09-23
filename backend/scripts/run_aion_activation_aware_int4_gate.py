#!/usr/bin/env python3
"""Activation-aware INT4 mechanism gate on real Granite layer activations."""

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
from transformers import AutoModelForCausalLM, AutoTokenizer

from backend.scripts.run_aion_int4pack_expert_sweep import (
    _dequantize_int4_groups, _pack_for_metal, _p95, _quantize_int4_groups,
)
from backend.scripts.run_aion_int8pack_expert_microbench import _quantize_rows
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256
from backend.scripts.run_aion_storage_first_multiprompt import PROMPTS, _chat_tokens


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def _weighted_error(weight: torch.Tensor, nibbles: torch.Tensor,
                    qparams: torch.Tensor, group_size: int,
                    activation_energy: torch.Tensor) -> float:
    restored = _dequantize_int4_groups(nibbles, qparams, group_size)
    error = (restored - weight.float()).square()
    energy = activation_energy.float().clamp_min(1e-12)
    energy = energy / energy.mean()
    return float((error * energy[None, :]).mean())


def _choose_clip(weight: torch.Tensor, activation_energy: torch.Tensor,
                 group_size: int, ratios: tuple[float, ...]
                 ) -> tuple[torch.Tensor, torch.Tensor, float, dict[str, float]]:
    candidates = {}
    tensors = {}
    for ratio in ratios:
        nibbles, qparams = _quantize_int4_groups(weight, group_size, ratio)
        candidates[str(ratio)] = _weighted_error(
            weight, nibbles, qparams, group_size, activation_energy,
        )
        tensors[ratio] = (nibbles, qparams)
    selected = min(ratios, key=lambda value: candidates[str(value)])
    return *tensors[selected], selected, candidates


def _routed_inputs(source_moe: Any, layer_input: torch.Tensor
                   ) -> tuple[list[torch.Tensor], torch.Tensor, torch.Tensor]:
    batch, length, embedding = layer_input.shape
    flattened = layer_input.reshape(-1, embedding)
    _, batch_index, batch_gates, expert_size, _ = source_moe.router(flattened)
    raw_sizes = (expert_size.detach().cpu().tolist()
                 if isinstance(expert_size, torch.Tensor) else expert_size)
    sizes = [int(value) for value in raw_sizes]
    return list(flattened[batch_index].split(sizes, dim=0)), batch_index, batch_gates


def _energy(values: list[torch.Tensor], width: int) -> torch.Tensor:
    populated = [value.float().cpu() for value in values if value.numel()]
    if not populated:
        return torch.ones(width)
    merged = torch.cat(populated, dim=0)
    return merged.square().mean(dim=0).clamp_min(1e-12)


def _build_activation_energies(source_moe: Any,
                               weights: list[tuple[torch.Tensor, torch.Tensor]],
                               calibration_inputs: list[torch.Tensor]
                               ) -> tuple[list[torch.Tensor], list[torch.Tensor], list[int]]:
    routed_by_expert: list[list[torch.Tensor]] = [[] for _ in weights]
    for layer_input in calibration_inputs:
        routed, _, _ = _routed_inputs(source_moe, layer_input.to("mps"))
        for index, values in enumerate(routed):
            if values.numel():
                routed_by_expert[index].append(values.detach().cpu())
    input_energies, output_energies, counts = [], [], []
    for index, ((input_weight, _), values) in enumerate(zip(weights, routed_by_expert, strict=True)):
        counts.append(sum(value.shape[0] for value in values))
        input_energy = _energy(values, input_weight.shape[1])
        input_energies.append(input_energy)
        activated = []
        if values:
            weight_mps = input_weight.to("mps")
            for value in values:
                hidden = functional.linear(value.to("mps"), weight_mps)
                gate, projected = hidden.chunk(2, dim=-1)
                activated.append((functional.silu(gate) * projected).detach().cpu())
            del weight_mps
        output_energies.append(_energy(activated, weights[index][1].shape[1]))
    return input_energies, output_energies, counts


def _fp16_layer(source_moe: Any, layer_input: torch.Tensor) -> torch.Tensor:
    return source_moe(layer_input)


def _packed_layer(source_moe: Any, layer_input: torch.Tensor,
                  weights: list[tuple[torch.Tensor, ...]], kind: str,
                  group_size: int = 32) -> torch.Tensor:
    batch, length, _ = layer_input.shape
    routed, batch_index, batch_gates = _routed_inputs(source_moe, layer_input)
    outputs = []
    for values, group in zip(routed, weights, strict=True):
        if kind == "int8":
            first, first_scale, second, second_scale = group
            hidden = torch._weight_int8pack_mm(values, first, first_scale)
        else:
            first, first_qparams, second, second_qparams = group
            hidden = torch._weight_int4pack_mm(values, first, group_size, first_qparams)
        gate, projected = hidden.chunk(2, dim=-1)
        activated = functional.silu(gate) * projected
        if kind == "int8":
            outputs.append(torch._weight_int8pack_mm(
                activated, second, second_scale,
            ))
        else:
            outputs.append(torch._weight_int4pack_mm(
                activated, second, group_size, second_qparams,
            ))
    expert_outputs = torch.cat(outputs, dim=0) * batch_gates[:, None]
    result = torch.zeros((batch * length, source_moe.input_size),
                         dtype=expert_outputs.dtype, device=expert_outputs.device)
    return result.index_add(0, batch_index, expert_outputs).view(batch, length, -1)


def _condition_metrics(actual: list[torch.Tensor], expected: list[torch.Tensor],
                       timings: list[float]) -> dict[str, float]:
    differences = [(left.float().cpu() - right.float().cpu()) for left, right in
                   zip(actual, expected, strict=True)]
    squared = sum(float(item.square().sum()) for item in differences)
    elements = sum(item.numel() for item in differences)
    signal = sum(float(item.float().cpu().square().sum()) for item in expected)
    return {"maximum_error": max(float(item.abs().max()) for item in differences),
            "mean_absolute_error": sum(float(item.abs().sum()) for item in differences) / elements,
            "normalized_rmse": (squared / elements) ** 0.5 / max((signal / elements) ** 0.5, 1e-12),
            "p50_decode_seconds": statistics.median(timings),
            "p95_decode_seconds_nearest_rank": _p95(timings)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=16)
    parser.add_argument("--group-size", type=int, default=32)
    parser.add_argument("--clip-ratios", type=float, nargs="+",
                        default=[1.0, 0.98, 0.95, 0.90, 0.85])
    parser.add_argument("--timing-samples", type=int, default=30)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {"model": args.model_path.resolve(),
             "source_manifest": args.source_manifest.resolve()}
    output = args.output.resolve()
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("model, weights and evidence must remain on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    ratios = tuple(args.clip_ratios)
    if 1.0 not in ratios:
        raise SystemExit("clip sweep must include the naive 1.0 control")

    manifest = json.loads(paths["source_manifest"].read_text())
    if not all(manifest["integrity"].values()):
        raise RuntimeError("source manifest integrity failed")
    tokenizer = AutoTokenizer.from_pretrained(paths["model"], local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        paths["model"], local_files_only=True, dtype=torch.float16,
        device_map={"": "mps"}, low_cpu_mem_usage=True,
    ).eval()
    source_moe = model.model.layers[args.layer].block_sparse_moe
    captured_inputs: list[torch.Tensor] = []
    captured_outputs: list[torch.Tensor] = []
    pre = source_moe.register_forward_pre_hook(
        lambda _module, values: captured_inputs.append(values[0].detach().cpu()))
    post = source_moe.register_forward_hook(
        lambda _module, _values, result: captured_outputs.append(result.detach().cpu()))
    with torch.inference_mode():
        for prompt in PROMPTS:
            model(**_chat_tokens(tokenizer, prompt["prompt"]), use_cache=False)
            torch.mps.synchronize()
    pre.remove(); post.remove()
    if len(captured_inputs) != 4 or len(captured_outputs) != 4:
        raise RuntimeError("real activation capture coverage failed")

    layer_entry = manifest["layers"][args.layer]
    index_path = Path(layer_entry["index_path"]).resolve()
    if root not in index_path.parents or _sha256(index_path) != layer_entry["index_sha256"]:
        raise RuntimeError("layer index integrity failed")
    index = json.loads(index_path.read_text())
    weights = []
    for entry in sorted(index["experts"], key=lambda item: int(item["expert"])):
        path = Path(entry["path"]).resolve()
        if root not in path.parents or _sha256(path) != entry["sha256"]:
            raise RuntimeError(f"expert integrity failed: {entry['expert']}")
        tensors = load_file(path, device="cpu")
        weights.append(tuple(tensors[name].half().contiguous() for name in
                             ("input_linear.weight", "output_linear.weight")))

    calibration_inputs = captured_inputs[:2]
    evaluation_inputs = captured_inputs[2:]
    evaluation_expected = captured_outputs[2:]
    input_energy, output_energy, token_counts = _build_activation_energies(
        source_moe, weights, calibration_inputs,
    )
    naive_cpu, aware_cpu, selections = [], [], []
    int8_cpu = []
    for expert, ((first, second), first_energy, second_energy) in enumerate(zip(
        weights, input_energy, output_energy, strict=True,
    )):
        first_naive = _quantize_int4_groups(first, args.group_size, 1.0)
        second_naive = _quantize_int4_groups(second, args.group_size, 1.0)
        first_n, first_q, first_ratio, first_losses = _choose_clip(
            first, first_energy, args.group_size, ratios)
        second_n, second_q, second_ratio, second_losses = _choose_clip(
            second, second_energy, args.group_size, ratios)
        naive_cpu.append((*first_naive, *second_naive))
        aware_cpu.append((first_n, first_q, second_n, second_q))
        first_i8, first_s = _quantize_rows(first)
        second_i8, second_s = _quantize_rows(second)
        int8_cpu.append((first_i8, first_s, second_i8, second_s))
        selections.append({"expert": expert, "calibration_routed_tokens": token_counts[expert],
                           "input_ratio": first_ratio, "output_ratio": second_ratio,
                           "input_proxy_losses": first_losses,
                           "output_proxy_losses": second_losses})

    def place_int4(groups: list[tuple[torch.Tensor, ...]]) -> list[tuple[torch.Tensor, ...]]:
        placed = []
        for first, first_q, second, second_q in groups:
            first_p, first_q_mps = _pack_for_metal(first, first_q)
            second_p, second_q_mps = _pack_for_metal(second, second_q)
            placed.append((first_p, first_q_mps, second_p, second_q_mps))
        return placed

    naive = place_int4(naive_cpu)
    aware = place_int4(aware_cpu)
    int8 = [tuple(t.to("mps") for t in group) for group in int8_cpu]
    eval_mps = [value.to("mps") for value in evaluation_inputs]
    decode_mps = [value[:, -1:, :] for value in eval_mps]
    functions = {
        "fp16": lambda value: _fp16_layer(source_moe, value),
        "int8": lambda value: _packed_layer(source_moe, value, int8, "int8"),
        "int4_naive": lambda value: _packed_layer(
            source_moe, value, naive, "int4", args.group_size),
        "int4_activation_aware": lambda value: _packed_layer(
            source_moe, value, aware, "int4", args.group_size),
    }
    results, timings = {name: [] for name in functions}, {name: [] for name in functions}
    with torch.inference_mode():
        for name, function in functions.items():
            for value in eval_mps:
                results[name].append(function(value).detach().cpu())
            for sample in range(args.timing_samples):
                value = decode_mps[sample % len(decode_mps)]
                started = time.perf_counter(); function(value); torch.mps.synchronize()
                timings[name].append(time.perf_counter() - started)

    metrics = {name: _condition_metrics(results[name], evaluation_expected, timings[name])
               for name in functions}
    fp16_p50 = metrics["fp16"]["p50_decode_seconds"]
    for item in metrics.values():
        item["p50_decode_improvement_vs_fp16_percent"] = 100 * (
            1 - item["p50_decode_seconds"] / fp16_p50)
    aware_error = metrics["int4_activation_aware"]["maximum_error"]
    naive_error = metrics["int4_naive"]["maximum_error"]
    int8_error = metrics["int8"]["maximum_error"]
    aware_time = metrics["int4_activation_aware"]["p50_decode_seconds"]
    naive_time = metrics["int4_naive"]["p50_decode_seconds"]
    acceptance = {
        "aware_max_error_reduced_at_least_20_percent_vs_naive": aware_error <= naive_error * .8,
        "aware_max_error_at_most_four_times_int8": aware_error <= int8_error * 4,
        "aware_decode_at_least_10_percent_faster_than_fp16": aware_time <= fp16_p50 * .9,
        "aware_decode_no_more_than_5_percent_slower_than_naive": aware_time <= naive_time * 1.05,
    }
    histogram = {str(ratio): sum(item[key] == ratio for item in selections
                                 for key in ("input_ratio", "output_ratio")) for ratio in ratios}
    report = {"schema_version": "aion.activation_aware_int4_gate.v1",
              "paths": {name: str(path) for name, path in paths.items()},
              "hashes": {"source_manifest": _sha256(paths["source_manifest"])},
              "layer": args.layer, "group_size": args.group_size,
              "calibration_families": [item["family"] for item in PROMPTS[:2]],
              "evaluation_families": [item["family"] for item in PROMPTS[2:]],
              "prompt_hashes": {item["family"]: hashlib.sha256(item["prompt"].encode()).hexdigest()
                                for item in PROMPTS},
              "clip_ratios": ratios, "selection_histogram": histogram,
              "selections": selections, "metrics": metrics, "acceptance": acceptance,
              "decision": "ADVANCE_TO_FULL_MODEL_INT4_GATE" if all(acceptance.values())
                          else "STOP_ACTIVATION_AWARE_INT4_V1",
              "claim_boundary": ("Post-hoc layer-16 mechanism gate using two fixed calibration "
                                 "and two disjoint evaluation prompt families. It measures real "
                                 "FP16 prefill activations and one-token layer timing, but cannot "
                                 "establish full-model generation speed or semantic quality.")}
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), "decision": report["decision"],
                      "selection_histogram": histogram, "metrics": metrics,
                      "acceptance": acceptance, "report_sha256": report["report_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
