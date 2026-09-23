#!/usr/bin/env python3
"""Build content-addressed per-expert Granite MoE shards on external storage."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import time

from safetensors import safe_open
from safetensors.torch import save_file


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _checkpoint_tensor(model_path: Path, key: str):
    for checkpoint in sorted(model_path.glob("*.safetensors")):
        with safe_open(checkpoint, framework="pt", device="cpu") as handle:
            if key in handle.keys():
                return handle.get_tensor(key)
    raise KeyError(f"checkpoint tensor not found: {key}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()

    model_path, storage_root = args.model_path.resolve(), args.storage_root.resolve()
    if storage_root not in model_path.parents:
        raise SystemExit("model must be inside the declared external storage root")
    config = json.loads((model_path / "config.json").read_text(encoding="utf-8"))
    layer_count = int(config["num_hidden_layers"])
    expert_count = int(config["num_local_experts"])
    output_root = (args.output_root or (
        storage_root / "expert-shards" / "granite-3.1-3b-a800m-instruct"
    )).resolve()
    if storage_root not in output_root.parents:
        raise SystemExit("shards must be written inside the declared external storage root")

    started = time.perf_counter()
    layer_manifests = []
    for layer in range(layer_count):
        prefix = f"model.layers.{layer}.block_sparse_moe"
        input_weights = _checkpoint_tensor(model_path, f"{prefix}.input_linear.weight")
        output_weights = _checkpoint_tensor(model_path, f"{prefix}.output_linear.weight")
        if input_weights.shape[0] != expert_count or output_weights.shape[0] != expert_count:
            raise RuntimeError(f"expert dimension mismatch in layer {layer}")
        layer_root = output_root / f"layer-{layer:02d}"
        blob_root = layer_root / "blobs"
        blob_root.mkdir(parents=True, exist_ok=True)
        entries = []
        for expert in range(expert_count):
            tensors = {
                "input_linear.weight": input_weights[expert].contiguous(),
                "output_linear.weight": output_weights[expert].contiguous(),
            }
            with tempfile.NamedTemporaryFile(
                dir=blob_root, suffix=".safetensors", delete=False
            ) as handle:
                temporary = Path(handle.name)
            save_file(tensors, temporary, metadata={"layer": str(layer), "expert": str(expert)})
            digest = _sha256(temporary)
            destination = blob_root / f"sha256-{digest}.safetensors"
            if destination.exists():
                temporary.unlink()
            else:
                temporary.replace(destination)
            entries.append({
                "expert": expert,
                "path": str(destination),
                "sha256": digest,
                "bytes": destination.stat().st_size,
            })
        layer_index = {
            "schema_version": "aion.expert_shard_index.v1",
            "model_path": str(model_path),
            "layer": layer,
            "dtype": str(input_weights.dtype).removeprefix("torch."),
            "experts": entries,
        }
        index_path = layer_root / "index.json"
        index_path.write_text(json.dumps(layer_index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        layer_manifests.append({
            "layer": layer,
            "index_path": str(index_path),
            "index_sha256": _sha256(index_path),
            "expert_shards": len(entries),
            "bytes": sum(entry["bytes"] for entry in entries),
        })
        print(json.dumps({"layer_complete": layer, "of": layer_count, "bytes": layer_manifests[-1]["bytes"]}), flush=True)

    checkpoints = sorted(model_path.glob("*.safetensors"))
    manifest = {
        "schema_version": "aion.expert_shard_manifest.v1",
        "model_path": str(model_path),
        "storage_root": str(storage_root),
        "output_root": str(output_root),
        "source_checkpoint": [
            {"path": str(path), "bytes": path.stat().st_size, "sha256": _sha256(path)}
            for path in checkpoints
        ],
        "architecture": {"layers": layer_count, "experts_per_layer": expert_count},
        "layers": layer_manifests,
        "totals": {
            "expert_shards": sum(item["expert_shards"] for item in layer_manifests),
            "bytes": sum(item["bytes"] for item in layer_manifests),
            "build_seconds": time.perf_counter() - started,
        },
        "integrity": {
            "all_layers_present": len(layer_manifests) == layer_count,
            "all_experts_present": all(item["expert_shards"] == expert_count for item in layer_manifests),
            "all_paths_on_external_storage": all(
                storage_root in Path(item["index_path"]).resolve().parents for item in layer_manifests
            ),
            "source_hashes_recorded": bool(checkpoints),
        },
    }
    manifest_path = output_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path), "manifest_sha256": _sha256(manifest_path),
                      **manifest["totals"], "integrity": manifest["integrity"]}, indent=2))
    return 0 if all(manifest["integrity"].values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
