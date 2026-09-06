#!/usr/bin/env python3
"""Test layer-scoped eviction and one-layer-ahead SD expert prefetch."""

from __future__ import annotations

import argparse
from concurrent.futures import Future, ThreadPoolExecutor
import gc
import hashlib
import json
from pathlib import Path
import statistics
import threading
import time
from typing import Any

import psutil
import torch
import torch.nn.functional as functional
from safetensors.torch import load_file
from transformers import AutoModelForCausalLM, AutoTokenizer

from backend.modules.aion_inference import AdaptiveInferenceRuntime, build_expert_prefetch_plan
from backend.scripts.run_aion_moe_end_to_end_fault_in import _memory_snapshot, _sha256


PROMPTS = (
    "Explain how a 7 percent tax changes a quoted price without calculating it.",
    "Human review is required and payment is forbidden. What can happen next?",
)
CONDITIONS = (
    "layer_scoped_demand",
    "glyph_layer_ahead_topk",
    "live_router_bounded_retention",
)


def _chat_tokens(tokenizer, prompt: str) -> dict[str, torch.Tensor]:
    encoded = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}],
        add_generation_prompt=True,
        tokenize=True,
        return_tensors="pt",
        return_dict=True,
    )
    return {key: value.to("mps") for key, value in encoded.items()}


class LayerScopedStore:
    def __init__(self, layer: int, index: dict[str, Any]) -> None:
        self.layer = layer
        self.entries = {int(entry["expert"]): entry for entry in index["experts"]}
        self.verified: set[int] = set()
        self.cpu_prefetch: dict[int, tuple[torch.Tensor, torch.Tensor]] = {}
        self.active: dict[int, tuple[torch.Tensor, torch.Tensor]] = {}
        self.retained: dict[int, tuple[torch.Tensor, torch.Tensor]] = {}
        self.events: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def preverify(self, root: Path) -> None:
        for expert, entry in self.entries.items():
            path = Path(entry["path"])
            if root not in path.resolve().parents or _sha256(path) != entry["sha256"]:
                raise RuntimeError(f"expert integrity failed: layer {self.layer}, expert {expert}")
            self.verified.add(expert)

    def prefetch_to_cpu(self, experts: tuple[int, ...]) -> dict[str, Any]:
        started = time.perf_counter()
        loaded: dict[int, tuple[torch.Tensor, torch.Tensor]] = {}
        logical_bytes = 0
        for expert in experts:
            entry = self.entries[expert]
            tensors = load_file(Path(entry["path"]), device="cpu")
            loaded[expert] = (tensors["input_linear.weight"], tensors["output_linear.weight"])
            logical_bytes += int(entry["bytes"])
        with self._lock:
            self.cpu_prefetch.update(loaded)
        event = {
            "kind": "cpu_layer_ahead_prefetch",
            "layer": self.layer,
            "experts": len(loaded),
            "logical_bytes": logical_bytes,
            "seconds": time.perf_counter() - started,
        }
        self.events.append(event)
        return event

    def activate(
        self,
        experts: tuple[int, ...],
        device: torch.device,
        dtype: torch.dtype,
    ) -> dict[int, tuple[torch.Tensor, torch.Tensor]]:
        started = time.perf_counter()
        prefetched_hits = 0
        retained_hits = 0
        demand_bytes = 0
        for expert in experts:
            retained_weights = self.retained.get(expert)
            if retained_weights is not None:
                self.active[expert] = retained_weights
                retained_hits += 1
                continue
            with self._lock:
                cpu_weights = self.cpu_prefetch.pop(expert, None)
            if cpu_weights is None:
                entry = self.entries[expert]
                tensors = load_file(Path(entry["path"]), device="cpu")
                cpu_weights = (tensors["input_linear.weight"], tensors["output_linear.weight"])
                demand_bytes += int(entry["bytes"])
            else:
                prefetched_hits += 1
            self.active[expert] = (
                cpu_weights[0].to(device=device, dtype=dtype),
                cpu_weights[1].to(device=device, dtype=dtype),
            )
        torch.mps.synchronize()
        self.events.append({
            "kind": "layer_activation",
            "layer": self.layer,
            "required_experts": len(experts),
            "prefetched_hits": prefetched_hits,
            "retained_hits": retained_hits,
            "demand_faults": len(experts) - prefetched_hits - retained_hits,
            "demand_logical_bytes": demand_bytes,
            "seconds": time.perf_counter() - started,
        })
        return self.active

    def release_layer(self, retain: tuple[int, ...] = ()) -> None:
        self.retained = {expert: self.active[expert] for expert in retain if expert in self.active}
        self.active.clear()
        with self._lock:
            self.cpu_prefetch.clear()

    def clear_all(self) -> None:
        self.active.clear()
        self.retained.clear()
        with self._lock:
            self.cpu_prefetch.clear()


class LayerAheadCoordinator:
    def __init__(
        self,
        stores: list[LayerScopedStore],
        plan: tuple[tuple[int, ...], ...],
    ) -> None:
        self.stores = stores
        self.plan = plan
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="aion-layer-ahead")
        self.futures: dict[int, Future] = {}
        self.wait_seconds: list[float] = []
        self.peak_mps_bytes = 0
        self.peak_rss_bytes = 0

    def schedule(self, layer: int) -> None:
        if layer >= len(self.stores) or not self.plan[layer] or layer in self.futures:
            return
        self.futures[layer] = self.executor.submit(
            self.stores[layer].prefetch_to_cpu, self.plan[layer]
        )

    def acquire(self, layer: int) -> None:
        future = self.futures.pop(layer, None)
        if future is None:
            return
        started = time.perf_counter()
        future.result()
        self.wait_seconds.append(time.perf_counter() - started)

    def observe_memory(self) -> None:
        self.peak_mps_bytes = max(self.peak_mps_bytes, torch.mps.current_allocated_memory())
        self.peak_rss_bytes = max(self.peak_rss_bytes, psutil.Process().memory_info().rss)

    def close(self) -> None:
        self.executor.shutdown(wait=True)


def _layer_scoped_forward(
    block,
    store: LayerScopedStore,
    coordinator: LayerAheadCoordinator,
    *,
    retain_live_router_topk: bool,
):
    router = block.router
    activation = block.activation
    input_size = block.input_size

    def forward(layer_input):
        coordinator.acquire(store.layer)
        coordinator.schedule(store.layer + 1)
        batch_size, length, embedding_size = layer_input.size()
        flattened = layer_input.reshape(-1, embedding_size)
        _, batch_index, batch_gates, expert_size, router_logits = router(flattened)
        expert_inputs = flattened[batch_index]
        input_list = expert_inputs.split(expert_size, dim=0)
        required = tuple(expert for expert, value in enumerate(input_list) if value.shape[0])
        weights = store.activate(required, layer_input.device, layer_input.dtype)
        coordinator.observe_memory()
        output_list = []
        for expert, expert_input in enumerate(input_list):
            if expert_input.shape[0] == 0:
                output_list.append(torch.empty(
                    (0, input_size), dtype=layer_input.dtype, device=layer_input.device
                ))
                continue
            input_weight, output_weight = weights[expert]
            hidden = functional.linear(expert_input, input_weight)
            gate_half, value_half = hidden.chunk(2, dim=-1)
            output_list.append(functional.linear(activation(gate_half) * value_half, output_weight))
        expert_outputs = torch.cat(output_list, dim=0) * batch_gates[:, None]
        zeros = torch.zeros(
            (batch_size * length, input_size),
            dtype=expert_outputs.dtype,
            device=expert_outputs.device,
        )
        result = zeros.index_add(0, batch_index, expert_outputs).view(batch_size, length, input_size)
        retain = ()
        if retain_live_router_topk:
            retain = tuple(
                sorted(router_logits[-1].topk(router.top_k, dim=-1).indices.tolist())
            )
        store.release_layer(retain)
        return result

    return forward


def _canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--shard-manifest", type=Path, required=True)
    parser.add_argument("--request-scope-reference", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--prefetch-experts-per-layer", type=int, default=8)
    parser.add_argument("--generated-tokens", type=int, default=2)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = args.storage_root.resolve()
    paths = tuple(path.resolve() for path in (
        args.model_path, args.profile, args.shard_manifest, args.request_scope_reference
    ))
    if any(root not in path.parents for path in paths):
        raise SystemExit("all models, profiles, shards, controls and evidence must reside on external storage")
    if not torch.backends.mps.is_available():
        raise SystemExit("Apple Metal/MPS is required")
    output = args.output or root / "experiments" / f"{args.run_id}.json"
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")

    model_path, profile_path, manifest_path, reference_path = paths
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    if not all(manifest["integrity"].values()):
        raise RuntimeError("shard manifest integrity gate failed")

    evidence_root = root / "runtime-evidence" / args.run_id
    runtime = AdaptiveInferenceRuntime(
        replay_path=evidence_root / "replay.sqlite3",
        trace_path=evidence_root / "trace.jsonl",
    )
    requests = []
    for prompt in PROMPTS:
        routed = runtime.route(prompt)
        prediction = dict(routed.proof_receipt["model_route_prediction"])
        plan = build_expert_prefetch_plan(
            profile,
            prediction["expert_prefetch_profile"],
            coverage_target=1.0,
            max_experts_per_layer=args.prefetch_experts_per_layer,
        )
        requests.append({
            "public_prompt": prompt,
            "glyph_address": routed.glyph_address,
            "model_input": routed.fallback_prompt,
            "prediction": prediction,
            "plan": plan,
        })

    checkpoint_started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        local_files_only=True,
        dtype=torch.float16,
        device_map={"": "mps"},
        low_cpu_mem_usage=True,
    ).eval()
    checkpoint_load_seconds = time.perf_counter() - checkpoint_started

    def generate(prompt: str) -> dict[str, Any]:
        inputs = _chat_tokens(tokenizer, prompt)
        started = time.perf_counter()
        with torch.inference_mode():
            generated = model.generate(
                **inputs,
                do_sample=False,
                max_new_tokens=args.generated_tokens,
                use_cache=True,
                return_dict_in_generate=True,
                output_scores=True,
                pad_token_id=tokenizer.eos_token_id,
            )
        torch.mps.synchronize()
        continuation = generated.sequences[0, inputs["input_ids"].shape[1]:].detach().cpu()
        logits = generated.scores[0][0].detach().float().cpu()
        return {
            "token_ids": continuation.tolist(),
            "text": tokenizer.decode(continuation),
            "first_token_id": int(logits.argmax()),
            "first_token_logits": logits,
            "seconds": time.perf_counter() - started,
        }

    unrestricted = [generate(request["model_input"]) for request in requests]
    unrestricted_memory = _memory_snapshot("after_unrestricted")

    layers = list(model.model.layers)
    stores: list[LayerScopedStore] = []
    for layer_number, (layer, manifest_layer) in enumerate(zip(layers, manifest["layers"], strict=True)):
        index_path = Path(manifest_layer["index_path"])
        if _sha256(index_path) != manifest_layer["index_sha256"]:
            raise RuntimeError(f"layer index integrity failed: {layer_number}")
        store = LayerScopedStore(layer_number, json.loads(index_path.read_text(encoding="utf-8")))
        stores.append(store)
        layer.block_sparse_moe.input_linear = None
        layer.block_sparse_moe.output_linear = None
    gc.collect()
    torch.mps.empty_cache()
    stripped_memory = _memory_snapshot("expert_tensors_removed")

    verification_started = time.perf_counter()
    for store in stores:
        store.preverify(root)
    verification_seconds = time.perf_counter() - verification_started

    reference_trials = {
        (trial["public_prompt"], trial["condition"]): trial for trial in reference["trials"]
    }
    trials = []
    for request_number, (request, control) in enumerate(zip(requests, unrestricted, strict=True)):
        plans = {
            "layer_scoped_demand": tuple(() for _ in stores),
            "glyph_layer_ahead_topk": request["plan"].experts_by_layer,
            "live_router_bounded_retention": tuple(() for _ in stores),
        }
        for condition in CONDITIONS:
            for store in stores:
                store.clear_all()
            gc.collect()
            torch.mps.empty_cache()
            event_starts = [len(store.events) for store in stores]
            coordinator = LayerAheadCoordinator(stores, plans[condition])
            coordinator.schedule(0)
            for layer, store in zip(layers, stores, strict=True):
                layer.block_sparse_moe.forward = _layer_scoped_forward(
                    layer.block_sparse_moe,
                    store,
                    coordinator,
                    retain_live_router_topk=condition == "live_router_bounded_retention",
                )
            result = generate(request["model_input"])
            coordinator.close()
            events = [
                event
                for store, start in zip(stores, event_starts, strict=True)
                for event in store.events[start:]
            ]
            prefetch_events = [event for event in events if event["kind"] == "cpu_layer_ahead_prefetch"]
            activation_events = [event for event in events if event["kind"] == "layer_activation"]
            logits = result.pop("first_token_logits")
            reference_trial = reference_trials[(request["public_prompt"], "no_prefetch")]
            trials.append({
                "request_number": request_number,
                "public_prompt": request["public_prompt"],
                "predicted_profile": request["prediction"]["expert_prefetch_profile"],
                "condition": condition,
                "plan_sha256": request["plan"].plan_sha256 if condition == "glyph_layer_ahead_topk" else None,
                "generation_seconds": result["seconds"],
                "reference_request_scoped_seconds": reference_trial["generation_seconds"],
                "peak_mps_bytes": coordinator.peak_mps_bytes,
                "reference_request_scoped_mps_bytes": reference_trial["mps_after_generation_bytes"],
                "peak_rss_bytes": coordinator.peak_rss_bytes,
                "prefetch_events": len(prefetch_events),
                "prefetch_logical_bytes": sum(event["logical_bytes"] for event in prefetch_events),
                "prefetch_worker_seconds": sum(event["seconds"] for event in prefetch_events),
                "prefetch_wait_seconds": sum(coordinator.wait_seconds),
                "required_expert_activations": sum(event["required_experts"] for event in activation_events),
                "prefetched_hits": sum(event["prefetched_hits"] for event in activation_events),
                "retained_hits": sum(event["retained_hits"] for event in activation_events),
                "demand_faults": sum(event["demand_faults"] for event in activation_events),
                "demand_logical_bytes": sum(event["demand_logical_bytes"] for event in activation_events),
                "token_ids": result["token_ids"],
                "text": result["text"],
                "token_ids_exact_match": result["token_ids"] == control["token_ids"],
                "first_token_id_match": result["first_token_id"] == control["first_token_id"],
                "first_token_max_absolute_logit_error": float(
                    (logits - control["first_token_logits"]).abs().max().item()
                ),
            })
            del logits
            for store in stores:
                store.clear_all()
            gc.collect()
            torch.mps.empty_cache()

    for control in unrestricted:
        control.pop("first_token_logits")
    aggregates = {}
    for condition in CONDITIONS:
        group = [trial for trial in trials if trial["condition"] == condition]
        aggregates[condition] = {
            "median_generation_seconds": statistics.median(item["generation_seconds"] for item in group),
            "maximum_peak_mps_bytes": max(item["peak_mps_bytes"] for item in group),
            "total_prefetch_logical_bytes": sum(item["prefetch_logical_bytes"] for item in group),
            "total_demand_logical_bytes": sum(item["demand_logical_bytes"] for item in group),
            "total_logical_bytes": sum(
                item["prefetch_logical_bytes"] + item["demand_logical_bytes"] for item in group
            ),
            "total_prefetch_wait_seconds": sum(item["prefetch_wait_seconds"] for item in group),
            "total_required_expert_activations": sum(item["required_expert_activations"] for item in group),
            "total_prefetched_hits": sum(item["prefetched_hits"] for item in group),
            "total_retained_hits": sum(item["retained_hits"] for item in group),
            "all_outputs_exact": all(item["token_ids_exact_match"] for item in group),
        }
    reference_group = [reference_trials[(prompt, "no_prefetch")] for prompt in PROMPTS]
    reference_summary = {
        "median_generation_seconds": statistics.median(item["generation_seconds"] for item in reference_group),
        "maximum_mps_after_generation_bytes": max(item["mps_after_generation_bytes"] for item in reference_group),
    }
    layer_demand = aggregates["layer_scoped_demand"]
    layer_ahead = aggregates["glyph_layer_ahead_topk"]
    live_retention = aggregates["live_router_bounded_retention"]
    outcomes = {
        "layer_scoped_peak_mps_reduction_percent_vs_request_scoped": 100.0 * (
            1.0 - layer_demand["maximum_peak_mps_bytes"] / reference_summary["maximum_mps_after_generation_bytes"]
        ),
        "layer_ahead_peak_mps_reduction_percent_vs_request_scoped": 100.0 * (
            1.0 - layer_ahead["maximum_peak_mps_bytes"] / reference_summary["maximum_mps_after_generation_bytes"]
        ),
        "layer_ahead_generation_time_change_percent_vs_layer_demand": 100.0 * (
            layer_ahead["median_generation_seconds"] / layer_demand["median_generation_seconds"] - 1.0
        ),
        "layer_ahead_logical_byte_change_percent_vs_layer_demand": 100.0 * (
            layer_ahead["total_logical_bytes"] / layer_demand["total_logical_bytes"] - 1.0
        ),
        "meaningful_memory_gate_passed": (
            layer_ahead["maximum_peak_mps_bytes"] <= reference_summary["maximum_mps_after_generation_bytes"] * 0.50
        ),
        "meaningful_speed_gate_passed": (
            layer_ahead["median_generation_seconds"] <= layer_demand["median_generation_seconds"] * 0.95
        ),
        "live_retention_peak_mps_reduction_percent_vs_request_scoped": 100.0 * (
            1.0 - live_retention["maximum_peak_mps_bytes"]
            / reference_summary["maximum_mps_after_generation_bytes"]
        ),
        "live_retention_time_change_percent_vs_layer_demand": 100.0 * (
            live_retention["median_generation_seconds"] / layer_demand["median_generation_seconds"] - 1.0
        ),
        "live_retention_time_change_percent_vs_request_scoped": 100.0 * (
            live_retention["median_generation_seconds"] / reference_summary["median_generation_seconds"] - 1.0
        ),
        "live_retention_peak_mps_bytes_saved_vs_request_scoped": (
            reference_summary["maximum_mps_after_generation_bytes"]
            - live_retention["maximum_peak_mps_bytes"]
        ),
        "live_retention_meaningful_memory_gate_passed": (
            live_retention["maximum_peak_mps_bytes"]
            <= reference_summary["maximum_mps_after_generation_bytes"] * 0.50
        ),
        "live_retention_speed_recovery_gate_passed": (
            live_retention["median_generation_seconds"] <= layer_demand["median_generation_seconds"] * 0.95
        ),
    }
    integrity = {
        "all_32_layers_scoped": len(stores) == 32,
        "all_1280_shards_preverified": sum(len(store.verified) for store in stores) == 1280,
        "topk_plan_capped_per_layer": all(
            max(request["plan"].expert_count_by_layer) == args.prefetch_experts_per_layer
            for request in requests
        ),
        "all_outputs_match_unrestricted": all(trial["token_ids_exact_match"] for trial in trials),
        "all_evidence_on_external_storage": all(
            root in path.resolve().parents
            for path in (model_path, profile_path, manifest_path, reference_path, output)
        ),
    }
    report = {
        "schema_version": "aion.layer_scoped_moe_experiment.v1",
        "run_id": args.run_id,
        "storage_root": str(root),
        "model_path": str(model_path),
        "profile_path": str(profile_path),
        "manifest_path": str(manifest_path),
        "request_scope_reference_path": str(reference_path),
        "request_scope_reference_sha256": _sha256(reference_path),
        "method": {
            "prompts": PROMPTS,
            "conditions": CONDITIONS,
            "generated_tokens": args.generated_tokens,
            "one_layer_ahead_cpu_prefetch": True,
            "prefetch_experts_per_layer": args.prefetch_experts_per_layer,
            "immediate_layer_eviction": True,
            "live_router_retention_experts_per_layer": 8,
            "os_file_cache_controlled": False,
        },
        "requests": [{
            "public_prompt": request["public_prompt"],
            "glyph_address": request["glyph_address"],
            "prediction": request["prediction"],
            "plan": request["plan"].to_dict(),
        } for request in requests],
        "unrestricted": unrestricted,
        "trials": trials,
        "aggregates": aggregates,
        "request_scoped_reference": reference_summary,
        "outcomes": outcomes,
        "timing": {
            "checkpoint_load_seconds": checkpoint_load_seconds,
            "shard_preverification_seconds": verification_seconds,
        },
        "memory": {
            "unrestricted": unrestricted_memory,
            "experts_removed": stripped_memory,
        },
        "integrity": integrity,
        "claim_boundary": (
            "This measures exact two-prompt Granite generation with immediate per-layer expert eviction "
            "and a single CPU I/O worker preparing a capped next-layer plan from SD-backed shards. "
            "The request-scoped control is a prior same-host run. macOS file-cache state, physical SD "
            "reads and repeated-run dispersion are not controlled."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "report_sha256": report["report_sha256"],
        "aggregates": aggregates,
        "request_scoped_reference": reference_summary,
        "outcomes": outcomes,
        "integrity": integrity,
    }, indent=2))
    return 0 if all(integrity.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
