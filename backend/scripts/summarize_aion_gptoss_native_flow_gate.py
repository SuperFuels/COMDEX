#!/usr/bin/env python3
"""Bind the fused-Metal, reusable-graph, and in-memory-flow experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metal", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--file-flow", type=Path, required=True)
    parser.add_argument("--memory-flow", type=Path, required=True)
    parser.add_argument("--two-token-memory-flow", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")

    metal, graph = load(args.metal), load(args.graph)
    file_flow, memory_flow = load(args.file_flow), load(args.memory_flow)
    two_token = load(args.two_token_memory_flow)
    flow_exact = all((
        file_flow["generated_token_id"] == memory_flow["generated_token_id"],
        file_flow["run_a"]["final_hidden_sha256"] == memory_flow["run_a"]["final_hidden_sha256"],
        file_flow["run_a"]["logits_sha256"] == memory_flow["run_a"]["logits_sha256"],
        [x["route"] for x in file_flow["run_a"]["layers"]]
        == [x["route"] for x in memory_flow["run_a"]["layers"]],
    ))
    warm_speedup = file_flow["run_b"]["wall_seconds"] / memory_flow["run_b"]["wall_seconds"]
    result = {
        "schema": "aion.gptoss-120b-native-flow-gates.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "inputs": {
            name: {"path": str(path.resolve()), "file_sha256": digest(path)}
            for name, path in {
                "fused_metal": args.metal,
                "reusable_graph": args.graph,
                "file_layer_flow": args.file_flow,
                "memory_layer_flow": args.memory_flow,
                "two_token_memory_flow": args.two_token_memory_flow,
            }.items()
        },
        "fused_metal": {
            "status": metal["status"],
            "cpu_p50_ms": metal["cpu"]["p50_ms"],
            "metal_p50_ms": metal["fused_metal"]["warm_p50_ms"],
            "metal_speedup": metal["metal_speedup"],
            "relative_l2_error": metal["relative_l2_error"],
            "bitwise_equal": metal["outputs_bitwise_equal"],
        },
        "reusable_graph": {
            "status": graph["status"],
            "wall_speedup": graph["wall_speedup"],
            "bitwise_equal": graph["all_outputs_bitwise_equal"],
        },
        "inmemory_layer_flow": {
            "status": "PROMOTE_EXACT_RESIDENT_FLOW" if flow_exact and warm_speedup >= 1.15 else "NOT_PROMOTED",
            "file_flow_warm_seconds": file_flow["run_b"]["wall_seconds"],
            "memory_flow_warm_seconds": memory_flow["run_b"]["wall_seconds"],
            "warm_speedup": warm_speedup,
            "exact_control_match": flow_exact,
            "generated_token_id": memory_flow["generated_token_id"],
        },
        "genuine_two_token_check": {
            "status": two_token["status"],
            "tokens": [x["generated_token_id"] for x in two_token["run_b"]["tokens"]],
            "token_wall_seconds": [x["wall_seconds"] for x in two_token["run_b"]["tokens"]],
            "two_pass_bitwise_repeatable": two_token["final_hidden_and_logits_bitwise_repeatable"],
            "routes_repeatable": two_token["routes_repeatable"],
        },
        "decision": "PROMOTE_INMEMORY_LAYER_FLOW_ONLY",
        "claim_boundary": (
            "The in-memory flow removes exact host-file round trips and is promoted for the "
            "resident execution path. Its 6.24x position-zero warm gain is not generated-token "
            "throughput. A genuine two-token run remained dominated by SD expert faults at "
            "about 16 seconds for the second token under a 3 GiB cache. Fused Metal and reusable "
            "graph metadata are stopped by their predeclared narrow gates."
        ),
    }
    body = json.dumps(result, sort_keys=True, separators=(",", ":"))
    result["canonical_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"decision": result["decision"],
                      "canonical_sha256": result["canonical_sha256"],
                      "warm_speedup": warm_speedup}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
