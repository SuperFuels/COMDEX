from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List

from backend.modules.sqi.factor.semiprime_tier_generator import generate_semiprime


OUT_DIR = Path("benchmarks/sqi_semiprime_lab/tier_transfer")


def _run_qwave_cli(
    *,
    n: int,
    prior_bits: str,
    prior_limit: int,
    beam_count: int,
    seeds_per_beam: int,
    max_steps: int,
    prefer: str,
) -> Dict[str, Any]:
    cmd = [
        sys.executable,
        "backend/modules/sqi/factor/qwave_parallel_factor_beams.py",
        str(n),
        "--beam-count", str(beam_count),
        "--seeds-per-beam", str(seeds_per_beam),
        "--max-steps", str(max_steps),
        "--prefer", prefer,
        "--use-prior-bank",
        "--prior-bits", prior_bits,
        "--prior-limit", str(prior_limit),
        "--json",
    ]

    proc = subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={"PYTHONPATH": ".", **__import__("os").environ},
    )

    text = proc.stdout.strip()

    # Find final JSON object in noisy SQI/GHX output.
    start = text.rfind("\n{")
    if start >= 0:
        raw = text[start + 1 :]
    else:
        start = text.find("{")
        raw = text[start:] if start >= 0 else ""

    try:
        payload = json.loads(raw)
    except Exception:
        payload = {
            "verified": False,
            "factor": None,
            "cofactor": None,
            "checks": None,
            "elapsed_ms": None,
            "method": "parse_failed",
            "raw_tail": text[-4000:],
            "returncode": proc.returncode,
        }

    payload.setdefault("returncode", proc.returncode)
    return payload


def run_case(
    *,
    p_bits: int,
    q_bits: int,
    seed: int,
    prior_bits: str,
    prior_limit: int,
    beam_count: int,
    seeds_per_beam: int,
    max_steps: int,
    prefer: str,
) -> Dict[str, Any]:
    target = generate_semiprime(p_bits, q_bits, seed)
    n = int(target["n"])

    started = perf_counter()
    result = _run_qwave_cli(
        n=n,
        prior_bits=prior_bits,
        prior_limit=prior_limit,
        beam_count=beam_count,
        seeds_per_beam=seeds_per_beam,
        max_steps=max_steps,
        prefer=prefer,
    )
    elapsed_ms = (perf_counter() - started) * 1000.0

    factor = result.get("factor")
    verified = bool(factor and n % int(factor) == 0)

    return {
        "tier": f"{p_bits}x{q_bits}",
        "target": target,
        "prior_bits": prior_bits,
        "prior_limit": prior_limit,
        "beam_count": beam_count,
        "seeds_per_beam": seeds_per_beam,
        "max_steps": max_steps,
        "prefer": prefer,
        "elapsed_ms_outer": elapsed_ms,
        "result": result,
        "verified": verified,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiers", default="52x76,54x78,56x80")
    ap.add_argument("--cases", type=int, default=3)
    ap.add_argument("--seed-start", type=int, default=1000)
    ap.add_argument("--prior-bits", default="48x72")
    ap.add_argument("--prior-limit", type=int, default=4)
    ap.add_argument("--beam-count", type=int, default=4)
    ap.add_argument("--seeds-per-beam", type=int, default=8)
    ap.add_argument("--max-steps", type=int, default=100000)
    ap.add_argument("--prefer", choices=["pollard", "brent"], default="pollard")
    ap.add_argument("--out-suffix", default="48x72_transfer_probe")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    case_idx = 0

    for tier in args.tiers.split(","):
        tier = tier.strip()
        if not tier:
            continue

        left, right = tier.lower().split("x")
        p_bits, q_bits = int(left), int(right)

        for _ in range(args.cases):
            seed = args.seed_start + case_idx
            case_idx += 1

            row = run_case(
                p_bits=p_bits,
                q_bits=q_bits,
                seed=seed,
                prior_bits=args.prior_bits,
                prior_limit=args.prior_limit,
                beam_count=args.beam_count,
                seeds_per_beam=args.seeds_per_beam,
                max_steps=args.max_steps,
                prefer=args.prefer,
            )
            rows.append(row)

            print(json.dumps({
                "event": "tier_transfer_case",
                "tier": row["tier"],
                "seed": seed,
                "verified": row["verified"],
                "factor": row["result"].get("factor"),
                "checks": row["result"].get("checks"),
                "elapsed_ms": row["result"].get("elapsed_ms"),
                "method": row["result"].get("method"),
            }, sort_keys=True), flush=True)

    summary: Dict[str, Any] = {
        "prior_bits": args.prior_bits,
        "prior_limit": args.prior_limit,
        "prefer": args.prefer,
        "beam_count": args.beam_count,
        "seeds_per_beam": args.seeds_per_beam,
        "max_steps": args.max_steps,
        "case_count": len(rows),
        "verified_count": sum(1 for r in rows if r["verified"]),
        "tiers": {},
        "rows": rows,
    }

    for r in rows:
        bucket = summary["tiers"].setdefault(r["tier"], {"cases": 0, "verified": 0})
        bucket["cases"] += 1
        bucket["verified"] += int(bool(r["verified"]))

    out_path = OUT_DIR / f"tier_transfer_{args.out_suffix}.json"
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps({
        "event": "tier_transfer_summary",
        "out_path": str(out_path),
        "case_count": summary["case_count"],
        "verified_count": summary["verified_count"],
        "tiers": summary["tiers"],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
