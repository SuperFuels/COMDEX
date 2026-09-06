#!/usr/bin/env python3
"""Compare granular expert shards with coalesced per-layer packs."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
import statistics
import time
from typing import Any

import torch
from safetensors import safe_open
from transformers import AutoModelForCausalLM, AutoTokenizer

from backend.modules.aion_inference import AdaptiveInferenceRuntime
from backend.scripts.run_aion_layer_scoped_moe_experiment import (
    LayerAheadCoordinator,
    LayerScopedStore,
    _chat_tokens,
    _layer_scoped_forward,
)
from backend.scripts.run_aion_moe_end_to_end_fault_in import _memory_snapshot, _sha256


PROMPT = "Human review is required and payment is forbidden. What can happen next?"
CONDITION_ORDER = ("granular", "packed", "packed", "granular")


def _canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class PackedLayerScopedStore(LayerScopedStore):
    """Read multiple selected experts through one layer-pack handle."""

    def __init__(self, layer: int, index: dict[str, Any], pack: dict[str, Any]) -> None:
        super().__init__(layer, index)
        self.pack = pack
        self.pack_opens = 0
        self.tensor_reads = 0

    def preverify(self, root: Path) -> None:
        path = Path(self.pack["path"])
        if root not in path.resolve().parents or _sha256(path) != self.pack["sha256"]:
            raise RuntimeError(f"layer pack integrity failed: layer {self.layer}")
        if int(self.pack["experts"]) != len(self.entries):
            raise RuntimeError(f"layer pack expert count failed: layer {self.layer}")
        self.verified.update(self.entries)

    def _load_cpu_many(
        self,
        experts: tuple[int, ...],
    ) -> dict[int, tuple[torch.Tensor, torch.Tensor]]:
        if not experts:
            return {}
        loaded = {}
        with safe_open(Path(self.pack["path"]), framework="pt", device="cpu") as handle:
            self.pack_opens += 1
            for expert in experts:
                prefix = f"experts.{expert}"
                loaded[expert] = (
                    handle.get_tensor(f"{prefix}.input_linear.weight"),
                    handle.get_tensor(f"{prefix}.output_linear.weight"),
                )
                self.tensor_reads += 2
        return loaded


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--shard-manifest", type=Path, required=True)
    parser.add_argument("--pack-manifest", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--generated-tokens", type=int, default=16)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = args.storage_root.resolve()
    model_path = args.model_path.resolve()
    profile_path = args.profile.resolve()
    shard_manifest_path = args.shard_manifest.resolve()
    pack_manifest_path = args.pack_manifest.resolve()
    output = (args.output or root / "experiments" / f"{args.run_id}.json").resolve()
    checked_paths = (model_path, profile_path, shard_manifest_path, pack_manifest_path, output)
    if any(root not in path.parents for path in checked_paths):
        raise SystemExit("model, manifests and evidence must reside on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    if not torch.backends.mps.is_available():
        raise SystemExit("Apple Metal/MPS is required")

    shard_manifest = json.loads(shard_manifest_path.read_text(encoding="utf-8"))
    pack_manifest = json.loads(pack_manifest_path.read_text(encoding="utf-8"))
    if not all(shard_manifest["integrity"].values()) or not all(pack_manifest["integrity"].values()):
        raise RuntimeError("manifest integrity gate failed")
    if pack_manifest["source_manifest_sha256"] != _sha256(shard_manifest_path):
        raise RuntimeError("pack/source manifest binding failed")

    evidence_root = root / "runtime-evidence" / args.run_id
    runtime = AdaptiveInferenceRuntime(
        replay_path=evidence_root / "replay.sqlite3",
        trace_path=evidence_root / "trace.jsonl",
    )
    routed = runtime.route(PROMPT)
    if not routed.model_call_required or not routed.fallback_prompt:
        raise RuntimeError("test prompt did not reach the model fallback")

    load_started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        local_files_only=True,
        dtype=torch.float16,
        device_map={"": "mps"},
        low_cpu_mem_usage=True,
    ).eval()
    checkpoint_load_seconds = time.perf_counter() - load_started

    def generate() -> dict[str, Any]:
        inputs = _chat_tokens(tokenizer, routed.fallback_prompt)
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
        return {
            "token_ids": continuation.tolist(),
            "text": tokenizer.decode(continuation),
            "scores": [score[0].detach().float().cpu() for score in generated.scores],
            "seconds": time.perf_counter() - started,
        }

    control = generate()
    unrestricted_memory = _memory_snapshot("after_unrestricted")
    layers = list(model.model.layers)
    if len(layers) != 32 or len(shard_manifest["layers"]) != 32 or len(pack_manifest["layers"]) != 32:
        raise RuntimeError("expected 32 model, shard and pack layers")

    indexes = []
    for layer_number, source_layer in enumerate(shard_manifest["layers"]):
        index_path = Path(source_layer["index_path"])
        if root not in index_path.resolve().parents or _sha256(index_path) != source_layer["index_sha256"]:
            raise RuntimeError(f"layer index integrity failed: {layer_number}")
        indexes.append(json.loads(index_path.read_text(encoding="utf-8")))
        layers[layer_number].block_sparse_moe.input_linear = None
        layers[layer_number].block_sparse_moe.output_linear = None
    gc.collect()
    torch.mps.empty_cache()
    stripped_memory = _memory_snapshot("expert_tensors_removed")

    stores_by_condition: dict[str, list[LayerScopedStore]] = {
        "granular": [LayerScopedStore(i, index) for i, index in enumerate(indexes)],
        "packed": [
            PackedLayerScopedStore(i, index, pack)
            for i, (index, pack) in enumerate(zip(indexes, pack_manifest["layers"], strict=True))
        ],
    }
    verification = {}
    for condition, stores in stores_by_condition.items():
        started = time.perf_counter()
        for store in stores:
            store.preverify(root)
        verification[condition] = time.perf_counter() - started

    trials = []
    empty_plan = tuple(() for _ in layers)
    for sequence, condition in enumerate(CONDITION_ORDER):
        stores = stores_by_condition[condition]
        for store in stores:
            store.clear_all()
        gc.collect()
        torch.mps.empty_cache()
        event_starts = [len(store.events) for store in stores]
        before_pack_opens = sum(getattr(store, "pack_opens", 0) for store in stores)
        coordinator = LayerAheadCoordinator(stores, empty_plan)
        for layer, store in zip(layers, stores, strict=True):
            layer.block_sparse_moe.forward = _layer_scoped_forward(
                layer.block_sparse_moe, store, coordinator, retention_depth=2
            )
        result = generate()
        coordinator.close()
        events = [
            event
            for store, start in zip(stores, event_starts, strict=True)
            for event in store.events[start:]
        ]
        activations = [event for event in events if event["kind"] == "layer_activation"]
        errors = [
            float((observed - expected).abs().max().item())
            for observed, expected in zip(result["scores"], control["scores"], strict=True)
        ]
        trials.append({
            "sequence": sequence,
            "condition": condition,
            "seconds": result["seconds"],
            "peak_mps_bytes": coordinator.peak_mps_bytes,
            "peak_rss_bytes": coordinator.peak_rss_bytes,
            "demand_faults": sum(event["demand_faults"] for event in activations),
            "demand_logical_bytes": sum(event["demand_logical_bytes"] for event in activations),
            "retained_hits": sum(event["retained_hits"] for event in activations),
            "storage_open_operations": (
                sum(getattr(store, "pack_opens", 0) for store in stores) - before_pack_opens
                if condition == "packed"
                else sum(event["demand_faults"] for event in activations)
            ),
            "token_ids": result["token_ids"],
            "text": result["text"],
            "token_ids_exact_match": result["token_ids"] == control["token_ids"],
            "all_step_logits_exact_match": all(error == 0.0 for error in errors),
            "maximum_step_logit_error": max(errors, default=0.0),
        })
        for store in stores:
            store.clear_all()

    control.pop("scores")
    aggregates = {}
    for condition in ("granular", "packed"):
        group = [trial for trial in trials if trial["condition"] == condition]
        aggregates[condition] = {
            "median_seconds": statistics.median(trial["seconds"] for trial in group),
            "median_storage_open_operations": statistics.median(
                trial["storage_open_operations"] for trial in group
            ),
            "maximum_peak_mps_bytes": max(trial["peak_mps_bytes"] for trial in group),
            "all_outputs_exact": all(
                trial["token_ids_exact_match"] and trial["all_step_logits_exact_match"]
                for trial in group
            ),
        }
    granular, packed = aggregates["granular"], aggregates["packed"]
    outcomes = {
        "packed_time_change_percent_vs_granular": 100.0 * (
            packed["median_seconds"] / granular["median_seconds"] - 1.0
        ),
        "packed_open_operation_reduction_percent": 100.0 * (
            1.0 - packed["median_storage_open_operations"]
            / granular["median_storage_open_operations"]
        ),
        "packed_peak_mps_change_percent": 100.0 * (
            packed["maximum_peak_mps_bytes"] / granular["maximum_peak_mps_bytes"] - 1.0
        ),
    }
    integrity = {
        "abba_order_completed": [trial["condition"] for trial in trials] == list(CONDITION_ORDER),
        "all_32_layer_packs_verified": len(stores_by_condition["packed"]) == 32,
        "all_1280_experts_addressable": sum(
            len(store.verified) for store in stores_by_condition["packed"]
        ) == 1280,
        "all_token_ids_and_step_logits_exact": all(
            trial["token_ids_exact_match"] and trial["all_step_logits_exact_match"]
            for trial in trials
        ),
        "evidence_bound_to_source_manifest": (
            pack_manifest["source_manifest_sha256"] == _sha256(shard_manifest_path)
        ),
        "all_artifacts_on_external_storage": all(root in path.parents for path in checked_paths),
    }
    report = {
        "schema_version": "aion.moe_layer_pack_experiment.v1",
        "run_id": args.run_id,
        "storage_root": str(root),
        "model_path": str(model_path),
        "profile_path": str(profile_path),
        "profile_sha256": _sha256(profile_path),
        "shard_manifest_path": str(shard_manifest_path),
        "shard_manifest_sha256": _sha256(shard_manifest_path),
        "pack_manifest_path": str(pack_manifest_path),
        "pack_manifest_sha256": _sha256(pack_manifest_path),
        "gateway_trace_path": str(evidence_root / "trace.jsonl"),
        "gateway_trace_sha256": _sha256(evidence_root / "trace.jsonl"),
        "method": {
            "prompt": PROMPT,
            "generated_tokens": args.generated_tokens,
            "condition_order": CONDITION_ORDER,
            "retention_depth": 2,
            "same_loaded_model": True,
            "os_file_cache_controlled": False,
        },
        "gateway": {
            "glyph_address": routed.glyph_address,
            "model_input_sha256": hashlib.sha256(routed.fallback_prompt.encode("utf-8")).hexdigest(),
            "proof_receipt_sha256": routed.proof_receipt["proof_receipt_sha256"],
        },
        "control": control,
        "trials": trials,
        "aggregates": aggregates,
        "outcomes": outcomes,
        "timing": {"checkpoint_load_seconds": checkpoint_load_seconds, "verification_seconds": verification},
        "memory": {"unrestricted": unrestricted_memory, "experts_removed": stripped_memory},
        "integrity": integrity,
        "claim_boundary": (
            "This same-model ABBA comparison isolates expert file layout for one deterministic "
            "16-token request with a two-route LRU. It does not establish cold physical SD reads, "
            "population-level latency, energy savings, or transfer to other models and storage media."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "report_sha256": report["report_sha256"],
        "aggregates": aggregates,
        "outcomes": outcomes,
        "integrity": integrity,
    }, indent=2))
    return 0 if all(integrity.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
