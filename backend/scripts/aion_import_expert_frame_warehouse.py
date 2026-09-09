#!/usr/bin/env python3
"""Materialize a frozen GGUF expert-frame plan as verified Zstandard packs."""

from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import hashlib
import json
import mmap
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MIB = 1024 * 1024


def sha256_path(path: Path, block_size: int = 8 * MIB) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(path.suffix + ".part")
    part.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    os.replace(part, path)


def canonical_hash(payload: dict) -> str:
    value = {key: item for key, item in payload.items() if key != "canonical_sha256"}
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class Zstd:
    def __init__(self) -> None:
        path = ctypes.util.find_library("zstd")
        if not path:
            raise RuntimeError("system libzstd is unavailable")
        self.library = ctypes.CDLL(path)
        self.library.ZSTD_compressBound.argtypes = [ctypes.c_size_t]
        self.library.ZSTD_compressBound.restype = ctypes.c_size_t
        self.library.ZSTD_compress.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
                                                ctypes.c_void_p, ctypes.c_size_t,
                                                ctypes.c_int]
        self.library.ZSTD_compress.restype = ctypes.c_size_t
        self.library.ZSTD_decompress.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
                                                  ctypes.c_void_p, ctypes.c_size_t]
        self.library.ZSTD_decompress.restype = ctypes.c_size_t
        self.library.ZSTD_isError.argtypes = [ctypes.c_size_t]
        self.library.ZSTD_isError.restype = ctypes.c_uint

    def compress(self, source_address: int, length: int, level: int) -> bytes:
        capacity = int(self.library.ZSTD_compressBound(length))
        target = ctypes.create_string_buffer(capacity)
        result = self.library.ZSTD_compress(target, capacity, source_address, length, level)
        if self.library.ZSTD_isError(result):
            raise RuntimeError("zstd compression failed")
        return target.raw[:int(result)]

    def decompress(self, encoded: bytes, raw_size: int) -> bytes:
        target = ctypes.create_string_buffer(raw_size)
        source = ctypes.create_string_buffer(encoded)
        result = self.library.ZSTD_decompress(target, raw_size, source, len(encoded))
        if self.library.ZSTD_isError(result) or int(result) != raw_size:
            raise RuntimeError("zstd decompression failed")
        return target.raw


def fetch_range(curl: Path, url: str, start: int, length: int, output: Path) -> None:
    subprocess.run([
        str(curl), "-L", "--fail", "--silent", "--show-error", "--retry", "8",
        "--retry-all-errors", "--connect-timeout", "30",
        "--range", f"{start}-{start + length - 1}", "--output", str(output), url,
    ], check=True)
    if output.stat().st_size != length:
        raise RuntimeError(f"range length mismatch: expected {length}, got {output.stat().st_size}")


def pack_region(zstd: Zstd, raw_path: Path, pack_part: Path,
                frames: list[dict], level: int) -> list[dict]:
    expected = sum(int(frame["raw_bytes"]) for frame in frames)
    if raw_path.stat().st_size != expected:
        raise RuntimeError("raw region does not match frame plan")
    packed_frames = []
    encoded_offset = 0
    with raw_path.open("r+b", buffering=0) as raw_handle, pack_part.open("wb") as output:
        with mmap.mmap(raw_handle.fileno(), 0, access=mmap.ACCESS_COPY) as mapped:
            for frame in frames:
                start = int(frame["relative_offset"])
                length = int(frame["raw_bytes"])
                address = ctypes.addressof(ctypes.c_char.from_buffer(mapped, start))
                encoded = zstd.compress(address, length, level)
                raw_hash = hashlib.sha256(memoryview(mapped)[start:start + length]).hexdigest()
                decoded = zstd.decompress(encoded, length)
                if hashlib.sha256(decoded).hexdigest() != raw_hash:
                    raise RuntimeError("frame round-trip verification failed")
                output.write(encoded)
                packed_frames.append({
                    **frame, "encoded_offset": encoded_offset,
                    "compressed_bytes": len(encoded),
                    "raw_sha256": raw_hash,
                    "compressed_sha256": hashlib.sha256(encoded).hexdigest(),
                })
                encoded_offset += len(encoded)
        output.flush()
        os.fsync(output.fileno())
    return packed_frames


def receipt_valid(receipt_path: Path, pack_path: Path) -> bool:
    if not receipt_path.is_file() or not pack_path.is_file():
        return False
    receipt = json.loads(receipt_path.read_text())
    return (receipt.get("pack_bytes") == pack_path.stat().st_size
            and receipt.get("pack_sha256") == sha256_path(pack_path))


def verify_source(zstd: Zstd, shard: dict, receipts: list[dict], root: Path) -> str:
    digest = hashlib.sha256()
    raw_total = 0
    for receipt in sorted(receipts, key=lambda item: item["region_index"]):
        pack_path = root / receipt["pack_relative_path"]
        with pack_path.open("rb", buffering=0) as handle:
            for frame in receipt["frames"]:
                handle.seek(int(frame["encoded_offset"]))
                encoded = handle.read(int(frame["compressed_bytes"]))
                if hashlib.sha256(encoded).hexdigest() != frame["compressed_sha256"]:
                    raise RuntimeError(f"pack frame hash mismatch: {pack_path}")
                raw = zstd.decompress(encoded, int(frame["raw_bytes"]))
                if hashlib.sha256(raw).hexdigest() != frame["raw_sha256"]:
                    raise RuntimeError(f"decoded frame hash mismatch: {pack_path}")
                digest.update(raw)
                raw_total += len(raw)
    if raw_total != int(shard["size"]):
        raise RuntimeError(f"reconstructed size mismatch: {raw_total} != {shard['size']}")
    value = digest.hexdigest()
    if value != shard["sha256"]:
        raise RuntimeError(f"reconstructed source hash mismatch: {value} != {shard['sha256']}")
    return value


def import_plan(plan: dict, destination: Path, level: int, reserve_bytes: int,
                curl: Path) -> dict:
    if (plan.get("schema") != "aion.gguf-expert-frame-plan.v1"
            or plan.get("status") != "FROZEN_BEFORE_FULL_IMPORT"):
        raise ValueError("packing plan is not frozen")
    if canonical_hash(plan) != plan.get("canonical_sha256"):
        raise ValueError("packing plan canonical hash mismatch")
    destination.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix="aion-expert-frame-import-"))
    zstd = Zstd()
    completed: list[dict[str, Any]] = []
    total_regions = sum(len(shard["regions"]) for shard in plan["shards"])
    try:
        for shard in plan["shards"]:
            shard_number = int(shard["shard_number"])
            pack_dir = destination / "packs" / f"shard-{shard_number:02d}"
            receipt_dir = destination / "receipts" / f"shard-{shard_number:02d}"
            pack_dir.mkdir(parents=True, exist_ok=True)
            receipt_dir.mkdir(parents=True, exist_ok=True)
            for region_index, region in enumerate(shard["regions"]):
                stem = f"region-{region_index:04d}"
                pack_path = pack_dir / f"{stem}.zstpack"
                receipt_path = receipt_dir / f"{stem}.json"
                if receipt_valid(receipt_path, pack_path):
                    receipt = json.loads(receipt_path.read_text())
                    completed.append(receipt)
                    print(f"resume {len(completed)}/{total_regions} {region['name']}", flush=True)
                    continue
                free = shutil.disk_usage(destination).free
                if free - reserve_bytes < int(region["raw_bytes"]):
                    raise RuntimeError(
                        f"insufficient safe pack space: {free} free, {reserve_bytes} reserved"
                    )
                raw_path = temp_root / f"shard-{shard_number:02d}-{stem}.raw"
                pack_part = pack_path.with_suffix(pack_path.suffix + ".part")
                fetch_range(curl, shard["url"], int(region["source_offset"]),
                            int(region["raw_bytes"]), raw_path)
                packed_frames = pack_region(zstd, raw_path, pack_part, region["frames"], level)
                if pack_part.stat().st_size + reserve_bytes > free:
                    raise RuntimeError("encoded region would breach reserve")
                os.replace(pack_part, pack_path)
                receipt = {
                    "schema": "aion.expert-frame-region-receipt.v1",
                    "shard_number": shard_number, "source_shard": shard["name"],
                    "region_index": region_index, "region_name": region["name"],
                    "region_kind": region["kind"],
                    "source_offset": int(region["source_offset"]),
                    "raw_bytes": int(region["raw_bytes"]),
                    "pack_relative_path": str(pack_path.relative_to(destination)),
                    "pack_bytes": pack_path.stat().st_size,
                    "pack_sha256": sha256_path(pack_path), "frames": packed_frames,
                }
                atomic_json(receipt_path, receipt)
                raw_path.unlink()
                completed.append(receipt)
                saving = 100.0 * (1.0 - receipt["pack_bytes"] / receipt["raw_bytes"])
                print(f"stored {len(completed)}/{total_regions} {region['name']} saved={saving:.3f}%",
                      flush=True)
                atomic_json(destination / "import-state.json", {
                    "schema": "aion.expert-frame-import-state.v1", "status": "IN_PROGRESS",
                    "completed_regions": len(completed), "total_regions": total_regions,
                    "raw_bytes_completed": sum(item["raw_bytes"] for item in completed),
                    "pack_bytes_completed": sum(item["pack_bytes"] for item in completed),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
        verified = []
        for shard in plan["shards"]:
            receipts = [item for item in completed
                        if item["source_shard"] == shard["name"]]
            verified.append({"name": shard["name"], "size": shard["size"],
                             "expected_sha256": shard["sha256"],
                             "verified_sha256": verify_source(zstd, shard, receipts, destination)})
        manifest = {
            "schema": "aion.expert-frame-warehouse.v1", "status": "COMPLETE_VERIFIED",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "plan_canonical_sha256": plan["canonical_sha256"],
            "codec": "zstd-independent-frames", "zstd_level": level,
            "raw_bytes": sum(item["raw_bytes"] for item in completed),
            "pack_bytes": sum(item["pack_bytes"] for item in completed),
            "verified_sources": verified, "regions": completed,
        }
        manifest["canonical_sha256"] = canonical_hash(manifest)
        atomic_json(destination / "manifest.v1.json", manifest)
        atomic_json(destination / "import-state.json", {
            "schema": "aion.expert-frame-import-state.v1", "status": "COMPLETE_VERIFIED",
            "manifest_sha256": sha256_path(destination / "manifest.v1.json"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        return manifest
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--zstd-level", type=int, default=3)
    parser.add_argument("--reserve-mib", type=int, default=1024)
    args = parser.parse_args()
    curl = Path(shutil.which("curl") or "")
    if not curl.is_file():
        raise SystemExit("curl is required")
    result = import_plan(json.loads(args.plan.read_text()), args.destination.resolve(),
                         args.zstd_level, args.reserve_mib * MIB, curl)
    print(json.dumps({"status": result["status"], "raw_bytes": result["raw_bytes"],
                      "pack_bytes": result["pack_bytes"],
                      "canonical_sha256": result["canonical_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
