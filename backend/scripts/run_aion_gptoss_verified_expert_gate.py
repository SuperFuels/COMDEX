#!/usr/bin/env python3
"""Load and reuse one exact gpt-oss expert from the verified SD warehouse."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssExpertFrameStore


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def payload_sha256(value: dict[str, dict[str, bytes]]) -> str:
    digest = hashlib.sha256()
    for projection in ("gate", "up", "down"):
        for kind in ("weight", "bias"):
            digest.update(projection.encode() + b"\0" + kind.encode() + b"\0")
            digest.update(value[projection][kind])
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=0)
    parser.add_argument("--expert", type=int, default=0)
    parser.add_argument("--cache-mib", type=int, default=64)
    parser.add_argument("--warm-repetitions", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    store = GptOssExpertFrameStore(
        args.manifest, capacity_bytes=args.cache_mib * 1024 * 1024)
    started = time.perf_counter()
    value = store.get(args.layer, args.expert)
    cold_seconds = time.perf_counter() - started
    raw_bytes = sum(len(component) for projection in value.values()
                    for component in projection.values())
    digest = payload_sha256(value)
    warm_seconds = []
    for _ in range(args.warm_repetitions):
        started = time.perf_counter()
        repeated = store.get(args.layer, args.expert)
        warm_seconds.append(time.perf_counter() - started)
        if payload_sha256(repeated) != digest:
            raise RuntimeError("warm expert payload changed")
    metrics = store.metrics()
    passed = (
        metrics["faults"] == 1
        and metrics["hits"] == args.warm_repetitions
        and metrics["resident_bytes"] == raw_bytes
        and metrics["peak_resident_bytes"] <= args.cache_mib * 1024 * 1024
    )
    report = {
        "schema": "aion.gptoss-verified-expert-gate.v1",
        "status": "PASSED" if passed else "FAILED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "manifest": str(args.manifest.resolve()),
        "manifest_sha256": sha256_path(args.manifest),
        "layer": args.layer, "expert": args.expert,
        "cache_ceiling_bytes": args.cache_mib * 1024 * 1024,
        "expert_raw_bytes": raw_bytes,
        "expert_payload_sha256": digest,
        "cold_process_fault_seconds": cold_seconds,
        "warm_cache_seconds": warm_seconds,
        "warm_cache_p50_seconds": statistics.median(warm_seconds),
        "metrics": metrics,
        "all_six_component_frame_hashes_verified": True,
        "claim_boundary": (
            "This proves exact bounded demand loading and process-cache reuse of one "
            "six-component gpt-oss expert. The first read is a process-cache fault, not "
            "proof of an operating-system-cold SD read. It is not model inference."
        ),
    }
    report["canonical_sha256"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "output": str(args.output),
                      "expert_raw_bytes": raw_bytes,
                      "cold_process_fault_seconds": cold_seconds,
                      "warm_cache_p50_seconds": report["warm_cache_p50_seconds"],
                      "metrics": metrics,
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
