#!/usr/bin/env python3
"""Shard one real Granite MoE layer and verify SD-backed expert fault-in."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
import statistics
import tempfile
import time
from typing import Callable

import torch
import torch.nn.functional as functional
from safetensors import safe_open
from safetensors.torch import load_file, save_file


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _checkpoint_tensor(model_path: Path, key: str) -> torch.Tensor:
    for checkpoint in sorted(model_path.glob("*.safetensors")):
        with safe_open(checkpoint, framework="pt", device="cpu") as handle:
            if key in handle.keys():
                return handle.get_tensor(key)
    raise KeyError(f"checkpoint tensor not found: {key}")


def _execute_layer(
    hidden: torch.Tensor,
    router_weight: torch.Tensor,
    experts_per_token: int,
    provider: Callable[[int], tuple[torch.Tensor, torch.Tensor]],
) -> tuple[torch.Tensor, list[int]]:
    logits = functional.linear(hidden, router_weight).float()
    top_logits, top_indices = logits.topk(experts_per_token, dim=1)
    gates = torch.softmax(top_logits, dim=1).to(hidden.dtype)
    output = torch.zeros_like(hidden)
    selected = sorted(set(top_indices.flatten().tolist()))
    for expert in selected:
        positions = (top_indices == expert).nonzero(as_tuple=False)
        token_indices, slots = positions[:, 0], positions[:, 1]
        input_weight, output_weight = provider(expert)
        projected = functional.linear(hidden[token_indices], input_weight)
        gate_half, value_half = projected.chunk(2, dim=-1)
        expert_output = functional.linear(functional.silu(gate_half) * value_half, output_weight)
        output.index_add_(0, token_indices, expert_output * gates[token_indices, slots, None])
    return output, selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=0)
    parser.add_argument("--tokens", type=int, default=4)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = args.storage_root.resolve()
    model_path, profile_path = args.model_path.resolve(), args.profile.resolve()
    if root not in model_path.parents or root not in profile_path.parents:
        raise SystemExit("model and profile must be inside the external storage root")
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    architecture = profile["architecture"]
    if not 0 <= args.layer < architecture["layers"]:
        raise SystemExit("layer is outside the checkpoint")
    resident = set(profile["training"]["resident_experts_by_layer"][args.layer])
    prefix = f"model.layers.{args.layer}.block_sparse_moe"
    input_weights = _checkpoint_tensor(model_path, f"{prefix}.input_linear.weight")
    output_weights = _checkpoint_tensor(model_path, f"{prefix}.output_linear.weight")
    router_weight = _checkpoint_tensor(model_path, f"{prefix}.router.layer.weight")

    shard_root = root / "expert-shards" / "granite-3.1-3b-a800m-instruct" / f"layer-{args.layer:02d}"
    blob_root = shard_root / "blobs"
    blob_root.mkdir(parents=True, exist_ok=True)
    entries = []
    for expert in range(architecture["experts_per_layer"]):
        tensors = {
            "input_linear.weight": input_weights[expert].contiguous(),
            "output_linear.weight": output_weights[expert].contiguous(),
        }
        with tempfile.NamedTemporaryFile(dir=blob_root, suffix=".safetensors", delete=False) as handle:
            temporary = Path(handle.name)
        save_file(tensors, temporary, metadata={"layer": str(args.layer), "expert": str(expert)})
        digest = _sha256(temporary)
        destination = blob_root / f"sha256-{digest}.safetensors"
        if destination.exists():
            temporary.unlink()
        else:
            temporary.replace(destination)
        entries.append({"expert": expert, "path": str(destination), "sha256": digest,
                        "bytes": destination.stat().st_size, "resident": expert in resident})
    index = {"schema_version": "aion.expert_shard_index.v1", "layer": args.layer,
             "model_path": str(model_path), "experts": entries}
    index_path = shard_root / "index.json"
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    torch.manual_seed(314159)
    hidden = torch.randn(args.tokens, architecture["hidden_size"], dtype=router_weight.dtype)
    reference_started = time.perf_counter()
    reference, selected = _execute_layer(
        hidden,
        router_weight,
        architecture["experts_selected_per_token"],
        lambda expert: (input_weights[expert], output_weights[expert]),
    )
    reference_seconds = time.perf_counter() - reference_started
    del input_weights, output_weights
    gc.collect()

    entry_by_expert = {entry["expert"]: entry for entry in entries}
    read_events: list[dict] = []

    def verified_load(expert: int, reason: str) -> tuple[torch.Tensor, torch.Tensor]:
        entry = entry_by_expert[expert]
        before = time.perf_counter()
        observed_hash = _sha256(Path(entry["path"]))
        if observed_hash != entry["sha256"]:
            raise RuntimeError(f"expert shard integrity failure: {expert}")
        tensors = load_file(entry["path"], device="cpu")
        elapsed = time.perf_counter() - before
        read_events.append({"expert": expert, "reason": reason, "bytes": entry["bytes"],
                            "seconds_including_hash_verification": elapsed})
        return tensors["input_linear.weight"], tensors["output_linear.weight"]

    preload_started = time.perf_counter()
    cache = {expert: verified_load(expert, "resident_preload") for expert in sorted(resident)}
    preload_seconds = time.perf_counter() - preload_started

    faulted: list[int] = []
    def provider(expert: int) -> tuple[torch.Tensor, torch.Tensor]:
        if expert not in cache:
            cache[expert] = verified_load(expert, "request_fault_in")
            faulted.append(expert)
        return cache[expert]

    execution_started = time.perf_counter()
    faulted_output, selected_again = _execute_layer(
        hidden, router_weight, architecture["experts_selected_per_token"], provider,
    )
    execution_seconds = time.perf_counter() - execution_started
    exact = torch.equal(reference, faulted_output)
    max_error = float((reference.float() - faulted_output.float()).abs().max().item())
    for expert in faulted:
        del cache[expert]

    resident_bytes = sum(entry["bytes"] for entry in entries if entry["resident"])
    fault_bytes = sum(entry_by_expert[expert]["bytes"] for expert in faulted)
    report = {
        "schema_version": "aion.real_moe_fault_in.v1",
        "storage_root": str(root), "model_path": str(model_path),
        "profile_path": str(profile_path), "profile_sha256": _sha256(profile_path),
        "shard_index": str(index_path), "shard_index_sha256": _sha256(index_path),
        "layer": args.layer,
        "method": {"synthetic_hidden_tokens": args.tokens, "random_seed": 314159,
                   "real_checkpoint_router_and_expert_weights": True,
                   "hash_verified_before_every_load": True},
        "routing": {"selected_experts": selected, "selected_experts_replay": selected_again,
                    "resident_experts": sorted(resident), "faulted_experts": faulted},
        "storage": {"expert_shards": len(entries), "total_shard_bytes": sum(e["bytes"] for e in entries),
                    "resident_shard_bytes": resident_bytes, "faulted_shard_bytes": fault_bytes,
                    "read_events": read_events},
        "timing": {"reference_seconds": reference_seconds, "resident_preload_seconds": preload_seconds,
                   "faulted_execution_seconds": execution_seconds,
                   "fault_read_median_seconds": statistics.median(
                       event["seconds_including_hash_verification"] for event in read_events
                       if event["reason"] == "request_fault_in"
                   ) if faulted else 0.0},
        "equivalence": {"exact_tensor_match": exact, "max_absolute_error": max_error},
        "integrity": {"all_shards_content_addressed": all(
            Path(entry["path"]).name == f"sha256-{entry['sha256']}.safetensors" for entry in entries),
            "model_profile_on_external_storage": root in profile_path.parents,
            "real_fault_occurred": bool(faulted), "route_reproduced": selected == selected_again,
            "output_exact": exact},
        "claim_boundary": "This is exact one-layer expert execution with real weights and synthetic hidden states. It proves SD-backed content-addressed fault-in mechanics, not whole-model memory reduction or end-to-end generation speed.",
    }
    output = args.output or root / "experiments" / "real-moe-fault-in-layer0-v1.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "selected_experts": selected,
                      "faulted_experts": faulted, "resident_shard_bytes": resident_bytes,
                      "faulted_shard_bytes": fault_bytes, "timing": report["timing"],
                      "equivalence": report["equivalence"], "integrity": report["integrity"]}, indent=2))
    return 0 if all(report["integrity"].values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
