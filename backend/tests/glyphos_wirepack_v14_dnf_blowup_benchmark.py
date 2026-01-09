import json
import gzip
from dataclasses import dataclass
from typing import List, Union

# ---------- Boolean family matching the Lean file ----------

@dataclass(frozen=True)
class Top: pass

@dataclass(frozen=True)
class Var:
    i: int

@dataclass(frozen=True)
class And:
    a: "Form"
    b: "Form"

@dataclass(frozen=True)
class Or:
    a: "Form"
    b: "Form"

Form = Union[Top, Var, And, Or]

def pair(i: int) -> Form:
    return Or(Var(2*i), Var(2*i + 1))

def fam(n: int) -> Form:
    f: Form = Top()
    for i in range(n):
        f = And(f, pair(i))
    return f

def dnf_terms(f: Form) -> List[List[int]]:
    """DNF as list of conjunction terms; sufficient to demonstrate blow-up."""
    if isinstance(f, Top):
        return [[]]
    if isinstance(f, Var):
        return [[f.i]]
    if isinstance(f, Or):
        return dnf_terms(f.a) + dnf_terms(f.b)
    if isinstance(f, And):
        xs = dnf_terms(f.a)
        ys = dnf_terms(f.b)
        out: List[List[int]] = []
        for x in xs:
            for y in ys:
                out.append(x + y)
        return out
    raise TypeError(f"unknown form: {type(f)}")

def canonical_tree_json(f: Form):
    """A compact canonical tree form (nested operators)."""
    if isinstance(f, Top):
        return {"T": []}
    if isinstance(f, Var):
        return {"v": f.i}
    if isinstance(f, Or):
        return {"or": [canonical_tree_json(f.a), canonical_tree_json(f.b)]}
    if isinstance(f, And):
        return {"and": [canonical_tree_json(f.a), canonical_tree_json(f.b)]}
    raise TypeError(type(f))

def gz_len(b: bytes) -> int:
    return len(gzip.compress(b, compresslevel=9))

def bench(max_n: int = 18):
    print("=== ✅ Bridge Benchmark v14: DNF blowup vs canonical tree ===")
    print("n | terms(DNF) | canon_raw | canon_gz | dnf_raw | dnf_gz | gz_ratio(dnf/canon)")
    print("--|-----------:|----------:|---------:|--------:|-------:|-------------------:")
    for n in range(1, max_n + 1):
        f = fam(n)
        canon = json.dumps(canonical_tree_json(f), separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        terms = dnf_terms(f)
        dnfj = json.dumps({"dnf": terms}, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

        canon_raw, canon_gz = len(canon), gz_len(canon)
        dnf_raw, dnf_gz = len(dnfj), gz_len(dnfj)
        ratio = (dnf_gz / canon_gz) if canon_gz else float("inf")

        print(f"{n:2d} | {len(terms):10d} | {canon_raw:9d} | {canon_gz:8d} | {dnf_raw:7d} | {dnf_gz:6d} | {ratio:19.2f}")

if __name__ == "__main__":
    bench()
