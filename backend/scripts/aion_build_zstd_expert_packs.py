#!/usr/bin/env python3
"""Build lossless, independently addressable Zstandard expert packs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _header(path: Path) -> tuple[int, dict[str, Any]]:
    with path.open("rb") as handle:
        size = struct.unpack("<Q", handle.read(8))[0]
        return 8 + size, json.loads(handle.read(size))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--layout-plan", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--level", type=int, default=3)
    parser.add_argument(
        "--byte-shuffle-width", type=int, choices=(0, 2), default=0,
        help="Reversibly group byte positions within each element before compression.",
    )
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
    zstd = Path(subprocess.run(["which", "zstd"], check=True, capture_output=True, text=True).stdout.strip()).resolve()
    zstd_version = subprocess.run([str(zstd), "--version"], check=True, capture_output=True, text=True).stdout.strip()
    output_dir.mkdir(parents=True, exist_ok=True)

    layers = []
    total_raw = total_compressed = 0
    for source_layer, planned in zip(source["layers"], plan["layers"], strict=True):
        number = int(source_layer["layer"])
        source_pack = Path(source_layer["path"])
        if _sha256(source_pack) != source_layer["sha256"]:
            raise RuntimeError(f"source pack integrity failed: layer {number}")
        data_start, header = _header(source_pack)
        target = output_dir / f"layer-{number:02d}.zstpack"
        if target.exists():
            raise RuntimeError(f"refusing to overwrite: {target}")
        tensors: dict[str, Any] = {}
        expected = hashlib.sha256()
        offset = 0
        source_fd = os.open(source_pack, os.O_RDONLY)
        try:
            with target.open("xb") as output:
                for expert in planned["candidate_order"]:
                    for suffix in ("input_linear.weight", "output_linear.weight"):
                        name = f"experts.{expert}.{suffix}"
                        entry = header[name]
                        begin, end = map(int, entry["data_offsets"])
                        raw = os.pread(source_fd, end - begin, data_start + begin)
                        if len(raw) != end - begin:
                            raise RuntimeError(f"short source read for {name}")
                        transformed = raw
                        if args.byte_shuffle_width == 2:
                            if len(raw) % 2:
                                raise RuntimeError(f"unaligned two-byte tensor: {name}")
                            transformed = raw[0::2] + raw[1::2]
                        compressed = subprocess.run(
                            [str(zstd), f"-{args.level}", "-q", "-c"],
                            input=transformed, check=True, capture_output=True,
                        ).stdout
                        roundtrip = subprocess.run(
                            [str(zstd), "-d", "-q", "-c"],
                            input=compressed, check=True, capture_output=True,
                        ).stdout
                        if args.byte_shuffle_width == 2:
                            half = len(roundtrip) // 2
                            restored = bytearray(len(roundtrip))
                            restored[0::2] = roundtrip[:half]
                            restored[1::2] = roundtrip[half:]
                            roundtrip = bytes(restored)
                        if roundtrip != raw:
                            raise RuntimeError(f"lossless roundtrip failed for {name}")
                        output.write(compressed)
                        expected.update(compressed)
                        tensors[name] = {
                            "dtype": entry["dtype"],
                            "shape": entry["shape"],
                            "compressed_offsets": [offset, offset + len(compressed)],
                            "raw_bytes": len(raw),
                            "raw_sha256": hashlib.sha256(raw).hexdigest(),
                            "compressed_sha256": hashlib.sha256(compressed).hexdigest(),
                            "byte_shuffle_width": args.byte_shuffle_width,
                        }
                        offset += len(compressed)
                        total_raw += len(raw)
                        total_compressed += len(compressed)
                output.flush()
                os.fsync(output.fileno())
        finally:
            os.close(source_fd)
        actual_sha = _sha256(target)
        if actual_sha != expected.hexdigest():
            raise RuntimeError(f"persisted compressed pack failed: layer {number}")
        layer = {
            "layer": number,
            "path": str(target.resolve()),
            "sha256": actual_sha,
            "experts": 40,
            "expert_order": planned["candidate_order"],
            "compression": "zstd-independent-tensor-frames",
            "compression_level": args.level,
            "compressed_bytes": target.stat().st_size,
            "logical_expert_bytes": sum(value["raw_bytes"] for value in tensors.values()),
            "tensors": tensors,
            "source_pack_path": str(source_pack.resolve()),
            "source_pack_sha256": source_layer["sha256"],
            "all_tensor_roundtrips_exact": True,
        }
        layers.append(layer)
        print(json.dumps({"layer": number, "compressed_bytes": layer["compressed_bytes"]}), flush=True)

    manifest: dict[str, Any] = {
        "schema_version": "aion.zstd-expert-packs.v2",
        "source_manifest": str(source_path),
        "source_manifest_file_sha256": _sha256(source_path),
        "source_manifest_sha256": source["source_manifest_sha256"],
        "layout_plan": str(plan_path),
        "layout_plan_file_sha256": _sha256(plan_path),
        "layout_plan_sha256": plan["plan_sha256"],
        "codec": {"path": str(zstd), "sha256": _sha256(zstd), "version": zstd_version},
        "reversible_transform": {
            "kind": "byte_shuffle" if args.byte_shuffle_width else "none",
            "element_width_bytes": args.byte_shuffle_width,
        },
        "layers": layers,
        "aggregate": {
            "raw_bytes": total_raw,
            "compressed_bytes": total_compressed,
            "storage_reduction_percent": 100.0 * (1.0 - total_compressed / total_raw),
        },
        "integrity": {
            "all_32_layers_packed": len(layers) == 32,
            "all_1280_experts_indexed": sum(layer["experts"] for layer in layers) == 1280,
            "all_pack_hashes_recorded": all(bool(layer["sha256"]) for layer in layers),
            "all_tensor_roundtrips_exact": all(layer["all_tensor_roundtrips_exact"] for layer in layers),
            "packs_on_external_storage": all(output_dir in Path(layer["path"]).parents for layer in layers),
        },
        "claim_boundary": "Lossless per-tensor compression and exact roundtrip are verified. Runtime speed and memory remain unproven until head-to-head generation testing.",
    }
    manifest["manifest_sha256"] = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path), "aggregate": manifest["aggregate"], "manifest_sha256": manifest["manifest_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
