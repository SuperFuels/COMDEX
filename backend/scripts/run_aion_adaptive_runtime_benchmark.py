"""Exercise verified routes, replay, fallback context, and persistent receipts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import time
import uuid

from backend.modules.aion_inference import AdaptiveInferenceRuntime


CASES = (
    ("profit", "Profit with revenue EUR 4000, materials EUR 1700 and labour EUR 900?"),
    ("percentage", "What is 15% of 240?"),
    ("area_metric", "Calculate the area of 5 m by 4 m."),
    ("area_mixed_units", "Calculate the area of 10 ft by 3 metres."),
    ("volume", "Calculate volume of 5 m by 4 m by 2.5 m."),
    ("conversion", "Convert 2.5 metres to centimetres."),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be positive")

    run_key = uuid.uuid4().hex
    evidence_root = args.storage_root / "runtime-evidence"
    runtime = AdaptiveInferenceRuntime(
        replay_path=evidence_root / f"replay-{run_key}.sqlite3",
        trace_path=evidence_root / f"trace-{run_key}.jsonl",
    )
    case_results = []
    for case_id, prompt in CASES:
        started = time.perf_counter()
        first = runtime.route(prompt)
        first_seconds = time.perf_counter() - started
        replay_durations = []
        replay = None
        for _ in range(args.iterations):
            started = time.perf_counter()
            replay = runtime.route(prompt)
            replay_durations.append(time.perf_counter() - started)
        assert replay is not None
        case_results.append({
            "case_id": case_id,
            "first_route": first.route,
            "replay_route": replay.route,
            "model_call_required": replay.model_call_required,
            "answer": replay.answer,
            "structured_result": replay.structured_result,
            "first_seconds": first_seconds,
            "replay_median_seconds": statistics.median(replay_durations),
            "replay_p95_seconds": sorted(replay_durations)[min(len(replay_durations) - 1, int(len(replay_durations) * 0.95))],
            "proof_receipt": replay.proof_receipt,
        })

    fallback = runtime.route(
        "Draft a customer update. Do not book or take payment; human review is required.",
        context=[
            "Customer asked for a patio quotation and supplied dimensions.",
            "Policy: every quotation must receive human approval.",
            "Do not take payment without a second confirmation.",
            "Warehouse shelf B contains blue paint.",
            "The unrelated office printer was serviced yesterday.",
        ],
        context_max_bytes=170,
    )
    payload = {
        "schema_version": "aion.adaptive_runtime.benchmark.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "iterations_per_replay_case": args.iterations,
        "verified_cases": case_results,
        "summary": {
            "verified_case_count": len(case_results),
            "verified_case_pass_count": sum(item["first_route"] == "verified_atomsheet" for item in case_results),
            "replay_pass_count": sum(item["replay_route"] == "verified_replay" for item in case_results),
            "model_calls_for_verified_cases": sum(bool(item["model_call_required"]) for item in case_results),
            "median_first_route_seconds": statistics.median(item["first_seconds"] for item in case_results),
            "median_replay_seconds": statistics.median(item["replay_median_seconds"] for item in case_results),
        },
        "fallback": {
            "route": fallback.route,
            "model_call_required": fallback.model_call_required,
            "constraints": fallback.proof_receipt,
            "context_selection": fallback.context_selection.__dict__ if fallback.context_selection else None,
            "fallback_prompt": fallback.fallback_prompt,
        },
        "evidence": {
            "replay_store": str(runtime.replay.path),
            "trace_log": str(runtime.trace_path),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
