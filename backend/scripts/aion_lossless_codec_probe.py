#!/usr/bin/env python3
"""Compare exact Zstandard and LZ4 decoding on real shuffled expert frames."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import ctypes
import ctypes.util
import hashlib
import json
from pathlib import Path
import statistics
import time
from typing import Any

from backend.scripts.run_aion_layer_pack_experiment import (
    _decode_zstd_frame,
    _zstd_library,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)]


def _lz4_library():
    path = ctypes.util.find_library("lz4")
    if not path:
        raise RuntimeError("liblz4 is unavailable")
    library = ctypes.CDLL(path)
    library.LZ4_compressBound.argtypes = (ctypes.c_int,)
    library.LZ4_compressBound.restype = ctypes.c_int
    library.LZ4_compress_default.argtypes = (
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
    )
    library.LZ4_compress_default.restype = ctypes.c_int
    library.LZ4_decompress_safe.argtypes = (
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
    )
    library.LZ4_decompress_safe.restype = ctypes.c_int
    return library


def _shuffle2(raw: bytes) -> bytes:
    if len(raw) % 2:
        raise RuntimeError("unaligned BF16 frame")
    return raw[0::2] + raw[1::2]


def _unshuffle2(raw: bytearray) -> bytes:
    half = len(raw) // 2
    restored = bytearray(len(raw))
    restored[0::2] = raw[:half]
    restored[1::2] = raw[half:]
    return bytes(restored)


def _lz4_compress(library, transformed: bytes) -> bytes:
    capacity = library.LZ4_compressBound(len(transformed))
    target = ctypes.create_string_buffer(capacity)
    written = library.LZ4_compress_default(
        ctypes.c_char_p(transformed), target, len(transformed), capacity
    )
    if written <= 0:
        raise RuntimeError("LZ4 compression failed")
    return target.raw[:written]


def _lz4_decode(library, compressed: bytes, raw_bytes: int) -> bytes:
    transformed = bytearray(raw_bytes)
    written = library.LZ4_decompress_safe(
        ctypes.c_char_p(compressed),
        (ctypes.c_ubyte * raw_bytes).from_buffer(transformed),
        len(compressed),
        raw_bytes,
    )
    if written != raw_bytes:
        raise RuntimeError("LZ4 decode failed")
    return _unshuffle2(transformed)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zstd-manifest", type=Path, required=True)
    parser.add_argument("--route-observation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--layers", default="0,10,20,31")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    if args.workers < 1:
        raise SystemExit("workers must be positive")
    manifest_path = args.zstd_manifest.resolve()
    observation_path = args.route_observation.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    observation = json.loads(observation_path.read_text(encoding="utf-8"))
    zstd = _zstd_library()
    lz4 = _lz4_library()
    selected_layers = tuple(int(value) for value in args.layers.split(","))
    encoded: dict[tuple[int, str], dict[str, Any]] = {}
    total_raw = total_zstd = total_lz4 = 0

    for layer_number in selected_layers:
        layer = manifest["layers"][layer_number]
        pack_path = Path(layer["path"])
        if _sha256(pack_path) != layer["sha256"]:
            raise RuntimeError(f"pack hash failed: layer {layer_number}")
        requested = {
            int(expert)
            for batch in observation["route_batches_by_layer"][layer_number][1:]
            for route in batch
            for expert in route
        }
        with pack_path.open("rb") as handle:
            for expert in sorted(requested):
                for suffix in ("input_linear.weight", "output_linear.weight"):
                    name = f"experts.{expert}.{suffix}"
                    entry = layer["tensors"][name]
                    begin, end = map(int, entry["compressed_offsets"])
                    handle.seek(begin)
                    zstd_frame = handle.read(end - begin)
                    raw = bytes(_decode_zstd_frame(zstd, zstd_frame, entry))
                    if hashlib.sha256(raw).hexdigest() != entry["raw_sha256"]:
                        raise RuntimeError(f"source roundtrip failed: {layer_number}:{name}")
                    lz4_frame = _lz4_compress(lz4, _shuffle2(raw))
                    if hashlib.sha256(_lz4_decode(lz4, lz4_frame, len(raw))).hexdigest() != entry["raw_sha256"]:
                        raise RuntimeError(f"LZ4 roundtrip failed: {layer_number}:{name}")
                    encoded[(layer_number, name)] = {
                        "entry": entry,
                        "zstd": zstd_frame,
                        "lz4": lz4_frame,
                    }
                    total_raw += len(raw)
                    total_zstd += len(zstd_frame)
                    total_lz4 += len(lz4_frame)

    trials = []
    executor = ThreadPoolExecutor(max_workers=args.workers)
    try:
        for layer_number in selected_layers:
            for batch_number, batch in enumerate(
                observation["route_batches_by_layer"][layer_number][1:], start=1
            ):
                experts = sorted({int(expert) for route in batch for expert in route})
                names = [
                    f"experts.{expert}.{suffix}"
                    for expert in experts
                    for suffix in ("input_linear.weight", "output_linear.weight")
                ]
                order = ("zstd", "lz4") if batch_number % 2 else ("lz4", "zstd")
                expected = {name: encoded[(layer_number, name)]["entry"]["raw_sha256"] for name in names}
                for codec in order:
                    started = time.perf_counter()
                    if codec == "zstd":
                        values = list(executor.map(
                            lambda name: bytes(_decode_zstd_frame(
                                zstd,
                                encoded[(layer_number, name)]["zstd"],
                                encoded[(layer_number, name)]["entry"],
                            )),
                            names,
                        ))
                    else:
                        values = list(executor.map(
                            lambda name: _lz4_decode(
                                lz4,
                                encoded[(layer_number, name)]["lz4"],
                                int(encoded[(layer_number, name)]["entry"]["raw_bytes"]),
                            ),
                            names,
                        ))
                    seconds = time.perf_counter() - started
                    exact = all(
                        hashlib.sha256(value).hexdigest() == expected[name]
                        for name, value in zip(names, values, strict=True)
                    )
                    trials.append({
                        "layer": layer_number,
                        "batch": batch_number,
                        "codec": codec,
                        "frames": len(names),
                        "seconds": seconds,
                        "all_raw_hashes_exact": exact,
                    })
    finally:
        executor.shutdown(wait=True)

    summaries = {}
    for codec in ("zstd", "lz4"):
        values = [trial["seconds"] for trial in trials if trial["codec"] == codec]
        summaries[codec] = {
            "sample_count": len(values),
            "p50_seconds": statistics.median(values),
            "p95_seconds": _p95(values),
            "total_seconds": sum(values),
        }
    summaries["lz4"]["p50_decode_improvement_percent_vs_zstd"] = 100.0 * (
        1.0 - summaries["lz4"]["p50_seconds"] / summaries["zstd"]["p50_seconds"]
    )
    report = {
        "schema_version": "aion.lossless-codec-probe.v1",
        "zstd_manifest": str(manifest_path),
        "zstd_manifest_file_sha256": _sha256(manifest_path),
        "route_observation": str(observation_path),
        "route_observation_file_sha256": _sha256(observation_path),
        "layers": list(selected_layers),
        "workers": args.workers,
        "sampled_unique_frames": len(encoded),
        "sampled_storage": {
            "raw_bytes": total_raw,
            "zstd_bytes": total_zstd,
            "lz4_bytes": total_lz4,
            "zstd_reduction_percent": 100.0 * (1.0 - total_zstd / total_raw),
            "lz4_reduction_percent": 100.0 * (1.0 - total_lz4 / total_raw),
        },
        "summaries": summaries,
        "integrity": {
            "all_source_and_lz4_roundtrips_exact": True,
            "all_timed_raw_hashes_exact": all(t["all_raw_hashes_exact"] for t in trials),
        },
        "method": "In-memory codec comparison over all generated-route experts in four real model layers; rotating codec order; four shared workers; no storage I/O in timed region.",
        "claim_boundary": "Mechanism-only decode and sampled compression test. Full SD pack, model exactness, memory, physical reads, and end-to-end latency remain unproven.",
        "trials": trials,
    }
    report["report_sha256"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "report_sha256": report["report_sha256"],
        "sampled_storage": report["sampled_storage"],
        "summaries": summaries,
        "integrity": report["integrity"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
