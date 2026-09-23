from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from math import isqrt
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


REPORT_PATH = Path("benchmarks/sqi_semiprime_lab/semiprime_lab_report.json")
OUT_PATH = Path("benchmarks/sqi_semiprime_lab/seed_wave_priors.json")


@dataclass
class FactorFeatureRow:
    case_id: str
    n: int
    n_bits: int
    p_bits: Optional[int]
    q_bits: Optional[int]
    relation: str
    near_square_gap: int
    near_square_score: float
    sqi_method: str
    winner: str
    verified: bool
    route_correct: bool
    seed_wave_used: bool
    winning_seed: Optional[int]
    winning_c: Optional[int]
    winning_branch: Optional[int]
    sqi_ms: float


def near_square_features(n: int) -> Tuple[int, float]:
    root = isqrt(n)
    ceil_root = root if root * root == n else root + 1
    gap = ceil_root * ceil_root - n
    score = max(0.0, 1.0 - (gap / max(1, ceil_root)))
    return gap, round(score, 6)


def extract_seed_wave_winner(trace_tail: List[Dict[str, Any]]) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """
    Extract winning seed/c/branch from trace tail if present.
    """
    seed = None
    c = None
    branch = None

    for ev in trace_tail or []:
        if ev.get("event") in {"seed_wave_collapse", "seed_wave_branch"}:
            if ev.get("seed") is not None:
                seed = ev.get("seed")
            if ev.get("c") is not None:
                c = ev.get("c")
            if ev.get("branch") is not None:
                branch = ev.get("branch")

    return seed, c, branch


def load_report(path: Path = REPORT_PATH) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Report not found: {path}. Run semiprime_lab.py first."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def feature_rows(report: Dict[str, Any]) -> List[FactorFeatureRow]:
    rows: List[FactorFeatureRow] = []

    for item in report.get("results", []):
        case = item["case"]
        sqi = item["sqi"]
        proof = item["proof"]

        n = int(case["n"])
        gap, score = near_square_features(n)

        seed, c, branch = extract_seed_wave_winner(sqi.get("trace_tail", []))

        rows.append(
            FactorFeatureRow(
                case_id=case["case_id"],
                n=n,
                n_bits=n.bit_length(),
                p_bits=case.get("p_bits"),
                q_bits=case.get("q_bits"),
                relation=case.get("relation", "unknown"),
                near_square_gap=gap,
                near_square_score=score,
                sqi_method=sqi.get("method", "unknown"),
                winner=item.get("winner_by_time", "unknown"),
                verified=bool(proof.get("verified")),
                route_correct=bool(item.get("route_correct_family")),
                seed_wave_used=bool(sqi.get("seed_wave_used")),
                winning_seed=seed,
                winning_c=c,
                winning_branch=branch,
                sqi_ms=float(sqi.get("elapsed_ms") or 0.0),
            )
        )

    return rows


def bucket_for_row(row: FactorFeatureRow) -> str:
    """
    Coarse bucket for learned priors.
    """
    if row.relation == "close" or row.near_square_score >= 0.98:
        return "near_square"

    if row.n_bits < 64:
        return "spread_lt64"

    if row.n_bits < 96:
        return "spread_64_95"

    if row.n_bits < 128:
        return "spread_96_127"

    return "spread_128_plus"


def build_priors(rows: List[FactorFeatureRow]) -> Dict[str, Any]:
    method_counts = Counter(row.sqi_method for row in rows)
    winner_counts = Counter(row.winner for row in rows)

    by_bucket: Dict[str, List[FactorFeatureRow]] = defaultdict(list)
    for row in rows:
        by_bucket[bucket_for_row(row)].append(row)

    bucket_priors: Dict[str, Any] = {}

    for bucket, bucket_rows in by_bucket.items():
        methods = Counter(row.sqi_method for row in bucket_rows)
        winners = Counter(row.winner for row in bucket_rows)
        solved = sum(1 for row in bucket_rows if row.verified)
        route_correct = sum(1 for row in bucket_rows if row.route_correct)

        seed_rows = [
            row for row in bucket_rows
            if row.seed_wave_used and row.winning_seed is not None
        ]

        seed_counts = Counter(row.winning_seed for row in seed_rows)
        c_counts = Counter(row.winning_c for row in seed_rows if row.winning_c is not None)
        branch_counts = Counter(row.winning_branch for row in seed_rows if row.winning_branch is not None)

        # Suggested method order from observed winners/methods.
        if winners:
            winner_order = [name for name, _ in winners.most_common()]
        else:
            winner_order = []

        method_order = [name for name, _ in methods.most_common()]

        # Ensure useful fallbacks.
        fallback = ["fermat", "brent_rho_seed_wave", "brent_rho", "pollard_rho", "sqi_wheel"]
        suggested_order = []
        for name in winner_order + method_order + fallback:
            if name not in suggested_order and name != "none":
                suggested_order.append(name)

        bucket_priors[bucket] = {
            "cases": len(bucket_rows),
            "solved": solved,
            "solved_rate": round(solved / len(bucket_rows), 4) if bucket_rows else 0.0,
            "route_correct": route_correct,
            "route_correct_rate": round(route_correct / len(bucket_rows), 4) if bucket_rows else 0.0,
            "method_counts": dict(methods),
            "winner_counts": dict(winners),
            "suggested_method_order": suggested_order,
            "seed_wave": {
                "winning_seed_counts": dict(seed_counts.most_common(20)),
                "winning_c_counts": dict(c_counts.most_common(20)),
                "winning_branch_counts": dict(branch_counts.most_common(20)),
                "observed_seed_wave_wins": len(seed_rows),
            },
        }

    return {
        "total_rows": len(rows),
        "method_counts": dict(method_counts),
        "winner_counts": dict(winner_counts),
        "buckets": bucket_priors,
        "rows": [asdict(row) for row in rows],
    }


def write_priors(report_path: Path = REPORT_PATH, out_path: Path = OUT_PATH) -> Dict[str, Any]:
    report = load_report(report_path)
    rows = feature_rows(report)
    priors = build_priors(rows)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(priors, indent=2, sort_keys=True), encoding="utf-8")

    return priors


def print_summary(priors: Dict[str, Any]) -> None:
    print("=== SQI Seed-Wave Priors ===")
    print(json.dumps({
        "total_rows": priors["total_rows"],
        "method_counts": priors["method_counts"],
        "winner_counts": priors["winner_counts"],
        "buckets": {
            name: {
                "cases": data["cases"],
                "solved_rate": data["solved_rate"],
                "route_correct_rate": data["route_correct_rate"],
                "suggested_method_order": data["suggested_method_order"],
                "seed_wave": data["seed_wave"],
            }
            for name, data in priors["buckets"].items()
        },
    }, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build SQI seed-wave priors from semiprime lab report")
    parser.add_argument("--report", type=str, default=str(REPORT_PATH))
    parser.add_argument("--out", type=str, default=str(OUT_PATH))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    priors = write_priors(Path(args.report), Path(args.out))

    if args.json:
        print(json.dumps(priors, indent=2, sort_keys=True))
    else:
        print_summary(priors)
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
