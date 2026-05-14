from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from random import Random
from time import perf_counter
from typing import Any, Dict, List, Optional, Tuple

from backend.modules.sqi.factor.sqi_prime_factorizer import (
    benchmark,
    brent_only_factor,
    brent_rho_factor,
    exact_factor,
    fermat_only_factor,
    miller_rabin_is_probable_prime,
    pollard_only_factor,
    sqi_factor_once,
    rho_seed_wave_search,
    time_call,
    wheel_only_factor,
)


OUT_DIR = Path("benchmarks/sqi_semiprime_lab")
OUT_DIR.mkdir(parents=True, exist_ok=True)
PRIORS_PATH = OUT_DIR / "seed_wave_priors.json"


def load_learned_seed_priors(bucket: str = "spread_64_95") -> List[Tuple[int, int]]:
    """
    Load learned seed/c pairs from previous SQI seed-wave wins.
    """
    if not PRIORS_PATH.exists():
        return []

    try:
        priors = json.loads(PRIORS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

    data = priors.get("buckets", {}).get(bucket, {})
    seed_counts = data.get("seed_wave", {}).get("winning_seed_counts", {})
    c_counts = data.get("seed_wave", {}).get("winning_c_counts", {})

    seeds = [int(k) for k, _ in sorted(seed_counts.items(), key=lambda kv: -kv[1])]
    cs = [int(k) for k, _ in sorted(c_counts.items(), key=lambda kv: -kv[1])]

    pairs: List[Tuple[int, int]] = []
    for seed in seeds:
        for c in cs or [1]:
            pairs.append((seed, c))

    return pairs[:16]



@dataclass
class FactorProofCertificate:
    n: int
    factor: Optional[int]
    cofactor: Optional[int]
    verified: bool
    probable_prime_factor: Optional[bool]
    probable_prime_cofactor: Optional[bool]
    proof: str


@dataclass
class SemiprimeCase:
    case_id: str
    p: int
    q: int
    n: int
    p_bits: int
    q_bits: int
    relation: str


@dataclass
class SemiprimeRunResult:
    case: SemiprimeCase
    sqi: Dict[str, Any]
    baselines: Dict[str, Any]
    proof: FactorProofCertificate
    winner_by_time: str
    winner_ms: float
    route_correct_family: bool


def make_proof_certificate(n: int, factor: Optional[int], cofactor: Optional[int]) -> FactorProofCertificate:
    if factor is None or cofactor is None:
        return FactorProofCertificate(
            n=n,
            factor=factor,
            cofactor=cofactor,
            verified=False,
            probable_prime_factor=None,
            probable_prime_cofactor=None,
            proof="No factor/cofactor pair was produced.",
        )

    verified = (factor * cofactor == n) and (n % factor == 0) and (n % cofactor == 0)

    return FactorProofCertificate(
        n=n,
        factor=factor,
        cofactor=cofactor,
        verified=verified,
        probable_prime_factor=miller_rabin_is_probable_prime(factor),
        probable_prime_cofactor=miller_rabin_is_probable_prime(cofactor),
        proof=(
            f"{factor} * {cofactor} == {n} and "
            f"{n} % {factor} == {n % factor} and "
            f"{n} % {cofactor} == {n % cofactor}"
        ),
    )


def random_odd_with_bits(bits: int, rng: Random) -> int:
    if bits < 2:
        raise ValueError("bits must be >= 2")

    n = rng.getrandbits(bits)
    n |= 1
    n |= 1 << (bits - 1)
    return n


def generate_probable_prime(bits: int, rng: Random, max_tries: int = 100_000) -> int:
    for _ in range(max_tries):
        n = random_odd_with_bits(bits, rng)

        # quick wheel-ish prefilter
        if any(n % p == 0 and n != p for p in [3, 5, 7, 11, 13, 17, 19, 23, 29, 31]):
            continue

        if miller_rabin_is_probable_prime(n):
            return n

    raise RuntimeError(f"failed to generate probable prime with {bits} bits")


def generate_close_prime_pair(bits: int, rng: Random, max_delta: int = 10_000) -> Tuple[int, int]:
    p = generate_probable_prime(bits, rng)

    # Find a nearby probable prime.
    start = p + 2
    limit = p + max_delta

    q = start
    while q <= limit:
        if q % 2 == 0:
            q += 1
            continue
        if miller_rabin_is_probable_prime(q):
            return p, q
        q += 2

    # fallback
    q = generate_probable_prime(bits, rng)
    return p, q


def generate_spread_prime_pair(p_bits: int, q_bits: int, rng: Random) -> Tuple[int, int]:
    p = generate_probable_prime(p_bits, rng)
    q = generate_probable_prime(q_bits, rng)

    if p == q:
        q = generate_probable_prime(q_bits, rng)

    return p, q


def build_cases(
    *,
    seed: int,
    close_bits: List[int],
    spread_pairs: List[Tuple[int, int]],
    per_tier: int,
) -> List[SemiprimeCase]:
    rng = Random(seed)
    cases: List[SemiprimeCase] = []

    for bits in close_bits:
        for i in range(per_tier):
            p, q = generate_close_prime_pair(bits, rng)
            n = p * q
            cases.append(
                SemiprimeCase(
                    case_id=f"close_{bits}bit_{i}",
                    p=p,
                    q=q,
                    n=n,
                    p_bits=p.bit_length(),
                    q_bits=q.bit_length(),
                    relation="close",
                )
            )

    for p_bits, q_bits in spread_pairs:
        for i in range(per_tier):
            p, q = generate_spread_prime_pair(p_bits, q_bits, rng)
            n = p * q
            cases.append(
                SemiprimeCase(
                    case_id=f"spread_{p_bits}x{q_bits}_{i}",
                    p=p,
                    q=q,
                    n=n,
                    p_bits=p.bit_length(),
                    q_bits=q.bit_length(),
                    relation="spread",
                )
            )

    return cases


def timed_baseline(name: str, fn, n: int, timeout_hint_bits: int) -> Dict[str, Any]:
    """
    Runs safe baselines. Naive/wheel are skipped for larger values because they can waste time.
    """
    if name in {"naive", "wheel"} and timeout_hint_bits > 44:
        return {
            "skipped": True,
            "reason": f"skipped for {timeout_hint_bits}-bit n",
            "factor": None,
            "cofactor": None,
            "checks": None,
            "elapsed_ms": None,
        }

    start = perf_counter()
    factor, checks = fn(n)
    elapsed_ms = (perf_counter() - start) * 1000

    return {
        "skipped": False,
        "factor": factor,
        "cofactor": n // factor if exact_factor(n, factor) else None,
        "checks": checks,
        "elapsed_ms": round(elapsed_ms, 6),
        "verified": exact_factor(n, factor),
    }


def method_family(method: str) -> str:
    if method in {"fermat"}:
        return "close"
    if method in {
        "brent_rho",
        "pollard_rho",
        "small_prime",
        "brent_rho_seed_wave",
        "brent_rho_seed_wave_learned_first",
        "pollard_rho_seed_wave",
    }:
        return "spread"
    return "unknown"


def choose_winner(sqi: Dict[str, Any], baselines: Dict[str, Any]) -> Tuple[str, float]:
    candidates: List[Tuple[str, float]] = []

    if sqi.get("factor") and sqi.get("elapsed_ms") is not None:
        candidates.append(("sqi", float(sqi["elapsed_ms"])))

    for name, row in baselines.items():
        if row.get("skipped"):
            continue
        if row.get("verified") and row.get("elapsed_ms") is not None:
            candidates.append((name, float(row["elapsed_ms"])))

    if not candidates:
        return "none", float("inf")

    return min(candidates, key=lambda x: x[1])


def run_case(case: SemiprimeCase, trace: bool = False, dashboard: bool = False) -> SemiprimeRunResult:
    n = case.n

    # Deep mode: larger spread semiprimes need more Rho depth and more seed branches.
    hard_mode = n.bit_length() >= 80 and case.relation == "spread"

    # Learned-first path:
    # If prior profiling found useful seed/c branches for this bucket,
    # try them before the heavier adaptive scheduler.
    learned_first_factor = None
    learned_first_checks = 0
    learned_first_trace = []
    learned_first_ms = 0.0

    if hard_mode:
        learned_priors_first = load_learned_seed_priors("spread_64_95")
        if learned_priors_first:
            learned_start = perf_counter()
            learned_first_factor, learned_first_checks, learned_first_trace = rho_seed_wave_search(
                n,
                seed_count=max(16, len(learned_priors_first)),
                max_steps_per_seed=100_000,
                rng_seed=case.n % 1_000_000,
                prefer="brent",
                learned_seed_priors=learned_priors_first,
            )
            learned_first_ms = (perf_counter() - learned_start) * 1000

    if exact_factor(n, learned_first_factor):
        from backend.modules.sqi.factor.sqi_prime_factorizer import FactorCollapseTrace

        sqi_result = FactorCollapseTrace(
            n=n,
            found_factor=learned_first_factor,
            cofactor=n // learned_first_factor,
            method="brent_rho_seed_wave_learned_first",
            checked=learned_first_checks,
            branches_generated=len(learned_priors_first),
            branches_pruned=0,
            elapsed_ms=learned_first_ms,
            trace=[
                {"event": "learned_seed_wave_first", "priors": learned_priors_first},
                *learned_first_trace,
            ],
            trace_path=None,
            dashboard_path=None,
        )
    else:
        sqi_result = sqi_factor_once(
            n,
            trace_jsonl=trace,
            dashboard_json=dashboard,
            max_rounds=500 if hard_mode else 250,
            rho_branches=32 if hard_mode else 8,
            rho_step_budget=100_000 if hard_mode else 25_000,
            rho_active_branches=4 if hard_mode else 2,
        )

    # Final hard-spread escalation: if the adaptive scheduler fails,
    # run seed-wave search over many Rho/Brent branches.
    seed_wave_trace = []
    if sqi_result.found_factor is None and hard_mode:
        wave_start = perf_counter()
        learned_priors = load_learned_seed_priors("spread_64_95")

        wave_factor, wave_checks, seed_wave_trace = rho_seed_wave_search(
            n,
            seed_count=128,
            max_steps_per_seed=75_000,
            rng_seed=case.n % 1_000_000,
            prefer="brent",
            learned_seed_priors=learned_priors,
        )
        wave_ms = (perf_counter() - wave_start) * 1000

        if exact_factor(n, wave_factor):
            sqi_result.found_factor = wave_factor
            sqi_result.cofactor = n // wave_factor
            sqi_result.method = "brent_rho_seed_wave"
            sqi_result.checked += wave_checks
            sqi_result.elapsed_ms += wave_ms
            sqi_result.trace.extend(seed_wave_trace)

    sqi = {
        "factor": sqi_result.found_factor,
        "cofactor": sqi_result.cofactor,
        "method": sqi_result.method,
        "checks": sqi_result.checked,
        "branches_generated": sqi_result.branches_generated,
        "branches_pruned": sqi_result.branches_pruned,
        "elapsed_ms": round(sqi_result.elapsed_ms, 6),
        "trace_path": sqi_result.trace_path,
        "dashboard_path": sqi_result.dashboard_path,
        "route": next((x for x in sqi_result.trace if x.get("event") == "branch_routing"), None),
        "seed_wave_used": bool(seed_wave_trace),
        "trace_tail": sqi_result.trace[-5:],
    }

    baselines = {
        "fermat_only": timed_baseline("fermat_only", fermat_only_factor, n, n.bit_length()),
        "pollard_only": timed_baseline("pollard_only", pollard_only_factor, n, n.bit_length()),
        "brent_only": timed_baseline("brent_only", brent_only_factor, n, n.bit_length()),
        "wheel": timed_baseline("wheel", wheel_only_factor, n, n.bit_length()),
        "naive": timed_baseline("naive", lambda x: benchmark(x)["naive_tuple"] if False else _naive_tuple(x), n, n.bit_length()),
    }

    proof = make_proof_certificate(n, sqi_result.found_factor, sqi_result.cofactor)
    winner_name, winner_ms = choose_winner(sqi, baselines)

    route_correct_family = method_family(sqi_result.method) == case.relation

    return SemiprimeRunResult(
        case=case,
        sqi=sqi,
        baselines=baselines,
        proof=proof,
        winner_by_time=winner_name,
        winner_ms=winner_ms,
        route_correct_family=route_correct_family,
    )


def _naive_tuple(n: int) -> Tuple[Optional[int], int]:
    from backend.modules.sqi.factor.sqi_prime_factorizer import naive_trial_factor
    return naive_trial_factor(n)


def summarize(results: List[SemiprimeRunResult]) -> Dict[str, Any]:
    total = len(results)
    solved = [r for r in results if r.proof.verified]
    route_correct = [r for r in results if r.route_correct_family]

    winners: Dict[str, int] = {}
    sqi_methods: Dict[str, int] = {}

    for r in results:
        winners[r.winner_by_time] = winners.get(r.winner_by_time, 0) + 1
        method = r.sqi.get("method", "unknown")
        sqi_methods[method] = sqi_methods.get(method, 0) + 1

    return {
        "total_cases": total,
        "sqi_solved": len(solved),
        "sqi_solved_rate": round(len(solved) / total, 4) if total else 0,
        "route_correct_family_count": len(route_correct),
        "route_correct_family_rate": round(len(route_correct) / total, 4) if total else 0,
        "winner_counts": winners,
        "sqi_method_counts": sqi_methods,
    }


def run_lab(
    *,
    seed: int = 20260507,
    close_bits: List[int] = [20, 24, 28, 32],
    spread_pairs: List[Tuple[int, int]] = [(16, 28), (20, 32), (24, 36), (28, 40)],
    per_tier: int = 2,
    trace: bool = False,
    dashboard: bool = False,
) -> Dict[str, Any]:
    cases = build_cases(
        seed=seed,
        close_bits=close_bits,
        spread_pairs=spread_pairs,
        per_tier=per_tier,
    )

    results = [run_case(c, trace=trace, dashboard=dashboard) for c in cases]
    summary = summarize(results)

    payload = {
        "seed": seed,
        "summary": summary,
        "results": [
            {
                "case": asdict(r.case),
                "sqi": r.sqi,
                "baselines": r.baselines,
                "proof": asdict(r.proof),
                "winner_by_time": r.winner_by_time,
                "winner_ms": r.winner_ms,
                "route_correct_family": r.route_correct_family,
            }
            for r in results
        ],
    }

    out_path = OUT_DIR / "semiprime_lab_report.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    summary_path = OUT_DIR / "semiprime_lab_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    return payload


def parse_pairs(raw: str) -> List[Tuple[int, int]]:
    if not raw:
        return []
    pairs = []
    for chunk in raw.split(","):
        left, right = chunk.split("x")
        pairs.append((int(left), int(right)))
    return pairs


def main() -> None:
    parser = argparse.ArgumentParser(description="SQI semiprime stress lab")
    parser.add_argument("--seed", type=int, default=20260507)
    parser.add_argument("--per-tier", type=int, default=2)
    parser.add_argument("--close-bits", type=str, default="20,24,28,32")
    parser.add_argument("--spread-pairs", type=str, default="16x28,20x32,24x36,28x40")
    parser.add_argument("--trace", action="store_true")
    parser.add_argument("--dashboard", action="store_true")
    parser.add_argument("--json", action="store_true")

    args = parser.parse_args()

    close_bits = [int(x) for x in args.close_bits.split(",") if x.strip()]
    spread_pairs = parse_pairs(args.spread_pairs)

    payload = run_lab(
        seed=args.seed,
        close_bits=close_bits,
        spread_pairs=spread_pairs,
        per_tier=args.per_tier,
        trace=args.trace,
        dashboard=args.dashboard,
    )

    if args.json:
        print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    else:
        print("=== SQI Semiprime Lab Summary ===")
        print(json.dumps(payload["summary"], indent=2, sort_keys=True))
        print("wrote benchmarks/sqi_semiprime_lab/semiprime_lab_report.json")
        print("wrote benchmarks/sqi_semiprime_lab/semiprime_lab_summary.json")


if __name__ == "__main__":
    main()
