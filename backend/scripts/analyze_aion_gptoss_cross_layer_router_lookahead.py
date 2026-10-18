#!/usr/bin/env python3
"""Measure value-preserving Colibri-style cross-layer router lookahead.

This is an offline admission gate.  It performs no expert reads and cannot
change model output.  For layer L it applies layer L+1's real router to the
post-attention residual already available at L, then compares the prediction
with the captured authoritative route at L+1.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from backend.modules.aion_inference.expert_frame_gguf_reader import ExpertFrameGGUFReader
from backend.modules.aion_inference.gguf_stream_index import read_gguf_stream_index


WIDTH = 2880
EXPERTS = 128
LAYERS = 36
EPSILON = np.float32(1.0e-5)


def canonical_sha(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def topk(values: np.ndarray, count: int) -> list[int]:
    return np.argsort(values, kind="stable")[-count:][::-1].astype(int).tolist()


def rms_norm(values: np.ndarray, weight: np.ndarray) -> np.ndarray:
    # Keep the operations F32 to match the runtime's router input closely.
    mean_square = np.mean(values * values, dtype=np.float32)
    return values * np.float32(1.0 / np.sqrt(mean_square + EPSILON)) * weight


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--capture", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prefetch-k", type=int, action="append", default=[])
    args = parser.parse_args()
    ks = sorted(set(args.prefetch_k or [4, 6, 8]))
    if not ks or min(ks) < 1 or max(ks) > EXPERTS:
        raise SystemExit("prefetch-k must stay within 1..128")

    manifest = json.loads(args.manifest.read_text())
    readers: dict[str, ExpertFrameGGUFReader] = {}
    tensor_index: dict[str, tuple[str, dict]] = {}
    for source in manifest["verified_sources"]:
        reader = ExpertFrameGGUFReader(args.manifest, source["name"], 64 * 1024 * 1024)
        readers[source["name"]] = reader
        index = read_gguf_stream_index(reader, int(source["size"]))
        for tensor in index["tensors"]:
            tensor_index[tensor["name"]] = (source["name"], tensor)

    def tensor_f32(name: str) -> np.ndarray:
        source, item = tensor_index[name]
        if int(item["ggml_type"]) != 0:
            raise SystemExit(f"{name} is not F32 (GGML type {item['ggml_type']})")
        raw = readers[source].read_at(int(item["absolute_offset"]), int(item["byte_length"]))
        return np.frombuffer(raw, dtype="<f4").copy()

    norms = []
    router_weights = []
    router_biases = []
    for layer in range(LAYERS):
        norms.append(tensor_f32(f"blk.{layer}.post_attention_norm.weight"))
        router_weights.append(
            tensor_f32(f"blk.{layer}.ffn_gate_inp.weight").reshape(EXPERTS, WIDTH)
        )
        router_biases.append(tensor_f32(f"blk.{layer}.ffn_gate_inp.bias"))

    family_rows = []
    aggregate = {k: {"hits": 0, "predicted": 0, "required": 0, "observations": 0} for k in ks}
    baseline_aggregate = {"hits": 0, "predicted": 0, "required": 0, "observations": 0}
    current_router_checks = 0
    current_router_mismatches = 0
    per_layer = {layer: {k: {"hits": 0, "predicted": 0, "required": 0, "observations": 0} for k in ks}
                 for layer in range(LAYERS - 1)}

    for capture in args.capture:
        metadata = sorted(capture.glob("position-*-layer-*.json"))
        records: dict[tuple[int, int], dict] = {}
        for path in metadata:
            item = json.loads(path.read_text())
            records[(int(item["position"]), int(item["layer"]))] = item
        positions = sorted({position for position, _ in records})
        family = {k: {"hits": 0, "predicted": 0, "required": 0, "observations": 0} for k in ks}
        baseline = {"hits": 0, "predicted": 0, "required": 0, "observations": 0}
        for position in positions:
            for layer in range(LAYERS - 1):
                current = records[(position, layer)]
                following = records[(position, layer + 1)]
                ffn = np.fromfile(capture / f"position-{position}-layer-{layer}-ffn.bin", dtype="<f4")
                router = np.fromfile(capture / f"position-{position}-layer-{layer}-router.bin", dtype="<f4")
                if ffn.size != WIDTH or router.size != WIDTH:
                    raise SystemExit(f"invalid capture width at {capture}, position {position}, layer {layer}")

                # Validate that the extracted router tensors reproduce each captured route.
                current_route = topk(router_weights[layer] @ router + router_biases[layer], 4)
                current_router_checks += 1
                if current_route != list(map(int, current["route"])):
                    current_router_mismatches += 1

                # Colibri PILOT: use the current post-attention residual as a stale
                # proxy for what the following layer will route after its attention.
                proxy = rms_norm(ffn, norms[layer + 1])
                logits = router_weights[layer + 1] @ proxy + router_biases[layer + 1]
                required = set(map(int, following["route"]))
                repeated = set(map(int, current["route"]))
                baseline["hits"] += len(repeated & required)
                baseline["predicted"] += len(repeated)
                baseline["required"] += len(required)
                baseline["observations"] += 1
                for k in ks:
                    predicted = set(topk(logits, k))
                    target = family[k]
                    target["hits"] += len(predicted & required)
                    target["predicted"] += len(predicted)
                    target["required"] += len(required)
                    target["observations"] += 1
                    layer_target = per_layer[layer][k]
                    layer_target["hits"] += len(predicted & required)
                    layer_target["predicted"] += len(predicted)
                    layer_target["required"] += len(required)
                    layer_target["observations"] += 1
        for k in ks:
            for name in aggregate[k]:
                aggregate[k][name] += family[k][name]
        for name in baseline_aggregate:
            baseline_aggregate[name] += baseline[name]
        family_rows.append({"capture": str(capture.resolve()), "positions": positions,
                            "same-layer-route-baseline": baseline, "metrics": family})

    def finish(metrics: dict) -> dict:
        value = dict(metrics)
        value["required_expert_recall"] = value["hits"] / value["required"] if value["required"] else 0.0
        value["prefetch_precision"] = value["hits"] / value["predicted"] if value["predicted"] else 0.0
        value["mean_useful_experts_per_layer"] = value["hits"] / value["observations"] if value["observations"] else 0.0
        value["mean_wasted_experts_per_layer"] = ((value["predicted"] - value["hits"]) / value["observations"]
                                                   if value["observations"] else 0.0)
        return value

    for family in family_rows:
        family["metrics"] = {str(k): finish(v) for k, v in family["metrics"].items()}
        family["same-layer-route-baseline"] = finish(family["same-layer-route-baseline"])
    result = {
        "schema": "aion.gptoss-120b-cross-layer-router-lookahead-gate.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "OFFLINE_MEASUREMENT_COMPLETE",
        "model": "GPT-OSS 120B Q4_K_M",
        "method": "Apply layer L+1's original router to layer L's captured post-attention residual; compare only with the authoritative L+1 top-four route.",
        "value_preserving_boundary": "This offline gate performs no expert prefetch and changes no router, weight, gate, hidden state, logit, or token. Any future runtime candidate must retain authoritative demand fallback and prove exact equivalence separately.",
        "manifest": str(args.manifest.resolve()),
        "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "current_router_reproduction": {
            "checks": current_router_checks,
            "mismatches": current_router_mismatches,
            "passed": current_router_mismatches == 0,
        },
        "families": family_rows,
        "same-layer-route-baseline": finish(baseline_aggregate),
        "aggregate": {str(k): finish(v) for k, v in aggregate.items()},
        "per_source_layer": {
            str(layer): {str(k): finish(v) for k, v in values.items()}
            for layer, values in per_layer.items()
        },
        "source_inspiration": {
            "project": "Colibri",
            "repository": "https://github.com/JustVugg/colibri",
            "upstream_commit": "fd93c41aa6ae2c7d1cc1a1e2d6b79dbe6d341708",
        },
    }
    result["canonical_sha256"] = canonical_sha(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(args.output), "aggregate": result["aggregate"],
                      "router_reproduction": result["current_router_reproduction"],
                      "canonical_sha256": result["canonical_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
