#!/usr/bin/env python3
"""Bind long-generation, teacher-quality and semantic evidence into one decision."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _canonical_sha256(value: dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _load_verified(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    claimed = value.get("report_sha256")
    canonical = {key: item for key, item in value.items() if key != "report_sha256"}
    if claimed != _canonical_sha256(canonical):
        raise ValueError(f"canonical report hash failed: {path}")
    return value


def _repeatability(report: dict[str, Any], condition: str) -> dict[str, Any]:
    exact = 0
    families = report["prompt_families"]
    for family in families:
        runs = sorted(
            (item for item in report["runs"]
             if item["family"] == family and item["condition"] == condition),
            key=lambda item: item["sequence"],
        )
        if len(runs) != 2:
            raise ValueError(f"expected two {condition} runs for {family}")
        exact += runs[0]["token_ids"] == runs[1]["token_ids"]
    return {"exact_family_count": exact, "family_count": len(families),
            "fraction": exact / len(families)}


def _summarize_generation(report: dict[str, Any]) -> dict[str, Any]:
    candidate = _repeatability(report, "dynamic_bank")
    control = _repeatability(report, "bank_native_int8")
    return {
        "generated_tokens_per_run": report["generated_tokens_per_run"],
        "family_count": len(report["prompt_families"]),
        "total_measured_tokens": sum(len(item["token_ids"]) for item in report["runs"]),
        "candidate_median_tokens_per_second": report["candidate"]["median_tokens_per_second"],
        "control_median_tokens_per_second": report["control"]["median_tokens_per_second"],
        "median_throughput_improvement_percent":
            report["aggregate"]["median_throughput_improvement_percent"],
        "p95_generation_time_improvement_percent":
            report["aggregate"]["p95_generation_time_improvement_percent"],
        "candidate_repeatability": candidate,
        "control_repeatability": control,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--generation-128", type=Path, required=True)
    parser.add_argument("--generation-256", type=Path, required=True)
    parser.add_argument("--teacher-quality", type=Path, required=True)
    parser.add_argument("--semantic-quality", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {"generation_128": args.generation_128.resolve(),
             "generation_256": args.generation_256.resolve(),
             "teacher_quality": args.teacher_quality.resolve(),
             "semantic_quality": args.semantic_quality.resolve()}
    output = args.output.resolve()
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("all evidence and output must remain on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    reports = {name: _load_verified(path) for name, path in paths.items()}
    generation_128 = _summarize_generation(reports["generation_128"])
    generation_256 = _summarize_generation(reports["generation_256"])
    teacher = reports["teacher_quality"]
    semantic = reports["semantic_quality"]
    rate_drop = 100 * (1 - generation_256["candidate_median_tokens_per_second"] /
                       generation_128["candidate_median_tokens_per_second"])
    acceptance = {
        "128_token_rate_at_least_20_tokens_per_second":
            generation_128["candidate_median_tokens_per_second"] >= 20,
        "256_token_rate_at_least_20_tokens_per_second":
            generation_256["candidate_median_tokens_per_second"] >= 20,
        "256_rate_drop_from_128_no_more_than_10_percent": rate_drop <= 10,
        "128_candidate_repeatability_not_below_native":
            generation_128["candidate_repeatability"]["fraction"] >=
            generation_128["control_repeatability"]["fraction"],
        "256_candidate_repeatability_not_below_native":
            generation_256["candidate_repeatability"]["fraction"] >=
            generation_256["control_repeatability"]["fraction"],
        "all_extended_teacher_quality_gates_passed": all(teacher["acceptance"].values()),
        "prior_frozen_semantic_gate_promoted":
            semantic["decision"] == "PROMOTE_DYNAMIC_BANK_WITHIN_VALIDATED_BOUNDARY"
            and all(semantic["acceptance"].values()),
    }
    report = {
        "schema_version": "aion.dynamic_bank_long_generation_promotion.v1",
        "track": "quality_gated_changed_kernel_not_bit_exact",
        "paths": {name: str(path) for name, path in paths.items()},
        "hashes": {name: hashlib.sha256(path.read_bytes()).hexdigest()
                   for name, path in paths.items()},
        "generation_128": generation_128,
        "generation_256": generation_256,
        "candidate_rate_drop_128_to_256_percent": rate_drop,
        "teacher_quality": {
            "positions": teacher["forced_positions"],
            "native": teacher["native_aggregate"],
            "dynamic": teacher["dynamic_aggregate"],
            "dynamic_vs_native_teacher_time_improvement_percent":
                teacher["dynamic_vs_native_teacher_time_improvement_percent"],
        },
        "semantic_quality": {
            "decision": semantic["decision"],
            "answer_agreement_fraction": semantic["answer_agreement_fraction"],
            "native_score": semantic["native"]["passes"],
            "dynamic_score": semantic["dynamic"]["passes"],
            "case_count": len(semantic["comparisons"]),
        },
        "acceptance": acceptance,
        "decision": ("PROMOTE_DYNAMIC_BANK_LONG_GENERATION_BOUNDARY"
                     if all(acceptance.values()) else "DO_NOT_EXTEND_DYNAMIC_BANK_PROMOTION"),
        "claim_boundary": (
            "Promotion covers one Granite MoE model on the measured 18 GB M3 Pro, an SD-native "
            "2.8196 GiB resident expert bank, eight frozen families at 128 tokens, a disjoint "
            "eight-family holdout at 256 tokens, 2,048 FP16 teacher-forced positions and the "
            "prior twelve-case semantic suite. It does not establish bit-exact logits, identical "
            "free-running wording, arbitrary larger models, or continuous SD streaming at the "
            "resident-bank token rate."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), "decision": report["decision"],
                      "generation_128": generation_128,
                      "generation_256": generation_256,
                      "rate_drop_percent": rate_drop, "acceptance": acceptance,
                      "report_sha256": report["report_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
