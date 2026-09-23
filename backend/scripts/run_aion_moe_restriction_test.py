#!/usr/bin/env python3
"""Falsify hard expert pruning using learned Granite MoE resident sets."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import time
from typing import Any

import torch
import torch.nn.functional as functional
from transformers import AutoModelForCausalLM, AutoTokenizer

from run_aion_moe_expert_profile import HOLDOUT, _chat_tokens


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _restricted_forward(router, allowed_experts: tuple[int, ...]):
    """Return the Granite router operation with non-resident logits masked."""
    def forward(hidden_states):
        logits = router.layer(hidden_states).float()
        allowed = torch.tensor(allowed_experts, device=logits.device, dtype=torch.long)
        masked_logits = torch.full_like(logits, float("-inf"))
        masked_logits[:, allowed] = logits[:, allowed]
        top_k_logits, top_k_indices = masked_logits.topk(router.top_k, dim=1)
        top_k_gates = torch.softmax(top_k_logits, dim=1).type_as(hidden_states)
        zeros = torch.zeros(
            [top_k_gates.size(0), router.num_experts],
            dtype=top_k_gates.dtype,
            device=top_k_gates.device,
        )
        gates = zeros.scatter(1, top_k_indices, 1)
        expert_size = gates.long().sum(0).tolist()
        top_k_experts = top_k_indices.flatten()
        _, index_sorted_experts = top_k_experts.sort(0)
        batch_index = index_sorted_experts.div(router.top_k, rounding_mode="trunc")
        batch_gates = top_k_gates.flatten()[index_sorted_experts]
        return index_sorted_experts, batch_index, batch_gates, expert_size, masked_logits

    return forward


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--generated-tokens", type=int, default=8)
    args = parser.parse_args()

    root, profile_path = args.storage_root.resolve(), args.profile.resolve()
    if root not in profile_path.parents:
        raise SystemExit("profile must be inside the declared external storage root")
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    model_path = Path(profile["model_path"]).resolve()
    if root not in model_path.parents:
        raise SystemExit("profile model must be inside the declared external storage root")
    resident_sets = profile["training"]["resident_experts_by_layer"]
    if not torch.backends.mps.is_available():
        raise SystemExit("Apple Metal/MPS is required for this experiment")

    started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        local_files_only=True,
        dtype=torch.float16,
        device_map={"": "mps"},
        low_cpu_mem_usage=True,
    ).eval()
    load_seconds = time.perf_counter() - started
    layers = list(model.model.layers)
    if len(layers) != len(resident_sets):
        raise SystemExit("profile layer count does not match checkpoint")

    prompts = [(domain, prompt) for domain, values in HOLDOUT.items() for prompt in values]

    def infer(prompt: str) -> tuple[torch.Tensor, str, float]:
        inputs = _chat_tokens(tokenizer, prompt, "mps")
        before = time.perf_counter()
        with torch.inference_mode():
            output = model(**inputs, use_cache=False, logits_to_keep=1)
            generated = model.generate(
                **inputs,
                do_sample=False,
                max_new_tokens=args.generated_tokens,
                use_cache=True,
                pad_token_id=tokenizer.eos_token_id,
            )
        elapsed = time.perf_counter() - before
        continuation = generated[0, inputs["input_ids"].shape[1]:]
        return output.logits[0, -1].detach().float().cpu(), tokenizer.decode(continuation), elapsed

    unrestricted: list[tuple[torch.Tensor, str, float]] = []
    for _, prompt in prompts:
        unrestricted.append(infer(prompt))

    originals = []
    for layer, allowed in zip(layers, resident_sets, strict=True):
        router = layer.block_sparse_moe.router
        originals.append(router.forward)
        router.forward = _restricted_forward(router, tuple(allowed))

    restricted: list[tuple[torch.Tensor, str, float]] = []
    try:
        for _, prompt in prompts:
            restricted.append(infer(prompt))
    finally:
        for layer, original in zip(layers, originals, strict=True):
            layer.block_sparse_moe.router.forward = original

    results: list[dict[str, Any]] = []
    for (domain, prompt), base, limited in zip(prompts, unrestricted, restricted, strict=True):
        base_logits, base_text, base_time = base
        limited_logits, limited_text, limited_time = limited
        base_log_probs = functional.log_softmax(base_logits, dim=-1)
        limited_log_probs = functional.log_softmax(limited_logits, dim=-1)
        base_probs = base_log_probs.exp()
        base_top = base_logits.topk(5).indices.tolist()
        limited_top = limited_logits.topk(5).indices.tolist()
        results.append({
            "domain": domain,
            "prompt": prompt,
            "unrestricted_next_token_id": int(base_logits.argmax().item()),
            "restricted_next_token_id": int(limited_logits.argmax().item()),
            "next_token_match": bool(base_logits.argmax() == limited_logits.argmax()),
            "top5_overlap": len(set(base_top) & set(limited_top)) / 5,
            "kl_unrestricted_to_restricted": float(
                (base_probs * (base_log_probs - limited_log_probs)).sum().item()
            ),
            "unrestricted_continuation": base_text,
            "restricted_continuation": limited_text,
            "continuation_exact_match": base_text == limited_text,
            "unrestricted_seconds": base_time,
            "restricted_seconds": limited_time,
        })

    next_matches = sum(item["next_token_match"] for item in results)
    continuation_matches = sum(item["continuation_exact_match"] for item in results)
    hard_pruning_safe = (
        profile["holdout"]["fully_resident_prompt_count"] == len(prompts)
        and next_matches == len(prompts)
        and continuation_matches == len(prompts)
    )
    report: dict[str, Any] = {
        "schema_version": "aion.real_moe_hard_restriction.v1",
        "profile_path": str(profile_path),
        "profile_sha256": _sha256(profile_path),
        "model_path": str(model_path),
        "storage_root": str(root),
        "method": {
            "description": "Mask every non-resident router logit, then compare unrestricted and hard-restricted inference on untouched prompts.",
            "holdout_prompts": len(prompts),
            "generated_tokens": args.generated_tokens,
            "sampling": "greedy",
        },
        "results": results,
        "summary": {
            "next_token_matches": next_matches,
            "continuation_exact_matches": continuation_matches,
            "median_top5_overlap": statistics.median(item["top5_overlap"] for item in results),
            "median_kl_divergence": statistics.median(item["kl_unrestricted_to_restricted"] for item in results),
            "unrestricted_median_seconds": statistics.median(item["unrestricted_seconds"] for item in results),
            "restricted_median_seconds": statistics.median(item["restricted_seconds"] for item in results),
            "hard_pruning_safe": hard_pruning_safe,
            "verdict": "HARD_PRUNING_SUPPORTED" if hard_pruning_safe else "HARD_PRUNING_REJECTED_REQUIRE_FAULT_IN",
        },
        "timing": {"checkpoint_load_seconds": load_seconds},
        "integrity": {
            "model_is_on_external_storage": root in model_path.parents,
            "profile_is_on_external_storage": root in profile_path.parents,
            "all_layers_restricted": len(layers) == len(resident_sets),
            "profile_checkpoint_hashes_present": bool(profile["checkpoint"]["safetensor_files"]),
        },
        "claim_boundary": "This tests hard routing restriction with full weights still loaded. It does not yet dynamically fault expert tensors into memory.",
    }
    output = args.output or root / "experiments" / "real-moe-hard-restriction-v1.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), **report["summary"], "integrity": report["integrity"]}, indent=2))
    return 0 if all(report["integrity"].values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
