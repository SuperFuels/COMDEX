#!/usr/bin/env python3
"""Build byte-exact Safetensors packs in a corpus-derived physical order."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_header(path: Path) -> tuple[int, dict[str, Any]]:
    with path.open("rb") as handle:
        size = struct.unpack("<Q", handle.read(8))[0]
        return 8 + size, json.loads(handle.read(size))


def _build_layer(source: Path, target: Path, order: tuple[int, ...]) -> dict[str, Any]:
    source_data_start, source_header = _read_header(source)
    entries: list[tuple[str, dict[str, Any], int, int]] = []
    offset = 0
    candidate_header: dict[str, Any] = {}
    if "__metadata__" in source_header:
        candidate_header["__metadata__"] = source_header["__metadata__"]
    for expert in order:
        for suffix in ("input_linear.weight", "output_linear.weight"):
            name = f"experts.{expert}.{suffix}"
            source_entry = source_header[name]
            source_begin, source_end = map(int, source_entry["data_offsets"])
            length = source_end - source_begin
            candidate_header[name] = {
                "dtype": source_entry["dtype"],
                "shape": source_entry["shape"],
                "data_offsets": [offset, offset + length],
            }
            entries.append((name, source_entry, offset, length))
            offset += length

    encoded = json.dumps(candidate_header, separators=(",", ":"), ensure_ascii=False).encode()
    encoded += b" " * ((8 - len(encoded) % 8) % 8)
    prefix = struct.pack("<Q", len(encoded)) + encoded
    expected_digest = hashlib.sha256(prefix)
    tensor_digests: dict[str, str] = {}
    source_fd = os.open(source, os.O_RDONLY)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("xb") as output:
            output.write(prefix)
            for name, source_entry, _, length in entries:
                begin = source_data_start + int(source_entry["data_offsets"][0])
                remaining = length
                tensor_digest = hashlib.sha256()
                while remaining:
                    block = os.pread(source_fd, min(4 * 1024 * 1024, remaining), begin)
                    if not block:
                        raise RuntimeError(f"short source read for {name}")
                    output.write(block)
                    expected_digest.update(block)
                    tensor_digest.update(block)
                    begin += len(block)
                    remaining -= len(block)
                tensor_digests[name] = tensor_digest.hexdigest()
            output.flush()
            os.fsync(output.fileno())
    finally:
        os.close(source_fd)
    actual_sha = _sha256(target)
    expected_sha = expected_digest.hexdigest()
    if actual_sha != expected_sha:
        raise RuntimeError(f"persisted candidate pack failed expected-content hash: {target}")
    return {
        "path": str(target.resolve()),
        "sha256": actual_sha,
        "file_bytes": target.stat().st_size,
        "expert_order": list(order),
        "tensor_payload_sha256": tensor_digests,
        "expected_content_hash_verified": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--layout-plan", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    source_path = args.source_manifest.resolve()
    plan_path = args.layout_plan.resolve()
    output_dir = args.output_dir.resolve()
    manifest_path = output_dir / "manifest.json"
    if manifest_path.exists():
        raise SystemExit(f"refusing to overwrite evidence: {manifest_path}")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan["source_pack_manifest_sha256"] != _sha256(source_path):
        raise SystemExit("layout plan/source manifest binding failed")
    if len(source["layers"]) != 32 or len(plan["layers"]) != 32:
        raise SystemExit("expected 32 source and plan layers")

    layers = []
    for source_layer, planned in zip(source["layers"], plan["layers"], strict=True):
        number = int(source_layer["layer"])
        if number != int(planned["layer"]):
            raise RuntimeError("layer alignment failed")
        source_pack = Path(source_layer["path"])
        if _sha256(source_pack) != source_layer["sha256"]:
            raise RuntimeError(f"source pack integrity failed: layer {number}")
        target = output_dir / f"layer-{number:02d}.safetensors"
        built = _build_layer(source_pack, target, tuple(planned["candidate_order"]))
        layers.append({
            **{key: value for key, value in source_layer.items() if key not in {"path", "sha256", "file_bytes"}},
            **built,
            "layer": number,
            "source_pack_path": str(source_pack.resolve()),
            "source_pack_sha256": source_layer["sha256"],
        })
        print(json.dumps({"layer": number, "sha256": built["sha256"]}), flush=True)

    manifest: dict[str, Any] = {
        "schema_version": "aion.route-aware-layer-packs.v1",
        "source_manifest": str(source_path),
        "source_manifest_file_sha256": _sha256(source_path),
        "source_manifest_sha256": source["source_manifest_sha256"],
        "layout_plan": str(plan_path),
        "layout_plan_file_sha256": _sha256(plan_path),
        "layout_plan_sha256": plan["plan_sha256"],
        "layers": layers,
        "integrity": {
            "all_32_layers_packed": len(layers) == 32,
            "all_1280_experts_indexed": sum(int(layer["experts"]) for layer in layers) == 1280,
            "all_pack_hashes_recorded": all(bool(layer["sha256"]) for layer in layers),
            "all_expected_content_hashes_verified": all(layer["expected_content_hash_verified"] for layer in layers),
            "packs_on_external_storage": all(output_dir in Path(layer["path"]).parents for layer in layers),
        },
        "claim_boundary": "The candidate changes only physical tensor order. Tensor names, dtypes, shapes and payload bytes are preserved exactly. Performance requires a separate head-to-head generation experiment.",
    }
    manifest["manifest_sha256"] = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path), "manifest_sha256": manifest["manifest_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
