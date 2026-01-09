#!/usr/bin/env python3
from __future__ import annotations

import gzip
import json
import math
import os
import time
from dataclasses import dataclass
from typing import List, Union, Dict, Any

# ----------------------------
# Boolean family + DNF expand
# ----------------------------

@dataclass(frozen=True)
class Top:
    pass

@dataclass(frozen=True)
class Var:
    i: int

@dataclass(frozen=True)
class And:
    a: "BExp"
    b: "BExp"

@dataclass(frozen=True)
class Or:
    a: "BExp"
    b: "BExp"

BExp = Union[Top, Var, And, Or]

def clause(i: int) -> BExp:
    return Or(Var(2*i), Var(2*i + 1))

def fam(n: int) -> BExp:
    e: BExp = Top()
    for k in range(n):
        e = And(e, clause(k))
    return e

def dnf_terms(e: BExp) -> List[List[int]]:
    """
    DNF terms as list-of-conjunctions; each conjunction is list of var IDs.
    top -> [[]]
    var -> [[i]]
    or  -> concat
    and -> cartesian product (blowup)
    """
    if isinstance(e, Top):
        return [[]]
    if isinstance(e, Var):
        return [[e.i]]
    if isinstance(e, Or):
        return dnf_terms(e.a) + dnf_terms(e.b)
    if isinstance(e, And):
        left = dnf_terms(e.a)
        right = dnf_terms(e.b)
        out: List[List[int]] = []
        for t1 in left:
            for t2 in right:
                out.append(t1 + t2)
        return out
    raise TypeError(e)

def canonical_tree_json(e: BExp) -> Any:
    """
    A compact canonical tree encoding (not GlyphOS yet; this is just to show linear growth).
    Replace with your real GlyphOS JSON wire if you want end-to-end.
    """
    if isinstance(e, Top):
        return {"⊤": []}
    if isinstance(e, Var):
        return {"v": e.i}
    if isinstance(e, Or):
        return {"∨": [canonical_tree_json(e.a), canonical_tree_json(e.b)]}
    if isinstance(e, And):
        return {"∧": [canonical_tree_json(e.a), canonical_tree_json(e.b)]}
    raise TypeError(e)

def as_bytes(obj: Any) -> bytes:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def gz_len(b: bytes) -> int:
    return len(gzip.compress(b, compresslevel=9))

# ----------------------------
# Benchmark
# ----------------------------

def main():
    # max_n=18 gives 2^18=262,144 terms, already huge; bump carefully.
    max_n = int(os.getenv("BLOWUP_N", "16"))
    print("\n=== ✅ Symatics Bridge Benchmark: Boolean DNF blowup vs Canonical Tree ===")
    print(f"Max n: {max_n}  (DNF terms = 2^n)\n")

    rows = []
    t0 = time.time()
    for n in range(1, max_n + 1):
        e = fam(n)

        # Expanded (forced) Boolean IR: explicit DNF
        terms = dnf_terms(e)
        expanded_ir = {"dnf": terms}  # mimic "expanded instruction stream"
        b_exp = as_bytes(expanded_ir)

        # Canonical tree (linear)
        tree = canonical_tree_json(e)
        b_can = as_bytes(tree)

        rows.append({
            "n": n,
            "dnf_terms": len(terms),
            "expanded_raw": len(b_exp),
            "expanded_gz": gz_len(b_exp),
            "canon_raw": len(b_can),
            "canon_gz": gz_len(b_can),
            "raw_ratio": (len(b_exp) / max(1, len(b_can))),
            "gz_ratio": (gz_len(b_exp) / max(1, gz_len(b_can))),
        })

        if n in (4, 8, 12, 16, max_n):
            r = rows[-1]
            print(
                f"n={n:2d} terms={r['dnf_terms']:<8d} "
                f"expanded_gz={r['expanded_gz']:<8d} canon_gz={r['canon_gz']:<6d} "
                f"ratio_gz={r['gz_ratio']:.1f}x"
            )

    dt = (time.time() - t0) * 1000.0
    last = rows[-1]

    print("\n--- Summary (last n) ---")
    print(f"n:                       {last['n']}")
    print(f"DNF terms:               {last['dnf_terms']} (= 2^n)")
    print(f"Expanded IR gzip (B):    {last['expanded_gz']}")
    print(f"Canonical tree gzip (B): {last['canon_gz']}")
    print(f"Gzip blowup ratio:       {last['gz_ratio']:.2f}x")
    print(f"Runtime:                 {dt:.1f} ms\n")

    out = {
        "max_n": max_n,
        "rows": rows,
        "notes": {
            "expanded_ir": "forced DNF expansion (representational blowup)",
            "canonical_tree": "linear AST (proxy for Symatics/GlyphOS canonical form)",
            "next_step": "replace canonical_tree_json with real GlyphOS wire + WirePack v10/v13 for investor-grade end-to-end numbers",
        },
    }
    os.makedirs("./benchmarks", exist_ok=True)
    path = "./benchmarks/symatics_bridge_boolean_blowup_latest.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Saved: {path}")

if __name__ == "__main__":
    main()
