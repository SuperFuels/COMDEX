import json
import gzip
from dataclasses import dataclass
from typing import List, Union
import hashlib

# -----------------------------
# Expr model (mirror Lean)
# -----------------------------

@dataclass(frozen=True)
class Leaf:
    i: int

@dataclass(frozen=True)
class Node:
    children: List["Expr"]

Expr = Union[Leaf, Node]


def gz_len(b: bytes) -> int:
    return len(gzip.compress(b, compresslevel=9))


def stable_u32(seed: int, x: int) -> int:
    # deterministic pseudo-random-ish 32-bit integer from (seed, x)
    h = hashlib.sha256(f"{seed}:{x}".encode("utf-8")).digest()
    return int.from_bytes(h[:4], "little")


def make_subtree(depth: int, fanout: int, seed: int, counter: int = 0) -> Expr:
    """
    Deterministic high-entropy-ish subtree: leaves carry hashed labels so gzip
    can't trivially collapse duplicates inside S itself.
    """
    if depth <= 0:
        return Leaf(stable_u32(seed, counter))
    children = []
    # advance counter deterministically across the tree
    base = counter * (fanout + 1) + 1
    for j in range(fanout):
        children.append(make_subtree(depth - 1, fanout, seed, base + j))
    return Node(children)


def tree_json(e: Expr):
    # tree-only encoding: fully expanded structure
    if isinstance(e, Leaf):
        return {"v": e.i}
    return {"n": [tree_json(c) for c in e.children]}


def family_tree(S: Expr, k: int) -> Expr:
    return Node([S for _ in range(k)])


def dag_canonical_json(S: Expr, k: int):
    """
    "DAG" canonical encoding: ship S once, and a list of k references.
    This is intentionally minimal and mirrors what stream interning achieves.
    """
    return {"S": tree_json(S), "refs": k}


def bench(max_k_pow: int = 12, depth: int = 6, fanout: int = 2, seed: int = 1337):
    """
    k = 2^p for p=0..max_k_pow, so up to 4096 by default.
    """
    print("=== ✅ Bridge Benchmark v16: DAG reuse vs tree duplication ===")
    print(f"subtree: depth={depth}, fanout={fanout}, seed={seed}")
    print("k | canon_raw | canon_gz | tree_raw | tree_gz | gz_ratio(tree/canon)")
    print("--|----------:|---------:|---------:|--------:|--------------------:")

    S = make_subtree(depth=depth, fanout=fanout, seed=seed)

    for p in range(0, max_k_pow + 1):
        k = 1 << p

        canon = json.dumps(dag_canonical_json(S, k), separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        tree  = json.dumps(tree_json(family_tree(S, k)), separators=(",", ":"), ensure_ascii=False).encode("utf-8")

        canon_raw, canon_gz = len(canon), gz_len(canon)
        tree_raw, tree_gz   = len(tree), gz_len(tree)

        ratio = (tree_gz / canon_gz) if canon_gz else float("inf")
        print(f"{k:4d} | {canon_raw:9d} | {canon_gz:8d} | {tree_raw:8d} | {tree_gz:7d} | {ratio:20.2f}")


if __name__ == "__main__":
    bench()
