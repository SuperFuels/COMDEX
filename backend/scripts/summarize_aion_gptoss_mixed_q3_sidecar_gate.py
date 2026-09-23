#!/usr/bin/env python3
"""Summarize a balanced mixed-Q3 sidecar runtime gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path


def canonical(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode()).hexdigest()


def continuation(run: dict, prompt: int) -> dict:
    tokens = run["tokens"][prompt:]
    elapsed = sum(token["wall_seconds"] for token in tokens)
    sidecar = run.get("mixed_q3_sidecar_metric_delta") or {}
    l2 = run["store_metric_delta"]
    return {
        "label": run["label"], "tokens_per_second": len(tokens) / elapsed,
        "token_ids": [token["generated_token_id"] for token in tokens],
        "p50_token_latency_seconds": statistics.median(
            token["wall_seconds"] for token in tokens),
        "l2_bytes": int(l2.get("l2_bytes_read", 0)),
        "sidecar_bytes": int(sidecar.get("bytes_read", 0)),
        "total_delivery_bytes": int(l2.get("l2_bytes_read", 0)
                                    + sidecar.get("bytes_read", 0)),
        "sd_fallbacks": int(l2.get("sd_fallbacks", 0)),
        "sidecar_misses": int(sidecar.get("misses", 0)),
        "sidecar_integrity_failures": int(sidecar.get("integrity_failures", 0)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    source = json.loads(args.input.read_text())
    pattern = source.get("selective_fourth_q3_pass_pattern")
    runs = [source["run_a"], source["run_b"], *source.get("additional_runs", [])]
    if not pattern or len(pattern) != len(runs):
        raise SystemExit("source has no complete mixed-Q3 pass pattern")
    rows = [continuation(run, int(source["prompt_token_count"])) for run in runs]
    first_candidate = pattern.index("1")
    measured_candidates = [row for index, row in enumerate(rows)
                           if pattern[index] == "1" and index != first_candidate]
    measured_controls = [row for index, row in enumerate(rows)
                         if pattern[index] == "0" and index > first_candidate]
    if not measured_candidates or not measured_controls:
        raise SystemExit("pattern lacks settled candidates or controls")
    candidate_rate = statistics.median(row["tokens_per_second"]
                                       for row in measured_candidates)
    control_rate = statistics.median(row["tokens_per_second"]
                                     for row in measured_controls)
    candidate_bytes = statistics.median(row["total_delivery_bytes"]
                                        for row in measured_candidates)
    control_bytes = statistics.median(row["total_delivery_bytes"]
                                      for row in measured_controls)
    same_tokens = all(row["token_ids"] == rows[0]["token_ids"] for row in rows)
    integrity = all(row["sidecar_misses"] == 0 and
                    row["sidecar_integrity_failures"] == 0
                    for row in measured_candidates)
    traffic_reduction = 1.0 - candidate_bytes / control_bytes
    acceptance = {
        "all_passes_same_continuation_tokens": same_tokens,
        "zero_measured_sidecar_misses_or_integrity_failures": integrity,
        "minimum_ten_percent_delivery_reduction": traffic_reduction >= .10,
        "candidate_faster_than_control": candidate_rate > control_rate,
    }
    report = {
        "schema": "aion.gptoss-120b-mixed-q3-sidecar-runtime-summary.v1",
        "status": "PROMOTE_MIXED_Q3_SIDECAR" if all(acceptance.values())
                  else "STOP_MIXED_Q3_SIDECAR",
        "source": str(args.input.resolve()),
        "source_file_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
        "source_canonical_sha256": source["canonical_sha256"],
        "pass_pattern": pattern, "first_candidate_is_warmup": True,
        "runs": rows, "candidate_median_tokens_per_second": candidate_rate,
        "control_median_tokens_per_second": control_rate,
        "speedup": candidate_rate / control_rate,
        "candidate_median_delivery_bytes": candidate_bytes,
        "control_median_delivery_bytes": control_bytes,
        "delivery_traffic_reduction": traffic_reduction,
        "one_time_conversion_seconds": source["selective_fourth_q3_conversion_seconds"],
        "retained_converted_projection_count": source["selective_fourth_q3_cached_projections"],
        "acceptance": acceptance,
        "claim_boundary": (
            "Balanced arithmetic short-window quality-track gate. Candidate uses a verified "
            "precompiled split sidecar and exact fallback. Matching token IDs do not establish "
            "semantic parity beyond this frozen sequence. Failure supplies no speed promotion."
        ),
    }
    report["canonical_sha256"] = canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in (
        "status", "candidate_median_tokens_per_second",
        "control_median_tokens_per_second", "speedup",
        "delivery_traffic_reduction", "canonical_sha256",
    )}, indent=2))


if __name__ == "__main__":
    main()
