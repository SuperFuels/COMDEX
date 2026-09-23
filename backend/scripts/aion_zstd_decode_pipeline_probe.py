#!/usr/bin/env python3
"""Measure coalesced reads and bounded parallel decode on real expert routes."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import ctypes
import ctypes.util
import hashlib
import json
import os
from pathlib import Path
import statistics
import time
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _summary(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    return {
        "p50_seconds": statistics.median(values),
        "p95_seconds": ordered[max(0, int(0.95 * len(ordered) + 0.999999) - 1)],
        "total_seconds": sum(values),
    }


def _library():
    path = ctypes.util.find_library("zstd")
    if not path:
        raise RuntimeError("system libzstd is unavailable")
    library = ctypes.CDLL(path)
    library.ZSTD_decompress.argtypes = (
        ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t
    )
    library.ZSTD_decompress.restype = ctypes.c_size_t
    library.ZSTD_isError.argtypes = (ctypes.c_size_t,)
    library.ZSTD_isError.restype = ctypes.c_uint
    return library


def _decode(library, compressed: bytes, entry: dict[str, Any]) -> bytes:
    raw = bytearray(int(entry["raw_bytes"]))
    written = library.ZSTD_decompress(
        (ctypes.c_ubyte * len(raw)).from_buffer(raw), len(raw),
        ctypes.c_char_p(compressed), len(compressed),
    )
    if library.ZSTD_isError(written) or written != len(raw):
        raise RuntimeError("zstd frame decode failed")
    if int(entry.get("byte_shuffle_width", 0)) == 2:
        half = len(raw) // 2
        restored = bytearray(len(raw))
        restored[0::2] = raw[:half]
        restored[1::2] = raw[half:]
        raw = restored
    return bytes(raw)


def _frames(layer: dict[str, Any], experts: tuple[int, ...]) -> list[tuple[str, dict[str, Any]]]:
    wanted = set(experts)
    result = []
    for expert in layer["expert_order"]:
        if expert not in wanted:
            continue
        for suffix in ("input_linear.weight", "output_linear.weight"):
            name = f"experts.{expert}.{suffix}"
            result.append((name, layer["tensors"][name]))
    return result


def _sequential(path: Path, frames, library) -> tuple[list[tuple[str, bytes]], int, float, float]:
    read_seconds = decode_seconds = 0.0
    decoded = []
    with path.open("rb") as handle:
        for name, entry in frames:
            begin, end = map(int, entry["compressed_offsets"])
            started = time.perf_counter()
            handle.seek(begin)
            compressed = handle.read(end - begin)
            read_seconds += time.perf_counter() - started
            started = time.perf_counter()
            decoded.append((name, _decode(library, compressed, entry)))
            decode_seconds += time.perf_counter() - started
    return decoded, len(frames), read_seconds, decode_seconds


def _coalesced(path: Path, frames, library, workers: int) -> tuple[list[tuple[str, bytes]], int, float, float]:
    expert_groups: list[list[tuple[str, dict[str, Any]]]] = []
    for frame in frames:
        expert = int(frame[0].split(".")[1])
        if not expert_groups or int(expert_groups[-1][0][0].split(".")[1]) != expert:
            expert_groups.append([])
        expert_groups[-1].append(frame)
    runs: list[list[tuple[str, dict[str, Any]]]] = []
    for group in expert_groups:
        begin = int(group[0][1]["compressed_offsets"][0])
        if runs and int(runs[-1][-1][1]["compressed_offsets"][1]) == begin:
            runs[-1].extend(group)
        else:
            runs.append(list(group))
    compressed_frames: list[tuple[str, dict[str, Any], bytes]] = []
    read_started = time.perf_counter()
    descriptor = os.open(path, os.O_RDONLY)
    try:
        for run in runs:
            run_begin = int(run[0][1]["compressed_offsets"][0])
            run_end = int(run[-1][1]["compressed_offsets"][1])
            block = os.pread(descriptor, run_end - run_begin, run_begin)
            if len(block) != run_end - run_begin:
                raise RuntimeError("short coalesced read")
            for name, entry in run:
                begin, end = map(int, entry["compressed_offsets"])
                compressed_frames.append((name, entry, block[begin - run_begin:end - run_begin]))
    finally:
        os.close(descriptor)
    read_seconds = time.perf_counter() - read_started
    decode_started = time.perf_counter()
    if workers == 1:
        raw_values = [_decode(library, compressed, entry) for _, entry, compressed in compressed_frames]
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            raw_values = list(executor.map(
                lambda item: _decode(library, item[2], item[1]), compressed_frames
            ))
    decode_seconds = time.perf_counter() - decode_started
    return list(zip((item[0] for item in compressed_frames), raw_values, strict=True)), len(runs), read_seconds, decode_seconds


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--route-observation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--layers", default="0,10,20,31")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    manifest_path = args.manifest.resolve()
    observation_path = args.route_observation.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    observation = json.loads(observation_path.read_text(encoding="utf-8"))
    library = _library()
    selected_layers = tuple(int(value) for value in args.layers.split(","))
    conditions = ("sequential", "coalesced_w1", "coalesced_w2", "coalesced_w4", "coalesced_w8")
    trials = []
    for layer_number in selected_layers:
        layer = manifest["layers"][layer_number]
        path = Path(layer["path"])
        if _sha256(path) != layer["sha256"]:
            raise RuntimeError(f"layer integrity failed: {layer_number}")
        batches = observation["route_batches_by_layer"][layer_number][1:]
        for batch_number, batch in enumerate(batches):
            experts = tuple(sorted({expert for route in batch for expert in route}))
            frames = _frames(layer, experts)
            order = conditions[batch_number % len(conditions):] + conditions[:batch_number % len(conditions)]
            expected = None
            for condition in order:
                started = time.perf_counter()
                if condition == "sequential":
                    decoded, read_calls, read_seconds, decode_seconds = _sequential(path, frames, library)
                    workers = 1
                else:
                    workers = int(condition.rsplit("w", 1)[1])
                    decoded, read_calls, read_seconds, decode_seconds = _coalesced(path, frames, library, workers)
                total_seconds = time.perf_counter() - started
                hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in decoded}
                manifest_exact = all(hashes[name] == layer["tensors"][name]["raw_sha256"] for name in hashes)
                if expected is None:
                    expected = hashes
                trials.append({
                    "layer": layer_number,
                    "batch": batch_number + 1,
                    "condition": condition,
                    "experts": len(experts),
                    "frames": len(frames),
                    "read_calls": read_calls,
                    "read_seconds": read_seconds,
                    "decode_seconds": decode_seconds,
                    "total_seconds": total_seconds,
                    "workers": workers,
                    "exact_manifest_hashes": manifest_exact,
                    "exact_across_conditions": hashes == expected,
                })
    summaries = {}
    for condition in conditions:
        selected = [trial for trial in trials if trial["condition"] == condition]
        summaries[condition] = {
            key: _summary([float(trial[key]) for trial in selected])
            for key in ("read_seconds", "decode_seconds", "total_seconds")
        } | {
            "mean_read_calls": statistics.mean(trial["read_calls"] for trial in selected),
            "sample_count": len(selected),
        }
    baseline = summaries["sequential"]["total_seconds"]["p50_seconds"]
    for condition in conditions[1:]:
        candidate = summaries[condition]["total_seconds"]["p50_seconds"]
        summaries[condition]["p50_improvement_percent"] = 100.0 * (1.0 - candidate / baseline)
    report: dict[str, Any] = {
        "schema_version": "aion.zstd-decode-pipeline-probe.v1",
        "manifest": str(manifest_path),
        "manifest_file_sha256": _sha256(manifest_path),
        "route_observation": str(observation_path),
        "route_observation_file_sha256": _sha256(observation_path),
        "layers": list(selected_layers),
        "conditions": list(conditions),
        "method": "Rotating condition order over real generated-token route sets; warm uncontrolled filesystem cache.",
        "summaries": summaries,
        "integrity": {
            "all_manifest_hashes_exact": all(trial["exact_manifest_hashes"] for trial in trials),
            "all_condition_outputs_exact": all(trial["exact_across_conditions"] for trial in trials),
        },
        "trials": trials,
        "claim_boundary": "Mechanism-only compressed read/decode test. It does not establish model token, logit, memory, or end-to-end throughput improvement.",
    }
    report["report_sha256"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "report_sha256": report["report_sha256"], "integrity": report["integrity"], "summaries": summaries}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
