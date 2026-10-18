from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any, Dict, List, Tuple

from backend.modules.sqi.factor.semiprime_lab import (
    OUT_DIR,
    SemiprimeCase,
    build_cases,
    make_proof_certificate,
    run_case,
)
from backend.modules.sqi.factor.seed_wave_profiler import profile_seed_wave
from backend.modules.sqi.factor.sqi_prime_factorizer import (
    adaptive_seed_wave_ladder,
    brent_only_factor,
    exact_factor,
    fermat_only_factor,
    pollard_only_factor,
)


GENERALIZATION_DIR = OUT_DIR / "generalization"
GENERALIZATION_DIR.mkdir(parents=True, exist_ok=True)


def timed_factor(fn, n: int) -> Dict[str, Any]:
    start = perf_counter()
    factor, checks = fn(n)
    elapsed_ms = (perf_counter() - start) * 1000
    return {
        "factor": factor,
        "cofactor": n // factor if exact_factor(n, factor) else None,
        "checks": checks,
        "elapsed_ms": round(elapsed_ms, 6),
        "verified": exact_factor(n, factor),
    }


def train_seed_priors(
    train_cases: List[SemiprimeCase],
    *,
    seed_count: int,
    max_steps: int,
) -> Dict[str, Any]:
    """
    Profile training cases and extract reusable seed/c priors.
    """
    candidate_scores: Dict[Tuple[int, int], Dict[str, Any]] = {}

    for case in train_cases:
        if case.relation != "spread":
            continue

        profile = profile_seed_wave(
            case.n,
            seed_count=seed_count,
            max_steps_per_seed=max_steps,
            rng_seed=case.n % 1_000_000,
            method="brent",
        )

        for row in profile["best"][:20]:
            key = (int(row["seed"]), int(row["c"]))
            bucket = candidate_scores.setdefault(
                key,
                {
                    "seed": key[0],
                    "c": key[1],
                    "wins": 0,
                    "total_checks": 0,
                    "total_ms": 0.0,
                    "cases": [],
                },
            )
            bucket["wins"] += 1
            bucket["total_checks"] += int(row["checks"])
            bucket["total_ms"] += float(row["elapsed_ms"])
            bucket["cases"].append(case.case_id)

    priors = []
    for item in candidate_scores.values():
        wins = item["wins"]
        priors.append({
            "seed": item["seed"],
            "c": item["c"],
            "wins": wins,
            "avg_checks": item["total_checks"] / wins,
            "avg_ms": item["total_ms"] / wins,
            "cases": item["cases"],
        })

    priors = sorted(priors, key=lambda x: (-x["wins"], x["avg_ms"], x["avg_checks"]))

    return {
        "seed_count": seed_count,
        "max_steps": max_steps,
        "training_cases": [asdict(c) for c in train_cases],
        "priors": priors,
        "learned_seed_pairs": [(p["seed"], p["c"]) for p in priors[:32]],
    }


def evaluate_case(
    case: SemiprimeCase,
    learned_seed_pairs: List[Tuple[int, int]],
    *,
    max_steps: int,
) -> Dict[str, Any]:
    n = case.n

    # SQI adaptive learned seed-wave ladder.
    start = perf_counter()
    factor, checks, trace, method_name = adaptive_seed_wave_ladder(
        n,
        learned_seed_priors=learned_seed_pairs,
        rng_seed=n % 1_000_000,
    )
    sqi_ms = (perf_counter() - start) * 1000

    sqi = {
        "factor": factor,
        "cofactor": n // factor if exact_factor(n, factor) else None,
        "checks": checks,
        "elapsed_ms": round(sqi_ms, 6),
        "verified": exact_factor(n, factor),
        "method": method_name,
        "trace_tail": trace[-8:],
    }

    baselines = {
        "fermat_only": timed_factor(fermat_only_factor, n),
        "brent_only": timed_factor(brent_only_factor, n),
        "pollard_only": timed_factor(pollard_only_factor, n),
    }

    candidates = []
    if sqi["verified"]:
        candidates.append(("sqi_learned", sqi["elapsed_ms"]))

    for name, row in baselines.items():
        if row["verified"]:
            candidates.append((name, row["elapsed_ms"]))

    winner = min(candidates, key=lambda x: x[1]) if candidates else ("none", float("inf"))

    proof = make_proof_certificate(n, sqi["factor"], sqi["cofactor"])

    return {
        "case": asdict(case),
        "sqi": sqi,
        "baselines": baselines,
        "proof": asdict(proof),
        "winner": winner[0],
        "winner_ms": winner[1],
    }


def summarize_eval(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(rows)
    sqi_solved = [r for r in rows if r["sqi"]["verified"]]
    sqi_wins = [r for r in rows if r["winner"] == "sqi_learned"]

    baseline_win_counts: Dict[str, int] = {}
    for r in rows:
        baseline_win_counts[r["winner"]] = baseline_win_counts.get(r["winner"], 0) + 1

    sqi_times = [r["sqi"]["elapsed_ms"] for r in sqi_solved]

    return {
        "total_eval_cases": total,
        "sqi_solved": len(sqi_solved),
        "sqi_solved_rate": round(len(sqi_solved) / total, 4) if total else 0,
        "sqi_wins": len(sqi_wins),
        "sqi_win_rate": round(len(sqi_wins) / total, 4) if total else 0,
        "winner_counts": baseline_win_counts,
        "avg_sqi_ms_solved": round(mean(sqi_times), 6) if sqi_times else None,
    }


def run_generalization_lab(
    *,
    seed: int = 20260508,
    train_per_tier: int = 2,
    eval_per_tier: int = 4,
    spread_pairs: List[Tuple[int, int]] = [(32, 56), (36, 60)],
    seed_count: int = 128,
    max_steps: int = 100_000,
) -> Dict[str, Any]:
    train_cases = build_cases(
        seed=seed,
        close_bits=[],
        spread_pairs=spread_pairs,
        per_tier=train_per_tier,
    )

    eval_cases = build_cases(
        seed=seed + 999,
        close_bits=[],
        spread_pairs=spread_pairs,
        per_tier=eval_per_tier,
    )

    training = train_seed_priors(
        train_cases,
        seed_count=seed_count,
        max_steps=max_steps,
    )

    learned_seed_pairs = training["learned_seed_pairs"]

    eval_rows = [
        evaluate_case(case, learned_seed_pairs, max_steps=max_steps)
        for case in eval_cases
    ]

    summary = summarize_eval(eval_rows)

    payload = {
        "seed": seed,
        "spread_pairs": spread_pairs,
        "train_per_tier": train_per_tier,
        "eval_per_tier": eval_per_tier,
        "training": training,
        "summary": summary,
        "evaluation": eval_rows,
    }

    out_path = GENERALIZATION_DIR / "semiprime_generalization_report.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    summary_path = GENERALIZATION_DIR / "semiprime_generalization_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    return payload


def parse_pairs(raw: str) -> List[Tuple[int, int]]:
    pairs = []
    for chunk in raw.split(","):
        if not chunk.strip():
            continue
        left, right = chunk.split("x")
        pairs.append((int(left), int(right)))
    return pairs


def main() -> None:
    parser = argparse.ArgumentParser(description="SQI semiprime seed-wave generalization lab")
    parser.add_argument("--seed", type=int, default=20260508)
    parser.add_argument("--train-per-tier", type=int, default=2)
    parser.add_argument("--eval-per-tier", type=int, default=4)
    parser.add_argument("--spread-pairs", type=str, default="32x56,36x60")
    parser.add_argument("--seed-count", type=int, default=128)
    parser.add_argument("--max-steps", type=int, default=100000)
    parser.add_argument("--json", action="store_true")

    args = parser.parse_args()

    payload = run_generalization_lab(
        seed=args.seed,
        train_per_tier=args.train_per_tier,
        eval_per_tier=args.eval_per_tier,
        spread_pairs=parse_pairs(args.spread_pairs),
        seed_count=args.seed_count,
        max_steps=args.max_steps,
    )

    if args.json:
        print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    else:
        print("=== SQI Semiprime Generalization Summary ===")
        print(json.dumps(payload["summary"], indent=2, sort_keys=True))
        print("wrote benchmarks/sqi_semiprime_lab/generalization/semiprime_generalization_report.json")
        print("wrote benchmarks/sqi_semiprime_lab/generalization/semiprime_generalization_summary.json")


if __name__ == "__main__":
    main()
