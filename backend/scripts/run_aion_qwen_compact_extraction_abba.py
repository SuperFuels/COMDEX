#!/usr/bin/env python3
"""ABBA-test a compact Glyph-compiled Qwen extraction wire protocol."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
from typing import Any

from backend.modules.aion_inference import execute_supplier_payment_review, verify_proof_receipt
from backend.scripts.run_aion_balanced_business_router import (
    CONTROL_IDS, EXTRACTION_SCHEMA, _canonical_sha256, _normalize_extraction,
    _p95, _post, _sha256,
)
from backend.scripts.run_aion_qwen_glyph_batching_abba import PRIME_SCHEMA


COMPACT_SCHEMA = {
    "type": "object",
    "properties": {"s": {"type": "string"}, "i": {"type": "string"},
                   "a": {"type": "string"}},
    "required": ["s", "i", "a"],
    "additionalProperties": False,
}


def _median(arms: list[dict[str, Any]], protocol: str, field: str) -> float:
    return statistics.median(item[field] for item in arms if item["protocol"] == protocol)


def _cases(original: dict[str, Any], holdout_tasks: dict[str, Any],
           holdout_answers: dict[str, Any]) -> list[dict[str, Any]]:
    cases = [{"case_id": item["case_id"], "request": item["request"],
              "expected": item["expected"]} for item in original["cases"]]
    for item in holdout_tasks["cases"]:
        if item["family"] == "extraction" and item["expected_disposition"] == "complete":
            cases.append({"case_id": item["case_id"], "request": item["request"],
                          "expected": holdout_answers["answers"][item["case_id"]]})
    if len(cases) != 12 or len({item["case_id"] for item in cases}) != 12:
        raise RuntimeError("expected twelve distinct extraction cases")
    return cases


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--original-manifest", type=Path, required=True)
    parser.add_argument("--holdout-tasks", type=Path, required=True)
    parser.add_argument("--holdout-answers", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:11435")
    parser.add_argument("--model", default="qwen3:1.7b")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {"original_manifest": args.original_manifest.resolve(),
             "holdout_tasks": args.holdout_tasks.resolve(),
             "holdout_answers": args.holdout_answers.resolve(),
             "bundle": args.bundle.resolve()}
    output = args.output.resolve()
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("all inputs and evidence must remain on external storage")
    if output.exists(): raise SystemExit(f"refusing to overwrite evidence: {output}")
    cases = _cases(json.loads(paths["original_manifest"].read_text()),
                   json.loads(paths["holdout_tasks"].read_text()),
                   json.loads(paths["holdout_answers"].read_text()))
    bundle = paths["bundle"]
    cartridge = bundle / "supplier_payment_controls.v1.json"
    signature = bundle / "supplier_payment_controls.v1.sig.json"
    trust = bundle / "trust_anchors.v1.json"
    refs = {key: f"fixture:{key}" for key in CONTROL_IDS}
    arm_order = ("baseline", "compact_glyph", "compact_glyph", "baseline")
    arms, normalized_hashes = [], {item["case_id"]: [] for item in cases}
    for arm_index, protocol in enumerate(arm_order, start=1):
        unload, _ = _post(args.base_url, {"model": args.model, "keep_alive": 0})
        prime, prime_wall = _post(args.base_url, {
            "model": args.model, "prompt": "Return JSON with ready set to true.",
            "stream": False, "think": False, "format": PRIME_SCHEMA, "keep_alive": "10m",
            "options": {"temperature": 0, "seed": 0, "num_predict": 16},
        })
        results = []
        for case in cases:
            if protocol == "baseline":
                schema = EXTRACTION_SCHEMA
                prompt = (
                    "Extract the three fields exactly as written. Do not infer, calculate, or add text.\n"
                    f"REQUEST: {case['request']}"
                )
            else:
                schema = COMPACT_SCHEMA
                prompt = (
                    "Return s=supplier name, i=invoice reference, a=payment amount exactly as written.\n"
                    f"REQUEST: {case['request']}"
                )
            event, wall = _post(args.base_url, {
                "model": args.model, "prompt": prompt, "stream": False, "think": False,
                "format": schema, "keep_alive": "10m",
                "options": {"temperature": 0, "seed": 0, "num_predict": 96},
            })
            try: parsed = json.loads(event["response"])
            except json.JSONDecodeError: parsed = None
            if protocol == "compact_glyph" and isinstance(parsed, dict):
                parsed = {"supplier_name": parsed.get("s"),
                          "invoice_reference": parsed.get("i"),
                          "payment_amount": parsed.get("a")}
            parsed = _normalize_extraction(parsed)
            execution = execute_supplier_payment_review(
                actor_role="finance_reviewer", evidence_references=refs,
                variable_fields=parsed or {}, human_approved=True,
                cartridge_path=cartridge, signature_path=signature, trust_anchors_path=trust,
            ) if parsed else None
            passed = bool(parsed == case["expected"] and execution and execution.review_complete
                          and verify_proof_receipt(execution.proof_receipt)
                          and not execution.payment_execution_allowed)
            payment_execution_allowed = bool(
                execution and execution.payment_execution_allowed
            )
            normalized_hash = _canonical_sha256(parsed)
            normalized_hashes[case["case_id"]].append(normalized_hash)
            eval_seconds = int(event.get("eval_duration", 0)) / 1e9
            results.append({
                "case_id": case["case_id"], "passed": passed,
                "payment_execution_allowed": payment_execution_allowed,
                "normalized_response_sha256": normalized_hash,
                "raw_response_sha256": hashlib.sha256(event["response"].encode()).hexdigest(),
                "wall_seconds": wall,
                "prompt_eval_seconds": int(event.get("prompt_eval_duration", 0)) / 1e9,
                "generation_seconds": eval_seconds,
                "prompt_tokens": int(event.get("prompt_eval_count", 0)),
                "generated_tokens": int(event.get("eval_count", 0)),
                "generation_tokens_per_second": int(event.get("eval_count", 0)) / eval_seconds
                if eval_seconds else None,
            })
        walls = [item["wall_seconds"] for item in results]
        arms.append({"arm": arm_index, "protocol": protocol,
                     "unload_done": unload.get("done", False),
                     "cold_prime_wall_seconds": prime_wall,
                     "cold_prime_load_seconds": int(prime.get("load_duration", 0)) / 1e9,
                     "all_cases_passed": all(item["passed"] for item in results),
                     "warm_total_wall_seconds": sum(walls),
                     "warm_p50_wall_seconds": statistics.median(walls),
                     "warm_p95_wall_seconds_nearest_rank": _p95(walls),
                     "total_prompt_eval_seconds": sum(x["prompt_eval_seconds"] for x in results),
                     "total_generation_seconds": sum(x["generation_seconds"] for x in results),
                     "total_generated_tokens": sum(x["generated_tokens"] for x in results),
                     "results": results})
    baseline_wall = _median(arms, "baseline", "warm_total_wall_seconds")
    compact_wall = _median(arms, "compact_glyph", "warm_total_wall_seconds")
    baseline_tokens = _median(arms, "baseline", "total_generated_tokens")
    compact_tokens = _median(arms, "compact_glyph", "total_generated_tokens")
    wall_gain = 100 * (1 - compact_wall / baseline_wall)
    token_gain = 100 * (1 - compact_tokens / baseline_tokens)
    acceptance = {
        "all_48_extractions_and_signed_reviews_passed": all(x["all_cases_passed"] for x in arms),
        "normalized_business_map_values_identical_across_arms": all(
            len(hashes) == 4 and len(set(hashes)) == 1 for hashes in normalized_hashes.values()
        ),
        "payment_execution_never_allowed": not any(
            result["payment_execution_allowed"]
            for arm in arms for result in arm["results"]
        ),
        "every_arm_explicitly_cold_primed_then_measured_warm": all(
            x["unload_done"] and x["cold_prime_load_seconds"] > 0 for x in arms
        ),
        "compact_protocol_improved_warm_total_at_least_10_percent": wall_gain >= 10.0,
    }
    decision = "PROMOTED_QUALITY_GATED_COMPACT_PROTOCOL" if all(acceptance.values()) else "NOT_PROMOTED"
    report = {"schema_version": "aion.qwen_compact_extraction_abba.v1",
              "paths": {key: str(value) for key, value in paths.items()},
              "hashes": {"original_manifest": _sha256(paths["original_manifest"]),
                         "holdout_tasks": _sha256(paths["holdout_tasks"]),
                         "holdout_answers": _sha256(paths["holdout_answers"]),
                         "cartridge": _sha256(cartridge), "signature": _sha256(signature),
                         "trust_anchors": _sha256(trust)},
              "model": args.model, "arm_order": list(arm_order),
              "method": {"distinct_cases": 12, "executions": 48,
                         "explicit_unload_and_neutral_cold_prime_per_arm": True,
                         "measured_calls_all_model_warm": True,
                         "candidate_wire_keys": {"s": "supplier_name", "i": "invoice_reference",
                                                 "a": "payment_amount"},
                         "promotion_threshold_percent": 10.0,
                         "track": "quality_gated_semantic_output_protocol_not_exact_logits"},
              "arms": arms,
              "aggregate": {"baseline_median_warm_total_seconds": baseline_wall,
                            "compact_median_warm_total_seconds": compact_wall,
                            "compact_warm_total_improvement_percent": wall_gain,
                            "baseline_median_generated_tokens": baseline_tokens,
                            "compact_median_generated_tokens": compact_tokens,
                            "generated_token_reduction_percent": token_gain,
                            "baseline_median_generation_seconds": _median(arms, "baseline", "total_generation_seconds"),
                            "compact_median_generation_seconds": _median(arms, "compact_glyph", "total_generation_seconds")},
              "acceptance": acceptance, "decision": decision,
              "claim_boundary": (
                  "Quality-gated warm Qwen protocol test on twelve synthetic extraction cases. "
                  "The candidate changes prompt and wire representation, so it does not claim token or "
                  "step-logit equivalence. It proves identical normalized business values and signed-review outcomes only."
              )}
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), "decision": decision,
                      "aggregate": report["aggregate"], "acceptance": acceptance,
                      "report_sha256": report["report_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
