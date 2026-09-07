#!/usr/bin/env python3
"""Build content-addressed native-INT8 Granite expert blocks on external storage."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any

from safetensors.torch import load_file, save_file
import torch

from backend.scripts.run_aion_int8pack_expert_microbench import _quantize_rows
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def _block_metadata(input_weight: torch.Tensor, output_weight: torch.Tensor) -> dict[str, str]:
    return {
        "schema_version": "aion.int8_glyph_block.v1",
        "quantization": "symmetric_per_output_channel_int8_fp16_scale",
        "input_shape": json.dumps(list(input_weight.shape), separators=(",", ":")),
        "output_shape": json.dumps(list(output_weight.shape), separators=(",", ":")),
        "input_offset_elements": "0",
        "output_offset_elements": str(input_weight.numel()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    source_manifest_path = args.source_manifest.resolve()
    destination = args.destination.resolve()
    if any(root not in path.parents for path in (source_manifest_path, destination)):
        raise SystemExit("source and destination must remain on external storage")
    if destination.exists():
        raise SystemExit(f"refusing to overwrite existing destination: {destination}")

    source = json.loads(source_manifest_path.read_text())
    if not all(source["integrity"].values()) or len(source["layers"]) != 32:
        raise RuntimeError("source expert manifest integrity failed")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    final_layers = []
    total_source_bytes = 0
    total_logical_packed_bytes = 0
    total_physical_bytes = 0
    total_experts = 0
    try:
        for layer_entry in source["layers"]:
            layer = int(layer_entry["layer"])
            source_index_path = Path(layer_entry["index_path"]).resolve()
            if (root not in source_index_path.parents or
                    _sha256(source_index_path) != layer_entry["index_sha256"]):
                raise RuntimeError(f"source layer {layer} index integrity failed")
            source_index = json.loads(source_index_path.read_text())
            layer_dir = staging / f"layer-{layer:02d}"
            blobs_dir = layer_dir / "blobs"
            blobs_dir.mkdir(parents=True)
            final_entries = []
            for entry in source_index["experts"]:
                expert = int(entry["expert"])
                source_path = Path(entry["path"]).resolve()
                if root not in source_path.parents or _sha256(source_path) != entry["sha256"]:
                    raise RuntimeError(f"source integrity failed for layer {layer} expert {expert}")
                tensors = load_file(source_path, device="cpu")
                input_weight = tensors["input_linear.weight"].to(torch.float16).contiguous()
                output_weight = tensors["output_linear.weight"].to(torch.float16).contiguous()
                input_q, input_scale = _quantize_rows(input_weight)
                output_q, output_scale = _quantize_rows(output_weight)
                weight_block = torch.cat((input_q.reshape(-1), output_q.reshape(-1)))
                temporary = blobs_dir / f"expert-{expert:02d}.safetensors"
                save_file(
                    {"weight_block": weight_block, "input_scale": input_scale,
                     "output_scale": output_scale},
                    temporary,
                    metadata=_block_metadata(input_weight, output_weight),
                )
                digest = _sha256(temporary)
                blob_name = f"sha256-{digest}.safetensors"
                blob_path = blobs_dir / blob_name
                temporary.rename(blob_path)
                logical_bytes = sum(t.numel() * t.element_size() for t in
                                    (weight_block, input_scale, output_scale))
                physical_bytes = blob_path.stat().st_size
                final_blob_path = destination / f"layer-{layer:02d}" / "blobs" / blob_name
                final_entries.append({
                    "layer": layer, "expert": expert,
                    "path": str(final_blob_path), "sha256": digest,
                    "source_path": str(source_path), "source_sha256": entry["sha256"],
                    "source_bytes": int(entry["bytes"]),
                    "logical_packed_bytes": logical_bytes,
                    "physical_bytes": physical_bytes,
                    "input_shape": list(input_weight.shape),
                    "output_shape": list(output_weight.shape),
                    "input_offset_elements": 0,
                    "output_offset_elements": input_weight.numel(),
                })
                total_source_bytes += int(entry["bytes"])
                total_logical_packed_bytes += logical_bytes
                total_physical_bytes += physical_bytes
                total_experts += 1
            index_document = {
                "schema_version": "aion.int8_glyph_layer_index.v1",
                "layer": layer, "experts": final_entries,
                "all_source_hashes_verified": True,
            }
            index_document["index_canonical_sha256"] = _canonical_sha256(index_document)
            index_path = layer_dir / "index.json"
            index_path.write_text(json.dumps(index_document, indent=2, sort_keys=True) + "\n")
            final_layers.append({
                "layer": layer, "expert_blocks": len(final_entries),
                "index_path": str(destination / f"layer-{layer:02d}" / "index.json"),
                "index_sha256": _sha256(index_path),
                "logical_packed_bytes": sum(x["logical_packed_bytes"] for x in final_entries),
                "physical_bytes": sum(x["physical_bytes"] for x in final_entries),
            })
            print(json.dumps({"layer_complete": layer, "experts": len(final_entries)}), flush=True)

        manifest = {
            "schema_version": "aion.int8_glyph_block_manifest.v1",
            "source_manifest_path": str(source_manifest_path),
            "source_manifest_sha256": _sha256(source_manifest_path),
            "destination": str(destination),
            "quantization": "symmetric_per_output_channel_int8_fp16_scale",
            "native_operation": "torch._weight_int8pack_mm",
            "layers": final_layers,
            "summary": {
                "layers": len(final_layers), "experts": total_experts,
                "source_bytes": total_source_bytes,
                "logical_packed_bytes": total_logical_packed_bytes,
                "physical_bytes": total_physical_bytes,
                "logical_byte_reduction_percent": 100 * (
                    1 - total_logical_packed_bytes / total_source_bytes
                ),
                "logical_packed_gibibytes": total_logical_packed_bytes / 1024**3,
            },
            "integrity": {
                "all_32_layers_present": len(final_layers) == 32,
                "all_1280_experts_present": total_experts == 1280,
                "all_source_hashes_verified": True,
                "all_output_hashes_recorded": True,
                "all_paths_on_external_storage": True,
            },
            "claim_boundary": (
                "Offline lossy INT8 derivative of verified Granite expert shards. This build "
                "proves storage and content integrity only; full-model quality and performance "
                "must pass separate gates."
            ),
        }
        manifest["manifest_canonical_sha256"] = _canonical_sha256(manifest)
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        )
        if not all(manifest["integrity"].values()):
            raise RuntimeError("derived manifest integrity gate failed")
        staging.rename(destination)
        print(json.dumps({"destination": str(destination), **manifest["summary"],
                          "manifest_canonical_sha256": manifest["manifest_canonical_sha256"]},
                         indent=2))
        return 0
    except Exception:
        # Preserve a failed build for diagnosis; never overwrite or silently discard evidence.
        failed = staging.with_name(staging.name + ".FAILED")
        if staging.exists():
            staging.rename(failed)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
