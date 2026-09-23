#!/usr/bin/env python3
"""Parse both gpt-oss GGUF headers directly from the verified SD warehouse."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from backend.modules.aion_inference.expert_frame_gguf_reader import ExpertFrameGGUFReader
from backend.modules.aion_inference.gguf_stream_index import read_gguf_stream_index


RETAINED_KEYS = {
    "general.architecture", "general.name", "general.alignment", "general.file_type",
    "split.count", "split.no", "split.tensors.count",
    "gpt-oss.block_count", "gpt-oss.expert_count", "gpt-oss.expert_used_count",
    "gpt-oss.swiglu_clamp_exp", "gpt-oss.swiglu_clamp_shexp",
}


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def canonical_hash(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--cache-mib", type=int, default=32)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    manifest = json.loads(args.manifest.read_text())
    shards = []
    for source in manifest.get("verified_sources", []):
        reader = ExpertFrameGGUFReader(
            args.manifest, source["name"], cache_bytes=args.cache_mib * 1024 * 1024)
        index = read_gguf_stream_index(reader, int(source["size"]), RETAINED_KEYS)
        shards.append({
            "source_shard": source["name"],
            "source_bytes": int(source["size"]),
            "expected_sha256": source["expected_sha256"],
            "verified_sha256": source["verified_sha256"],
            "gguf_version": index["version"],
            "data_offset": index["data_offset"],
            "tensor_count": len(index["tensors"]),
            "metadata": index["metadata"],
            "reader_metrics": reader.metrics(),
        })
    report = {
        "schema": "aion.gptoss-warehouse-header-gate.v1",
        "status": "PASSED" if shards and all(
            row["expected_sha256"] == row["verified_sha256"] for row in shards) else "FAILED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "manifest": str(args.manifest.resolve()),
        "manifest_sha256": sha256_path(args.manifest),
        "cache_ceiling_bytes_per_reader": args.cache_mib * 1024 * 1024,
        "shards": shards,
        "claim_boundary": (
            "This proves bounded exact parsing of the original GGUF headers through the "
            "compressed expert-frame warehouse. It is not model inference and has no "
            "tokens-per-second meaning."
        ),
    }
    report["canonical_sha256"] = canonical_hash(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "output": str(args.output),
                      "canonical_sha256": report["canonical_sha256"],
                      "shards": [{"name": row["source_shard"],
                                  "tensors": row["tensor_count"],
                                  "metadata": row["metadata"],
                                  "metrics": row["reader_metrics"]}
                                 for row in shards]}, sort_keys=True))


if __name__ == "__main__":
    main()
