#!/usr/bin/env python3
import gzip
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class Tree:
    kind: str  # "leaf" | "node"
    left: Optional["Tree"] = None
    right: Optional["Tree"] = None
    value: Optional[int] = None


def make_chain(n_leaves: int) -> Tree:
    assert n_leaves >= 1
    t = Tree(kind="leaf", value=0)
    for i in range(1, n_leaves):
        t = Tree(kind="node", left=t, right=Tree(kind="leaf", value=i))
    return t


def make_balanced(n_leaves: int) -> Tree:
    assert n_leaves >= 1
    leaves = [Tree(kind="leaf", value=i) for i in range(n_leaves)]
    while len(leaves) > 1:
        nxt = []
        it = iter(leaves)
        for a in it:
            b = next(it, None)
            if b is None:
                nxt.append(a)
            else:
                nxt.append(Tree(kind="node", left=a, right=b))
        leaves = nxt
    return leaves[0]


def count_nodes(t: Tree) -> int:
    if t.kind == "leaf":
        return 1
    return 1 + count_nodes(t.left) + count_nodes(t.right)  # type: ignore[arg-type]


def count_edges(t: Tree) -> int:
    if t.kind == "leaf":
        return 0
    return 2 + count_edges(t.left) + count_edges(t.right)  # type: ignore[arg-type]


def to_native_ast(t: Tree) -> Dict[str, Any]:
    if t.kind == "leaf":
        return {"op": "v", "x": t.value}
    return {"op": "interf", "a": to_native_ast(t.left), "b": to_native_ast(t.right)}  # type: ignore[arg-type]


def to_tagged_ast(t: Tree, phase: str = "P") -> Dict[str, Any]:
    """
    Tagged model: attach a phase tag around every internal node.
    This corresponds to “≤ 1 tag per node” (tighter than per-edge tagging).
    """
    if t.kind == "leaf":
        return {"op": "v", "x": t.value}
    inner = {"op": "interf", "a": to_tagged_ast(t.left, phase), "b": to_tagged_ast(t.right, phase)}  # type: ignore[arg-type]
    return {"op": "tag", "ph": phase, "child": inner}


def json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def gz_bytes(b: bytes) -> bytes:
    return gzip.compress(b, compresslevel=9)


def bench_one(name: str, t: Tree) -> Tuple[str, int, int, int, int, int, int]:
    n = count_nodes(t)
    e = count_edges(t)

    native = to_native_ast(t)
    tagged = to_tagged_ast(t)

    b_native = json_bytes(native)
    b_tagged = json_bytes(tagged)

    g_native = gz_bytes(b_native)
    g_tagged = gz_bytes(b_tagged)

    return (name, n, e, len(b_native), len(b_tagged), len(g_native), len(g_tagged))


def main() -> None:
    sizes = [8, 16, 32, 64, 128, 256, 512]
    rows = []
    for n in sizes:
        rows.append(bench_one(f"chain-{n}", make_chain(n)))
        rows.append(bench_one(f"bal-{n}", make_balanced(n)))

    print("case,nodes,edges,json_native,json_tagged,gz_native,gz_tagged,tagged/json_ratio,tagged/gz_ratio")
    for (name, nodes, edges, jn, jt, gn, gt) in rows:
        rj = jt / max(1, jn)
        rg = gt / max(1, gn)
        print(f"{name},{nodes},{edges},{jn},{jt},{gn},{gt},{rj:.4f},{rg:.4f}")

    print("\nStructural sanity (1 tag per internal node => tagged_items <= 2*nodes):")
    for (name, nodes, _, _, _, _, _) in rows:
        print(f"{name}: nodes={nodes} => 2*nodes={2*nodes}")


if __name__ == "__main__":
    main()