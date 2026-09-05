#!/usr/bin/env python3
"""Profile real Granite MoE routing and evaluate workload-specific residency."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
import time
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


TRAIN = {
    "arithmetic": [
        "Calculate 18 percent of 275.", "A product costs 240. Add a 15 percent markup.",
        "Take 25 percent off 880.", "A worker earns 32 per hour for 7 hours.",
    ],
    "business": [
        "Revenue is 6000, materials 2100, labour 1400. Calculate profit.",
        "Summarize the commercial risks in accepting an unverified quotation.",
        "Classify this request: customer asks for a patio quote.",
        "List the checks required before sending an invoice.",
    ],
    "policy": [
        "A quotation requires human approval. May it be sent automatically?",
        "Payment is prohibited before confirmation. State the permitted next action.",
        "Do not book installation without consent. Explain the restriction.",
        "Extract every mandatory rule from: review quotes; confirm payments; obtain booking consent.",
    ],
    "coding": [
        "Write a Python function that returns the sum of two decimals.",
        "Explain why a content hash changes after a JSON contract changes.",
        "Find the bug: for i in range(len(items)+1): print(items[i]).",
        "Design a unit test for a parser that must reject ambiguous numbers.",
    ],
    "general": [
        "Explain photosynthesis in one paragraph.", "Write a short description of Madrid in spring.",
        "What causes ocean tides?", "Give three ways to organize a workshop.",
    ],
}

HOLDOUT = {
    "arithmetic": ["Add 7 percent tax to 430.", "Calculate 19 times 23."],
    "business": ["A job earned 7200 and cost 4650. What was the profit?", "Draft a cautious quotation summary."],
    "policy": ["Human review is required and payment is forbidden. What can happen next?", "Can a booking proceed without explicit consent?"],
    "coding": ["Write a test that confirms division by zero is rejected.", "Explain deterministic replay in software."],
    "general": ["Why do leaves change colour?", "Suggest a simple weekend walking plan."],
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _chat_tokens(tokenizer, prompt: str, device: str):
    encoded = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}], add_generation_prompt=True,
        tokenize=True, return_tensors="pt", return_dict=True,
    )
    return {key: value.to(device) for key, value in encoded.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--coverage-target", type=float, default=0.95)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    model_path, root = args.model_path.resolve(), args.storage_root.resolve()
    if root not in model_path.parents:
        raise SystemExit("model path must be inside the declared external storage root")
    if not torch.backends.mps.is_available():
        raise SystemExit("Apple Metal/MPS is required for this experiment")

    started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path, local_files_only=True, dtype=torch.float16,
        device_map={"": "mps"}, low_cpu_mem_usage=True,
    ).eval()
    load_seconds = time.perf_counter() - started
    config = model.config
    layers = list(model.model.layers)
    captures: list[list[torch.Tensor]] = [[] for _ in layers]
    hooks = []
    for layer_index, layer in enumerate(layers):
        def capture(_module, _inputs, output, index=layer_index):
            captures[index].append(output[4].detach().float().cpu())
        hooks.append(layer.block_sparse_moe.router.register_forward_hook(capture))

    def forward(prompt: str) -> tuple[int, list[torch.Tensor], float]:
        for values in captures:
            values.clear()
        inputs = _chat_tokens(tokenizer, prompt, "mps")
        before = time.perf_counter()
        with torch.inference_mode():
            output = model(**inputs, use_cache=False, logits_to_keep=1)
        elapsed = time.perf_counter() - before
        routed = [values[-1] for values in captures]
        return int(output.logits[0, -1].argmax().item()), routed, elapsed

    train_counts = [[0] * config.num_local_experts for _ in layers]
    train_by_domain: dict[str, list[list[int]]] = {}
    train_timings = []
    for domain, prompts in TRAIN.items():
        domain_counts = [[0] * config.num_local_experts for _ in layers]
        for prompt in prompts:
            _, routed, elapsed = forward(prompt)
            train_timings.append(elapsed)
            for layer_index, logits in enumerate(routed):
                selected = logits.topk(config.num_experts_per_tok, dim=-1).indices.flatten().tolist()
                for expert in selected:
                    train_counts[layer_index][expert] += 1
                    domain_counts[layer_index][expert] += 1
        train_by_domain[domain] = domain_counts

    resident_sets: list[list[int]] = []
    for counts in train_counts:
        ordered = [expert for expert, _ in Counter(dict(enumerate(counts))).most_common()]
        threshold, running, chosen = sum(counts) * args.coverage_target, 0, []
        for expert in ordered:
            chosen.append(expert)
            running += counts[expert]
            if running >= threshold and len(chosen) >= config.num_experts_per_tok:
                break
        resident_sets.append(sorted(chosen))

    holdout_results, holdout_timings = [], []
    holdout_hits = [0] * len(layers)
    holdout_total = [0] * len(layers)
    for domain, prompts in HOLDOUT.items():
        for prompt in prompts:
            token, routed, elapsed = forward(prompt)
            holdout_timings.append(elapsed)
            all_resident = True
            per_layer = []
            for layer_index, logits in enumerate(routed):
                selected = logits.topk(config.num_experts_per_tok, dim=-1).indices.flatten().tolist()
                resident = set(resident_sets[layer_index])
                hits = sum(expert in resident for expert in selected)
                holdout_hits[layer_index] += hits
                holdout_total[layer_index] += len(selected)
                all_resident &= hits == len(selected)
                per_layer.append({"assignments": len(selected), "resident_hits": hits})
            holdout_results.append({"domain": domain, "prompt": prompt, "next_token_id": token,
                                    "all_assignments_resident": all_resident, "layers": per_layer})

    for hook in hooks:
        hook.remove()
    parameter_bytes = sum(parameter.numel() * parameter.element_size() for parameter in model.parameters())
    expert_bytes = sum(
        parameter.numel() * parameter.element_size() for name, parameter in model.named_parameters()
        if ".block_sparse_moe.input_linear.weight" in name or ".block_sparse_moe.output_linear.weight" in name
    )
    resident_fractions = [len(chosen) / config.num_local_experts for chosen in resident_sets]
    estimated_resident_expert_bytes = int(expert_bytes * statistics.mean(resident_fractions))
    estimated_total_bytes = parameter_bytes - expert_bytes + estimated_resident_expert_bytes
    assignment_hits, assignment_total = sum(holdout_hits), sum(holdout_total)
    model_files = [path for path in model_path.glob("*.safetensors") if path.is_file()]
    report: dict[str, Any] = {
        "schema_version": "aion.real_moe_expert_profile.v1",
        "model_path": str(model_path), "storage_root": str(root),
        "checkpoint": {"safetensor_files": [{"name": path.name, "bytes": path.stat().st_size,
                                                "sha256": _sha256(path)} for path in model_files]},
        "architecture": {"layers": len(layers), "experts_per_layer": config.num_local_experts,
                         "experts_selected_per_token": config.num_experts_per_tok,
                         "hidden_size": config.hidden_size, "intermediate_size": config.intermediate_size},
        "method": {"training_prompts": sum(map(len, TRAIN.values())),
                   "holdout_prompts": sum(map(len, HOLDOUT.values())),
                   "coverage_target": args.coverage_target, "greedy_next_token_only": True},
        "training": {"counts_by_layer": train_counts, "counts_by_domain": train_by_domain,
                     "resident_experts_by_layer": resident_sets,
                     "resident_expert_count_by_layer": list(map(len, resident_sets))},
        "holdout": {"results": holdout_results,
                    "resident_assignment_coverage": assignment_hits / assignment_total,
                    "fully_resident_prompt_count": sum(item["all_assignments_resident"] for item in holdout_results)},
        "memory_estimate": {"parameter_bytes_fp16": parameter_bytes, "expert_parameter_bytes_fp16": expert_bytes,
                            "estimated_resident_parameter_bytes_fp16": estimated_total_bytes,
                            "estimated_reduction_percent": (1 - estimated_total_bytes / parameter_bytes) * 100},
        "timing": {"load_seconds": load_seconds, "training_forward_median_seconds": statistics.median(train_timings),
                   "holdout_forward_median_seconds": statistics.median(holdout_timings)},
        "integrity": {"all_layers_captured": all(sum(counts) > 0 for counts in train_counts),
                      "model_is_on_external_storage": root in model_path.parents,
                      "safetensor_hashes_recorded": bool(model_files)},
        "claim_boundary": "Real top-k router traces and an analytical FP16 residency estimate. No expert weights were dynamically unloaded in this experiment.",
    }
    output = args.output or root / "experiments" / "real-moe-expert-profile-v1.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "architecture": report["architecture"],
                      "resident_experts_median": statistics.median(map(len, resident_sets)),
                      "holdout_assignment_coverage": report["holdout"]["resident_assignment_coverage"],
                      "estimated_reduction_percent": report["memory_estimate"]["estimated_reduction_percent"],
                      "integrity": report["integrity"]}, indent=2))
    return 0 if all(report["integrity"].values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
