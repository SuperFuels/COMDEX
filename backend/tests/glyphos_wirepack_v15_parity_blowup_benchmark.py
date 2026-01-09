#!/usr/bin/env python3

"""GlyphOS Bridge Benchmark v15: Parity (XOR) minterm blowup vs canonical tree.

Canonical form (compact): XOR-chain over (n+1) variables.
Boolean-expanded IR (blowup): full minterm DNF (truth-table DNF) for parity over (n+1) vars.

This mirrors the v14 harness output format:
  n | terms(DNF) | canon_raw | canon_gz | dnf_raw | dnf_gz | gz_ratio(dnf/canon)

It also writes:
  - glyphos_wirepack_v15_parity_blowup_results.json
  - glyphos_wirepack_v15_parity_blowup_results.md
"""

import argparse
import gzip
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Union


# ---------------- Canonical parity family (XOR-chain) ----------------

@dataclass(frozen=True)
class Var:
    i: int  # 0-based variable index


@dataclass(frozen=True)
class Xor:
    a: "Form"
    b: "Form"


Form = Union[Var, Xor]


def parity_chain(n: int) -> Form:
    """
    Return XOR-chain over vars 0..n (so (n+1) vars total).
    This matches the Lean file's `parity n`.
    """
    f: Form = Var(0)
    for i in range(1, n + 1):
        f = Xor(f, Var(i))
    return f


def canonical_tree_json(f: Form) -> Dict[str, Any]:
    if isinstance(f, Var):
        return {"v": f.i}
    if isinstance(f, Xor):
        return {"xor": [canonical_tree_json(f.a), canonical_tree_json(f.b)]}
    raise TypeError(type(f))


# ---------------- Boolean-expanded IR: minterm DNF for parity ----------------

def _popcount(x: int) -> int:
    return x.bit_count()


def parity_minterm_dnf_terms(n: int) -> List[List[int]]:
    """
    Full minterm DNF for parity over vars 0..n:
      one conjunction term per satisfying assignment (odd parity).
    Literals are encoded as signed ints:
      +(i+1) means var i is True
      -(i+1) means var i is False
    """
    m = n + 1
    out: List[List[int]] = []
    for mask in range(1 << m):
        if _popcount(mask) % 2 == 1:
            term: List[int] = []
            for i in range(m):
                bit = (mask >> i) & 1
                lit = (i + 1) if bit else -(i + 1)
                term.append(lit)
            out.append(term)
    return out


# ---------------- Utilities ----------------

def gz_len(b: bytes) -> int:
    return len(gzip.compress(b, compresslevel=9))


def sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def bench(max_n: int) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []

    print("=== ✅ Bridge Benchmark v15: Parity (XOR) minterm blowup vs canonical tree ===")
    print("n | terms(DNF) | canon_raw | canon_gz | dnf_raw | dnf_gz | gz_ratio(dnf/canon)")
    print("--|-----------:|----------:|---------:|--------:|-------:|-------------------:")

    for n in range(1, max_n + 1):
        f = parity_chain(n)
        canon_bytes = json.dumps(
            canonical_tree_json(f), separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")

        terms = parity_minterm_dnf_terms(n)
        dnf_bytes = json.dumps(
            {"dnf": terms}, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")

        canon_raw, canon_gz = len(canon_bytes), gz_len(canon_bytes)
        dnf_raw, dnf_gz = len(dnf_bytes), gz_len(dnf_bytes)
        ratio = (dnf_gz / canon_gz) if canon_gz else float("inf")

        print(f"{n:2d} | {len(terms):10d} | {canon_raw:9d} | {canon_gz:8d} | {dnf_raw:7d} | {dnf_gz:6d} | {ratio:19.2f}")

        rows.append(
            dict(
                n=n,
                terms=len(terms),
                canon_raw=canon_raw,
                canon_gz=canon_gz,
                dnf_raw=dnf_raw,
                dnf_gz=dnf_gz,
                gz_ratio=ratio,
                sha256_canon_json=sha256_bytes(canon_bytes),
                sha256_dnf_json=sha256_bytes(dnf_bytes),
            )
        )

    return {"max_n": max_n, "rows": rows}


def write_results(out_dir: Path, data: Dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "glyphos_wirepack_v15_parity_blowup_results.json"
    md_path = out_dir / "glyphos_wirepack_v15_parity_blowup_results.md"

    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # Markdown table
    lines: List[str] = []
    lines.append("# Bridge Benchmark v15: Parity (XOR) minterm blowup vs canonical tree\n")
    lines.append("n | terms(DNF) | canon_raw | canon_gz | dnf_raw | dnf_gz | gz_ratio(dnf/canon)\n")
    lines.append("--|-----------:|----------:|---------:|--------:|-------:|-------------------:\n")
    for r in data["rows"]:
        lines.append(
            f"{r['n']:2d} | {r['terms']:10d} | {r['canon_raw']:9d} | {r['canon_gz']:8d} | "
            f"{r['dnf_raw']:7d} | {r['dnf_gz']:6d} | {r['gz_ratio']:19.2f}\n"
        )

    # One-liner claim (investor-grade)
    last = data["rows"][-1]
    lines.append("\n**Investor-grade claim (v15):** ")
    lines.append(
        "We formally prove (Lean) a parity program family where Boolean minterm DNF materialization produces 2^n terms "
        "while the canonical XOR operator tree stays 1+2n nodes, and we empirically measure that the gzipped "
        f"Boolean-expanded IR becomes >{int(last['gz_ratio']):,}× larger than the gzipped canonical form by n={last['n']}.\n"
    )

    md_path.write_text("".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-n", type=int, default=18)
    ap.add_argument(
        "--out",
        type=str,
        default=".",
        help="output directory for results JSON/MD",
    )
    args = ap.parse_args()

    data = bench(args.max_n)
    write_results(Path(args.out), data)


if __name__ == "__main__":
    main()