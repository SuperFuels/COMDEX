"""Replay a captured Qwen prompt route through the bounded expert store."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from pathlib import Path

from .qwen_expert_glyph_store import QwenExpertGlyphStore


def _p95(values: list[float]) -> float:
    return sorted(values)[max(0, (95 * len(values) + 99) // 100 - 1)]


def run(manifest_path: Path, route_path: Path, capacity_bytes: int) -> dict:
    corpus = json.loads(route_path.read_text())
    if not corpus.get("complete") or len(corpus.get("layers", [])) != 48:
        raise ValueError("route corpus is incomplete")
    layer_seconds = []
    logical_bytes = 0
    with QwenExpertGlyphStore(manifest_path, capacity_bytes) as store:
        for layer_entry in corpus["layers"]:
            layer = int(layer_entry["layer"])
            started = time.perf_counter()
            for route in layer_entry["routes"]:
                values = store.get_layer_route(layer, [int(value) for value in route])
                logical_bytes += sum(len(part) for expert in values for part in expert)
            layer_seconds.append(time.perf_counter() - started)
        metrics = store.metrics()
    report = {
        "schema": "aion.qwen3moe.real-route-expert-store-gate.v1",
        "manifest_path": str(manifest_path.resolve()),
        "route_path": str(route_path.resolve()),
        "capacity_bytes": capacity_bytes,
        "execution_order": "prompt-layer-major",
        "layers": 48,
        "prompt_tokens": int(corpus["token_count"]),
        "route_count": sum(len(layer["routes"]) for layer in corpus["layers"]),
        "expert_accesses": sum(len(route) for layer in corpus["layers"]
                               for route in layer["routes"]),
        "logical_bytes_without_cache": logical_bytes,
        "physical_bytes": metrics["physical_bytes"],
        "physical_byte_reduction": 1 - metrics["physical_bytes"] / logical_bytes,
        "layer_seconds_p50": statistics.median(layer_seconds),
        "layer_seconds_p95_nearest_rank": _p95(layer_seconds),
        "total_store_seconds": sum(layer_seconds),
        "cache": metrics,
    }
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    report["canonical_sha256"] = hashlib.sha256(canonical).hexdigest()
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("route_corpus", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--capacity-mib", type=int, default=256)
    args = parser.parse_args()
    report = run(args.manifest, args.route_corpus, args.capacity_mib * 1024 * 1024)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
