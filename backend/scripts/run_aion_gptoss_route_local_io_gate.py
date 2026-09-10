#!/usr/bin/env python3
"""ABBA-test scattered component frames against exact expert-local reads."""

from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import fcntl
import hashlib
import json
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path


COMPONENTS = tuple((projection, kind) for projection in ("gate", "up", "down")
                   for kind in ("weight", "bias"))


def zstd() -> ctypes.CDLL:
    library = ctypes.CDLL(ctypes.util.find_library("zstd"))
    library.ZSTD_decompress.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
                                         ctypes.c_void_p, ctypes.c_size_t]
    library.ZSTD_decompress.restype = ctypes.c_size_t
    library.ZSTD_isError.argtypes = [ctypes.c_size_t]
    library.ZSTD_isError.restype = ctypes.c_uint
    return library


def decode(library: ctypes.CDLL, encoded: bytes, address: dict) -> bytes:
    if hashlib.sha256(encoded).hexdigest() != address["compressed_sha256"]:
        raise RuntimeError("compressed hash mismatch")
    target = ctypes.create_string_buffer(int(address["raw_bytes"]))
    source = ctypes.create_string_buffer(encoded)
    count = library.ZSTD_decompress(target, int(address["raw_bytes"]), source, len(encoded))
    if library.ZSTD_isError(count) or int(count) != int(address["raw_bytes"]):
        raise RuntimeError("zstd decode failed")
    raw = target.raw
    if hashlib.sha256(raw).hexdigest() != address["raw_sha256"]:
        raise RuntimeError("raw hash mismatch")
    return raw


def open_uncached(path: str | Path) -> int:
    fd = os.open(path, os.O_RDONLY)
    fcntl.fcntl(fd, fcntl.F_NOCACHE, 1)
    return fd


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[int(fraction * (len(values) - 1))]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warehouse-manifest", type=Path, required=True)
    parser.add_argument("--route-local-manifest", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    warehouse = json.loads(args.warehouse_manifest.read_text())
    local = json.loads(args.route_local_manifest.read_text())
    trace = json.loads(args.trace.read_text())
    if local["status"] != "COMPLETE_VERIFIED":
        raise SystemExit("route-local pack is not verified")
    layer = int(local["layer"])
    addresses = {}
    for region in warehouse["regions"]:
        prefix = f"blk.{layer}.ffn_"
        if not region["region_name"].startswith(prefix):
            continue
        suffix = region["region_name"][len(prefix):]
        if "_exps." not in suffix:
            continue
        projection, kind = suffix.split("_exps.")
        if (projection, kind) not in COMPONENTS:
            continue
        path = args.warehouse_manifest.parent / region["pack_relative_path"]
        for frame in region["frames"]:
            addresses[(int(frame["expert"]), projection, kind)] = {**frame, "path": path}
    selected = set(local["experts"])
    routes = [token["layers"][layer]["route"] for token in trace["run_a"]["tokens"]
              if set(token["layers"][layer]["route"]) <= selected]
    if not routes:
        raise SystemExit("trace has no route fully represented by the micropack")
    library = zstd()

    def scattered(route: list[int]) -> tuple[str, int]:
        digest = hashlib.sha256(); reads = 0
        for expert in route:
            for projection, kind in COMPONENTS:
                address = addresses[(expert, projection, kind)]
                fd = open_uncached(address["path"])
                try:
                    encoded = os.pread(fd, int(address["compressed_bytes"]),
                                       int(address["encoded_offset"]))
                finally:
                    os.close(fd)
                digest.update(decode(library, encoded, address)); reads += 1
        return digest.hexdigest(), reads

    local_fd = open_uncached(local["pack"])
    def route_local(route: list[int]) -> tuple[str, int]:
        digest = hashlib.sha256(); reads = 0
        for expert in route:
            entry = local["entries"][str(expert)]
            chunk = os.pread(local_fd, int(entry["compressed_bytes"]), int(entry["offset"]))
            if len(chunk) != int(entry["compressed_bytes"]):
                raise RuntimeError("short route-local expert read")
            for component in entry["components"]:
                start = int(component["relative_offset"])
                end = start + int(component["compressed_bytes"])
                digest.update(decode(library, chunk[start:end], component))
            reads += 1
        return digest.hexdigest(), reads

    samples = {"scattered": [], "route_local": []}; digests = []
    try:
        for index, route in enumerate(routes):
            order = ("scattered", "route_local", "route_local", "scattered") \
                if index % 2 == 0 else ("route_local", "scattered", "scattered", "route_local")
            observed = {}
            for name in order:
                started = time.perf_counter_ns()
                value, reads = scattered(route) if name == "scattered" else route_local(route)
                elapsed = (time.perf_counter_ns() - started) / 1_000_000
                samples[name].append({"milliseconds": elapsed, "read_calls": reads})
                observed.setdefault(name, value)
            if observed["scattered"] != observed["route_local"]:
                raise RuntimeError("route-local decoded values differ")
            digests.append(observed["scattered"])
    finally:
        os.close(local_fd)
    summary = {}
    for name, values in samples.items():
        times = [value["milliseconds"] for value in values]
        summary[name] = {"samples": len(times), "p50_ms": statistics.median(times),
                         "p95_ms": percentile(times, .95),
                         "read_calls_per_route": values[0]["read_calls"]}
    speedup = summary["scattered"]["p50_ms"] / summary["route_local"]["p50_ms"]
    report = {
        "schema": "aion.gptoss-120b-route-local-io-gate.v1",
        "status": "ADVANCE_ROUTE_LOCAL_LAYOUT" if speedup >= 1.15 else "NOT_PROMOTED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "layer": layer, "routes": routes, "route_count": len(routes),
        "summaries": summary, "median_speedup": speedup,
        "decoded_route_digests": digests,
        "all_decoded_values_exact": True,
        "macos_f_nocache": True,
        "route_local_manifest": str(args.route_local_manifest.resolve()),
        "route_local_manifest_sha256": hashlib.sha256(args.route_local_manifest.read_bytes()).hexdigest(),
        "trace_sha256": hashlib.sha256(args.trace.read_bytes()).hexdigest(),
        "claim_boundary": (
            "This is an uncached one-layer I/O/decompression microgate over routes contained "
            "in a 32-expert trace-selected micropack. It tests exact physical layout and does "
            "not establish full-token speed or held-out route coverage."
        ),
    }
    body = json.dumps(report, sort_keys=True, separators=(",", ":"))
    report["canonical_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "median_speedup": speedup,
                      "route_count": len(routes),
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
