from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, median
from time import perf_counter
from typing import Any, Dict, List, Optional, Tuple

from backend.modules.sqi.factor.semiprime_generalization_lab import run_generalization_lab


DEFAULT_OUT_DIR = Path("benchmarks/sqi_semiprime_lab/bit_size_ablation")


def parse_spread_pairs(raw: str) -> List[str]:
    pairs = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if "x" not in item:
            raise ValueError(f"invalid spread pair: {item!r}; expected e.g. 40x64")
        left, right = item.split("x", 1)
        int(left)
        int(right)
        pairs.append(f"{left}x{right}")
    if not pairs:
        raise ValueError("at least one spread pair is required")
    return pairs


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def summarize_tier(report: Dict[str, Any]) -> Dict[str, Any]:
    summary = report.get("summary", {})
    evaluation = report.get("evaluation", [])

    solved_times = []
    winners: Dict[str, int] = {}
    method_counts: Dict[str, int] = {}
    failures = []

    for row in evaluation:
        sqi = row.get("sqi", {})
        winner = row.get("winner", "unknown")
        winners[winner] = winners.get(winner, 0) + 1

        method = sqi.get("method", "unknown")
        method_counts[method] = method_counts.get(method, 0) + 1

        if sqi.get("verified"):
            t = _safe_float(sqi.get("elapsed_ms"))
            if t is not None:
                solved_times.append(t)
        else:
            failures.append({
                "case": row.get("case", {}).get("case_id"),
                "bits": f'{row.get("case", {}).get("p_bits")}x{row.get("case", {}).get("q_bits")}',
                "method": method,
                "winner": winner,
            })

    return {
        "total_eval_cases": int(summary.get("total_eval_cases", len(evaluation))),
        "sqi_solved": int(summary.get("sqi_solved", 0)),
        "sqi_solved_rate": summary.get("sqi_solved_rate", 0),
        "sqi_wins": int(summary.get("sqi_wins", 0)),
        "sqi_win_rate": summary.get("sqi_win_rate", 0),
        "avg_sqi_ms_solved": summary.get("avg_sqi_ms_solved"),
        "median_sqi_ms_solved": round(median(solved_times), 6) if solved_times else None,
        "min_sqi_ms_solved": round(min(solved_times), 6) if solved_times else None,
        "max_sqi_ms_solved": round(max(solved_times), 6) if solved_times else None,
        "winner_counts": winners,
        "method_counts": method_counts,
        "failure_count": len(failures),
        "failures": failures,
    }




def _parse_pair(pair):
    if isinstance(pair, tuple):
        return pair
    if isinstance(pair, str):
        left, right = pair.lower().split("x", 1)
        return int(left), int(right)
    raise TypeError(f"unsupported spread pair: {pair!r}")

def run_bit_size_ablation(
    *,
    spread_pairs: List[str],
    train_per_tier: int,
    eval_per_tier: int,
    seed_count: int,
    max_steps: int,
    base_seed: int,
    out_dir: Path = DEFAULT_OUT_DIR,
) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)

    started = perf_counter()
    tiers = []

    for index, pair in enumerate(spread_pairs):
        run_seed = base_seed + index

        report = run_generalization_lab(
            train_per_tier=train_per_tier,
            eval_per_tier=eval_per_tier,
            spread_pairs=[_parse_pair(pair)],
            seed_count=seed_count,
            max_steps=max_steps,
        )

        tier_summary = summarize_tier(report)

        tier_row = {
            "spread_pair": pair,
            "seed": run_seed,
            "summary": tier_summary,
            "report": report,
        }
        tiers.append(tier_row)

        tier_path = out_dir / f"bit_size_ablation_{pair}.json"
        tier_path.write_text(json.dumps(tier_row, indent=2, sort_keys=True), encoding="utf-8")

    solved_rates = [float(t["summary"]["sqi_solved_rate"]) for t in tiers]
    win_rates = [float(t["summary"]["sqi_win_rate"]) for t in tiers]
    median_times = [
        t["summary"]["median_sqi_ms_solved"]
        for t in tiers
        if t["summary"]["median_sqi_ms_solved"] is not None
    ]

    aggregate = {
        "tiers": len(tiers),
        "spread_pairs": spread_pairs,
        "train_per_tier": train_per_tier,
        "eval_per_tier": eval_per_tier,
        "seed_count": seed_count,
        "max_steps": max_steps,
        "base_seed": base_seed,
        "mean_solved_rate": round(mean(solved_rates), 6) if solved_rates else 0,
        "mean_win_rate": round(mean(win_rates), 6) if win_rates else 0,
        "median_of_tier_median_ms": round(median(median_times), 6) if median_times else None,
        "elapsed_ms": round((perf_counter() - started) * 1000, 6),
    }

    final_report = {
        "aggregate": aggregate,
        "tiers": tiers,
    }

    (out_dir / "semiprime_bit_size_ablation_report.json").write_text(
        json.dumps(final_report, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    compact = {
        "aggregate": aggregate,
        "tiers": [
            {
                "spread_pair": t["spread_pair"],
                "seed": t["seed"],
                **t["summary"],
            }
            for t in tiers
        ],
    }

    (out_dir / "semiprime_bit_size_ablation_summary.json").write_text(
        json.dumps(compact, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return compact


def main() -> None:
    parser = argparse.ArgumentParser(description="SQI semiprime bit-size ablation lab")
    parser.add_argument("--spread-pairs", default="40x64,48x72,56x80,64x96")
    parser.add_argument("--train-per-tier", type=int, default=1)
    parser.add_argument("--eval-per-tier", type=int, default=1)
    parser.add_argument("--seed-count", type=int, default=128)
    parser.add_argument("--max-steps", type=int, default=100000)
    parser.add_argument("--base-seed", type=int, default=20260508)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    out = run_bit_size_ablation(
        spread_pairs=parse_spread_pairs(args.spread_pairs),
        train_per_tier=args.train_per_tier,
        eval_per_tier=args.eval_per_tier,
        seed_count=args.seed_count,
        max_steps=args.max_steps,
        base_seed=args.base_seed,
    )

    if args.json:
        print(json.dumps(out["aggregate"], indent=2, sort_keys=True))
    else:
        print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
