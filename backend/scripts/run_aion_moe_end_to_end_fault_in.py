#!/usr/bin/env python3
"""Run Granite end-to-end with SD-backed, workload-resident expert caches."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
import statistics
import time
from typing import Any

import psutil
import torch
import torch.nn.functional as functional
from safetensors.torch import load_file
from transformers import AutoModelForCausalLM, AutoTokenizer


PROMPTS = [
    "Add 7 percent tax to 430.",
    "A job earned 7200 and cost 4650. What was the profit?",
    "Human review is required and payment is forbidden. What can happen next?",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _chat_tokens(tokenizer, prompt: str):
    encoded = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}],
        add_generation_prompt=True,
        tokenize=True,
        return_tensors="pt",
        return_dict=True,
    )
    return {key: value.to("mps") for key, value in encoded.items()}


def _memory_snapshot(label: str) -> dict[str, int | str]:
    torch.mps.synchronize()
    return {
        "label": label,
        "process_rss_bytes": psutil.Process().memory_info().rss,
        "mps_current_allocated_bytes": torch.mps.current_allocated_memory(),
        "mps_driver_allocated_bytes": torch.mps.driver_allocated_memory(),
    }


class LayerExpertStore:
    def __init__(self, layer: int, index: dict[str, Any], resident: set[int]):
        self.layer = layer
        self.entries = {entry["expert"]: entry for entry in index["experts"]}
        self.resident = resident
        self.cache: dict[int, tuple[torch.Tensor, torch.Tensor]] = {}
        self.request_cache: dict[int, tuple[torch.Tensor, torch.Tensor]] = {}
        self.request_cache_peak_bytes = 0
        self.verified: set[int] = set()
        self.events: list[dict[str, Any]] = []
        self.phase = "unassigned"

    def get(self, expert: int, device: torch.device, dtype: torch.dtype):
        if expert in self.cache:
            return self.cache[expert]
        if expert in self.request_cache:
            return self.request_cache[expert]
        entry = self.entries[expert]
        path = Path(entry["path"])
        started = time.perf_counter()
        verified_now = expert not in self.verified
        if verified_now:
            observed = _sha256(path)
            if observed != entry["sha256"]:
                raise RuntimeError(f"expert shard hash mismatch: layer {self.layer}, expert {expert}")
            self.verified.add(expert)
        tensors = load_file(path, device="cpu")
        weights = (
            tensors["input_linear.weight"].to(device=device, dtype=dtype),
            tensors["output_linear.weight"].to(device=device, dtype=dtype),
        )
        torch.mps.synchronize()
        self.events.append({
            "layer": self.layer,
            "expert": expert,
            "resident": expert in self.resident,
            "phase": self.phase,
            "verified_now": verified_now,
            "logical_bytes": entry["bytes"],
            "seconds": time.perf_counter() - started,
        })
        if expert in self.resident:
            self.cache[expert] = weights
        else:
            self.request_cache[expert] = weights
            self.request_cache_peak_bytes = max(
                self.request_cache_peak_bytes,
                sum(self.entries[item]["bytes"] for item in self.request_cache),
            )
        return weights

    def end_request(self) -> None:
        self.request_cache.clear()

    def configure_resident(self, experts: set[int]) -> None:
        unknown = experts - self.entries.keys()
        if unknown:
            raise ValueError(f"unknown experts for layer {self.layer}: {sorted(unknown)}")
        self.resident = set(experts)

    def prefetch(self, device: torch.device, dtype: torch.dtype) -> None:
        """Materialize the configured resident experts before model execution."""
        for expert in sorted(self.resident):
            self.get(expert, device, dtype)

    def clear_all(self) -> None:
        self.cache.clear()
        self.request_cache.clear()

    @property
    def cached_bytes(self) -> int:
        return sum(self.entries[expert]["bytes"] for expert in self.cache)


def _dynamic_forward(block, store: LayerExpertStore):
    router = block.router
    activation = block.activation
    input_size = block.input_size

    def forward(layer_input):
        batch_size, length, embedding_size = layer_input.size()
        flattened = layer_input.reshape(-1, embedding_size)
        _, batch_index, batch_gates, expert_size, _ = router(flattened)
        expert_inputs = flattened[batch_index]
        input_list = expert_inputs.split(expert_size, dim=0)
        output_list = []
        for expert, expert_input in enumerate(input_list):
            if expert_input.shape[0] == 0:
                output_list.append(torch.empty(
                    (0, input_size), dtype=layer_input.dtype, device=layer_input.device
                ))
                continue
            input_weight, output_weight = store.get(expert, layer_input.device, layer_input.dtype)
            hidden = functional.linear(expert_input, input_weight)
            gate_half, value_half = hidden.chunk(2, dim=-1)
            output_list.append(functional.linear(activation(gate_half) * value_half, output_weight))
        expert_outputs = torch.cat(output_list, dim=0) * batch_gates[:, None]
        zeros = torch.zeros(
            (batch_size * length, input_size),
            dtype=expert_outputs.dtype,
            device=expert_outputs.device,
        )
        return zeros.index_add(0, batch_index, expert_outputs).view(batch_size, length, input_size)

    return forward


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--shard-manifest", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--generated-tokens", type=int, default=4)
    args = parser.parse_args()

    root = args.storage_root.resolve()
    model_path = args.model_path.resolve()
    profile_path = args.profile.resolve()
    manifest_path = args.shard_manifest.resolve()
    if any(root not in path.parents for path in (model_path, profile_path, manifest_path)):
        raise SystemExit("model, profile, and shards must reside under external storage root")
    if not torch.backends.mps.is_available():
        raise SystemExit("Apple Metal/MPS is required")
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not all(manifest["integrity"].values()):
        raise SystemExit("expert shard manifest integrity gate failed")

    memory = [_memory_snapshot("before_model_load")]
    load_started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        local_files_only=True,
        dtype=torch.float16,
        device_map={"": "mps"},
        low_cpu_mem_usage=True,
    ).eval()
    load_seconds = time.perf_counter() - load_started
    memory.append(_memory_snapshot("full_model_loaded"))

    def generate(prompt: str) -> dict[str, Any]:
        inputs = _chat_tokens(tokenizer, prompt)
        started = time.perf_counter()
        with torch.inference_mode():
            result = model.generate(
                **inputs,
                do_sample=False,
                max_new_tokens=args.generated_tokens,
                use_cache=True,
                return_dict_in_generate=True,
                output_scores=True,
                pad_token_id=tokenizer.eos_token_id,
            )
        torch.mps.synchronize()
        continuation_ids = result.sequences[0, inputs["input_ids"].shape[1]:].detach().cpu()
        return {
            "token_ids": continuation_ids.tolist(),
            "text": tokenizer.decode(continuation_ids),
            "first_token_logits": result.scores[0][0].detach().float().cpu(),
            "seconds": time.perf_counter() - started,
        }

    unrestricted = [generate(prompt) for prompt in PROMPTS]
    memory.append(_memory_snapshot("after_unrestricted_generation"))

    layers = list(model.model.layers)
    resident_sets = profile["training"]["resident_experts_by_layer"]
    if len(layers) != len(manifest["layers"]) or len(layers) != len(resident_sets):
        raise SystemExit("model, profile, and shard layer counts differ")
    stores = []
    for layer_number, (layer, manifest_layer, residents) in enumerate(
        zip(layers, manifest["layers"], resident_sets, strict=True)
    ):
        index_path = Path(manifest_layer["index_path"])
        if _sha256(index_path) != manifest_layer["index_sha256"]:
            raise RuntimeError(f"layer index hash mismatch: {layer_number}")
        index = json.loads(index_path.read_text(encoding="utf-8"))
        store = LayerExpertStore(layer_number, index, set(residents))
        stores.append(store)
        block = layer.block_sparse_moe
        block.forward = _dynamic_forward(block, store)
        block.input_linear = None
        block.output_linear = None
    gc.collect()
    torch.mps.empty_cache()
    memory.append(_memory_snapshot("expert_tensors_removed"))

    dynamic_request_memory = []
    def dynamic_pass(phase: str):
        results = []
        for store in stores:
            store.phase = phase
        for prompt_number, prompt in enumerate(PROMPTS):
            results.append(generate(prompt))
            dynamic_request_memory.append(_memory_snapshot(f"{phase}_request_{prompt_number}_peak"))
            for store in stores:
                store.end_request()
            gc.collect()
            torch.mps.empty_cache()
            dynamic_request_memory.append(_memory_snapshot(f"{phase}_request_{prompt_number}_after_eviction"))
        return results

    dynamic = dynamic_pass("population")
    memory.append(_memory_snapshot("after_dynamic_generation"))
    steady_dynamic = dynamic_pass("steady_state")
    memory.append(_memory_snapshot("after_steady_state_generation"))

    comparisons = []
    for prompt, full, streamed, steady in zip(PROMPTS, unrestricted, dynamic, steady_dynamic, strict=True):
        full_logits = full.pop("first_token_logits")
        streamed_logits = streamed.pop("first_token_logits")
        steady_logits = steady.pop("first_token_logits")
        comparisons.append({
            "prompt": prompt,
            "unrestricted": full,
            "dynamic": streamed,
            "steady_state_dynamic": steady,
            "token_ids_exact_match": full["token_ids"] == streamed["token_ids"],
            "steady_state_token_ids_exact_match": full["token_ids"] == steady["token_ids"],
            "first_token_id_match": int(full_logits.argmax()) == int(streamed_logits.argmax()),
            "first_token_max_absolute_logit_error": float(
                (full_logits - streamed_logits).abs().max().item()
            ),
            "steady_state_first_token_max_absolute_logit_error": float(
                (full_logits - steady_logits).abs().max().item()
            ),
        })

    events = [event for store in stores for event in store.events]
    resident_events = [event for event in events if event["resident"]]
    miss_events = [event for event in events if not event["resident"]]
    population_events = [event for event in events if event["phase"] == "population"]
    steady_events = [event for event in events if event["phase"] == "steady_state"]
    full_memory = next(item for item in memory if item["label"] == "after_unrestricted_generation")
    stripped_memory = next(item for item in memory if item["label"] == "expert_tensors_removed")
    dynamic_memory = next(item for item in memory if item["label"] == "after_dynamic_generation")
    all_output_match = all(
        item["token_ids_exact_match"] and item["steady_state_token_ids_exact_match"]
        for item in comparisons
    )
    report = {
        "schema_version": "aion.real_moe_end_to_end_fault_in.v1",
        "storage_root": str(root),
        "model_path": str(model_path),
        "profile_path": str(profile_path),
        "profile_sha256": _sha256(profile_path),
        "shard_manifest_path": str(manifest_path),
        "shard_manifest_sha256": _sha256(manifest_path),
        "method": {
            "prompts": PROMPTS,
            "generated_tokens": args.generated_tokens,
            "dtype": "float16",
            "device": "mps",
            "resident_policy": "retain learned resident experts across requests",
            "miss_policy": "retain non-resident experts for one complete request, then evict",
            "os_cache_controlled": False,
        },
        "comparisons": comparisons,
        "storage": {
            "load_events": len(events),
            "resident_load_events": len(resident_events),
            "nonresident_fault_events": len(miss_events),
            "population_load_events": len(population_events),
            "steady_state_load_events": len(steady_events),
            "population_logical_bytes_requested": sum(event["logical_bytes"] for event in population_events),
            "steady_state_logical_bytes_requested": sum(event["logical_bytes"] for event in steady_events),
            "logical_bytes_requested": sum(event["logical_bytes"] for event in events),
            "nonresident_logical_bytes_requested": sum(event["logical_bytes"] for event in miss_events),
            "resident_cache_logical_bytes": sum(store.cached_bytes for store in stores),
            "request_cache_peak_logical_bytes_upper_bound": sum(
                store.request_cache_peak_bytes for store in stores
            ),
            "median_load_seconds": statistics.median(event["seconds"] for event in events),
            "events": events,
        },
        "timing": {
            "full_checkpoint_load_seconds": load_seconds,
            "unrestricted_generation_seconds": [item["unrestricted"]["seconds"] for item in comparisons],
            "dynamic_generation_seconds": [item["dynamic"]["seconds"] for item in comparisons],
            "steady_state_generation_seconds": [
                item["steady_state_dynamic"]["seconds"] for item in comparisons
            ],
        },
        "memory": {
            "snapshots": memory,
            "dynamic_request_snapshots": dynamic_request_memory,
            "mps_reduction_after_expert_removal_bytes": (
                full_memory["mps_current_allocated_bytes"] - stripped_memory["mps_current_allocated_bytes"]
            ),
            "mps_reduction_after_dynamic_run_bytes": (
                full_memory["mps_current_allocated_bytes"] - dynamic_memory["mps_current_allocated_bytes"]
            ),
        },
        "integrity": {
            "all_32_layers_dynamic": len(stores) == 32,
            "all_loaded_shards_verified": all(
                event["expert"] in stores[event["layer"]].verified for event in events
            ),
            "real_nonresident_faults": bool(miss_events),
            "all_generated_tokens_match": all_output_match,
            "model_and_evidence_on_external_storage": all(
                root in path.parents for path in (model_path, profile_path, manifest_path)
            ),
        },
        "claim_boundary": "End-to-end all-layer generation with real content-addressed SD expert loads. Logical requested bytes are measured from shard files; physical device reads and cold-cache state are not controlled.",
    }
    output = args.output or root / "experiments" / "real-moe-end-to-end-fault-in-v1.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "output": str(output),
        "all_generated_tokens_match": all_output_match,
        "nonresident_fault_events": len(miss_events),
        "logical_bytes_requested": report["storage"]["logical_bytes_requested"],
        "resident_cache_logical_bytes": report["storage"]["resident_cache_logical_bytes"],
        "mps_reduction_after_expert_removal_bytes": report["memory"]["mps_reduction_after_expert_removal_bytes"],
        "mps_reduction_after_dynamic_run_bytes": report["memory"]["mps_reduction_after_dynamic_run_bytes"],
        "timing": report["timing"],
        "integrity": report["integrity"],
    }
    print(json.dumps(summary, indent=2))
    return 0 if all(report["integrity"].values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
