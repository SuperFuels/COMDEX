from __future__ import annotations

import argparse
import json
from pathlib import Path
from random import Random
from time import perf_counter
from typing import Any, Dict, List, Optional, Tuple

from backend.modules.sqi.factor.sqi_prime_factorizer import (
    brent_rho_factor,
    exact_factor,
    pollard_rho_factor,
)


OUT_DIR = Path("benchmarks/sqi_semiprime_lab")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def profile_seed_wave(
    n: int,
    *,
    seed_count: int = 256,
    max_steps_per_seed: int = 100_000,
    rng_seed: int = 777,
    method: str = "brent",
) -> Dict[str, Any]:
    rng = Random(rng_seed)

    branches: List[Tuple[int, int]] = []

    # Low deterministic seeds first.
    for i in range(min(seed_count, 64)):
        branches.append((2 + i, 1 + (i % 31)))

    # Then wider random exploration.
    while len(branches) < seed_count:
        pair = (
            rng.randint(2, max(3, min(n - 2, 2_000_000))),
            rng.randint(1, 127),
        )
        if pair not in branches:
            branches.append(pair)

    rows: List[Dict[str, Any]] = []

    for branch_i, (seed, c) in enumerate(branches):
        start = perf_counter()

        if method == "pollard":
            factor, checks, trace = pollard_rho_factor(
                n,
                seed=seed,
                c=c,
                max_steps=max_steps_per_seed,
            )
            method_name = "pollard"
        else:
            factor, checks, trace = brent_rho_factor(
                n,
                seed=seed,
                c=c,
                max_steps=max_steps_per_seed,
            )
            method_name = "brent"

        elapsed_ms = (perf_counter() - start) * 1000
        verified = exact_factor(n, factor)

        rows.append({
            "branch": branch_i,
            "method": method_name,
            "seed": seed,
            "c": c,
            "factor": factor,
            "cofactor": n // factor if verified else None,
            "checks": checks,
            "elapsed_ms": round(elapsed_ms, 6),
            "verified": verified,
            "trace_tail": trace[-3:],
        })

    winners = [r for r in rows if r["verified"]]
    winners_sorted = sorted(winners, key=lambda r: (r["elapsed_ms"], r["checks"]))

    payload = {
        "n": n,
        "seed_count": seed_count,
        "max_steps_per_seed": max_steps_per_seed,
        "rng_seed": rng_seed,
        "method": method,
        "total_winners": len(winners_sorted),
        "best": winners_sorted[:20],
        "rows": rows,
    }

    out_path = OUT_DIR / f"seed_wave_profile_{n}_{method}.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    summary_path = OUT_DIR / f"seed_wave_profile_{n}_{method}_summary.json"
    summary = {
        "n": n,
        "method": method,
        "seed_count": seed_count,
        "total_winners": len(winners_sorted),
        "best": winners_sorted[:10],
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile SQI seed/c Rho branches")
    parser.add_argument("n", type=int)
    parser.add_argument("--seed-count", type=int, default=256)
    parser.add_argument("--max-steps", type=int, default=100_000)
    parser.add_argument("--rng-seed", type=int, default=777)
    parser.add_argument("--method", choices=["brent", "pollard"], default="brent")
    parser.add_argument("--json", action="store_true")

    args = parser.parse_args()

    payload = profile_seed_wave(
        args.n,
        seed_count=args.seed_count,
        max_steps_per_seed=args.max_steps,
        rng_seed=args.rng_seed,
        method=args.method,
    )

    summary = {
        "n": payload["n"],
        "method": payload["method"],
        "seed_count": payload["seed_count"],
        "total_winners": payload["total_winners"],
        "best": payload["best"][:10],
    }

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print("=== SQI Seed-Wave Profile Summary ===")
        print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
