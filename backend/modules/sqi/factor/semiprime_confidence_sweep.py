from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, List, Tuple

from backend.modules.sqi.factor.semiprime_generalization_lab import (
    GENERALIZATION_DIR,
    parse_pairs,
    run_generalization_lab,
)


SWEEP_DIR = GENERALIZATION_DIR / "confidence_sweep"
SWEEP_DIR.mkdir(parents=True, exist_ok=True)


def safe_mean(values: List[float]) -> float | None:
    return round(mean(values), 6) if values else None


def safe_median(values: List[float]) -> float | None:
    return round(median(values), 6) if values else None


def run_confidence_sweep(
    *,
    start_seed: int = 20260508,
    runs: int = 5,
    train_per_tier: int = 2,
    eval_per_tier: int = 3,
    spread_pairs: List[Tuple[int, int]] = [(32, 56), (36, 60)],
    seed_count: int = 128,
    max_steps: int = 100_000,
) -> Dict[str, Any]:
    run_rows: List[Dict[str, Any]] = []

    for i in range(runs):
        seed = start_seed + i

        payload = run_generalization_lab(
            seed=seed,
            train_per_tier=train_per_tier,
            eval_per_tier=eval_per_tier,
            spread_pairs=spread_pairs,
            seed_count=seed_count,
            max_steps=max_steps,
        )

        summary = payload["summary"]
        eval_rows = payload["evaluation"]

        failures = [
            {
                "case": row["case"]["case_id"],
                "bits": f'{row["case"]["p_bits"]}x{row["case"]["q_bits"]}',
                "n": row["case"]["n"],
                "method": row["sqi"]["method"],
                "sqi_ms": row["sqi"]["elapsed_ms"],
            }
            for row in eval_rows
            if not row["sqi"]["verified"]
        ]

        run_rows.append({
            "run_index": i,
            "seed": seed,
            "summary": summary,
            "failures": failures,
            "winner_counts": summary["winner_counts"],
            "eval_cases": [
                {
                    "case": row["case"]["case_id"],
                    "bits": f'{row["case"]["p_bits"]}x{row["case"]["q_bits"]}',
                    "sqi_verified": row["sqi"]["verified"],
                    "sqi_ms": row["sqi"]["elapsed_ms"],
                    "method": row["sqi"]["method"],
                    "winner": row["winner"],
                    "winner_ms": row["winner_ms"],
                }
                for row in eval_rows
            ],
        })

    total_cases = sum(row["summary"]["total_eval_cases"] for row in run_rows)
    total_solved = sum(row["summary"]["sqi_solved"] for row in run_rows)
    total_wins = sum(row["summary"]["sqi_wins"] for row in run_rows)
    total_failures = total_cases - total_solved

    solved_rates = [row["summary"]["sqi_solved_rate"] for row in run_rows]
    win_rates = [row["summary"]["sqi_win_rate"] for row in run_rows]
    avg_times = [
        row["summary"]["avg_sqi_ms_solved"]
        for row in run_rows
        if row["summary"]["avg_sqi_ms_solved"] is not None
    ]

    winner_counts: Dict[str, int] = {}
    method_counts: Dict[str, int] = {}

    for row in run_rows:
        for winner, count in row["summary"]["winner_counts"].items():
            winner_counts[winner] = winner_counts.get(winner, 0) + count

        for case in row["eval_cases"]:
            method = case["method"]
            method_counts[method] = method_counts.get(method, 0) + 1

    aggregate = {
        "runs": runs,
        "total_cases": total_cases,
        "total_solved": total_solved,
        "total_failures": total_failures,
        "total_sqi_wins": total_wins,
        "overall_solved_rate": round(total_solved / total_cases, 6) if total_cases else 0,
        "overall_sqi_win_rate": round(total_wins / total_cases, 6) if total_cases else 0,
        "mean_run_solved_rate": safe_mean(solved_rates),
        "median_run_solved_rate": safe_median(solved_rates),
        "mean_run_win_rate": safe_mean(win_rates),
        "median_run_win_rate": safe_median(win_rates),
        "mean_avg_sqi_ms_solved": safe_mean(avg_times),
        "median_avg_sqi_ms_solved": safe_median(avg_times),
        "winner_counts": winner_counts,
        "method_counts": method_counts,
    }

    payload = {
        "config": {
            "start_seed": start_seed,
            "runs": runs,
            "train_per_tier": train_per_tier,
            "eval_per_tier": eval_per_tier,
            "spread_pairs": spread_pairs,
            "seed_count": seed_count,
            "max_steps": max_steps,
        },
        "aggregate": aggregate,
        "runs_detail": run_rows,
    }

    out_path = SWEEP_DIR / "semiprime_confidence_sweep_report.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    summary_path = SWEEP_DIR / "semiprime_confidence_sweep_summary.json"
    summary_path.write_text(json.dumps(aggregate, indent=2, sort_keys=True), encoding="utf-8")

    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="SQI semiprime generalization confidence sweep")
    parser.add_argument("--start-seed", type=int, default=20260508)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--train-per-tier", type=int, default=2)
    parser.add_argument("--eval-per-tier", type=int, default=3)
    parser.add_argument("--spread-pairs", type=str, default="32x56,36x60")
    parser.add_argument("--seed-count", type=int, default=128)
    parser.add_argument("--max-steps", type=int, default=100000)
    parser.add_argument("--json", action="store_true")

    args = parser.parse_args()

    payload = run_confidence_sweep(
        start_seed=args.start_seed,
        runs=args.runs,
        train_per_tier=args.train_per_tier,
        eval_per_tier=args.eval_per_tier,
        spread_pairs=parse_pairs(args.spread_pairs),
        seed_count=args.seed_count,
        max_steps=args.max_steps,
    )

    if args.json:
        print(json.dumps(payload["aggregate"], indent=2, sort_keys=True))
    else:
        print("=== SQI Semiprime Confidence Sweep ===")
        print(json.dumps(payload["aggregate"], indent=2, sort_keys=True))
        print("wrote benchmarks/sqi_semiprime_lab/generalization/confidence_sweep/semiprime_confidence_sweep_report.json")
        print("wrote benchmarks/sqi_semiprime_lab/generalization/confidence_sweep/semiprime_confidence_sweep_summary.json")


if __name__ == "__main__":
    main()
