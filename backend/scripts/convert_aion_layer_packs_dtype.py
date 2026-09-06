#!/usr/bin/env python3
"""Create immutable execution-dtype layer packs from verified source packs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
from typing import Any

import torch
from safetensors import safe_open
from safetensors.torch import save_file

from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-pack-manifest", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--pack-id", required=True)
    parser.add_argument("--target-dtype", choices=("float16",), default="float16")
    args = parser.parse_args()

    root = args.storage_root.resolve()
    source_path = args.source_pack_manifest.resolve()
    output_root = (root / "expert-layer-packs" / args.pack_id).resolve()
    if root not in source_path.parents or root not in output_root.parents:
        raise SystemExit("source and output packs must remain on external storage")
    manifest_path = output_root / "manifest.json"
    if output_root.exists() or manifest_path.exists():
        raise SystemExit(f"refusing to overwrite pack output: {output_root}")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    if not all(source["integrity"].values()) or len(source["layers"]) != 32:
        raise RuntimeError("source pack manifest integrity failed")
    output_root.mkdir(parents=True, exist_ok=False)

    started = time.perf_counter()
    layers = []
    all_roundtrips_exact = True
    all_stored_tensors_exact = True
    for source_layer in source["layers"]:
        layer = int(source_layer["layer"])
        source_pack = Path(source_layer["path"])
        if root not in source_pack.resolve().parents or _sha256(source_pack) != source_layer["sha256"]:
            raise RuntimeError(f"source pack integrity failed: layer {layer}")
        with safe_open(source_pack, framework="pt", device="cpu") as handle:
            source_tensors = {name: handle.get_tensor(name) for name in handle.keys()}
        tensors = {name: tensor.to(torch.float16) for name, tensor in source_tensors.items()}
        layer_roundtrip_exact = all(
            torch.equal(tensors[name].to(torch.bfloat16), source_tensors[name])
            for name in tensors
        )
        all_roundtrips_exact = all_roundtrips_exact and layer_roundtrip_exact
        pack_path = output_root / f"layer-{layer:02d}.safetensors"
        temporary = output_root / f"layer-{layer:02d}.partial"
        save_file(
            tensors,
            temporary,
            metadata={
                "schema_version": "aion.moe_execution_dtype_pack.v1",
                "layer": str(layer),
                "source_pack_sha256": source_layer["sha256"],
                "source_dtype": "bfloat16",
                "target_dtype": args.target_dtype,
                "roundtrip_exact": str(layer_roundtrip_exact).lower(),
            },
        )
        temporary.rename(pack_path)
        with safe_open(pack_path, framework="pt", device="cpu") as handle:
            stored_tensors_exact = set(handle.keys()) == set(tensors) and all(
                torch.equal(handle.get_tensor(name), tensors[name]) for name in tensors
            )
        all_stored_tensors_exact = all_stored_tensors_exact and stored_tensors_exact
        layers.append({
            **source_layer,
            "path": str(pack_path),
            "sha256": _sha256(pack_path),
            "file_bytes": pack_path.stat().st_size,
            "source_pack_path": str(source_pack),
            "source_pack_sha256": source_layer["sha256"],
            "source_dtype": "bfloat16",
            "target_dtype": args.target_dtype,
            "roundtrip_exact": layer_roundtrip_exact,
            "stored_fp16_matches_source_converted_to_fp16": stored_tensors_exact,
        })
        print(json.dumps({"converted_layer": layer, "file_bytes": pack_path.stat().st_size}), flush=True)
        del source_tensors, tensors

    manifest: dict[str, Any] = {
        "schema_version": "aion.moe_execution_dtype_pack_manifest.v1",
        "pack_id": args.pack_id,
        "storage_root": str(root),
        "source_manifest_path": source["source_manifest_path"],
        "source_manifest_sha256": source["source_manifest_sha256"],
        "source_pack_manifest_path": str(source_path),
        "source_pack_manifest_sha256": _sha256(source_path),
        "source_dtype": "bfloat16",
        "target_dtype": args.target_dtype,
        "layers": layers,
        "totals": {
            "layers": len(layers),
            "experts": sum(int(layer["experts"]) for layer in layers),
            "file_bytes": sum(int(layer["file_bytes"]) for layer in layers),
            "build_seconds": time.perf_counter() - started,
        },
        "integrity": {
            "all_32_layers_packed": len(layers) == 32,
            "all_1280_experts_indexed": sum(int(layer["experts"]) for layer in layers) == 1280,
            "all_pack_hashes_recorded": all(len(layer["sha256"]) == 64 for layer in layers),
            "all_stored_fp16_matches_source_converted_to_fp16": all_stored_tensors_exact,
            "packs_on_external_storage": all(root in Path(layer["path"]).resolve().parents for layer in layers),
        },
        "representation_observation": {
            "all_bf16_fp16_bf16_roundtrips_exact": all_roundtrips_exact,
            "lossless_relative_to_bf16_source": all_roundtrips_exact,
            "exact_relative_to_fp16_execution": all_stored_tensors_exact,
        },
        "claim_boundary": (
            "These packs precompute the same BF16-to-FP16 conversion used by the FP16 execution "
            "control. They are exact relative to FP16 execution but not necessarily lossless "
            "relative to the BF16 source. They are not proof of runtime improvement."
        ),
    }
    manifest["manifest_sha256"] = _canonical_sha256(manifest)
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
