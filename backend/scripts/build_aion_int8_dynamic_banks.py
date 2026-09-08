#!/usr/bin/env python3
"""Build one integrity-bound contiguous INT8 expert bank per Granite layer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

from safetensors.torch import load_file, save_file
import torch

from backend.scripts.run_aion_int8_glyph_full_model import _canonical_sha256
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256


def _layer_metadata(layer: int, input_shape: list[int],
                    output_shape: list[int]) -> dict[str, str]:
    return {"schema_version": "aion.int8_dynamic_bank_layer.v1",
            "layer": str(layer), "experts": "40",
            "input_shape": json.dumps(input_shape, separators=(",", ":")),
            "output_shape": json.dumps(output_shape, separators=(",", ":")),
            "quantization": "symmetric_per_output_channel_int8_fp16_scale"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--glyph-manifest", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    source_path = args.glyph_manifest.resolve()
    destination = args.destination.resolve()
    if any(root not in path.parents for path in (source_path, destination)):
        raise SystemExit("source and destination must remain on external storage")
    if destination.exists():
        raise SystemExit(f"refusing to overwrite destination: {destination}")
    source = json.loads(source_path.read_text())
    if not all(source["integrity"].values()) or len(source["layers"]) != 32:
        raise RuntimeError("source Glyph manifest integrity failed")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    layer_entries = []
    total_logical = 0
    total_physical = 0
    try:
        for layer_entry in source["layers"]:
            layer = int(layer_entry["layer"])
            index_path = Path(layer_entry["index_path"]).resolve()
            if root not in index_path.parents or _sha256(index_path) != layer_entry["index_sha256"]:
                raise RuntimeError(f"layer {layer} index integrity failed")
            index = json.loads(index_path.read_text())
            experts = sorted(index["experts"], key=lambda item: int(item["expert"]))
            if [int(item["expert"]) for item in experts] != list(range(40)):
                raise RuntimeError(f"layer {layer} expert coverage failed")
            input_weights = []; input_scales = []; output_weights = []; output_scales = []
            for expert in experts:
                path = Path(expert["path"]).resolve()
                if root not in path.parents or _sha256(path) != expert["sha256"]:
                    raise RuntimeError(f"layer {layer} expert integrity failed: {path}")
                tensors = load_file(path, device="cpu")
                block = tensors["weight_block"]
                offset = int(expert["output_offset_elements"])
                input_weights.append(block[:offset].view(expert["input_shape"]))
                output_weights.append(block[offset:].view(expert["output_shape"]))
                input_scales.append(tensors["input_scale"])
                output_scales.append(tensors["output_scale"])
            banks = {"input_bank": torch.stack(input_weights).contiguous(),
                     "input_scale_bank": torch.stack(input_scales).contiguous(),
                     "output_bank": torch.stack(output_weights).contiguous(),
                     "output_scale_bank": torch.stack(output_scales).contiguous()}
            temporary = staging / f"layer-{layer:02d}.safetensors"
            save_file(banks, temporary, metadata=_layer_metadata(
                layer, list(banks["input_bank"].shape), list(banks["output_bank"].shape)))
            digest = _sha256(temporary)
            blob_name = f"layer-{layer:02d}-sha256-{digest}.safetensors"
            blob_path = staging / blob_name
            temporary.rename(blob_path)
            logical = sum(t.numel() * t.element_size() for t in banks.values())
            physical = blob_path.stat().st_size
            layer_entries.append({"layer": layer,
                                  "path": str(destination / blob_name),
                                  "sha256": digest,
                                  "logical_bytes": logical,
                                  "physical_bytes": physical,
                                  "input_bank_shape": list(banks["input_bank"].shape),
                                  "output_bank_shape": list(banks["output_bank"].shape),
                                  "source_index_path": str(index_path),
                                  "source_index_sha256": layer_entry["index_sha256"]})
            total_logical += logical
            total_physical += physical
            print(json.dumps({"layer_complete": layer, "bytes": physical}), flush=True)
        manifest = {"schema_version": "aion.int8_dynamic_bank_manifest.v1",
                    "source_glyph_manifest_path": str(source_path),
                    "source_glyph_manifest_sha256": _sha256(source_path),
                    "destination": str(destination), "layers": layer_entries,
                    "summary": {"layers": len(layer_entries), "experts_per_layer": 40,
                                "logical_bytes": total_logical,
                                "physical_bytes": total_physical,
                                "duplicate_weight_bytes_at_runtime": 0},
                    "integrity": {"all_source_hashes_verified": True,
                                  "all_layers_written": len(layer_entries) == 32}}
        manifest["manifest_canonical_sha256"] = _canonical_sha256(manifest)
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        staging.rename(destination)
        print(json.dumps({"destination": str(destination), "summary": manifest["summary"],
                          "manifest_canonical_sha256": manifest["manifest_canonical_sha256"]},
                         indent=2))
    except BaseException:
        invalid = staging.with_name(staging.name + ".INVALID")
        if staging.exists():
            staging.rename(invalid)
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
