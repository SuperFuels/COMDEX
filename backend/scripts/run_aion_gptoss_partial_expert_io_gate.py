#!/usr/bin/env python3
"""Measure one fully imported gpt-oss expert before the whole warehouse exists."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from backend.modules.aion_inference.gptoss_expert_frame_store import _zstd


EXPERT = re.compile(r"^blk\.(?P<layer>\d+)\.ffn_(?P<projection>down|gate|up)_exps\.(?P<kind>weight|bias)$")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * fraction + 0.999999)))
    return ordered[position]


def addresses(root: Path, layer: int, expert: int) -> list[dict]:
    result = []
    for receipt_path in sorted((root / "receipts").glob("shard-*/*.json")):
        if receipt_path.name.startswith("._"):
            continue
        receipt = json.loads(receipt_path.read_text())
        match = EXPERT.match(receipt["region_name"])
        if not match or int(match.group("layer")) != layer:
            continue
        frame = next((item for item in receipt["frames"]
                      if int(item["expert"]) == expert), None)
        if frame is not None:
            result.append({**frame, "projection": match.group("projection"),
                           "kind": match.group("kind"),
                           "path": str(root / receipt["pack_relative_path"])})
    if {(item["projection"], item["kind"]) for item in result} != {
            (projection, kind) for projection in ("gate", "up", "down")
            for kind in ("weight", "bias")}:
        raise RuntimeError("selected expert is not completely imported")
    return result


def run_once(library: ctypes.CDLL, items: list[dict], uncached: bool) -> dict:
    started = time.perf_counter()
    compressed = raw_total = 0
    for item in items:
        path = Path(item["path"])
        with path.open("rb", buffering=0) as handle:
            if uncached:
                try:
                    import fcntl
                    fcntl.fcntl(handle.fileno(), 48, 1)  # macOS F_NOCACHE
                except (ImportError, OSError):
                    pass
            encoded = os.pread(handle.fileno(), int(item["compressed_bytes"]),
                               int(item["encoded_offset"]))
        if hashlib.sha256(encoded).hexdigest() != item["compressed_sha256"]:
            raise RuntimeError("compressed frame hash mismatch")
        raw_size = int(item["raw_bytes"])
        target = ctypes.create_string_buffer(raw_size)
        source = ctypes.create_string_buffer(encoded)
        decoded = library.ZSTD_decompress(target, raw_size, source, len(encoded))
        if library.ZSTD_isError(decoded) or int(decoded) != raw_size:
            raise RuntimeError("frame decode failed")
        if hashlib.sha256(target.raw).hexdigest() != item["raw_sha256"]:
            raise RuntimeError("decoded frame hash mismatch")
        compressed += len(encoded)
        raw_total += raw_size
    return {"seconds": time.perf_counter() - started,
            "compressed_bytes": compressed, "raw_bytes": raw_total}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warehouse", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=0)
    parser.add_argument("--expert", type=int, default=0)
    parser.add_argument("--repetitions", type=int, default=4)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.warehouse.resolve()
    state_path = root / "import-state.json"
    state = json.loads(state_path.read_text())
    if state.get("status") != "IN_PROGRESS":
        raise SystemExit("this diagnostic is only for a partial import")
    items = addresses(root, args.layer, args.expert)
    library = _zstd()
    samples = {"f_nocache_requested": [], "normal_read": []}
    order = ["f_nocache_requested", "normal_read", "normal_read", "f_nocache_requested"] * args.repetitions
    for condition in order:
        samples[condition].append(run_once(
            library, items, condition == "f_nocache_requested"))
    summary = {}
    for condition, values in samples.items():
        times = [item["seconds"] for item in values]
        summary[condition] = {
            "runs": len(values), "p50_seconds": statistics.median(times),
            "p95_seconds": percentile(times, 0.95),
            "compressed_bytes_per_expert": values[0]["compressed_bytes"],
            "raw_bytes_per_expert": values[0]["raw_bytes"],
        }
    report = {
        "schema": "aion.gptoss-partial-expert-io-gate.v1",
        "status": "PARTIAL_STORAGE_GATE_NOT_MODEL_INFERENCE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "warehouse": str(root), "import_state": state,
        "import_state_sha256": sha(state_path),
        "layer": args.layer, "expert": args.expert,
        "condition_order": order, "all_frame_hashes_verified": True,
        "summary": summary, "samples": samples,
        "claim_boundary": "Measures six-frame SD read, Zstandard decode and SHA-256 verification for one imported expert while the full import is paused. F_NOCACHE is requested but does not prove that pages populated by the importer were absent from all operating-system caches. It is not model generation and has no tokens-per-second meaning.",
    }
    report["canonical_sha256"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(args.output), "summary": summary,
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
