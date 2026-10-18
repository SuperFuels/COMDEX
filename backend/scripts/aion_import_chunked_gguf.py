#!/usr/bin/env python3
"""Import oversized GGUF shards as independently compressed verified chunks.

The importer is intentionally resumable.  A completed chunk is immutable and has
its own receipt; mutable progress state is staging metadata, never evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


MIB = 1024 * 1024


@dataclass(frozen=True)
class SourceShard:
    name: str
    url: str
    size: int
    sha256: str


def sha256_path(path: Path, block_size: int = 8 * MIB) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def chunk_ranges(size: int, chunk_size: int) -> Iterable[tuple[int, int, int]]:
    index = 0
    for start in range(0, size, chunk_size):
        length = min(chunk_size, size - start)
        yield index, start, length
        index += 1


def fetch_range(curl: Path, shard: SourceShard, start: int, length: int, output: Path) -> None:
    end = start + length - 1
    subprocess.run(
        [
            str(curl), "-L", "--fail", "--silent", "--show-error",
            "--retry", "8", "--retry-all-errors", "--connect-timeout", "30",
            "--range", f"{start}-{end}", "--output", str(output), shard.url,
        ],
        check=True,
    )
    actual = output.stat().st_size
    if actual != length:
        raise RuntimeError(
            f"range length mismatch for {shard.name}@{start}: expected {length}, got {actual}"
        )


def compress_verified(zstd: Path, raw: Path, encoded_part: Path, level: int) -> tuple[str, str]:
    raw_hash = sha256_path(raw)
    subprocess.run(
        [str(zstd), f"-{level}", "-q", "-f", str(raw), "-o", str(encoded_part)],
        check=True,
    )
    decoded_hash = hashlib.sha256()
    process = subprocess.Popen(
        [str(zstd), "-q", "-d", "-c", str(encoded_part)], stdout=subprocess.PIPE
    )
    assert process.stdout is not None
    while block := process.stdout.read(8 * MIB):
        decoded_hash.update(block)
    if process.wait() != 0:
        raise RuntimeError(f"zstd verification failed for {encoded_part}")
    if decoded_hash.hexdigest() != raw_hash:
        raise RuntimeError(f"lossless round-trip mismatch for {encoded_part}")
    return raw_hash, sha256_path(encoded_part)


def receipt_valid(receipt_path: Path, encoded_path: Path) -> bool:
    if not receipt_path.is_file() or not encoded_path.is_file():
        return False
    receipt = json.loads(receipt_path.read_text())
    return (
        receipt.get("compressed_bytes") == encoded_path.stat().st_size
        and receipt.get("compressed_sha256") == sha256_path(encoded_path)
    )


def verify_shard(zstd: Path, shard: SourceShard, receipts: list[dict], root: Path) -> str:
    digest = hashlib.sha256()
    total = 0
    for receipt in sorted(receipts, key=lambda item: item["chunk_index"]):
        encoded_path = root / receipt["relative_path"]
        process = subprocess.Popen(
            [str(zstd), "-q", "-d", "-c", str(encoded_path)], stdout=subprocess.PIPE
        )
        assert process.stdout is not None
        while block := process.stdout.read(8 * MIB):
            total += len(block)
            digest.update(block)
        if process.wait() != 0:
            raise RuntimeError(f"final decode failed for {encoded_path}")
    if total != shard.size:
        raise RuntimeError(f"reconstructed size mismatch for {shard.name}: {total} != {shard.size}")
    actual = digest.hexdigest()
    if actual != shard.sha256:
        raise RuntimeError(f"source SHA-256 mismatch for {shard.name}: {actual} != {shard.sha256}")
    return actual


def import_shards(
    *, destination: Path, shards: list[SourceShard], chunk_size: int,
    level: int, reserve_bytes: int, curl: Path, zstd: Path,
) -> dict:
    destination.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(tempfile.mkdtemp(prefix="aion-gguf-import-"))
    all_receipts: list[dict] = []
    try:
        for shard_number, shard in enumerate(shards, start=1):
            shard_dir = destination / f"shard-{shard_number:02d}"
            shard_dir.mkdir(exist_ok=True)
            shard_receipts: list[dict] = []
            for chunk_index, start, length in chunk_ranges(shard.size, chunk_size):
                stem = f"chunk-{chunk_index:05d}"
                encoded = shard_dir / f"{stem}.zst"
                receipt_path = shard_dir / f"{stem}.json"
                if receipt_valid(receipt_path, encoded):
                    receipt = json.loads(receipt_path.read_text())
                    shard_receipts.append(receipt)
                    all_receipts.append(receipt)
                    print(
                        f"resume shard={shard_number}/{len(shards)} chunk={chunk_index} "
                        f"compressed={receipt['compressed_bytes']}",
                        flush=True,
                    )
                    continue

                free = shutil.disk_usage(destination).free
                if free - reserve_bytes < length:
                    raise RuntimeError(
                        f"insufficient safe working space: {free} free, {reserve_bytes} reserved"
                    )
                raw = temporary_root / f"shard-{shard_number:02d}-{stem}.raw"
                encoded_part = shard_dir / f"{stem}.zst.part"
                fetch_range(curl, shard, start, length, raw)
                raw_hash, encoded_hash = compress_verified(zstd, raw, encoded_part, level)
                os.replace(encoded_part, encoded)
                receipt = {
                    "schema": "aion.chunk-receipt.v1",
                    "source_shard": shard.name,
                    "source_offset": start,
                    "chunk_index": chunk_index,
                    "raw_bytes": length,
                    "raw_sha256": raw_hash,
                    "codec": "zstd-independent-frame",
                    "zstd_level": level,
                    "compressed_bytes": encoded.stat().st_size,
                    "compressed_sha256": encoded_hash,
                    "relative_path": str(encoded.relative_to(destination)),
                }
                atomic_json(receipt_path, receipt)
                shard_receipts.append(receipt)
                all_receipts.append(receipt)
                raw.unlink()
                saved = 100.0 * (1.0 - receipt["compressed_bytes"] / receipt["raw_bytes"])
                print(
                    f"stored shard={shard_number}/{len(shards)} chunk={chunk_index} "
                    f"raw={length} compressed={receipt['compressed_bytes']} saved={saved:.3f}%",
                    flush=True,
                )
                atomic_json(destination / "import-state.json", {
                    "schema": "aion.chunked-gguf-import-state.v1",
                    "status": "IN_PROGRESS",
                    "completed_chunks": len(all_receipts),
                    "raw_bytes_completed": sum(item["raw_bytes"] for item in all_receipts),
                    "compressed_bytes_completed": sum(item["compressed_bytes"] for item in all_receipts),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })

        verified_sources = []
        for shard_number, shard in enumerate(shards, start=1):
            prefix = f"shard-{shard_number:02d}/"
            receipts = [r for r in all_receipts if r["relative_path"].startswith(prefix)]
            verified_sources.append({**asdict(shard), "verified_sha256": verify_shard(
                zstd, shard, receipts, destination
            )})
        manifest = {
            "schema": "aion.chunked-gguf-warehouse.v1",
            "status": "COMPLETE_VERIFIED",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "representation": "bit-exact GGUF bytes in independently compressed Zstandard frames",
            "chunk_size_bytes": chunk_size,
            "zstd_level": level,
            "source_shards": verified_sources,
            "raw_bytes": sum(r["raw_bytes"] for r in all_receipts),
            "compressed_bytes": sum(r["compressed_bytes"] for r in all_receipts),
            "chunks": all_receipts,
        }
        atomic_json(destination / "manifest.v1.json", manifest)
        atomic_json(destination / "import-state.json", {
            "schema": "aion.chunked-gguf-import-state.v1",
            "status": "COMPLETE_VERIFIED",
            "manifest_sha256": sha256_path(destination / "manifest.v1.json"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        return manifest
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--chunk-mib", type=int, default=64)
    parser.add_argument("--zstd-level", type=int, default=3)
    parser.add_argument("--reserve-mib", type=int, default=1024)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = json.loads(args.source_manifest.read_text())
    shards = [SourceShard(**item) for item in payload["shards"]]
    curl = Path(shutil.which("curl") or "")
    zstd = Path(shutil.which("zstd") or "")
    if not curl.is_file() or not zstd.is_file():
        raise SystemExit("curl and zstd are required")
    manifest = import_shards(
        destination=args.destination.resolve(), shards=shards,
        chunk_size=args.chunk_mib * MIB, level=args.zstd_level,
        reserve_bytes=args.reserve_mib * MIB, curl=curl, zstd=zstd,
    )
    print(json.dumps({
        "status": manifest["status"],
        "raw_bytes": manifest["raw_bytes"],
        "compressed_bytes": manifest["compressed_bytes"],
    }, indent=2))


if __name__ == "__main__":
    main()
