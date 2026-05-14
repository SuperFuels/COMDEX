from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from time import perf_counter
from typing import Any, Dict, List, Optional, Tuple

from backend.modules.sqi.factor.qwave_factor_worker import run_factor_beam


def parse_seed_priors(value: str | None) -> List[Tuple[int, int]]:
    """
    Parse CLI seed/c priors.

    Accepted format:
      6:10
      6:10,15:14,169557:15
    """
    if not value:
        return []

    priors: List[Tuple[int, int]] = []

    for raw_part in value.split(","):
        part = raw_part.strip()
        if not part:
            continue

        if ":" not in part:
            raise ValueError(
                f"Invalid prior {part!r}. Expected format seed:c, for example 6:10"
            )

        seed_raw, c_raw = part.split(":", 1)
        seed = int(seed_raw.strip())
        c = int(c_raw.strip())

        if seed <= 0:
            raise ValueError(f"Invalid seed in prior {part!r}; seed must be > 0")
        if c <= 0:
            raise ValueError(f"Invalid c in prior {part!r}; c must be > 0")

        priors.append((seed, c))

    return priors


def load_prior_bank_priors(
    *,
    bits: str,
    method: str,
    limit: int,
) -> List[Tuple[int, int]]:
    """
    Load ranked seed/c priors from semiprime_prior_bank_lab.

    Uses the existing CLI command:
      semiprime_prior_bank_lab.py rank --bits 48x72 --method pollard --limit 8

    This avoids requiring a rank_priors() Python function to exist.
    """
    import subprocess
    import sys

    cmd = [
        sys.executable,
        "backend/modules/sqi/factor/semiprime_prior_bank_lab.py",
        "rank",
        "--bits",
        bits,
        "--method",
        method,
        "--limit",
        str(limit),
    ]

    proc = subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        text=True,
    )

    ranked = proc.stdout.strip()
    return parse_seed_priors(ranked)


def _chunk_seeds(
    seeds: List[Tuple[int, int]],
    *,
    beam_count: int,
) -> List[List[Tuple[int, int]]]:
    if beam_count <= 0:
        raise ValueError("beam_count must be > 0")

    chunks: List[List[Tuple[int, int]]] = [[] for _ in range(beam_count)]

    for index, seed_pair in enumerate(seeds):
        chunks[index % beam_count].append(seed_pair)

    return chunks


def _default_seed_pairs(
    *,
    seed_count: int,
    rng_seed: int,
    learned_seed_priors: Optional[List[Tuple[int, int]]] = None,
) -> List[Tuple[int, int]]:
    """
    Build deterministic seed/c pairs for QWave factor beams.

    learned_seed_priors are placed first so known-good branches get first collapse
    opportunity. The rest are deterministic low/random-style branches.
    """
    priors = list(learned_seed_priors or [])

    seen = set()
    out: List[Tuple[int, int]] = []

    for seed, c in priors:
        pair = (int(seed), int(c))
        if pair not in seen:
            out.append(pair)
            seen.add(pair)

    low_pairs = [
        (2, 1),
        (3, 2),
        (5, 1),
        (7, 3),
        (11, 6),
        (13, 12),
        (15, 14),
        (17, 16),
        (19, 8),
        (23, 22),
        (29, 10),
        (31, 12),
        (37, 5),
        (41, 9),
        (42, 10),
        (57, 25),
        (64, 1),
    ]

    for pair in low_pairs:
        if len(out) >= seed_count:
            return out
        if pair not in seen:
            out.append(pair)
            seen.add(pair)

    # Lightweight deterministic pseudo-random expansion.
    # Avoid importing random so this file remains cheap to import.
    x = int(rng_seed) & 0x7FFFFFFF

    while len(out) < seed_count:
        x = (1103515245 * x + 12345) & 0x7FFFFFFF
        seed = 2 + (x % 2_000_000)

        x = (1103515245 * x + 12345) & 0x7FFFFFFF
        c = 1 + (x % 127)

        pair = (seed, c)
        if pair not in seen:
            out.append(pair)
            seen.add(pair)

    return out


def _result_to_dict(result: Any) -> Dict[str, Any]:
    """
    Normalize either a dict result or a FactorBeamResult dataclass/object into a dict.
    """
    if isinstance(result, dict):
        return {
            "beam_id": result.get("beam_id"),
            "factor": result.get("factor"),
            "cofactor": result.get("cofactor"),
            "checks": result.get("checks", 0),
            "elapsed_ms": result.get("elapsed_ms", 0.0),
            "verified": result.get("verified", False),
            "method": result.get("method", "parallel_qwave_unknown"),
            "trace_tail": result.get("trace_tail", []),
            "seed": result.get("seed"),
            "c": result.get("c"),
        }

    return {
        "beam_id": getattr(result, "beam_id", None),
        "factor": getattr(result, "factor", None),
        "cofactor": getattr(result, "cofactor", None),
        "checks": getattr(result, "checks", 0),
        "elapsed_ms": getattr(result, "elapsed_ms", 0.0),
        "verified": getattr(result, "verified", False),
        "method": getattr(result, "method", "parallel_qwave_unknown"),
        "trace_tail": getattr(result, "trace_tail", []),
        "seed": getattr(result, "seed", None),
        "c": getattr(result, "c", None),
    }


def _run_seed_beam_worker(args: Tuple[Any, ...]) -> Dict[str, Any]:
    (
        n,
        beam_index,
        prefer,
        seeds,
        max_steps_per_seed,
    ) = args

    result = run_factor_beam(
        n=n,
        beam_id=f"qwave_factor_beam_{beam_index}",
        seeds=seeds,
        prefer=prefer,
        max_steps=max_steps_per_seed,
    )

    return _result_to_dict(result)


def _append_beam_result_trace(
    trace: List[Dict[str, Any]],
    row: Dict[str, Any],
) -> None:
    trace.append(
        {
            "event": "parallel_qwave_beam_result",
            "beam_id": row.get("beam_id"),
            "verified": row.get("verified"),
            "factor": row.get("factor"),
            "cofactor": row.get("cofactor"),
            "checks": row.get("checks"),
            "elapsed_ms": row.get("elapsed_ms"),
            "method": row.get("method"),
            "seed": row.get("seed"),
            "c": row.get("c"),
        }
    )


def _append_collapse_trace(
    trace: List[Dict[str, Any]],
    row: Dict[str, Any],
    *,
    total_checks: int,
    started: float,
) -> None:
    elapsed_ms = (perf_counter() - started) * 1000

    trace.append(
        {
            "event": "parallel_qwave_collapse",
            "beam_id": row.get("beam_id"),
            "factor": row.get("factor"),
            "cofactor": row.get("cofactor"),
            "total_checks_observed": total_checks,
            "elapsed_ms_observed": round(elapsed_ms, 6),
            "method": row.get("method"),
            "seed": row.get("seed"),
            "c": row.get("c"),
        }
    )


def parallel_qwave_seed_beam_search(
    n: int,
    *,
    beam_count: int = 8,
    seeds_per_beam: int = 64,
    max_steps_per_seed: int = 100_000,
    prefer: str = "brent",
    rng_seed: int = 20260508,
    learned_seed_priors: Optional[List[Tuple[int, int]]] = None,
) -> Tuple[Optional[int], int, List[Dict[str, Any]], str]:
    """
    Parallel QWave-style seed beam search.

    Each process is treated as one independent QWaveBeam:
      - different seed/c branch slice
      - same factor target n
      - same branch family, Brent or Pollard
      - first verified collapse wins

    For beam_count=1 this runs inline to avoid ProcessPool startup/import overhead.

    Returns:
      factor, total_checks, trace, method
    """
    if prefer not in {"brent", "pollard"}:
        raise ValueError("prefer must be 'brent' or 'pollard'")

    if beam_count <= 0:
        raise ValueError("beam_count must be > 0")

    if seeds_per_beam <= 0:
        raise ValueError("seeds_per_beam must be > 0")

    if max_steps_per_seed <= 0:
        raise ValueError("max_steps_per_seed must be > 0")

    started = perf_counter()
    total_seed_count = beam_count * seeds_per_beam

    seed_pairs = _default_seed_pairs(
        seed_count=total_seed_count,
        rng_seed=rng_seed,
        learned_seed_priors=learned_seed_priors,
    )

    seed_chunks = _chunk_seeds(seed_pairs, beam_count=beam_count)

    jobs = [
        (
            n,
            i,
            prefer,
            seed_chunks[i],
            max_steps_per_seed,
        )
        for i in range(beam_count)
    ]

    trace: List[Dict[str, Any]] = [
        {
            "event": "parallel_qwave_beam_start",
            "n": n,
            "beam_count": beam_count,
            "seeds_per_beam": seeds_per_beam,
            "max_steps_per_seed": max_steps_per_seed,
            "prefer": prefer,
            "prior_count": len(learned_seed_priors or []),
        }
    ]

    total_checks = 0
    best_failure_tail: List[Dict[str, Any]] = []

    # Critical fast path:
    # If there is only one beam, do not spawn a child process.
    # This gives a true measurement of the factor worker instead of measuring
    # multiprocessing/import overhead.
    if beam_count == 1:
        row = _result_to_dict(_run_seed_beam_worker(jobs[0]))
        total_checks += int(row.get("checks") or 0)

        _append_beam_result_trace(trace, row)

        trace_tail = row.get("trace_tail") or []
        if trace_tail:
            best_failure_tail = trace_tail

        if row.get("verified"):
            _append_collapse_trace(
                trace,
                row,
                total_checks=total_checks,
                started=started,
            )

            return (
                int(row["factor"]),
                total_checks,
                trace,
                f"parallel_qwave_{prefer}",
            )

        trace.append(
            {
                "event": "parallel_qwave_no_collapse",
                "total_checks": total_checks,
                "failure_tail": best_failure_tail[-5:],
            }
        )

        return None, total_checks, trace, f"parallel_qwave_{prefer}_none"

    with ProcessPoolExecutor(max_workers=beam_count) as pool:
        futures = [pool.submit(_run_seed_beam_worker, job) for job in jobs]

        for fut in as_completed(futures):
            row = _result_to_dict(fut.result())
            total_checks += int(row.get("checks") or 0)

            _append_beam_result_trace(trace, row)

            trace_tail = row.get("trace_tail") or []
            if trace_tail:
                best_failure_tail = trace_tail

            if row.get("verified"):
                _append_collapse_trace(
                    trace,
                    row,
                    total_checks=total_checks,
                    started=started,
                )

                return (
                    int(row["factor"]),
                    total_checks,
                    trace,
                    f"parallel_qwave_{prefer}",
                )

    trace.append(
        {
            "event": "parallel_qwave_no_collapse",
            "total_checks": total_checks,
            "failure_tail": best_failure_tail[-5:],
        }
    )

    return None, total_checks, trace, f"parallel_qwave_{prefer}_none"


def _exact_factor(n: int, factor: Optional[int]) -> bool:
    if factor is None:
        return False

    if not isinstance(factor, int):
        return False

    return factor > 1 and n % factor == 0 and factor != n


def benchmark_parallel_qwave(
    n: int,
    *,
    beam_count: int = 8,
    seeds_per_beam: int = 64,
    max_steps_per_seed: int = 100_000,
    prefer: str = "brent",
    learned_seed_priors: Optional[List[Tuple[int, int]]] = None,
) -> Dict[str, Any]:
    start = perf_counter()

    factor, checks, trace, method = parallel_qwave_seed_beam_search(
        n,
        beam_count=beam_count,
        seeds_per_beam=seeds_per_beam,
        max_steps_per_seed=max_steps_per_seed,
        prefer=prefer,
        rng_seed=n % 1_000_000,
        learned_seed_priors=learned_seed_priors,
    )

    elapsed_ms = (perf_counter() - start) * 1000
    verified = _exact_factor(n, factor)

    return {
        "n": n,
        "factor": factor if verified else None,
        "cofactor": n // factor if verified else None,
        "verified": verified,
        "method": method,
        "beam_count": beam_count,
        "seeds_per_beam": seeds_per_beam,
        "max_steps_per_seed": max_steps_per_seed,
        "prior_count": len(learned_seed_priors or []),
        "checks": checks,
        "elapsed_ms": round(elapsed_ms, 6),
        "trace_tail": trace[-10:],
    }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Parallel QWave seed-beam semiprime factor search"
    )
    parser.add_argument("n", type=int)
    parser.add_argument("--beam-count", type=int, default=8)
    parser.add_argument("--seeds-per-beam", type=int, default=64)
    parser.add_argument("--max-steps", type=int, default=100000)
    parser.add_argument("--prefer", choices=["brent", "pollard"], default="brent")
    parser.add_argument(
        "--priors",
        type=str,
        default="",
        help="Comma-separated seed:c priors, for example 6:10 or 6:10,15:14",
    )
    parser.add_argument("--use-prior-bank", action="store_true")
    parser.add_argument("--prior-bits", type=str, default="")
    parser.add_argument("--prior-limit", type=int, default=8)
    parser.add_argument("--json", action="store_true")

    args = parser.parse_args()

    learned_seed_priors = parse_seed_priors(args.priors)

    if args.use_prior_bank:
        if not args.prior_bits:
            raise SystemExit(
                "--use-prior-bank requires --prior-bits, for example --prior-bits 48x72"
            )

        bank_priors = load_prior_bank_priors(
            bits=args.prior_bits,
            method=args.prefer,
            limit=args.prior_limit,
        )

        # Explicit --priors stay first, bank priors fill after.
        seen = set(learned_seed_priors)
        for pair in bank_priors:
            if pair not in seen:
                learned_seed_priors.append(pair)
                seen.add(pair)

    out = benchmark_parallel_qwave(
        args.n,
        beam_count=args.beam_count,
        seeds_per_beam=args.seeds_per_beam,
        max_steps_per_seed=args.max_steps,
        prefer=args.prefer,
        learned_seed_priors=learned_seed_priors,
    )

    print(json.dumps(out, indent=2, sort_keys=True))