#!/usr/bin/env python3
"""Bind the exact in-memory 6+4 GiB core/halo scale result to its controls."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def response(run: dict, prompt_positions: int) -> dict:
    tokens = run["tokens"][prompt_positions:]
    times = [token["wall_seconds"] for token in tokens]
    wall = sum(times)
    return {
        "tokens": len(tokens),
        "wall_seconds": wall,
        "tokens_per_second": len(tokens) / wall,
        "latency_p50_seconds": statistics.median(times),
        "latency_p95_seconds": sorted(times)[int(.95 * (len(times) - 1))],
        "store_metric_delta": run["store_metric_delta"],
    }


def same_trace(left: dict, right: dict) -> bool:
    return all(
        a["generated_token_id"] == b["generated_token_id"]
        and a["final_hidden_sha256"] == b["final_hidden_sha256"]
        and a["logits_sha256"] == b["logits_sha256"]
        and [x["route"] for x in a["layers"]] == [x["route"] for x in b["layers"]]
        for a, b in zip(left["tokens"], right["tokens"], strict=True)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--file-flow", type=Path, required=True)
    parser.add_argument("--memory-flow", type=Path, required=True)
    parser.add_argument("--prompt-positions", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    control, file_flow, memory_flow = map(load, (args.control, args.file_flow, args.memory_flow))
    exact_control = all(same_trace(memory_flow[name], control[name]) for name in ("run_a", "run_b"))
    exact_file = all(same_trace(memory_flow[name], file_flow[name]) for name in ("run_a", "run_b"))
    result = {
        "schema": "aion.gptoss-120b-inmemory-core-halo-scale-gate.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "prompt_positions": args.prompt_positions,
        "inputs": {
            name: {"path": str(path.resolve()), "file_sha256": file_hash(path),
                   "canonical_sha256": value["canonical_sha256"]}
            for name, path, value in (
                ("unrestricted_control", args.control, control),
                ("file_flow_core_halo", args.file_flow, file_flow),
                ("memory_flow_core_halo", args.memory_flow, memory_flow),
            )
        },
        "file_flow": {name: response(file_flow[name], args.prompt_positions)
                      for name in ("run_a", "run_b")},
        "memory_flow": {name: response(memory_flow[name], args.prompt_positions)
                        for name in ("run_a", "run_b")},
        "paired_speedup_percent": [
            (response(file_flow[name], args.prompt_positions)["wall_seconds"]
             / response(memory_flow[name], args.prompt_positions)["wall_seconds"] - 1) * 100
            for name in ("run_a", "run_b")
        ],
        "exact_to_unrestricted_control": exact_control,
        "exact_to_file_flow_core_halo": exact_file,
        "decision": "NOT_PROMOTED_FOR_SD_BOUND_GENERATION",
        "claim_boundary": (
            "The exact in-memory layer flow was scaled to the promoted 6+4 GiB core/halo "
            "configuration over a 26-position prompt and 22 generated positions, twice. "
            "It remained bit-exact but delivered no replicated response-speed improvement: "
            "one pass was marginally faster and one regressed. The resident-only 6.24x gain "
            "therefore does not transfer while SD expert faults dominate."
        ),
    }
    body = json.dumps(result, sort_keys=True, separators=(",", ":"))
    result["canonical_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"decision": result["decision"], "exact": exact_control and exact_file,
                      "paired_speedup_percent": result["paired_speedup_percent"],
                      "canonical_sha256": result["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
