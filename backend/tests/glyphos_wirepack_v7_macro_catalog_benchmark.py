# 📁 backend/tests/glyphos_wirepack_v7_macro_catalog_benchmark.py
from __future__ import annotations

import gzip
import json
import os
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

# ------------------------------------------------------------
# Same ops/tags as prior benchmarks
# ------------------------------------------------------------
OPS = {"↔", "⊕", "⟲", "->", "⧖"}
OP_TAG = {"↔": 1, "⊕": 2, "⟲": 3, "->": 4, "⧖": 5}

# ------------------------------------------------------------
# Generator (identical shape)
# ------------------------------------------------------------
def make_glyph_tree(depth_steps: int = 30) -> Dict[str, Any]:
    branch1 = {
        "⊕": [
            {"⊕": ["A1", "B1"]},
            {"⟲": ["A2", "B2"]},
        ]
    }

    subtree: Any = {"⟲": ["Z3", "Z4"]}
    subtree = {"->": [{"->": ["Z1", "Z2"]}, subtree]}

    for i in range(depth_steps):
        a = f"L{i}_1"
        b = f"L{i}_2"
        mod = i % 5
        if mod == 0:
            left = {"↔": [a, b]}
        elif mod == 1:
            left = {"⊕": [a, b]}
        elif mod == 2:
            left = {"⧖": [a, b]}
        elif mod == 3:
            left = {"⟲": [a, b]}
        else:
            left = {"->": [a, b]}
        subtree = {"->": [left, subtree]}

    return {"↔": [branch1, subtree]}

# ------------------------------------------------------------
# JSON + gzip helpers
# ------------------------------------------------------------
def to_wire_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=False).encode("utf-8")

def gzip_bytes(b: bytes, level: int = 9) -> bytes:
    return gzip.compress(b, compresslevel=level)

# ------------------------------------------------------------
# Fallback pack (v5-ish): arity=2 elision + varints
# ------------------------------------------------------------
def _varint(n: int) -> bytes:
    if n < 0:
        raise ValueError("varint expects non-negative")
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(0x80 | b)
        else:
            out.append(b)
            break
    return bytes(out)

def _encode_string_raw(s: str) -> bytes:
    b = s.encode("utf-8")
    return bytes([0x53]) + _varint(len(b)) + b  # 0x53 = 'S'

def _encode_node_v5(node: Any) -> bytes:
    if isinstance(node, str):
        return _encode_string_raw(node)

    if isinstance(node, dict):
        for op, v in node.items():
            tag = OP_TAG.get(op, 0)
            if tag == 0:
                raise ValueError(f"unknown op: {op}")
            children = v if isinstance(v, list) else [v]

            out = bytearray()
            out.append(0xD0)
            out.append(tag)

            # omit arity when == 2
            if len(children) != 2:
                out.append(0xA0)
                out += _varint(len(children))

            for ch in children:
                out += _encode_node_v5(ch)
            return bytes(out)

    if isinstance(node, list):
        out = bytearray()
        out.append(0xD0)
        out.append(OP_TAG["->"])
        out.append(0xA0)
        out += _varint(len(node))
        for ch in node:
            out += _encode_node_v5(ch)
        return bytes(out)

    return _encode_string_raw("null")

def to_glyphpack_fallback(tree: Any) -> bytes:
    return _encode_node_v5(tree)

# ------------------------------------------------------------
# v6 macro: guarded canonical grammar → 4 bytes payload
# ------------------------------------------------------------
_L_RE = re.compile(r"^L(\d+)_([12])$")

def _match_and_extract_depth(tree: Any) -> Tuple[bool, int]:
    """
    Returns (True, depth_steps) ONLY when the tree matches make_glyph_tree(depth_steps)
    exactly (shape + op-cycle + labels), otherwise (False, -1).
    """
    if not isinstance(tree, dict) or len(tree) != 1 or "↔" not in tree:
        return (False, -1)
    pair = tree["↔"]
    if not (isinstance(pair, list) and len(pair) == 2):
        return (False, -1)
    branch1, cur = pair[0], pair[1]

    # branch1 exact
    if not (isinstance(branch1, dict) and len(branch1) == 1 and "⊕" in branch1):
        return (False, -1)
    b1 = branch1["⊕"]
    if not (isinstance(b1, list) and len(b1) == 2):
        return (False, -1)
    if b1[0] != {"⊕": ["A1", "B1"]}:
        return (False, -1)
    if b1[1] != {"⟲": ["A2", "B2"]}:
        return (False, -1)

    base = {"->": [{"->": ["Z1", "Z2"]}, {"⟲": ["Z3", "Z4"]}]}
    if cur == base:
        return (True, 0)

    step = 0
    while True:
        if not (isinstance(cur, dict) and len(cur) == 1 and "->" in cur):
            return (False, -1)
        v = cur["->"]
        if not (isinstance(v, list) and len(v) == 2):
            return (False, -1)
        left, right = v[0], v[1]

        if not (isinstance(left, dict) and len(left) == 1):
            return (False, -1)
        op = next(iter(left.keys()))
        lv = left[op]
        if not (isinstance(lv, list) and len(lv) == 2 and all(isinstance(x, str) for x in lv)):
            return (False, -1)

        m0 = _L_RE.match(lv[0])
        m1 = _L_RE.match(lv[1])
        if not (m0 and m1):
            return (False, -1)

        i0, s0 = int(m0.group(1)), m0.group(2)
        i1, s1 = int(m1.group(1)), m1.group(2)
        if i0 != i1 or {s0, s1} != {"1", "2"}:
            return (False, -1)
        if i0 != step:
            return (False, -1)

        mod = step % 5
        expected_op = (
            "↔" if mod == 0 else
            "⊕" if mod == 1 else
            "⧖" if mod == 2 else
            "⟲" if mod == 3 else
            "->"
        )
        if op != expected_op:
            return (False, -1)

        step += 1
        cur = right

        if cur == base:
            return (True, step)

        if step > 200000:
            return (False, -1)

def to_glyphpack_v6_macro_or_fallback(tree: Any) -> Tuple[bytes, bool, str]:
    ok, depth = _match_and_extract_depth(tree)
    if ok:
        # [0xC6][variant_id=1][depth_varint]
        out = bytearray()
        out.append(0xC6)
        out.append(1)
        out += _varint(depth)
        return (bytes(out), True, "v6-macro(depth)")
    return (to_glyphpack_fallback(tree), False, "fallback(v5-ish)")

# ------------------------------------------------------------
# Mutations (to test macro guard)
# ------------------------------------------------------------
def mutate_one_leaf(tree: Any) -> Any:
    t = json.loads(json.dumps(tree, ensure_ascii=False))
    # A1 -> A1x
    t["↔"][0]["⊕"][0]["⊕"][0] = "A1x"
    return t

def mutate_label_scheme(tree: Any) -> Any:
    def rewrite(n: Any) -> Any:
        if isinstance(n, str):
            if n.startswith("L") and n.endswith("_1"):
                return n.replace("_1", "a")
            if n.startswith("L") and n.endswith("_2"):
                return n.replace("_2", "b")
            return n
        if isinstance(n, list):
            return [rewrite(x) for x in n]
        if isinstance(n, dict):
            return {k: rewrite(v) for k, v in n.items()}
        return n
    return rewrite(tree)

def mutate_random_L_leaf(tree: Any, seed: int = 1) -> Any:
    rng = random.Random(seed)
    t = json.loads(json.dumps(tree, ensure_ascii=False))

    # collect paths to L* leaves
    paths: List[List[Any]] = []

    def walk(n: Any, p: List[Any]) -> None:
        if isinstance(n, dict):
            for k, v in n.items():
                walk(v, p + [k])
        elif isinstance(n, list):
            for i, x in enumerate(n):
                walk(x, p + [i])
        elif isinstance(n, str):
            if n.startswith("L") and (n.endswith("_1") or n.endswith("_2")):
                paths.append(p)

    def get_at(root: Any, p: List[Any]) -> Any:
        cur = root
        for step in p:
            cur = cur[step]
        return cur

    def set_at(root: Any, p: List[Any], val: Any) -> None:
        cur = root
        for step in p[:-1]:
            cur = cur[step]
        cur[p[-1]] = val

    walk(t, [])
    if not paths:
        return t

    pick = rng.choice(paths)
    old = get_at(t, pick)
    set_at(t, pick, old + "x")
    return t

# ------------------------------------------------------------
# Benchmark rows
# ------------------------------------------------------------
@dataclass
class Row:
    name: str
    depth: int
    macro_enabled: bool
    macro_used: bool
    variant: str
    json_bytes: int
    json_gz: int
    pack_bytes: int
    pack_gz: int
    ratio_raw: float
    ratio_gz: float

def _ratio(a: int, b: int) -> float:
    return round((a / b) if b else 0.0, 4)

def _pack(tree: Any, macro_enabled: bool) -> Tuple[bytes, bool, str]:
    if macro_enabled:
        return to_glyphpack_v6_macro_or_fallback(tree)
    return (to_glyphpack_fallback(tree), False, "fallback(v5-ish)")

def main() -> None:
    depths = [5, 30, 100]
    macro_enabled = os.environ.get("GLYPHOS_MACRO", "1").strip() not in {"0", "false", "False"}
    seed = int(os.environ.get("GLYPHOS_SEED", "1"))

    t0 = time.perf_counter()
    rows: List[Row] = []

    for d in depths:
        base = make_glyph_tree(d)

        cases: List[Tuple[str, Any]] = [
            ("canonical", base),
            ("near_miss_one_leaf", mutate_one_leaf(base)),
            ("relabel_namespace", mutate_label_scheme(base)),
            ("random_L_leaf_mutation", mutate_random_L_leaf(base, seed=seed + d)),
            ("canonical_depth_plus_one", make_glyph_tree(d + 1)),
        ]

        for name, tree in cases:
            j = to_wire_json_bytes(tree)
            jg = gzip_bytes(j)
            p, used, variant = _pack(tree, macro_enabled=macro_enabled)
            pg = gzip_bytes(p)

            rows.append(
                Row(
                    name=name,
                    depth=d,
                    macro_enabled=macro_enabled,
                    macro_used=used,
                    variant=variant,
                    json_bytes=len(j),
                    json_gz=len(jg),
                    pack_bytes=len(p),
                    pack_gz=len(pg),
                    ratio_raw=_ratio(len(j), len(p)),
                    ratio_gz=_ratio(len(jg), len(pg)),
                )
            )

    dur_ms = (time.perf_counter() - t0) * 1000.0

    total = len(rows)
    hits = sum(1 for r in rows if r.macro_used)
    hit_rate = round(hits / total, 4) if total else 0.0

    bad_hits = [r for r in rows if r.macro_used and r.name not in {"canonical", "canonical_depth_plus_one"}]

    print("\n=== ✅ GlyphOS WirePack v7 Macro Catalog Benchmark ===")
    print(f"Macro enabled (GLYPHOS_MACRO):     {int(macro_enabled)}")
    print(f"Seed (GLYPHOS_SEED):               {seed}")
    print(f"Depths tested:                     {depths}\n")

    for r in rows:
        print(
            f"- {r.name:24s} depth={r.depth:3d}  macro_used={str(r.macro_used):5s}  "
            f"pack={r.pack_bytes:4d}B (gz {r.pack_gz:3d}B)  "
            f"JSON/pack raw={r.ratio_raw:8.4f}x  gz={r.ratio_gz:8.4f}x  "
            f"variant={r.variant}"
        )

    print("\n--- Summary ---")
    print(f"Total cases:                        {total}")
    print(f"Macro hits:                         {hits}")
    print(f"Macro hit rate:                     {hit_rate}")
    print(f"BAD macro hits (should be 0):       {len(bad_hits)}")
    if bad_hits:
        for b in bad_hits[:10]:
            print(f"  ❌ bad hit: {b.name} depth={b.depth} variant={b.variant}")

    print(f"\nRuntime:                            {round(dur_ms, 3)} ms")

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "macro_enabled": macro_enabled,
        "seed": seed,
        "depths": depths,
        "runtime_ms": round(dur_ms, 3),
        "macro_hits": hits,
        "total_cases": total,
        "macro_hit_rate": hit_rate,
        "bad_macro_hits": [b.__dict__ for b in bad_hits],
        "rows": [r.__dict__ for r in rows],
    }

    os.makedirs("./benchmarks", exist_ok=True)
    out_path = "./benchmarks/glyphos_wirepack_v7_macro_catalog_latest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f"Saved:                              {out_path}\n")

if __name__ == "__main__":
    main()
