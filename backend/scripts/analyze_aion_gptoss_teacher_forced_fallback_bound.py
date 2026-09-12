#!/usr/bin/env python3
"""Measure the optimistic fallback ceiling from a teacher-forced quality trace."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--teacher", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    teacher = json.loads(args.teacher.read_text())
    candidate = json.loads(args.candidate.read_text())
    boundary = int(candidate["prompt_token_count"])
    if boundary != len(teacher["input_token_ids"]):
        raise SystemExit("teacher prompt and candidate boundary differ")
    if len(candidate["input_token_ids"]) != candidate["token_count"]:
        raise SystemExit("candidate must force the complete teacher trajectory")

    rows = []
    for position in range(boundary, candidate["token_count"]):
        exact = teacher["run_a"]["tokens"][position]
        fast = candidate["run_a"]["tokens"][position]
        rows.append({
            "position": position,
            "teacher_token_id": exact["generated_token_id"],
            "candidate_token_id": fast["generated_token_id"],
            "token_equal": exact["generated_token_id"] == fast["generated_token_id"],
            "candidate_margin": fast["output"]["margin"],
            "candidate_seconds": fast["wall_seconds"],
            "teacher_seconds": exact["wall_seconds"],
            "two_expert_layers": sum(len(layer["route"]) == 2 for layer in fast["layers"]),
            "three_expert_layers": sum(len(layer["route"]) == 3 for layer in fast["layers"]),
        })
    unsafe = [row for row in rows if not row["token_equal"]]
    safe = [row for row in rows if row["token_equal"]]
    maximum_unsafe_margin = max(row["candidate_margin"] for row in unsafe)
    margin_rejections = [
        row for row in rows if row["candidate_margin"] <= maximum_unsafe_margin
    ]
    candidate_seconds = sum(row["candidate_seconds"] for row in rows)
    exact_seconds = sum(row["teacher_seconds"] for row in rows)
    unsafe_exact_seconds = sum(row["teacher_seconds"] for row in unsafe)
    safe_candidate_seconds = sum(row["candidate_seconds"] for row in safe)
    cost_aware_safe_seconds = sum(
        min(row["candidate_seconds"], row["teacher_seconds"]) for row in safe
    )
    threshold_exact_seconds = sum(row["teacher_seconds"] for row in margin_rejections)
    report = {
        "schema": "aion.gptoss-120b-teacher-forced-fallback-bound.v2",
        "status": "STOP_CONFIDENCE_FALLBACK_AS_NORTH_STAR_PATH",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "teacher": {
            "path": str(args.teacher.resolve()),
            "file_sha256": digest(args.teacher),
            "canonical_sha256": teacher["canonical_sha256"],
        },
        "candidate": {
            "path": str(args.candidate.resolve()),
            "file_sha256": digest(args.candidate),
            "canonical_sha256": candidate["canonical_sha256"],
            "policy": {
                "continuation_gate_mass_threshold": candidate.get(
                    "continuation_gate_mass_threshold"
                ),
                "continuation_min_active_experts": candidate.get(
                    "continuation_min_active_experts"
                ),
                "continuation_top1_threshold_plan_path": candidate.get(
                    "continuation_top1_threshold_plan_path"
                ),
                "preserve_top1_gate_mass": candidate.get(
                    "preserve_top1_gate_mass"
                ),
            },
            "internally_repeatable": candidate[
                "final_hidden_and_logits_bitwise_repeatable"
            ],
        },
        "positions": len(rows),
        "matching_positions": len(safe),
        "unsafe_positions": len(unsafe),
        "token_agreement_fraction": len(safe) / len(rows),
        "unsafe_position_indices": [row["position"] for row in unsafe],
        "measured_tokens_per_second": {
            "unrestricted_exact": len(rows) / exact_seconds,
            "teacher_forced_candidate": len(rows) / candidate_seconds,
            "perfect_preclassifier_upper_bound": len(rows) / (
                safe_candidate_seconds + unsafe_exact_seconds
            ),
            "perfect_quality_and_cost_oracle_upper_bound": len(rows) / (
                cost_aware_safe_seconds + unsafe_exact_seconds
            ),
            "perfect_postcandidate_verifier_upper_bound": len(rows) / (
                candidate_seconds + unsafe_exact_seconds
            ),
            "all_unsafe_recall_margin_rule_upper_bound": len(rows) / (
                candidate_seconds + threshold_exact_seconds
            ),
        },
        "margin_rule": {
            "reject_at_or_below": maximum_unsafe_margin,
            "rejected_positions": len(margin_rejections),
            "rejected_fraction": len(margin_rejections) / len(rows),
            "unsafe_recall": 1.0,
            "safe_positions_rejected": sum(row["token_equal"] for row in margin_rejections),
        },
        "rows": rows,
        "claim_boundary": (
            "The candidate was evaluated on the exact teacher token history, so each "
            "position is an independent next-token counterfactual and earlier candidate "
            "errors cannot contaminate later labels. The perfect classifier rates are "
            "optimistic upper bounds derived from measured per-position times; they do "
            "not implement a deployable oracle or constitute generated-quality evidence."
        ),
    }
    report["canonical_sha256"] = hashlib.sha256(json.dumps(
        report, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": report["status"],
        "token_agreement_fraction": report["token_agreement_fraction"],
        "perfect_preclassifier_upper_bound": report[
            "measured_tokens_per_second"
        ]["perfect_preclassifier_upper_bound"],
        "canonical_sha256": report["canonical_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
