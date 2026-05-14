from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from time import time
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_BANK_PATH = Path("benchmarks/sqi_semiprime_lab/prior_bank/semiprime_prior_bank.json")


@dataclass(frozen=True)
class PriorBankEntry:
    bits: str
    p_bits: int
    q_bits: int
    n: int
    factor: int
    cofactor: int
    method: str
    seed: int
    c: int
    checks: int
    elapsed_ms: Optional[float] = None
    source: str = "manual"
    created_ts: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        row = asdict(self)
        if not row["created_ts"]:
            row["created_ts"] = time()
        return row


def bit_pair_from_factor_pair(factor: int, cofactor: int) -> Tuple[int, int]:
    a = int(factor).bit_length()
    b = int(cofactor).bit_length()
    return (min(a, b), max(a, b))


def bits_label(p_bits: int, q_bits: int) -> str:
    return f"{int(p_bits)}x{int(q_bits)}"


def _entry_key(row: Dict[str, Any]) -> str:
    return "|".join(
        [
            str(row.get("bits")),
            str(row.get("method")),
            str(row.get("seed")),
            str(row.get("c")),
            str(row.get("factor")),
            str(row.get("cofactor")),
        ]
    )


def load_prior_bank(path: Path = DEFAULT_BANK_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {
            "type": "semiprime_prior_bank",
            "version": 1,
            "entries": [],
            "summary": {},
        }

    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("type", "semiprime_prior_bank")
    data.setdefault("version", 1)
    data.setdefault("entries", [])
    data.setdefault("summary", {})
    return data


def summarize_prior_bank(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_bits: Dict[str, List[Dict[str, Any]]] = {}

    for row in entries:
        by_bits.setdefault(str(row.get("bits")), []).append(row)

    tiers: Dict[str, Dict[str, Any]] = {}

    for bits, rows in sorted(by_bits.items()):
        checks = [int(r.get("checks") or 0) for r in rows if r.get("checks") is not None]
        methods: Dict[str, int] = {}
        seeds: Dict[str, int] = {}

        for r in rows:
            methods[str(r.get("method"))] = methods.get(str(r.get("method")), 0) + 1
            prior = f'{r.get("seed")}:{r.get("c")}'
            seeds[prior] = seeds.get(prior, 0) + 1

        ranked_priors = sorted(
            rows,
            key=lambda r: (
                int(r.get("checks") or 10**30),
                float(r.get("elapsed_ms") or 10**30),
                int(r.get("seed") or 10**30),
                int(r.get("c") or 10**30),
            ),
        )

        tiers[bits] = {
            "entry_count": len(rows),
            "method_counts": methods,
            "prior_counts": seeds,
            "best_prior": {
                "seed": ranked_priors[0].get("seed"),
                "c": ranked_priors[0].get("c"),
                "method": ranked_priors[0].get("method"),
                "checks": ranked_priors[0].get("checks"),
                "elapsed_ms": ranked_priors[0].get("elapsed_ms"),
            }
            if ranked_priors
            else None,
            "median_checks": median(checks) if checks else None,
            "min_checks": min(checks) if checks else None,
            "max_checks": max(checks) if checks else None,
        }

    return {
        "entry_count": len(entries),
        "bits": sorted(by_bits.keys()),
        "tiers": tiers,
        "updated_ts": time(),
    }


def save_prior_bank(bank: Dict[str, Any], path: Path = DEFAULT_BANK_PATH) -> Dict[str, Any]:
    entries = list(bank.get("entries") or [])

    deduped: Dict[str, Dict[str, Any]] = {}
    for row in entries:
        deduped[_entry_key(row)] = row

    bank["entries"] = list(deduped.values())
    bank["summary"] = summarize_prior_bank(bank["entries"])

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bank, indent=2, sort_keys=True), encoding="utf-8")
    return bank


def add_prior_entry(
    *,
    n: int,
    factor: int,
    cofactor: int,
    method: str,
    seed: int,
    c: int,
    checks: int,
    elapsed_ms: Optional[float] = None,
    source: str = "manual",
    path: Path = DEFAULT_BANK_PATH,
) -> Dict[str, Any]:
    if factor <= 1 or cofactor <= 1:
        raise ValueError("factor and cofactor must be > 1")

    if factor * cofactor != n:
        raise ValueError("factor * cofactor does not equal n")

    p_bits, q_bits = bit_pair_from_factor_pair(factor, cofactor)

    entry = PriorBankEntry(
        bits=bits_label(p_bits, q_bits),
        p_bits=p_bits,
        q_bits=q_bits,
        n=int(n),
        factor=int(factor),
        cofactor=int(cofactor),
        method=str(method),
        seed=int(seed),
        c=int(c),
        checks=int(checks),
        elapsed_ms=elapsed_ms,
        source=str(source),
        created_ts=time(),
    ).to_dict()

    bank = load_prior_bank(path)
    bank.setdefault("entries", []).append(entry)
    return save_prior_bank(bank, path)


def rank_priors_for_bits(
    bits: str,
    *,
    method: Optional[str] = None,
    limit: int = 8,
    path: Path = DEFAULT_BANK_PATH,
) -> List[Tuple[int, int]]:
    bank = load_prior_bank(path)

    rows = [
        r
        for r in bank.get("entries", [])
        if str(r.get("bits")) == str(bits)
        and (method is None or str(r.get("method")) == str(method))
    ]

    rows.sort(
        key=lambda r: (
            int(r.get("checks") or 10**30),
            float(r.get("elapsed_ms") or 10**30),
            int(r.get("seed") or 10**30),
            int(r.get("c") or 10**30),
        )
    )

    priors: List[Tuple[int, int]] = []
    seen = set()

    for r in rows:
        pair = (int(r["seed"]), int(r["c"]))
        if pair not in seen:
            priors.append(pair)
            seen.add(pair)
        if len(priors) >= limit:
            break

    return priors


def parse_prior_hit_json(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts either:
      - prior discovery JSON with best_hit
      - qwave benchmark JSON with factor/cofactor/trace_tail
    """
    if payload.get("best_hit"):
        hit = payload["best_hit"]
        return {
            "n": int(payload["n"]) if payload.get("n") else None,
            "factor": int(hit["factor"]),
            "cofactor": int(hit["cofactor"]),
            "method": str(hit.get("prefer") or hit.get("method") or "pollard"),
            "seed": int(hit["seed"]),
            "c": int(hit["c"]),
            "checks": int(hit["checks"]),
            "elapsed_ms": payload.get("elapsed_ms"),
            "source": "prior_discovery",
        }

    if payload.get("verified") and payload.get("factor") and payload.get("cofactor"):
        seed = None
        c = None

        for row in reversed(payload.get("trace_tail") or []):
            if row.get("seed") is not None and row.get("c") is not None:
                seed = row.get("seed")
                c = row.get("c")
                break

        if seed is None or c is None:
            raise ValueError("verified qwave payload did not include seed/c in trace_tail")

        method = str(payload.get("method") or "pollard")
        method = method.replace("parallel_qwave_", "")

        return {
            "n": int(payload["n"]),
            "factor": int(payload["factor"]),
            "cofactor": int(payload["cofactor"]),
            "method": method,
            "seed": int(seed),
            "c": int(c),
            "checks": int(payload.get("checks") or 0),
            "elapsed_ms": payload.get("elapsed_ms"),
            "source": "qwave_benchmark",
        }

    raise ValueError("unsupported prior hit payload")


def add_from_json_file(
    json_path: Path,
    *,
    n_override: Optional[int] = None,
    bank_path: Path = DEFAULT_BANK_PATH,
) -> Dict[str, Any]:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    parsed = parse_prior_hit_json(payload)

    n = parsed.get("n") or n_override
    if n is None:
        raise ValueError("n missing from JSON payload; pass --n")

    return add_prior_entry(
        n=int(n),
        factor=int(parsed["factor"]),
        cofactor=int(parsed["cofactor"]),
        method=str(parsed["method"]),
        seed=int(parsed["seed"]),
        c=int(parsed["c"]),
        checks=int(parsed["checks"]),
        elapsed_ms=parsed.get("elapsed_ms"),
        source=str(parsed["source"]),
        path=bank_path,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="SQI semiprime prior bank")
    sub = parser.add_subparsers(dest="cmd", required=True)

    add = sub.add_parser("add", help="Add one verified prior")
    add.add_argument("--n", type=int, required=True)
    add.add_argument("--factor", type=int, required=True)
    add.add_argument("--cofactor", type=int, required=True)
    add.add_argument("--method", choices=["pollard", "brent", "parallel_qwave_pollard", "parallel_qwave_brent"], required=True)
    add.add_argument("--seed", type=int, required=True)
    add.add_argument("--c", type=int, required=True)
    add.add_argument("--checks", type=int, required=True)
    add.add_argument("--elapsed-ms", type=float, default=None)
    add.add_argument("--source", type=str, default="manual")
    add.add_argument("--bank", type=Path, default=DEFAULT_BANK_PATH)

    add_json = sub.add_parser("add-json", help="Add one verified prior from JSON output")
    add_json.add_argument("json_path", type=Path)
    add_json.add_argument("--n", type=int, default=None)
    add_json.add_argument("--bank", type=Path, default=DEFAULT_BANK_PATH)

    rank = sub.add_parser("rank", help="Rank priors for bit family")
    rank.add_argument("--bits", type=str, required=True)
    rank.add_argument("--method", type=str, default=None)
    rank.add_argument("--limit", type=int, default=8)
    rank.add_argument("--bank", type=Path, default=DEFAULT_BANK_PATH)

    summary = sub.add_parser("summary", help="Print bank summary")
    summary.add_argument("--bank", type=Path, default=DEFAULT_BANK_PATH)

    args = parser.parse_args()

    if args.cmd == "add":
        bank = add_prior_entry(
            n=args.n,
            factor=args.factor,
            cofactor=args.cofactor,
            method=args.method,
            seed=args.seed,
            c=args.c,
            checks=args.checks,
            elapsed_ms=args.elapsed_ms,
            source=args.source,
            path=args.bank,
        )
        print(json.dumps(bank["summary"], indent=2, sort_keys=True))
        return

    if args.cmd == "add-json":
        bank = add_from_json_file(args.json_path, n_override=args.n, bank_path=args.bank)
        print(json.dumps(bank["summary"], indent=2, sort_keys=True))
        return

    if args.cmd == "rank":
        priors = rank_priors_for_bits(
            args.bits,
            method=args.method,
            limit=args.limit,
            path=args.bank,
        )
        print(",".join(f"{seed}:{c}" for seed, c in priors))
        return

    if args.cmd == "summary":
        bank = load_prior_bank(args.bank)
        bank = save_prior_bank(bank, args.bank)
        print(json.dumps(bank["summary"], indent=2, sort_keys=True))
        return


if __name__ == "__main__":
    main()
