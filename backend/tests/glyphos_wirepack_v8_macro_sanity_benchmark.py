# 📁 backend/tests/glyphos_wirepack_v8_macro_sanity_benchmark.py
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

# -----------------------------
# Config
# -----------------------------
OPS = {"↔", "⊕", "⟲", "->", "⧖"}
OP_TAG = {"↔": 1, "⊕": 2, "⟲": 3, "->": 4, "⧖": 5}

_L_RE = re.compile(r"^L(\d+)_([12])$")

def to_wire_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=False).encode("utf-8")

def gzip_bytes(b: bytes, level: int = 9) -> bytes:
    return gzip.compress(b, compresslevel=level)

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

# -----------------------------
# Canonical benchmark generator
# -----------------------------
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

# -----------------------------
# Fallback pack (v5-ish): arity=2 elision + raw strings
# -----------------------------
def _encode_string_raw(s: str) -> bytes:
    b = s.encode("utf-8")
    return bytes([0x53]) + _varint(len(b)) + b  # 'S' + len + bytes

def _encode_node_fallback(node: Any) -> bytes:
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

            # elide arity when == 2 (common case here)
            if len(children) != 2:
                out.append(0xA0)
                out += _varint(len(children))

            for ch in children:
                out += _encode_node_fallback(ch)
            return bytes(out)

    if isinstance(node, list):
        out = bytearray()
        out.append(0xD0)
        out.append(OP_TAG["->"])
        out.append(0xA0)
        out += _varint(len(node))
        for ch in node:
            out += _encode_node_fallback(ch)
        return bytes(out)

    return _encode_string_raw("null")

def to_pack_fallback(tree: Any) -> bytes:
    return _encode_node_fallback(tree)

# -----------------------------
# Macro matcher (STRICT): must match the canonical generator exactly
# Returns (True, depth_steps) or (False, -1)
# -----------------------------
def _match_and_extract_depth(tree: Any) -> Tuple[bool, int]:
    # Root: {"↔": [branch1, subtree]}
    if not (isinstance(tree, dict) and len(tree) == 1 and "↔" in tree):
        return (False, -1)
    pair = tree["↔"]
    if not (isinstance(pair, list) and len(pair) == 2):
        return (False, -1)
    branch1, cur = pair[0], pair[1]

    # branch1 must be exact
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

    # depth=0 special-case
    if cur == base:
        return (True, 0)

    idxs: List[int] = []
    ops: List[str] = []

    # Walk wrapper chain until base
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

        idxs.append(i0)
        ops.append(op)

        cur = right
        if cur == base:
            break
        if len(idxs) > 200000:
            return (False, -1)

    # Indices must be: N-1, N-2, ..., 0
    if not idxs:
        return (False, -1)
    if idxs[-1] != 0:
        return (False, -1)

    depth_steps = len(idxs)
    if idxs[0] != depth_steps - 1:
        return (False, -1)
    for pos in range(depth_steps):
        if idxs[pos] != (depth_steps - 1 - pos):
            return (False, -1)

    # Op must match generator rule for each i
    for pos, i in enumerate(idxs):
        expected_op = (
            "↔" if (i % 5) == 0 else
            "⊕" if (i % 5) == 1 else
            "⧖" if (i % 5) == 2 else
            "⟲" if (i % 5) == 3 else
            "->"
        )
        if ops[pos] != expected_op:
            return (False, -1)

    return (True, depth_steps)

# -----------------------------
# Macro pack: [0xC6][variant=1][depth(varint)]
# -----------------------------
def to_pack_macro_or_fallback(tree: Any) -> Tuple[bytes, bool, str]:
    ok, depth = _match_and_extract_depth(tree)

    macro_enabled = os.environ.get("GLYPHOS_MACRO", "1").strip() not in {"0", "false", "False"}
    if macro_enabled and ok:
        out = bytearray()
        out.append(0xC6)
        out.append(1)  # variant id
        out += _varint(depth)
        return (bytes(out), True, "v8-macro(depth)")

    return (to_pack_fallback(tree), False, "fallback(v5-ish)")

# -----------------------------
# Mutations (guard should reject)
# -----------------------------
def mutate_one_leaf(tree: Any) -> Any:
    t = json.loads(json.dumps(tree, ensure_ascii=False))
    # A1 -> A1x
    t["↔"][0]["⊕"][0]["⊕"][0] = "A1x"
    return t

def relabel_namespace(tree: Any) -> Any:
    def rewrite(n: Any) -> Any:
        if isinstance(n, str):
            if n.startswith("L") and n.endswith("_1"):
                return n[:-2] + "a"
            if n.startswith("L") and n.endswith("_2"):
                return n[:-2] + "b"
            return n
        if isinstance(n, list):
            return [rewrite(x) for x in n]
        if isinstance(n, dict):
            return {k: rewrite(v) for k, v in n.items()}
        return n
    return rewrite(tree)

def random_L_leaf_mutation(tree: Any, seed: int) -> Any:
    rng = random.Random(seed)
    t = json.loads(json.dumps(tree, ensure_ascii=False))

    # collect all L* leaves
    leaves: List[Tuple[List[Any], str]] = []

    def walk(n: Any, path: List[Any]) -> None:
        if isinstance(n, str):
            if _L_RE.match(n):
                leaves.append((path[:], n))
            return
        if isinstance(n, list):
            for i, x in enumerate(n):
                walk(x, path + [i])
            return
        if isinstance(n, dict):
            for k, v in n.items():
                walk(v, path + [k])

    walk(t, [])

    if not leaves:
        return t

    p, val = rng.choice(leaves)

    # set the chosen leaf to a near-miss label
    def set_at(root: Any, path: List[Any], newv: str) -> None:
        cur = root
        for key in path[:-1]:
            cur = cur[key]
        cur[path[-1]] = newv

    set_at(t, p, val + "x")
    return t

# -----------------------------
# Result schema + runner
# -----------------------------
@dataclass
class Row:
    name: str
    depth: int
    macro_used: bool
    variant: str
    extracted_depth: int
    json_bytes: int
    json_gz: int
    pack_bytes: int
    pack_gz: int
    json_over_pack: float
    jsongz_over_packgz: float

def _safe_x(a: int, b: int) -> float:
    return round((a / b) if b else 0.0, 4)

def main() -> None:
    depths = os.environ.get("GLYPHOS_DEPTHS", "5,30,100")
    depths_list = [int(x.strip()) for x in depths.split(",") if x.strip()]
    seed = int(os.environ.get("GLYPHOS_SEED", "1"))

    t0 = time.perf_counter()
    rows: List[Row] = []

    for d in depths_list:
        base = make_glyph_tree(d)
        cases = [
            ("canonical", base),
            ("near_miss_one_leaf", mutate_one_leaf(base)),
            ("relabel_namespace", relabel_namespace(base)),
            ("random_L_leaf_mutation", random_L_leaf_mutation(base, seed=seed + d)),
            ("canonical_depth_plus_one", make_glyph_tree(d + 1)),
        ]

        for name, tree in cases:
            j = to_wire_json_bytes(tree)
            jg = gzip_bytes(j)

            pack, used, variant = to_pack_macro_or_fallback(tree)
            pg = gzip_bytes(pack)

            ok, extracted = _match_and_extract_depth(tree)

            rows.append(
                Row(
                    name=name,
                    depth=d,
                    macro_used=used,
                    variant=variant,
                    extracted_depth=extracted if ok else -1,
                    json_bytes=len(j),
                    json_gz=len(jg),
                    pack_bytes=len(pack),
                    pack_gz=len(pg),
                    json_over_pack=_safe_x(len(j), len(pack)),
                    jsongz_over_packgz=_safe_x(len(jg), len(pg)),
                )
            )

    dur_ms = round((time.perf_counter() - t0) * 1000.0, 3)

    macro_hits = sum(1 for r in rows if r.macro_used)
    bad_hits = sum(1 for r in rows if r.macro_used and r.name != "canonical" and not r.name.startswith("canonical_depth_plus_one"))

    print("\n=== ✅ GlyphOS WirePack v8 Macro Sanity Benchmark ===")
    print(f"Macro enabled (GLYPHOS_MACRO):     {os.environ.get('GLYPHOS_MACRO','1')}")
    print(f"Seed (GLYPHOS_SEED):               {seed}")
    print(f"Depths tested:                     {depths_list}\n")

    for r in rows:
        print(
            f"- {r.name:22s} depth={r.depth:3d} "
            f"macro_used={str(r.macro_used):5s} "
            f"pack={r.pack_bytes:4d}B (gz {r.pack_gz:3d}B) "
            f"JSON/pack raw={r.json_over_pack:8.4f}x "
            f"gz={r.jsongz_over_packgz:8.4f}x "
            f"variant={r.variant} "
            f"extract={r.extracted_depth}"
        )

    print("\n--- Summary ---")
    print(f"Total cases:                        {len(rows)}")
    print(f"Macro hits:                         {macro_hits}")
    print(f"Macro hit rate:                     {round(macro_hits/len(rows), 4) if rows else 0.0}")
    print(f"BAD macro hits (should be 0):       {bad_hits}")
    print(f"Runtime:                            {dur_ms} ms")

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "macro_enabled": os.environ.get("GLYPHOS_MACRO", "1"),
        "seed": seed,
        "depths": depths_list,
        "runtime_ms": dur_ms,
        "macro_hits": macro_hits,
        "bad_macro_hits": bad_hits,
        "rows": [r.__dict__ for r in rows],
    }

    out_dir = "./benchmarks"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "glyphos_wirepack_v8_macro_sanity_latest.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f"Saved:                              {out_path}\n")

if __name__ == "__main__":
    main()
