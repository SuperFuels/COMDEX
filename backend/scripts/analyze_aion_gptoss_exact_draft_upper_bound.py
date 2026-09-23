#!/usr/bin/env python3
"""Bound exact speculative verification before building a draft runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grouping-report", type=Path, required=True)
    parser.add_argument("--exact-core-halo-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    grouping = json.loads(args.grouping_report.read_text())
    halo = json.loads(args.exact_core_halo_report.read_text())
    rates = [halo["results"]["protected_6gib_plus_4gib_halo"]["response"][name]["tokens_per_second"]
             for name in ("run_a", "run_b")]
    best_rate = max(rates)
    remaining_fraction = 1 - grouping["perfect_grouping_byte_reduction"]
    optimistic = best_rate / remaining_fraction
    required_reduction_for_one = 1 - best_rate / 1.0
    required_reduction_for_thirty = 1 - best_rate / 30.0
    report = {
        "schema": "aion.gptoss-120b-exact-draft-upper-bound.v1",
        "status": "STOP_EXACT_DRAFT_AS_BREAKTHROUGH_PATH" if optimistic < 1 else "ADVANCE_EXACT_DRAFT",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "current_best_exact_tokens_per_second": best_rate,
        "observed_perfect_grouping_byte_reduction": grouping["perfect_grouping_byte_reduction"],
        "observed_mean_activations_per_loaded_expert": grouping["mean_activations_per_loaded_expert"],
        "observed_maximum_expert_batch": grouping["maximum_observed_expert_batch"],
        "optimistic_zero_cost_full_acceptance_tokens_per_second": optimistic,
        "required_byte_reduction_for_one_token_per_second": required_reduction_for_one,
        "required_byte_reduction_for_thirty_tokens_per_second": required_reduction_for_thirty,
        "assumptions": [
            "Every draft token is accepted.",
            "Draft generation and verification scheduling cost zero time.",
            "All repeated layer/expert routes are grouped perfectly.",
            "Wall time scales linearly with expert bytes and all non-I/O cost disappears.",
        ],
        "inputs": {
            "grouping": {"path": str(args.grouping_report.resolve()),
                         "file_sha256": hashlib.sha256(args.grouping_report.read_bytes()).hexdigest(),
                         "canonical_sha256": grouping["canonical_sha256"]},
            "core_halo": {"path": str(args.exact_core_halo_report.resolve()),
                          "file_sha256": hashlib.sha256(args.exact_core_halo_report.read_bytes()).hexdigest(),
                          "canonical_sha256": halo["canonical_sha256"]},
        },
        "claim_boundary": (
            "This intentionally optimistic bound combines measured route reuse with the best "
            "exact core/halo rate. It is not an executed speculative decoder. Real acceptance, "
            "draft cost and scheduling can only reduce the bound."
        ),
    }
    body = json.dumps(report, sort_keys=True, separators=(",", ":"))
    report["canonical_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"],
                      "optimistic_tokens_per_second": optimistic,
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
