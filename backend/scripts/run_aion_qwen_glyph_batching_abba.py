#!/usr/bin/env python3
"""ABBA-test warm Qwen execution grouped by genuinely shared task prefixes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
import statistics
from typing import Any

from backend.scripts.run_aion_balanced_business_router import (
    _canonical_sha256, _p95, _post, _sha256,
)
from backend.scripts.run_aion_business_holdout import _evaluate_model_task


MODEL_FAMILIES = {"extraction", "drafting", "planning", "coding"}
PRIME_SCHEMA = {
    "type": "object",
    "properties": {"ready": {"type": "boolean"}},
    "required": ["ready"],
    "additionalProperties": False,
}


def _median_arms(arms: list[dict[str, Any]], schedule: str, field: str) -> float:
    return statistics.median(item[field] for item in arms if item["schedule"] == schedule)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--answers", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:11435")
    parser.add_argument("--model", default="qwen3:1.7b")
    parser.add_argument("--seed", type=int, default=90717)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {"tasks": args.tasks.resolve(), "answers": args.answers.resolve(),
             "bundle": args.bundle.resolve()}
    output = args.output.resolve()
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("all inputs and evidence must remain on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    task_document = json.loads(paths["tasks"].read_text())
    answer_document = json.loads(paths["answers"].read_text())
    candidates = [item for item in task_document["cases"]
                  if item["expected_disposition"] == "complete" and item["family"] in MODEL_FAMILIES]
    if len(candidates) != 16 or set(answer_document["answers"]) < {x["case_id"] for x in candidates}:
        raise RuntimeError("expected sixteen answer-bound model tasks")
    shuffled = list(candidates)
    random.Random(args.seed).shuffle(shuffled)
    grouped = sorted(shuffled, key=lambda item: item["family"])
    schedules = {"shuffled": shuffled, "glyph_family_grouped": grouped}
    bundle = paths["bundle"]
    cartridge = bundle / "supplier_payment_controls.v1.json"
    signature = bundle / "supplier_payment_controls.v1.sig.json"
    trust = bundle / "trust_anchors.v1.json"
    arm_order = ("shuffled", "glyph_family_grouped", "glyph_family_grouped", "shuffled")
    arms = []
    response_hashes: dict[str, list[str]] = {item["case_id"]: [] for item in candidates}
    for arm_index, schedule_name in enumerate(arm_order, start=1):
        unload, _ = _post(args.base_url, {"model": args.model, "keep_alive": 0})
        prime, prime_wall = _post(args.base_url, {
            "model": args.model,
            "prompt": "Return JSON with ready set to true.",
            "stream": False, "think": False, "format": PRIME_SCHEMA, "keep_alive": "10m",
            "options": {"temperature": 0, "seed": 0, "num_predict": 16},
        })
        results = []
        for call_number, task in enumerate(schedules[schedule_name], start=2):
            passed, metrics, parsed = _evaluate_model_task(
                task=task, expected=answer_document["answers"][task["case_id"]],
                model=args.model, base_url=args.base_url, call_number=call_number,
                cartridge=cartridge, signature=signature, trust=trust,
            )
            response_hash = _canonical_sha256(parsed)
            response_hashes[task["case_id"]].append(response_hash)
            results.append({"case_id": task["case_id"], "family": task["family"],
                            "passed": passed, "response_sha256": response_hash,
                            "metrics": metrics})
        wall = [item["metrics"]["wall_seconds"] for item in results]
        prompt_eval = [item["metrics"]["prompt_eval_seconds"] for item in results]
        arms.append({
            "arm": arm_index, "schedule": schedule_name,
            "unload_done": unload.get("done", False),
            "cold_prime_wall_seconds": prime_wall,
            "cold_prime_load_seconds": int(prime.get("load_duration", 0)) / 1e9,
            "all_tasks_passed": all(item["passed"] for item in results),
            "warm_total_wall_seconds": sum(wall),
            "warm_p50_wall_seconds": statistics.median(wall),
            "warm_p95_wall_seconds_nearest_rank": _p95(wall),
            "warm_total_prompt_eval_seconds": sum(prompt_eval),
            "results": results,
        })
    shuffled_total = _median_arms(arms, "shuffled", "warm_total_wall_seconds")
    grouped_total = _median_arms(arms, "glyph_family_grouped", "warm_total_wall_seconds")
    shuffled_prompt = _median_arms(arms, "shuffled", "warm_total_prompt_eval_seconds")
    grouped_prompt = _median_arms(arms, "glyph_family_grouped", "warm_total_prompt_eval_seconds")
    improvement = 100 * (1 - grouped_total / shuffled_total)
    prompt_improvement = 100 * (1 - grouped_prompt / shuffled_prompt) if shuffled_prompt else 0.0
    acceptance = {
        "all_64_task_executions_passed": all(item["all_tasks_passed"] for item in arms),
        "all_case_outputs_identical_across_arms": all(
            len(set(hashes)) == 1 and len(hashes) == 4 for hashes in response_hashes.values()
        ),
        "every_arm_explicitly_cold_primed_then_measured_warm": all(
            item["unload_done"] and item["cold_prime_load_seconds"] > 0 for item in arms
        ),
        "grouped_warm_total_improved_at_least_3_percent": improvement >= 3.0,
    }
    decision = "PROMOTED" if all(acceptance.values()) else "NOT_PROMOTED"
    report = {
        "schema_version": "aion.qwen_glyph_batching_abba.v1",
        "paths": {key: str(value) for key, value in paths.items()},
        "hashes": {"tasks": _sha256(paths["tasks"]), "answers": _sha256(paths["answers"]),
                   "cartridge": _sha256(cartridge), "signature": _sha256(signature),
                   "trust_anchors": _sha256(trust)},
        "model": args.model, "seed": args.seed, "arm_order": list(arm_order),
        "method": {"tasks_per_arm": 16, "families": sorted(MODEL_FAMILIES),
                   "explicit_unload_and_neutral_cold_prime_per_arm": True,
                   "measured_calls_are_all_model_warm": True,
                   "grouping_key": "post-route bounded executor family with identical schema/prompt prefix",
                   "promotion_threshold_percent": 3.0},
        "arms": arms,
        "aggregate": {
            "shuffled_median_warm_total_seconds": shuffled_total,
            "grouped_median_warm_total_seconds": grouped_total,
            "grouped_warm_total_improvement_percent": improvement,
            "shuffled_median_prompt_eval_seconds": shuffled_prompt,
            "grouped_median_prompt_eval_seconds": grouped_prompt,
            "prompt_eval_improvement_percent": prompt_improvement,
        },
        "acceptance": acceptance, "decision": decision,
        "claim_boundary": (
            "Warm Qwen ABBA mechanism test over sixteen frozen synthetic tasks. Grouping uses only "
            "genuinely shared bounded-executor prefixes. This does not measure Granite, SD expert I/O, "
            "concurrent queue latency, natural customer arrivals or Qwen step-logit equivalence."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), "decision": decision,
                      "aggregate": report["aggregate"], "acceptance": acceptance,
                      "report_sha256": report["report_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
