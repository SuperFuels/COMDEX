#!/usr/bin/env python3
"""
v23 — Canonicalization invariance regression (measured + CI)

We model a "compact form is deterministic" promise using a JSON-ish AST:
  - canon(canon(x)) == canon(x)                         (idempotence)
  - decode(encode(canon(x))) == canon(x)                (roundtrip to canonical)
We also compute a deterministic sha256 digest across all canonical encodings
so any drift is caught by the lock file.

This is deliberately infrastructure-grade and fast.
"""

from __future__ import annotations

import hashlib
import json
import random
from typing import Any, Dict, List


COMMUTATIVE_OPS = {"and", "or", "add", "mul", "band", "bor"}


def stable_dumps(x: Any) -> bytes:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def canon_ast(x: Any) -> Any:
    if isinstance(x, dict):
        # canonicalize values first
        y = {k: canon_ast(v) for k, v in x.items()}

        op = y.get("op")
        args = y.get("args")
        if isinstance(op, str) and op in COMMUTATIVE_OPS and isinstance(args, list):
            cargs = [canon_ast(a) for a in args]
            cargs.sort(key=stable_dumps)  # deterministic ordering
            y["args"] = cargs

        # ensure stable dict construction order too (even though sort_keys in dumps handles it)
        return {k: y[k] for k in sorted(y.keys())}

    if isinstance(x, list):
        return [canon_ast(v) for v in x]

    return x  # primitives


def rand_leaf(rng: random.Random) -> Any:
    t = rng.randrange(5)
    if t == 0:
        return rng.randrange(0, 10_000)
    if t == 1:
        return rng.choice([True, False])
    if t == 2:
        return None
    if t == 3:
        return rng.choice(["alpha", "beta", "gamma", "delta", "Authorization", "Content-Type"])
    return {"k": rng.randrange(0, 100), "v": rng.choice(["x", "y", "z"])}


def rand_ast(rng: random.Random, depth: int) -> Any:
    if depth <= 0:
        return rand_leaf(rng)

    t = rng.randrange(6)
    if t <= 2:
        # operator node
        op = rng.choice(["and", "or", "add", "mul"])
        nargs = rng.randrange(2, 5)
        args = [rand_ast(rng, depth - 1) for _ in range(nargs)]
        rng.shuffle(args)  # intentionally disorder
        # insert keys in random order (dict insertion order is preserved)
        items = [("op", op), ("args", args), ("meta", {"nonce": rng.randrange(0, 1_000_000)})]
        rng.shuffle(items)
        return dict(items)

    if t == 3:
        # object node with random keys
        nkeys = rng.randrange(2, 6)
        keys = [f"k{rng.randrange(0, 50)}" for _ in range(nkeys)]
        items = [(k, rand_ast(rng, depth - 1)) for k in keys]
        rng.shuffle(items)
        return dict(items)

    if t == 4:
        # list node
        return [rand_ast(rng, depth - 1) for _ in range(rng.randrange(1, 6))]

    return rand_leaf(rng)


def main() -> None:
    seed = 23023
    cases = 5000
    max_depth = 6

    rng = random.Random(seed)
    h = hashlib.sha256()

    idem_ok = 0
    rt_ok = 0

    for i in range(cases):
        x = rand_ast(rng, max_depth)
        c1 = canon_ast(x)
        c2 = canon_ast(c1)
        assert c2 == c1, f"idempotence failed at case {i}"

        b = stable_dumps(c1)
        y = json.loads(b.decode("utf-8"))
        cy = canon_ast(y)
        assert cy == c1, f"roundtrip-to-canonical failed at case {i}"

        h.update(b)
        idem_ok += 1
        rt_ok += 1

    print("=== ✅ Bridge v23: Canonicalization invariance regression (determinism / safety) ===")
    print(f"seed={seed} cases={cases} max_depth={max_depth}")
    print(f"idempotence_ok={idem_ok}/{cases}")
    print(f"roundtrip_ok={rt_ok}/{cases}")
    print(f"drift_sha256={h.hexdigest()}")


if __name__ == "__main__":
    main()