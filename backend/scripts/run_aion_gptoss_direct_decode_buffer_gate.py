#!/usr/bin/env python3
"""Compare copied zstd output with exact reusable decode targets on real weights."""

from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import hashlib
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[int(fraction * (len(values) - 1))]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expert", type=int, required=True)
    parser.add_argument("--rounds", type=int, default=30)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    manifest = json.loads(args.manifest.read_text())
    entry = manifest["entries"][str(args.expert)]
    pack = Path(manifest["pack"])
    with pack.open("rb", buffering=0) as handle:
        handle.seek(int(entry["offset"]))
        chunk = handle.read(int(entry["compressed_bytes"]))
    encoded = []
    for component in entry["components"]:
        start = int(component["relative_offset"])
        value = chunk[start:start + int(component["compressed_bytes"])]
        if hashlib.sha256(value).hexdigest() != component["compressed_sha256"]:
            raise RuntimeError("encoded component hash mismatch")
        encoded.append(value)

    library = ctypes.CDLL(ctypes.util.find_library("zstd"))
    library.ZSTD_decompress.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
                                         ctypes.c_void_p, ctypes.c_size_t]
    library.ZSTD_decompress.restype = ctypes.c_size_t
    library.ZSTD_isError.argtypes = [ctypes.c_size_t]
    library.ZSTD_isError.restype = ctypes.c_uint
    reusable = [ctypes.create_string_buffer(int(component["raw_bytes"]))
                for component in entry["components"]]
    direct_sources = [ctypes.c_char_p(value) for value in encoded]
    samples = {"copied": [], "direct_allocated": [], "direct_reused": []}
    digests = {name: [] for name in samples}

    def run(name: str) -> str:
        digest = hashlib.sha256()
        for index, (value, component) in enumerate(zip(encoded, entry["components"], strict=True)):
            size = int(component["raw_bytes"])
            if name == "copied":
                target = ctypes.create_string_buffer(size)
                source = ctypes.create_string_buffer(value)
            elif name == "direct_allocated":
                target = ctypes.create_string_buffer(size)
                source = direct_sources[index]
            else:
                target = reusable[index]
                source = direct_sources[index]
            count = library.ZSTD_decompress(target, size, source, len(value))
            if library.ZSTD_isError(count) or int(count) != size:
                raise RuntimeError("zstd decode failed")
            digest.update(memoryview(target).cast("B"))
            if hashlib.sha256(memoryview(target).cast("B")).hexdigest() != component["raw_sha256"]:
                raise RuntimeError("decoded component hash mismatch")
        return digest.hexdigest()

    order = ("copied", "direct_allocated", "direct_reused",
             "direct_reused", "direct_allocated", "copied")
    for _ in range(args.rounds):
        for name in order:
            started = time.perf_counter_ns()
            digest = run(name)
            samples[name].append((time.perf_counter_ns() - started) / 1_000_000)
            digests[name].append(digest)
    if len(set(value for values in digests.values() for value in values)) != 1:
        raise RuntimeError("decode variants differ")
    summaries = {
        name: {"samples": len(values), "p50_ms": statistics.median(values),
               "p95_ms": percentile(values, .95)}
        for name, values in samples.items()
    }
    speedup = summaries["copied"]["p50_ms"] / summaries["direct_reused"]["p50_ms"]
    report = {
        "schema": "aion.gptoss-120b-direct-decode-buffer-gate.v1",
        "status": "ADVANCE_DIRECT_REUSABLE_DECODE" if speedup >= 1.10 else "NOT_PROMOTED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "layer": manifest["layer"], "expert": args.expert,
        "raw_bytes": sum(int(x["raw_bytes"]) for x in entry["components"]),
        "compressed_bytes": int(entry["compressed_bytes"]),
        "summaries": summaries,
        "direct_reuse_speedup": speedup,
        "all_outputs_hash_exact": True,
        "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "promotion_gate": {"minimum_median_speedup": 1.10, "requires_exact_hashes": True},
        "claim_boundary": (
            "One real expert's six encoded components were already resident for this decode-only "
            "ABBA gate. It isolates zstd source/target copies and allocation; it does not measure "
            "SD reads, native matrix calculation, full layers or generated-token throughput."
        ),
    }
    body = json.dumps(report, sort_keys=True, separators=(",", ":"))
    report["canonical_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "direct_reuse_speedup": speedup,
                      "summaries": summaries,
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
