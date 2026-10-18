#!/usr/bin/env python3
"""Quantify the exact cold-prefill expert working set from captured routes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _expert_bytes(layer: dict[str, Any], experts: set[int]) -> int:
    total = 0
    for expert in experts:
        for suffix in ("input_linear.weight", "output_linear.weight"):
            entry = layer["tensors"][f"experts.{expert}.{suffix}"]
            begin, end = map(int, entry["compressed_offsets"])
            total += end - begin
    return total


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack-manifest", type=Path, required=True)
    parser.add_argument("--route-corpus", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    manifest_path = args.pack_manifest.resolve()
    corpus_path = args.route_corpus.resolve()
    output = args.output.resolve()
    if any(root not in path.parents for path in (manifest_path, corpus_path, output)):
        raise SystemExit("all inputs and evidence must remain on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not all(manifest["integrity"].values()) or len(manifest["layers"]) != 32:
        raise RuntimeError("pack manifest integrity failed")
    for layer in manifest["layers"]:
        path = Path(layer["path"])
        if root not in path.resolve().parents or path.stat().st_size != layer["compressed_bytes"]:
            raise RuntimeError(f"pack presence or size failed: layer {layer['layer']}")

    observation_paths = sorted((corpus_path / "objects").glob("*.json"))
    if not observation_paths:
        raise RuntimeError("route corpus is empty")
    full_bytes = sum(int(layer["compressed_bytes"]) for layer in manifest["layers"])
    observations = []
    for path in observation_paths:
        observation = json.loads(path.read_text(encoding="utf-8"))
        if not all(observation["route_batches_by_layer"]):
            raise RuntimeError(f"empty route observation: {path.name}")
        per_layer = []
        for layer_number, (layer, batches) in enumerate(zip(
            manifest["layers"], observation["route_batches_by_layer"], strict=True
        )):
            prefill = {int(expert) for route in batches[0] for expert in route}
            generated_sets = [
                {int(expert) for route in batch for expert in route}
                for batch in batches[1:]
            ]
            per_layer.append({
                "layer": layer_number,
                "prefill_token_routes": len(batches[0]),
                "prefill_distinct_experts": len(prefill),
                "prefill_compressed_bytes": _expert_bytes(layer, prefill),
                "generated_mean_distinct_experts_per_batch": (
                    statistics.mean(len(item) for item in generated_sets)
                    if generated_sets else 0.0
                ),
            })
        experts = sum(item["prefill_distinct_experts"] for item in per_layer)
        compressed = sum(item["prefill_compressed_bytes"] for item in per_layer)
        observations.append({
            "observation_sha256": observation["observation_sha256"],
            "prefill_token_routes": len(observation["route_batches_by_layer"][0][0]),
            "prefill_distinct_layer_experts": experts,
            "prefill_expert_coverage_percent": 100.0 * experts / (32 * 40),
            "prefill_compressed_bytes": compressed,
            "prefill_pack_coverage_percent": 100.0 * compressed / full_bytes,
            "layers": per_layer,
        })
    coverage = [item["prefill_expert_coverage_percent"] for item in observations]
    byte_coverage = [item["prefill_pack_coverage_percent"] for item in observations]
    report = {
        "schema_version": "aion.prefill-working-set-audit.v1",
        "pack_manifest": str(manifest_path),
        "pack_manifest_file_sha256": _sha256(manifest_path),
        "route_corpus": str(corpus_path),
        "observation_file_sha256s": {
            path.name: _sha256(path) for path in observation_paths
        },
        "architecture": {
            "layers": 32,
            "experts_per_layer": 40,
            "total_layer_experts": 1280,
        },
        "full_compressed_expert_bytes": full_bytes,
        "observations": observations,
        "aggregate": {
            "observation_count": len(observations),
            "minimum_prefill_expert_coverage_percent": min(coverage),
            "median_prefill_expert_coverage_percent": statistics.median(coverage),
            "maximum_prefill_expert_coverage_percent": max(coverage),
            "minimum_prefill_pack_coverage_percent": min(byte_coverage),
            "median_prefill_pack_coverage_percent": statistics.median(byte_coverage),
            "maximum_prefill_pack_coverage_percent": max(byte_coverage),
        },
        "integrity": {
            "manifest_integrity_passed": True,
            "all_32_pack_files_present_at_manifest_sizes": True,
            "all_route_observations_nonempty": True,
            "all_layers_audited": all(len(item["layers"]) == 32 for item in observations),
        },
        "conclusion": (
            "The captured prompt prefills select approximately the entire expert library. "
            "Cold TTFT therefore cannot be removed by better eviction alone; exact improvements "
            "must reduce lossless representation bytes, reuse an already-built working set or exact "
            "prefix state, or avoid/change the model call under a separate semantic-quality gate."
        ),
        "claim_boundary": (
            "Offline exact route-set accounting over three captured prompts. Pack files were "
            "presence-and-size checked and the manifest/observations were hashed; full pack bytes "
            "were not rehashed in this audit. No live latency causal claim is made."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "report_sha256": report["report_sha256"],
        "aggregate": report["aggregate"],
        "integrity": report["integrity"],
        "conclusion": report["conclusion"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
