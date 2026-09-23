#!/usr/bin/env python3
"""Test equivalent activation/weight rescaling for native Metal INT4 experts."""

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

from backend.scripts.run_aion_activation_aware_int4_gate import (
    _build_activation_energies, _canonical_sha256, _condition_metrics,
    _packed_layer, _routed_inputs,
)
from backend.scripts.run_aion_int4pack_expert_sweep import (
    _dequantize_int4_groups, _pack_for_metal, _quantize_int4_groups,
)
from backend.scripts.run_aion_int8pack_expert_microbench import _quantize_rows
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256
from backend.scripts.run_aion_storage_first_multiprompt import PROMPTS, _chat_tokens


def _equivalent_scale(weight: torch.Tensor, activation_energy: torch.Tensor,
                      alpha: float, group_size: int,
                      minimum: float = 0.25, maximum: float = 4.0) -> torch.Tensor:
    """Produce bounded per-input-channel scales, normalized within INT4 groups."""
    if not 0 <= alpha <= 1:
        raise ValueError("alpha must be in [0, 1]")
    activation = activation_energy.float().sqrt().clamp_min(1e-8)
    weight_magnitude = weight.float().abs().amax(dim=0).clamp_min(1e-8)
    scale = activation.pow(alpha) / weight_magnitude.pow(1 - alpha)
    grouped = scale.reshape(-1, group_size)
    grouped = grouped / grouped.log().mean(dim=1, keepdim=True).exp()
    return grouped.clamp(minimum, maximum).reshape(-1).to(torch.float16)


def _effective_weight(weight: torch.Tensor, activation_energy: torch.Tensor,
                      alpha: float | None, group_size: int
                      ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, float]:
    scale = (torch.ones(weight.shape[1], dtype=torch.float16) if alpha is None else
             _equivalent_scale(weight, activation_energy, alpha, group_size))
    nibbles, qparams = _quantize_int4_groups(
        weight * scale.float()[None, :], group_size,
    )
    restored = _dequantize_int4_groups(nibbles, qparams, group_size)
    effective = restored / scale.float()[None, :]
    energy = activation_energy.float().clamp_min(1e-12)
    energy = energy / energy.mean()
    loss = float(((effective - weight.float()).square() * energy[None, :]).mean())
    return nibbles, qparams, scale, loss


def _choose_alpha(weight: torch.Tensor, activation_energy: torch.Tensor,
                  alphas: tuple[float, ...], group_size: int
                  ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, str, dict[str, float]]:
    candidates: dict[str, tuple[torch.Tensor, torch.Tensor, torch.Tensor, float]] = {
        "identity": _effective_weight(weight, activation_energy, None, group_size),
    }
    for alpha in alphas:
        candidates[str(alpha)] = _effective_weight(
            weight, activation_energy, alpha, group_size,
        )
    selected = min(candidates, key=lambda key: candidates[key][3])
    nibbles, qparams, scale, _ = candidates[selected]
    return nibbles, qparams, scale, selected, {
        key: value[3] for key, value in candidates.items()
    }


def _scaled_layer(source_moe: Any, layer_input: torch.Tensor,
                  weights: list[tuple[torch.Tensor, ...]], group_size: int) -> torch.Tensor:
    batch, length, _ = layer_input.shape
    routed, batch_index, batch_gates = _routed_inputs(source_moe, layer_input)
    outputs = []
    for values, group in zip(routed, weights, strict=True):
        first, first_qparams, first_scale, second, second_qparams, second_scale = group
        hidden = torch._weight_int4pack_mm(
            values / first_scale, first, group_size, first_qparams,
        )
        gate, projected = hidden.chunk(2, dim=-1)
        activated = functional.silu(gate) * projected
        outputs.append(torch._weight_int4pack_mm(
            activated / second_scale, second, group_size, second_qparams,
        ))
    expert_outputs = torch.cat(outputs, dim=0) * batch_gates[:, None]
    result = torch.zeros((batch * length, source_moe.input_size),
                         dtype=expert_outputs.dtype, device=expert_outputs.device)
    return result.index_add(0, batch_index, expert_outputs).view(batch, length, -1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=16)
    parser.add_argument("--group-size", type=int, default=32)
    parser.add_argument("--alphas", type=float, nargs="+", default=[0.25, 0.5, 0.75, 1.0])
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
    alphas = tuple(args.alphas)

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

    input_energy, output_energy, token_counts = _build_activation_energies(
        source_moe, weights, captured_inputs[:2],
    )
    naive_cpu, scaled_cpu, int8_cpu, selections = [], [], [], []
    for expert, ((first, second), first_energy, second_energy) in enumerate(zip(
        weights, input_energy, output_energy, strict=True,
    )):
        first_naive = _quantize_int4_groups(first, args.group_size)
        second_naive = _quantize_int4_groups(second, args.group_size)
        first_n, first_q, first_scale, first_choice, first_losses = _choose_alpha(
            first, first_energy, alphas, args.group_size)
        second_n, second_q, second_scale, second_choice, second_losses = _choose_alpha(
            second, second_energy, alphas, args.group_size)
        naive_cpu.append((*first_naive, *second_naive))
        scaled_cpu.append((first_n, first_q, first_scale,
                           second_n, second_q, second_scale))
        first_i8, first_s = _quantize_rows(first)
        second_i8, second_s = _quantize_rows(second)
        int8_cpu.append((first_i8, first_s, second_i8, second_s))
        selections.append({"expert": expert, "calibration_routed_tokens": token_counts[expert],
                           "input_choice": first_choice, "output_choice": second_choice,
                           "input_proxy_losses": first_losses,
                           "output_proxy_losses": second_losses})

    naive = []
    for first, first_q, second, second_q in naive_cpu:
        first_p, first_q_mps = _pack_for_metal(first, first_q)
        second_p, second_q_mps = _pack_for_metal(second, second_q)
        naive.append((first_p, first_q_mps, second_p, second_q_mps))
    scaled = []
    for first, first_q, first_s, second, second_q, second_s in scaled_cpu:
        first_p, first_q_mps = _pack_for_metal(first, first_q)
        second_p, second_q_mps = _pack_for_metal(second, second_q)
        scaled.append((first_p, first_q_mps, first_s.to("mps"),
                       second_p, second_q_mps, second_s.to("mps")))
    int8 = [tuple(item.to("mps") for item in group) for group in int8_cpu]

    evaluation_expected = captured_outputs[2:]
    eval_mps = [value.to("mps") for value in captured_inputs[2:]]
    decode_mps = [value[:, -1:, :] for value in eval_mps]
    functions = {
        "fp16": lambda value: source_moe(value),
        "int8": lambda value: _packed_layer(source_moe, value, int8, "int8"),
        "int4_naive": lambda value: _packed_layer(
            source_moe, value, naive, "int4", args.group_size),
        "int4_equivalent_scaled": lambda value: _scaled_layer(
            source_moe, value, scaled, args.group_size),
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
    scaled_error = metrics["int4_equivalent_scaled"]["maximum_error"]
    naive_error = metrics["int4_naive"]["maximum_error"]
    int8_error = metrics["int8"]["maximum_error"]
    scaled_time = metrics["int4_equivalent_scaled"]["p50_decode_seconds"]
    naive_time = metrics["int4_naive"]["p50_decode_seconds"]
    acceptance = {
        "scaled_max_error_reduced_at_least_20_percent_vs_naive": scaled_error <= naive_error * .8,
        "scaled_max_error_at_most_four_times_int8": scaled_error <= int8_error * 4,
        "scaled_decode_at_least_10_percent_faster_than_fp16": scaled_time <= fp16_p50 * .9,
        "scaled_decode_no_more_than_10_percent_slower_than_naive": scaled_time <= naive_time * 1.10,
    }
    choices = ("identity",) + tuple(str(value) for value in alphas)
    histogram = {choice: sum(item[key] == choice for item in selections
                             for key in ("input_choice", "output_choice")) for choice in choices}
    fp16_bytes = sum(t.numel() * t.element_size() for pair in weights for t in pair)
    scaled_bytes = sum(t.numel() * t.element_size() for group in scaled_cpu for t in group)
    report = {"schema_version": "aion.equivalent_scaled_int4_gate.v1",
              "paths": {name: str(path) for name, path in paths.items()},
              "hashes": {"source_manifest": _sha256(paths["source_manifest"])},
              "layer": args.layer, "group_size": args.group_size,
              "calibration_families": [item["family"] for item in PROMPTS[:2]],
              "evaluation_families": [item["family"] for item in PROMPTS[2:]],
              "prompt_hashes": {item["family"]: hashlib.sha256(item["prompt"].encode()).hexdigest()
                                for item in PROMPTS},
              "alphas": alphas, "selection_histogram": histogram,
              "bytes": {"fp16_layer_experts": fp16_bytes,
                        "scaled_int4_layer_experts_and_runtime_scales": scaled_bytes,
                        "reduction_percent": 100 * (1 - scaled_bytes / fp16_bytes)},
              "selections": selections, "metrics": metrics, "acceptance": acceptance,
              "decision": "ADVANCE_TO_FULL_MODEL_INT4_GATE" if all(acceptance.values())
                          else "STOP_EQUIVALENT_SCALED_INT4_V1",
              "claim_boundary": ("Post-hoc layer-16 mechanism gate using two calibration and "
                                 "two disjoint evaluation prompt families. Runtime inverse "
                                 "scaling is charged. Full-model speed and semantic quality "
                                 "are not established.")}
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), "decision": report["decision"],
                      "selection_histogram": histogram, "bytes": report["bytes"],
                      "metrics": metrics, "acceptance": acceptance,
                      "report_sha256": report["report_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
