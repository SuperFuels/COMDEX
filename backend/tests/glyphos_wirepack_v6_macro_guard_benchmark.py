# 📁 backend/tests/glyphos_wirepack_v6_macro_guard_benchmark.py
from __future__ import annotations

import gzip
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

# Keep identical OPS set to stay comparable
OPS = {"↔", "⊕", "⟲", "->", "⧖"}
OP_TAG = {"↔": 1, "⊕": 2, "⟲": 3, "->": 4, "⧖": 5}

# -----------------------------
# Generator (same as your benchmarks)
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
# JSON helpers
# -----------------------------
def to_wire_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=False).encode("utf-8")

def gzip_bytes(b: bytes, level: int = 9) -> bytes:
    return gzip.compress(b, compresslevel=level)

# -----------------------------
# GlyphPack v5-ish (fallback binary): arity=2 elision + varints
# -----------------------------
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
    return bytes([0x53]) + _varint(len(b)) + b  # 'S' raw string

def _encode_node_v5(node: Any) -> bytes:
    # v5 rule: most ops are arity=2 in this benchmark; omit arity when ==2
    if isinstance(node, str):
        return _encode_string_raw(node)

    if isinstance(node, dict):
        for op, v in node.items():
            tag = OP_TAG.get(op, 0)
            if tag == 0:
                raise ValueError(f"unknown op: {op}")
            children = v if isinstance(v, list) else [v]

            out = bytearray()
            out.append(0xD0)  # dict/op marker
            out.append(tag)   # op tag

            if len(children) != 2:
                out.append(0xA0)  # arity marker if not 2
                out += _varint(len(children))

            for ch in children:
                out += _encode_node_v5(ch)
            return bytes(out)

    if isinstance(node, list):
        # encode list as sequence op
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

# -----------------------------
# GlyphPack v6 macro: only when tree matches canonical grammar (guarded)
# -----------------------------
_L_RE = re.compile(r"^L(\d+)_([12])$")

_BASE_TAIL: Dict[str, Any] = {"->": [{"->": ["Z1", "Z2"]}, {"⟲": ["Z3", "Z4"]}]}

def _expected_op_for_index(i: int) -> str:
    mod = i % 5
    return (
        "↔" if mod == 0 else
        "⊕" if mod == 1 else
        "⧖" if mod == 2 else
        "⟲" if mod == 3 else
        "->"
    )

def _match_and_extract_depth(tree: Any) -> Tuple[bool, int]:
    """
    Strictly match the canonical make_glyph_tree(depth_steps) shape.

    IMPORTANT detail:
      The generator *wraps* the chain, so the OUTERMOST wrapper has index (depth_steps-1),
      then it descends ... down to index 0, then hits the fixed Z-tail base.

    Returns (True, depth_steps) when exact; otherwise (False, -1).
    """

    # Root: {"↔": [branch1, subtree]}
    if not (isinstance(tree, dict) and len(tree) == 1 and "↔" in tree):
        return (False, -1)
    pair = tree["↔"]
    if not (isinstance(pair, list) and len(pair) == 2):
        return (False, -1)
    branch1, cur = pair[0], pair[1]

    # branch1 exact structure (and labels)
    if not (isinstance(branch1, dict) and len(branch1) == 1 and "⊕" in branch1):
        return (False, -1)
    b1 = branch1["⊕"]
    if not (isinstance(b1, list) and len(b1) == 2):
        return (False, -1)
    if b1[0] != {"⊕": ["A1", "B1"]}:
        return (False, -1)
    if b1[1] != {"⟲": ["A2", "B2"]}:
        return (False, -1)

    # If depth_steps==0, subtree is exactly the base tail.
    if cur == _BASE_TAIL:
        return (True, 0)

    # Walk the -> chain wrappers until we reach the base tail.
    # Outer wrapper index should be (depth_steps-1), and indices must be consecutive descending.
    step = 0
    start_i: int | None = None

    while True:
        if not (isinstance(cur, dict) and len(cur) == 1 and "->" in cur):
            return (False, -1)
        v = cur["->"]
        if not (isinstance(v, list) and len(v) == 2):
            return (False, -1)
        left, right = v[0], v[1]

        # left must be a single op node with two string leaves L{i}_1 / L{i}_2
        if not (isinstance(left, dict) and len(left) == 1):
            return (False, -1)
        op = next(iter(left.keys()))
        if op not in OPS:
            return (False, -1)
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

        if start_i is None:
            start_i = i0

        expected_i = start_i - step
        if i0 != expected_i:
            return (False, -1)

        expected_op = _expected_op_for_index(i0)
        if op != expected_op:
            return (False, -1)

        step += 1
        cur = right

        if cur == _BASE_TAIL:
            # number of wrappers == depth_steps
            return (True, step)

        if step > 100_000:
            return (False, -1)

def to_glyphpack_v6_macro_or_fallback(tree: Any) -> Tuple[bytes, bool, str]:
    """
    If macro matches canonical grammar, encode as a tiny header:
      [0xC6][variant_id][flags][depth_varint]
    else fallback to binary tree encoding (v5-ish).
    """
    ok, depth = _match_and_extract_depth(tree)
    if ok:
        variant_id = 1  # v6-macro(depth)
        flags = 0       # reserved
        out = bytearray()
        out.append(0xC6)
        out.append(variant_id)
        out.append(flags)
        out += _varint(depth)
        return (bytes(out), True, "v6-macro(depth)")

    return (to_glyphpack_fallback(tree), False, "fallback(v5-ish)")

# -----------------------------
# Tree perturbations to prove guard behavior
# -----------------------------
def mutate_one_leaf(tree: Any) -> Any:
    """
    Change exactly one leaf value without changing shape.
    This MUST break the macro match.
    """
    t = json.loads(json.dumps(tree, ensure_ascii=False))
    # A1 -> A1x (branch1)
    t["↔"][0]["⊕"][0]["⊕"][0] = "A1x"
    return t

def mutate_label_scheme(tree: Any) -> Any:
    """
    Change label namespace for all L{i}_1/2 to L{i}a/b.
    Shape remains identical, macro MUST fail.
    """
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

# -----------------------------
# Result schema
# -----------------------------
@dataclass
class CaseResult:
    name: str
    macro_used: bool
    variant: str
    json_bytes: int
    json_gzip_bytes: int
    pack_bytes: int
    pack_gzip_bytes: int
    json_vs_pack_raw_x: float
    json_vs_pack_gzip_x: float

@dataclass
class BenchResult:
    timestamp: str
    depth_steps: int
    cases: List[CaseResult]
    runtime_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "depth_steps": self.depth_steps,
            "runtime_ms": self.runtime_ms,
            "cases": [c.__dict__ for c in self.cases],
        }

def _safe_x(a: int, b: int) -> float:
    return round((a / b) if b else 0.0, 4)

def run_benchmark(depth_steps: int = 30) -> BenchResult:
    t0 = time.perf_counter()

    base = make_glyph_tree(depth_steps)
    near = mutate_one_leaf(base)
    relabel = mutate_label_scheme(base)
    deeper = make_glyph_tree(depth_steps + 1)

    cases: List[Tuple[str, Any]] = [
        ("canonical(depth)", base),
        ("near-miss(one-leaf)", near),
        ("relabel(namespace)", relabel),
        ("canonical(depth+1)", deeper),
    ]

    macro_enabled = os.environ.get("GLYPHOS_MACRO", "1").strip() not in {"0", "false", "False"}

    out_cases: List[CaseResult] = []
    for name, tree in cases:
        j = to_wire_json_bytes(tree)
        jg = gzip_bytes(j)

        if macro_enabled:
            pack, used, variant = to_glyphpack_v6_macro_or_fallback(tree)
        else:
            pack, used, variant = (to_glyphpack_fallback(tree), False, "fallback(v5-ish)")

        pg = gzip_bytes(pack)

        out_cases.append(
            CaseResult(
                name=name,
                macro_used=used,
                variant=variant,
                json_bytes=len(j),
                json_gzip_bytes=len(jg),
                pack_bytes=len(pack),
                pack_gzip_bytes=len(pg),
                json_vs_pack_raw_x=_safe_x(len(j), len(pack)),
                json_vs_pack_gzip_x=_safe_x(len(jg), len(pg)),
            )
        )

    dur_ms = (time.perf_counter() - t0) * 1000.0
    return BenchResult(
        timestamp=datetime.now(timezone.utc).isoformat(),
        depth_steps=depth_steps,
        cases=out_cases,
        runtime_ms=round(dur_ms, 3),
    )

def main() -> None:
    depth_steps = int(os.environ.get("GLYPHOS_BENCH_DEPTH", "30"))
    res = run_benchmark(depth_steps)

    macro_env = os.environ.get("GLYPHOS_MACRO", "1")

    print("\n=== ✅ GlyphOS WirePack v6 Macro Guard Benchmark ===")
    print(f"Depth steps used:                 {res.depth_steps}")
    print(f"Macro enabled (env GLYPHOS_MACRO): {macro_env}\n")

    for c in res.cases:
        print(f"--- Case: {c.name} ---")
        print(f"Macro used:                        {c.macro_used}")
        print(f"Variant:                           {c.variant}")
        print(f"JSON bytes:                        {c.json_bytes}")
        print(f"JSON gzip bytes:                   {c.json_gzip_bytes}")
        print(f"Pack bytes:                        {c.pack_bytes}")
        print(f"Pack gzip bytes:                   {c.pack_gzip_bytes}")
        print(f"✅ JSON vs Pack (raw):              {c.json_vs_pack_raw_x}x")
        print(f"✅ JSON vs Pack (gzip):             {c.json_vs_pack_gzip_x}x\n")

    print(f"Runtime:                           {res.runtime_ms} ms")

    out_dir = "./benchmarks"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "glyphos_wirepack_v6_macro_guard_latest.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res.to_dict(), f, indent=2, ensure_ascii=False)

    print(f"Saved:                             {out_path}\n")

if __name__ == "__main__":
    main()
