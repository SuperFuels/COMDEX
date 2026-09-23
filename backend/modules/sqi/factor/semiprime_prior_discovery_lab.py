from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from statistics import median
from time import perf_counter, time
from typing import Any, Dict, Iterable, List, Optional, Tuple

from backend.modules.sqi.factor.qwave_factor_worker import run_factor_beam


DEFAULT_OUT_DIR = Path("benchmarks/sqi_semiprime_lab/prior_discovery")


SeedPair = Tuple[int, int]


def _verify(n: int, factor: Optional[int]) -> tuple[Optional[int], bool]:
    if factor is None:
        return None, False
    if not isinstance(factor, int):
        return None, False
    if factor <= 1 or factor >= n:
        return None, False
    if n % factor != 0:
        return None, False
    return n // factor, True


def _result_to_dict(result: Any) -> Dict[str, Any]:
    if isinstance(result, dict):
        return dict(result)

    return {
        "beam_id": getattr(result, "beam_id", None),
        "factor": getattr(result, "factor", None),
        "cofactor": getattr(result, "cofactor", None),
        "checks": getattr(result, "checks", 0),
        "elapsed_ms": getattr(result, "elapsed_ms", 0.0),
        "verified": getattr(result, "verified", False),
        "method": getattr(result, "method", None),
        "trace_tail": getattr(result, "trace_tail", []),
        "seed": getattr(result, "seed", None),
        "c": getattr(result, "c", None),
    }


def _report_path(out_dir: Path, out_suffix: str | None) -> Path:
    suffix = (out_suffix or "").strip()
    if suffix:
        return out_dir / f"semiprime_prior_discovery_report_{suffix}.json"
    return out_dir / "semiprime_prior_discovery_report.json"


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _chunk_list(items: List[SeedPair], chunk_size: int) -> List[List[SeedPair]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def _grid_seed_pairs(
    *,
    seed_start: int,
    seed_end: int,
    c_start: int,
    c_end: int,
) -> List[SeedPair]:
    pairs: List[SeedPair] = []
    for seed in range(seed_start, seed_end + 1):
        for c in range(c_start, c_end + 1):
            pairs.append((seed, c))
    return pairs


def _random_seed_pairs(
    *,
    sample_count: int,
    seed_min: int,
    seed_max: int,
    c_min: int,
    c_max: int,
    rng_seed: int,
) -> List[SeedPair]:
    rng = random.Random(rng_seed)
    seen: set[SeedPair] = set()
    pairs: List[SeedPair] = []

    while len(pairs) < sample_count:
        pair = (rng.randint(seed_min, seed_max), rng.randint(c_min, c_max))
        if pair not in seen:
            seen.add(pair)
            pairs.append(pair)

    return pairs


def parse_seed_priors(value: str | None) -> List[SeedPair]:
    if not value:
        return []

    priors: List[SeedPair] = []
    seen: set[SeedPair] = set()

    for raw in value.split(","):
        part = raw.strip()
        if not part:
            continue
        if ":" not in part:
            raise ValueError(f"invalid prior {part!r}; expected seed:c")

        seed_raw, c_raw = part.split(":", 1)
        pair = (int(seed_raw.strip()), int(c_raw.strip()))

        if pair[0] <= 0 or pair[1] <= 0:
            raise ValueError(f"invalid prior {part!r}; seed and c must be > 0")

        if pair not in seen:
            seen.add(pair)
            priors.append(pair)

    return priors


def _load_bank_priors(
    *,
    bits: str | None,
    method: str,
    limit: int,
) -> List[SeedPair]:
    if not bits:
        return []

    try:
        from backend.modules.sqi.factor.semiprime_prior_bank_lab import rank_priors

        ranked = rank_priors(bits=bits, method=method, limit=limit)
        if isinstance(ranked, str):
            return parse_seed_priors(ranked)
        return [(int(seed), int(c)) for seed, c in ranked]
    except Exception:
        # Fallback through CLI, because older bank versions may not export rank_priors.
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
        out = subprocess.check_output(cmd, text=True).strip()
        return parse_seed_priors(out)


def _dedupe_pairs(pairs: Iterable[SeedPair]) -> List[SeedPair]:
    seen: set[SeedPair] = set()
    out: List[SeedPair] = []
    for seed, c in pairs:
        pair = (int(seed), int(c))
        if pair not in seen:
            seen.add(pair)
            out.append(pair)
    return out


def _run_chunk_worker(args: Tuple[Any, ...]) -> Dict[str, Any]:
    (
        n,
        prefer,
        chunk_index,
        seed_pairs,
        max_steps,
    ) = args

    started = perf_counter()
    result = run_factor_beam(
        n=n,
        beam_id=f"prior_discovery_{prefer}_chunk_{chunk_index}",
        seeds=seed_pairs,
        prefer=prefer,
        max_steps=max_steps,
    )

    row = _result_to_dict(result)
    factor = row.get("factor")
    cofactor, verified = _verify(n, factor)

    elapsed_ms = round((perf_counter() - started) * 1000, 6)
    checks = int(row.get("checks") or 0)

    # If the worker does not return checks, use conservative full budget estimate.
    if checks <= 0:
        checks = len(seed_pairs) * int(max_steps)

    return {
        "chunk_index": chunk_index,
        "prefer": prefer,
        "verified": bool(verified),
        "factor": int(factor) if verified else None,
        "cofactor": int(cofactor) if verified and cofactor is not None else None,
        "seed": row.get("seed") if verified else None,
        "c": row.get("c") if verified else None,
        "checks": checks,
        "elapsed_ms": elapsed_ms,
        "attempts": len(seed_pairs),
        "method": row.get("method") or f"prior_discovery_{prefer}",
        "trace_tail": row.get("trace_tail") or [],
    }


def _make_partial_report(
    *,
    n: int,
    prefer: str,
    seed_range: List[int],
    c_range: List[int],
    max_steps: int,
    attempts: int,
    total_checks: int,
    elapsed_ms: float,
    hits: List[Dict[str, Any]],
    done: bool,
    methods_run: List[str],
) -> Dict[str, Any]:
    hit_checks = [int(h["checks"]) for h in hits if h.get("checks") is not None]
    hits_sorted = sorted(
        hits,
        key=lambda h: (
            int(h.get("checks") or 10**30),
            int(h.get("seed") or 10**30),
            int(h.get("c") or 10**30),
        ),
    )

    return {
        "n": n,
        "prefer": prefer,
        "methods_run": methods_run,
        "verified": bool(hits_sorted),
        "done": done,
        "hit_count": len(hits_sorted),
        "best_hit": hits_sorted[0] if hits_sorted else None,
        "hits": hits_sorted,
        "attempts": attempts,
        "total_checks": total_checks,
        "elapsed_ms": round(elapsed_ms, 6),
        "seed_range": seed_range,
        "c_range": c_range,
        "max_steps": max_steps,
        "best_checks": min(hit_checks) if hit_checks else None,
        "median_hit_checks": median(hit_checks) if hit_checks else None,
        "updated_ts": time(),
    }


def _add_best_hit_to_bank(
    *,
    report: Dict[str, Any],
    bits: str,
    source: str,
) -> None:
    hit = report.get("best_hit")
    if not hit:
        return

    cmd = [
        sys.executable,
        "backend/modules/sqi/factor/semiprime_prior_bank_lab.py",
        "add",
        "--n",
        str(report["n"]),
        "--factor",
        str(hit["factor"]),
        "--cofactor",
        str(hit["cofactor"]),
        "--method",
        str(hit.get("prefer") or report.get("prefer") or "pollard"),
        "--seed",
        str(hit["seed"]),
        "--c",
        str(hit["c"]),
        "--checks",
        str(hit["checks"]),
        "--elapsed-ms",
        str(hit.get("elapsed_ms") or report.get("elapsed_ms") or 0),
        "--source",
        source,
    ]

    # Older bank versions may not support --bits. So do not pass it unless your bank supports it.
    # Tier is inferred by factor bit lengths in the current bank implementation.
    subprocess.run(cmd, check=True)


def run_prior_discovery_lab(
    n: int,
    *,
    prefer: str = "both",
    seed_start: int = 1,
    seed_end: int = 10_000,
    c_start: int = 1,
    c_end: int = 128,
    max_steps: int = 500_000,
    workers: int = 4,
    chunk_size: int = 32,
    stop_after_first: bool = True,
    progress_every: int = 0,
    save_partial: bool = False,
    out_dir: Path = DEFAULT_OUT_DIR,
    out_suffix: str | None = None,
    priors: Optional[List[SeedPair]] = None,
    prior_bank_bits: str | None = None,
    prior_limit: int = 0,
    random_samples: int = 0,
    random_seed_min: int = 1,
    random_seed_max: int = 2_000_000,
    random_c_min: int = 1,
    random_c_max: int = 4096,
    rng_seed: int = 20260509,
    add_to_bank: bool = False,
    bank_bits: str | None = None,
    bank_source: str = "prior_discovery_lab",
) -> Dict[str, Any]:
    if prefer not in {"pollard", "brent", "both"}:
        raise ValueError("prefer must be pollard, brent, or both")
    if workers <= 0:
        raise ValueError("workers must be > 0")

    started = perf_counter()
    out_path = _report_path(out_dir, out_suffix)

    methods = ["pollard", "brent"] if prefer == "both" else [prefer]

    all_jobs: List[Tuple[Any, ...]] = []
    method_pair_counts: Dict[str, int] = {}

    for method in methods:
        bank_priors = _load_bank_priors(
            bits=prior_bank_bits,
            method=method,
            limit=prior_limit,
        ) if prior_bank_bits and prior_limit > 0 else []

        base_pairs: List[SeedPair] = []
        base_pairs.extend(priors or [])
        base_pairs.extend(bank_priors)
        base_pairs.extend(_grid_seed_pairs(
            seed_start=seed_start,
            seed_end=seed_end,
            c_start=c_start,
            c_end=c_end,
        ))

        if random_samples > 0:
            base_pairs.extend(_random_seed_pairs(
                sample_count=random_samples,
                seed_min=random_seed_min,
                seed_max=random_seed_max,
                c_min=random_c_min,
                c_max=random_c_max,
                rng_seed=rng_seed + (17 if method == "brent" else 0),
            ))

        pairs = _dedupe_pairs(base_pairs)
        method_pair_counts[method] = len(pairs)

        for chunk_index, chunk in enumerate(_chunk_list(pairs, chunk_size)):
            all_jobs.append((n, method, chunk_index, chunk, max_steps))

    hits: List[Dict[str, Any]] = []
    attempts = 0
    total_checks = 0
    completed_chunks = 0

    initial_report = _make_partial_report(
        n=n,
        prefer=prefer,
        seed_range=[seed_start, seed_end],
        c_range=[c_start, c_end],
        max_steps=max_steps,
        attempts=0,
        total_checks=0,
        elapsed_ms=0.0,
        hits=[],
        done=False,
        methods_run=methods,
    )
    initial_report["method_pair_counts"] = method_pair_counts
    initial_report["job_count"] = len(all_jobs)

    if save_partial:
        _write_json(out_path, initial_report)

    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_run_chunk_worker, job) for job in all_jobs]

        for fut in as_completed(futures):
            row = fut.result()
            completed_chunks += 1
            attempts += int(row.get("attempts") or 0)
            total_checks += int(row.get("checks") or 0)

            if row.get("verified"):
                hit = {
                    "prefer": row.get("prefer"),
                    "seed": row.get("seed"),
                    "c": row.get("c"),
                    "factor": row.get("factor"),
                    "cofactor": row.get("cofactor"),
                    "checks": row.get("checks"),
                    "elapsed_ms": row.get("elapsed_ms"),
                    "chunk_index": row.get("chunk_index"),
                    "method": row.get("method"),
                }
                hits.append(hit)

            elapsed_ms = (perf_counter() - started) * 1000

            if progress_every and completed_chunks % progress_every == 0:
                print(json.dumps({
                    "event": "prior_discovery_progress",
                    "prefer": prefer,
                    "methods_run": methods,
                    "completed_chunks": completed_chunks,
                    "total_chunks": len(all_jobs),
                    "attempts": attempts,
                    "total_checks": total_checks,
                    "hit_count": len(hits),
                    "elapsed_ms": round(elapsed_ms, 6),
                }), flush=True)

            if save_partial:
                partial = _make_partial_report(
                    n=n,
                    prefer=prefer,
                    seed_range=[seed_start, seed_end],
                    c_range=[c_start, c_end],
                    max_steps=max_steps,
                    attempts=attempts,
                    total_checks=total_checks,
                    elapsed_ms=elapsed_ms,
                    hits=hits,
                    done=False,
                    methods_run=methods,
                )
                partial["method_pair_counts"] = method_pair_counts
                partial["completed_chunks"] = completed_chunks
                partial["total_chunks"] = len(all_jobs)
                _write_json(out_path, partial)

            if hits and stop_after_first:
                for pending in futures:
                    pending.cancel()
                break

    elapsed_ms = (perf_counter() - started) * 1000

    report = _make_partial_report(
        n=n,
        prefer=prefer,
        seed_range=[seed_start, seed_end],
        c_range=[c_start, c_end],
        max_steps=max_steps,
        attempts=attempts,
        total_checks=total_checks,
        elapsed_ms=elapsed_ms,
        hits=hits,
        done=True,
        methods_run=methods,
    )
    report["method_pair_counts"] = method_pair_counts
    report["completed_chunks"] = completed_chunks
    report["total_chunks"] = len(all_jobs)
    report["workers"] = workers
    report["chunk_size"] = chunk_size
    report["prior_bank_bits"] = prior_bank_bits
    report["prior_limit"] = prior_limit
    report["random_samples"] = random_samples

    _write_json(out_path, report)

    if add_to_bank and report.get("best_hit"):
        _add_best_hit_to_bank(
            report=report,
            bits=bank_bits or prior_bank_bits or "",
            source=bank_source,
        )

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SQI semiprime seed/c prior discovery diagnostic"
    )

    parser.add_argument("n", type=int)
    parser.add_argument("--prefer", choices=["pollard", "brent", "both"], default="both")
    parser.add_argument("--seed-start", type=int, default=1)
    parser.add_argument("--seed-end", type=int, default=10000)
    parser.add_argument("--c-start", type=int, default=1)
    parser.add_argument("--c-end", type=int, default=128)
    parser.add_argument("--max-steps", type=int, default=500000)

    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--chunk-size", type=int, default=32)
    parser.add_argument("--exhaustive", action="store_true")
    parser.add_argument("--progress-every", type=int, default=0)
    parser.add_argument("--save-partial", action="store_true")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--out-suffix", type=str, default="")

    parser.add_argument("--priors", type=str, default="")
    parser.add_argument("--prior-bank-bits", "--prior-bits", dest="prior_bank_bits", type=str, default="")
    parser.add_argument("--prior-limit", type=int, default=0)

    parser.add_argument("--random-samples", type=int, default=0)
    parser.add_argument("--random-seed-min", type=int, default=1)
    parser.add_argument("--random-seed-max", type=int, default=2_000_000)
    parser.add_argument("--random-c-min", type=int, default=1)
    parser.add_argument("--random-c-max", type=int, default=4096)
    parser.add_argument("--rng-seed", type=int, default=20260509)

    parser.add_argument("--add-to-bank", action="store_true")
    parser.add_argument("--bank-bits", type=str, default="")
    parser.add_argument("--bank-source", type=str, default="prior_discovery_lab")

    parser.add_argument("--json", action="store_true")

    args = parser.parse_args()

    report = run_prior_discovery_lab(
        args.n,
        prefer=args.prefer,
        seed_start=args.seed_start,
        seed_end=args.seed_end,
        c_start=args.c_start,
        c_end=args.c_end,
        max_steps=args.max_steps,
        workers=args.workers,
        chunk_size=args.chunk_size,
        stop_after_first=not args.exhaustive,
        progress_every=args.progress_every,
        save_partial=args.save_partial,
        out_dir=args.out_dir,
        out_suffix=args.out_suffix,
        priors=parse_seed_priors(args.priors),
        prior_bank_bits=args.prior_bank_bits or None,
        prior_limit=args.prior_limit,
        random_samples=args.random_samples,
        random_seed_min=args.random_seed_min,
        random_seed_max=args.random_seed_max,
        random_c_min=args.random_c_min,
        random_c_max=args.random_c_max,
        rng_seed=args.rng_seed,
        add_to_bank=args.add_to_bank,
        bank_bits=args.bank_bits or None,
        bank_source=args.bank_source,
    )

    if args.json:
        print(json.dumps({
            "n": report["n"],
            "verified": report["verified"],
            "hit_count": report["hit_count"],
            "best_hit": report["best_hit"],
            "elapsed_ms": report["elapsed_ms"],
            "attempts": report["attempts"],
            "total_checks": report["total_checks"],
            "methods_run": report["methods_run"],
            "seed_range": report["seed_range"],
            "c_range": report["c_range"],
            "max_steps": report["max_steps"],
            "report_path": str(_report_path(args.out_dir, args.out_suffix)),
        }, indent=2, sort_keys=True))
    else:
        print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
