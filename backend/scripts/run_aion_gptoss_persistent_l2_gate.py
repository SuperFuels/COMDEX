#!/usr/bin/env python3
"""Cross-process exact retrieval gate for the bounded internal-NVMe expert L2."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from backend.modules.aion_inference.gptoss_expert_frame_store import (
    GptOssPersistentL2ExpertFrameStore,
)


ORDER = tuple((projection, kind) for projection in ("gate", "up", "down")
              for kind in ("weight", "bias"))


def expert_sha(value: dict[str, dict[str, bytes]]) -> str:
    digest = hashlib.sha256()
    for projection, kind in ORDER:
        digest.update(value[projection][kind])
    return digest.hexdigest()


def worker(args: argparse.Namespace) -> int:
    store = GptOssPersistentL2ExpertFrameStore(
        args.manifest, 0, args.cache_root, args.l2_capacity_mib * 1024 * 1024)
    experts = [int(value) for value in args.experts.split(",")]
    started = time.perf_counter_ns()
    values = store.get_layer_route_parallel(args.layer, experts, workers=args.workers)
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
    result = {
        "elapsed_ms": elapsed_ms,
        "expert_sha256": [expert_sha(value) for value in values],
        "metrics": store.metrics(),
    }
    if args.worker_output.exists():
        raise SystemExit("refusing to overwrite worker evidence")
    args.worker_output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[int(0.95 * (len(ordered) - 1))]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=35)
    parser.add_argument("--experts", default="0,31,63,127")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--l2-capacity-mib", type=int, default=256)
    parser.add_argument("--l2-runs", type=int, default=4)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--worker-output", type=Path)
    args = parser.parse_args()
    if args.worker_output is not None:
        return worker(args)
    if args.output is None:
        raise SystemExit("--output is required")
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    if args.cache_root.exists() and any(args.cache_root.rglob("*.aionraw")):
        raise SystemExit("cache root already contains expert frames")
    args.cache_root.mkdir(parents=True, exist_ok=True)
    worker_outputs = []
    for index in range(1 + args.l2_runs):
        output = args.cache_root / f"worker-{index}.json"
        command = [
            sys.executable, str(Path(__file__).resolve()),
            "--manifest", str(args.manifest),
            "--cache-root", str(args.cache_root),
            "--layer", str(args.layer),
            "--experts", args.experts,
            "--workers", str(args.workers),
            "--l2-capacity-mib", str(args.l2_capacity_mib),
            "--worker-output", str(output),
        ]
        subprocess.run(command, check=True)
        worker_outputs.append(json.loads(output.read_text()))
    populate = worker_outputs[0]
    l2_runs = worker_outputs[1:]
    l2_times = [run["elapsed_ms"] for run in l2_runs]
    hashes = [run["expert_sha256"] for run in worker_outputs]
    exact = len({tuple(value) for value in hashes}) == 1
    cross_process = all(run["metrics"]["sd_fallbacks"] == 0
                        and run["metrics"]["l2_hits"] == len(hashes[0])
                        for run in l2_runs)
    speedup = populate["elapsed_ms"] / statistics.median(l2_times)
    result = {
        "schema": "aion.gptoss-120b-persistent-internal-l2-gate.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "layer": args.layer,
        "experts": [int(value) for value in args.experts.split(",")],
        "workers": args.workers,
        "l2_capacity_bytes": args.l2_capacity_mib * 1024 * 1024,
        "cache_root": str(args.cache_root.resolve()),
        "populate": populate,
        "l2_runs": l2_runs,
        "l2_elapsed_p50_ms": statistics.median(l2_times),
        "l2_elapsed_p95_ms": p95(l2_times),
        "populate_over_l2_speedup": speedup,
        "all_expert_bytes_bitwise_equal": exact,
        "all_l2_runs_avoided_sd": cross_process,
        "status": "ADVANCE_PERSISTENT_L2" if exact and cross_process and speedup >= 5.0
                  else "NOT_PROMOTED",
        "claim_boundary": (
            "Four original experts were populated from the authoritative SD warehouse and "
            "then read by fresh Python processes from a hash-verified internal-disk L2. The "
            "populate cost is disclosed. macOS may retain newly written L2 pages in its page "
            "cache, so this is a cross-process warm-L2 gate, not a reboot-cold NVMe claim or "
            "generated-token measurement."
        ),
    }
    result["canonical_sha256"] = hashlib.sha256(json.dumps(
        result, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: result[key] for key in (
        "status", "populate_over_l2_speedup", "l2_elapsed_p50_ms",
        "l2_elapsed_p95_ms", "all_expert_bytes_bitwise_equal",
        "all_l2_runs_avoided_sd", "canonical_sha256",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
