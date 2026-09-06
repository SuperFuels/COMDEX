#!/usr/bin/env python3
"""Coalesce content-addressed expert shards into verified per-layer packs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
from typing import Any

from safetensors.torch import load_file, save_file


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shard-manifest", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--pack-id", required=True)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()

    root = args.storage_root.resolve()
    source_manifest_path = args.shard_manifest.resolve()
    if root not in source_manifest_path.parents:
        raise SystemExit("source shards must reside under the external storage root")
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    if not all(source_manifest["integrity"].values()):
        raise RuntimeError("source shard manifest integrity gate failed")
    output_root = (args.output_root or root / "expert-layer-packs" / args.pack_id).resolve()
    if root not in output_root.parents:
        raise SystemExit("layer packs must be written under the external storage root")
    manifest_path = output_root / "manifest.json"
    if manifest_path.exists():
        raise SystemExit(f"refusing to overwrite existing pack manifest: {manifest_path}")
    output_root.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    layers: list[dict[str, Any]] = []
    for layer_number, source_layer in enumerate(source_manifest["layers"]):
        index_path = Path(source_layer["index_path"])
        if _sha256(index_path) != source_layer["index_sha256"]:
            raise RuntimeError(f"source index integrity failed: layer {layer_number}")
        index = json.loads(index_path.read_text(encoding="utf-8"))
        tensors = {}
        source_hashes = {}
        logical_bytes = 0
        for entry in index["experts"]:
            expert = int(entry["expert"])
            source = Path(entry["path"])
            if _sha256(source) != entry["sha256"]:
                raise RuntimeError(f"source expert integrity failed: layer {layer_number}, expert {expert}")
            weights = load_file(source, device="cpu")
            tensors[f"experts.{expert}.input_linear.weight"] = weights["input_linear.weight"]
            tensors[f"experts.{expert}.output_linear.weight"] = weights["output_linear.weight"]
            source_hashes[str(expert)] = entry["sha256"]
            logical_bytes += int(entry["bytes"])
        pack_path = output_root / f"layer-{layer_number:02d}.safetensors"
        if pack_path.exists():
            raise RuntimeError(f"refusing to overwrite partial pack: {pack_path}")
        save_file(
            tensors,
            pack_path,
            metadata={
                "schema_version": "aion.moe_layer_pack.v1",
                "layer": str(layer_number),
                "source_index_sha256": source_layer["index_sha256"],
            },
        )
        layers.append({
            "layer": layer_number,
            "path": str(pack_path),
            "sha256": _sha256(pack_path),
            "file_bytes": pack_path.stat().st_size,
            "logical_expert_bytes": logical_bytes,
            "experts": len(index["experts"]),
            "source_index_path": str(index_path),
            "source_index_sha256": source_layer["index_sha256"],
            "source_expert_sha256": source_hashes,
        })
        print(json.dumps({"packed_layer": layer_number, "file_bytes": pack_path.stat().st_size}), flush=True)

    manifest: dict[str, Any] = {
        "schema_version": "aion.moe_layer_pack_manifest.v1",
        "pack_id": args.pack_id,
        "storage_root": str(root),
        "source_manifest_path": str(source_manifest_path),
        "source_manifest_sha256": _sha256(source_manifest_path),
        "layers": layers,
        "totals": {
            "layers": len(layers),
            "experts": sum(layer["experts"] for layer in layers),
            "file_bytes": sum(layer["file_bytes"] for layer in layers),
            "logical_expert_bytes": sum(layer["logical_expert_bytes"] for layer in layers),
            "build_seconds": time.perf_counter() - started,
        },
        "integrity": {
            "all_32_layers_packed": len(layers) == 32,
            "all_1280_experts_indexed": sum(layer["experts"] for layer in layers) == 1280,
            "all_pack_hashes_recorded": all(len(layer["sha256"]) == 64 for layer in layers),
            "packs_on_external_storage": all(root in Path(layer["path"]).resolve().parents for layer in layers),
        },
        "claim_boundary": (
            "Each pack coalesces already-verified per-expert tensors into one Safetensors file per "
            "layer. Expert keys remain independently selectable, but this is storage coalescing, not "
            "weight compression and not a claim of fewer logical tensor bytes."
        ),
    }
    manifest["manifest_sha256"] = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "manifest": str(manifest_path),
        "manifest_file_sha256": _sha256(manifest_path),
        "totals": manifest["totals"],
        "integrity": manifest["integrity"],
    }, indent=2))
    return 0 if all(manifest["integrity"].values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
