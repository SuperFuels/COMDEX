#!/usr/bin/env python3
import gzip
import json
from dataclasses import dataclass
from typing import Any, Union

@dataclass
class Atom:
    k: int

@dataclass
class Inter:
    phi: int
    a: "Expr"
    b: "Expr"

Expr = Union[Atom, Inter]

def family(n: int) -> Expr:
    e: Expr = Atom(0)
    for i in range(n):
        e = Inter(i, e, Atom(i + 1))
    return e

def enc_canon(e: Expr) -> Any:
    if isinstance(e, Atom):
        return ["a", e.k]
    return ["i", e.phi, enc_canon(e.a), enc_canon(e.b)]

def enc_tagged(e: Expr) -> Any:
    if isinstance(e, Atom):
        return ["a", e.k]
    return ["and", ["phase", e.phi], ["and", enc_tagged(e.a), enc_tagged(e.b)]]

def js_bytes(obj: Any) -> bytes:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def gz_len(b: bytes) -> int:
    return len(gzip.compress(b, compresslevel=9))

def main() -> None:
    print("=== ✅ Bridge Benchmark v17: Phase-interference tag bloat vs native operator ===")
    print("family: inter(phi) chain over atoms 0..n")
    print()
    print(f"{'n':>4}  {'canon_raw':>10}  {'canon_gz':>8}  {'tagged_raw':>11}  {'tagged_gz':>9}  {'gz_ratio':>8}")
    print(f"{'-'*4}  {'-'*10}  {'-'*8}  {'-'*11}  {'-'*9}  {'-'*8}")

    for n in [1, 2, 4, 8, 16, 32, 64, 128, 256]:
        e = family(n)
        canon_b = js_bytes(enc_canon(e))
        tag_b = js_bytes(enc_tagged(e))
        canon_gz = gz_len(canon_b)
        tag_gz = gz_len(tag_b)
        ratio = tag_gz / canon_gz if canon_gz else float("inf")
        print(f"{n:>4}  {len(canon_b):>10}  {canon_gz:>8}  {len(tag_b):>11}  {tag_gz:>9}  {ratio:>8.2f}")

if __name__ == "__main__":
    main()
