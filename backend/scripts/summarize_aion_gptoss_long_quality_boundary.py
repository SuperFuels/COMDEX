#!/usr/bin/env python3
"""Bind the 2026-09-11 GPT-OSS 120B long-form quality boundary evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _token_ids(report: dict, run: str) -> list[int]:
    prompt_tokens = len(report["input_token_ids"])
    return [
        int(token["generated_token_id"])
        for token in report[run]["tokens"][prompt_tokens:]
    ]


def _first_divergence(reference: list[int], candidate: list[int]) -> int | None:
    for index, (expected, actual) in enumerate(zip(reference, candidate)):
        if expected != actual:
            return index
    if len(reference) != len(candidate):
        return min(len(reference), len(candidate))
    return None


def _run_metrics(report: dict, run: str) -> dict:
    prompt_tokens = len(report["input_token_ids"])
    continuation = report[run]["tokens"][prompt_tokens:]
    latencies = [float(token["wall_seconds"]) for token in continuation]
    settled = latencies[1:]
    store = report[run].get("store_metric_delta", {})
    active_counts: dict[str, int] = {}
    for token in continuation:
        for layer in token["layers"]:
            count = str(len(layer["route"]))
            active_counts[count] = active_counts.get(count, 0) + 1
    return {
        "continuation_tokens": len(continuation),
        "continuation_tokens_per_second": len(latencies) / sum(latencies),
        "settled_tokens_per_second": len(settled) / sum(settled),
        "p50_token_latency_seconds": statistics.median(latencies),
        "p95_token_latency_seconds": sorted(latencies)[
            max(0, min(len(latencies) - 1, int(0.95 * len(latencies)) - 1))
        ],
        "active_expert_layer_calls": active_counts,
        "raw_bytes_materialized": store.get("raw_bytes_materialized"),
        "l2_bytes_read": store.get("l2_bytes_read"),
        "compressed_bytes_read": store.get("compressed_bytes_read"),
        "sd_fallbacks": store.get("sd_fallbacks"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--teacher", type=Path, required=True)
    parser.add_argument(
        "--candidate", action="append", default=[], metavar="LABEL=PATH",
        help="Candidate label and report path; may be repeated.",
    )
    parser.add_argument("--metal-gate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")

    teacher = json.loads(args.teacher.read_text())
    teacher_tokens = _token_ids(teacher, "run_a")
    candidates: dict[str, dict] = {}
    for item in args.candidate:
        if "=" not in item:
            raise SystemExit(f"candidate must be LABEL=PATH: {item}")
        label, raw_path = item.split("=", 1)
        path = Path(raw_path)
        report = json.loads(path.read_text())
        run_a_tokens = _token_ids(report, "run_a")
        run_b_tokens = _token_ids(report, "run_b")
        candidates[label] = {
            "path": str(path.resolve()),
            "file_sha256": _sha256(path),
            "canonical_sha256": report["canonical_sha256"],
            "internal_token_repeatability": run_a_tokens == run_b_tokens,
            "exact_teacher_prefix_tokens": (
                _first_divergence(teacher_tokens, run_a_tokens)
                if _first_divergence(teacher_tokens, run_a_tokens) is not None
                else len(teacher_tokens)
            ),
            "run_a": _run_metrics(report, "run_a"),
            "run_b": _run_metrics(report, "run_b"),
        }

    metal = json.loads(args.metal_gate.read_text())
    report = {
        "schema": "aion.gptoss-120b-long-quality-boundary.v1",
        "status": "BOUNDARY_VERIFIED_NO_QUALITY_TRACK_PROMOTION",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "teacher": {
            "path": str(args.teacher.resolve()),
            "file_sha256": _sha256(args.teacher),
            "canonical_sha256": teacher["canonical_sha256"],
            "routes_repeatable": teacher["routes_repeatable"],
            "final_hidden_and_logits_bitwise_repeatable": teacher[
                "final_hidden_and_logits_bitwise_repeatable"
            ],
            "run_a": _run_metrics(teacher, "run_a"),
            "run_b": _run_metrics(teacher, "run_b"),
            "quality_assessment": (
                "AUTHORITATIVE_CORRECT_AND_COHERENT: identifies invoice A-104, "
                "EUR 287.50, and begins the requested JSON output."
            ),
        },
        "candidates": candidates,
        "candidate_quality_assessment": (
            "NOT_PROMOTED: every 96-position reduced-expert candidate became "
            "repetitive, incomplete, or factually incorrect. The adaptive-0.75 "
            "control itself first diverged after a 23-token exact continuation prefix."
        ),
        "split_mxfp4_metal_gate": {
            "path": str(args.metal_gate.resolve()),
            "file_sha256": _sha256(args.metal_gate),
            "canonical_sha256": metal["canonical_sha256"],
            "status": metal["status"],
            "metal_speedup": metal["metal_speedup"],
            "relative_l2_error": metal["relative_l2_error"],
        },
        "claim_boundary": (
            "The exact unrestricted teacher is the only quality authority in this "
            "report. Reduced-expert rates are physical or quality-track observations, "
            "not an exact or generally usable GPT-OSS 120B performance claim. Manual "
            "quality labels are bound here to immutable source reports and token arrays."
        ),
    }
    report["canonical_sha256"] = hashlib.sha256(json.dumps(
        report, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": report["status"],
        "canonical_sha256": report["canonical_sha256"],
        "candidate_count": len(candidates),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
