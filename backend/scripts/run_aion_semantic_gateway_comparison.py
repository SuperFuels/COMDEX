"""Compare the first guarded AtomSheet route with a Phase 0 model baseline."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import time

from backend.modules.aion_inference import SemanticGateway, load_workloads


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--case", default="business-profit-001")
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be positive")

    workload = next((case for case in load_workloads() if case.case_id == args.case), None)
    if workload is None:
        parser.error(f"unknown workload case: {args.case}")
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    baseline_result = next(
        (item for item in baseline["results"] if item["case_id"] == args.case), None
    )
    if baseline_result is None:
        parser.error(f"case is absent from baseline: {args.case}")

    gateway = SemanticGateway()
    durations: list[float] = []
    result = None
    for _ in range(args.iterations):
        started = time.perf_counter()
        result = gateway.route(workload.prompt)
        durations.append(time.perf_counter() - started)
    assert result is not None
    if result.route != "verified_atomsheet" or result.model_call_required:
        raise SystemExit("comparison refused: workload did not pass the guarded AtomSheet gate")

    baseline_wall = float(baseline_result["measurements"]["wall_time"]["value"])
    baseline_prompt_tokens = int(baseline_result["measurements"]["prompt_tokens"]["value"])
    baseline_output_tokens = int(baseline_result["measurements"]["output_tokens"]["value"])
    ordered = sorted(durations)
    median = statistics.median(ordered)
    p95 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))]
    payload = {
        "schema_version": "aion.semantic_gateway.comparison.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "case_id": args.case,
        "iterations": args.iterations,
        "baseline": {
            "run_id": baseline["run_id"],
            "model": baseline["model"],
            "route": "full_model",
            "model_calls": 1,
            "wall_seconds": baseline_wall,
            "prompt_tokens": baseline_prompt_tokens,
            "output_tokens": baseline_output_tokens,
            "quality_status": baseline_result["quality_status"],
        },
        "semantic_gateway": {
            "route": result.route,
            "model_calls": 0,
            "median_wall_seconds": median,
            "p95_wall_seconds": p95,
            "quality_status": "pass" if result.proof_receipt["inverse_verified"] else "fail",
            "structured_result": result.structured_result,
            "proof_receipt": result.proof_receipt,
        },
        "measured_change": {
            "model_calls_avoided": 1,
            "model_call_reduction_percent": 100.0,
            "model_prompt_tokens_avoided": baseline_prompt_tokens,
            "model_output_tokens_avoided": baseline_output_tokens,
            "median_latency_reduction_percent": (1.0 - median / baseline_wall) * 100.0,
            "baseline_and_gateway_quality_passed": (
                baseline_result["quality_status"] == "pass"
                and bool(result.proof_receipt["inverse_verified"])
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
