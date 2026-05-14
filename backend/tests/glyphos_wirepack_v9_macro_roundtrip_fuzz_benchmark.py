# 📁 backend/tests/glyphos_wirepack_v9_macro_roundtrip_fuzz_benchmark.py
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
TAG_OP = {v: k for k, v in OP_TAG.items()}

def to_wire_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=False).encode("utf-8")

def gzip_bytes(b: bytes, level: int = 9) -> bytes:
    return gzip.compress(b, compresslevel=level)

# -----------------------------
# Canonical generator (matches your other benches)
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
# Varint
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

def _read_varint(buf: bytes, i: int) -> Tuple[int, int]:
    shift = 0
    val = 0
    while True:
        if i >= len(buf):
            raise ValueError("truncated varint")
        b = buf[i]
        i += 1
        val |= (b & 0x7F) << shift
        if (b & 0x80) == 0:
            return val, i
        shift += 7
        if shift > 63:
            raise ValueError("varint too large")

# -----------------------------
# Fallback pack/unpack (v5-ish): arity=2 elision
# -----------------------------
def _encode_string_raw(s: str) -> bytes:
    b = s.encode("utf-8")
    return bytes([0x53]) + _varint(len(b)) + b  # 'S'

def _decode_string_raw(buf: bytes, i: int) -> Tuple[str, int]:
    if i >= len(buf) or buf[i] != 0x53:
        raise ValueError("expected string tag 0x53")
    i += 1
    n, i = _read_varint(buf, i)
    if i + n > len(buf):
        raise ValueError("truncated string")
    s = buf[i : i + n].decode("utf-8")
    return s, i + n

def _encode_node_fallback(node: Any) -> bytes:
    if isinstance(node, str):
        return _encode_string_raw(node)

    if isinstance(node, dict):
        if len(node) != 1:
            raise ValueError("expected single-key op dict")
        op = next(iter(node.keys()))
        v = node[op]
        tag = OP_TAG.get(op, 0)
        if tag == 0:
            raise ValueError(f"unknown op: {op}")
        children = v if isinstance(v, list) else [v]

        out = bytearray()
        out.append(0xD0)
        out.append(tag)

        # arity=2 default unless explicit marker
        if len(children) != 2:
            out.append(0xA0)
            out += _varint(len(children))

        for ch in children:
            out += _encode_node_fallback(ch)
        return bytes(out)

    if isinstance(node, list):
        # encode list as sequence op with explicit arity
        out = bytearray()
        out.append(0xD0)
        out.append(OP_TAG["->"])
        out.append(0xA0)
        out += _varint(len(node))
        for ch in node:
            out += _encode_node_fallback(ch)
        return bytes(out)

    return _encode_string_raw("null")

def _decode_node_fallback(buf: bytes, i: int) -> Tuple[Any, int]:
    if i >= len(buf):
        raise ValueError("truncated")
    t = buf[i]

    if t == 0x53:
        s, j = _decode_string_raw(buf, i)
        return s, j

    if t == 0xD0:
        i += 1
        if i >= len(buf):
            raise ValueError("truncated op tag")
        tag = buf[i]
        i += 1
        op = TAG_OP.get(tag)
        if op is None:
            raise ValueError(f"unknown op tag: {tag}")

        # arity=2 default unless marker present
        if i < len(buf) and buf[i] == 0xA0:
            i += 1
            arity, i = _read_varint(buf, i)
        else:
            arity = 2

        children: List[Any] = []
        for _ in range(arity):
            ch, i = _decode_node_fallback(buf, i)
            children.append(ch)
        return {op: children}, i

    raise ValueError(f"unknown type byte: {t}")

def pack_fallback(tree: Any) -> bytes:
    return _encode_node_fallback(tree)

def unpack_fallback(buf: bytes) -> Any:
    node, i = _decode_node_fallback(buf, 0)
    if i != len(buf):
        raise ValueError("trailing bytes")
    return node

# -----------------------------
# Macro matcher (MUST match the canonical generator exactly)
# -----------------------------
_L_RE = re.compile(r"^L(\d+)_([12])$")

def _expected_op_for_i(i: int) -> str:
    mod = i % 5
    return (
        "↔" if mod == 0 else
        "⊕" if mod == 1 else
        "⧖" if mod == 2 else
        "⟲" if mod == 3 else
        "->"
    )

def _match_and_extract_depth(tree: Any) -> Tuple[bool, int]:
    # Root: {"↔": [branch1, chain]}
    if not isinstance(tree, dict) or len(tree) != 1 or "↔" not in tree:
        return (False, -1)
    pair = tree["↔"]
    if not (isinstance(pair, list) and len(pair) == 2):
        return (False, -1)
    branch1, cur = pair[0], pair[1]

    # branch1 exact structure (labels included)
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

    # Walk outer -> wrappers:
    # canonical build yields indices descending: L{depth-1}, ..., L0, then base tail.
    depth = 0
    first_i: int | None = None
    prev_i: int | None = None
    last_i: int | None = None

    while cur != base:
        if not (isinstance(cur, dict) and len(cur) == 1 and "->" in cur):
            return (False, -1)
        v = cur["->"]
        if not (isinstance(v, list) and len(v) == 2):
            return (False, -1)
        left, right = v[0], v[1]

        # left must be {op:[Lk_?, Lk_?]} with same k and suffixes {1,2}
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

        if op != _expected_op_for_i(i0):
            return (False, -1)

        if first_i is None:
            first_i = i0
        if prev_i is not None and i0 != prev_i - 1:
            return (False, -1)

        prev_i = i0
        last_i = i0
        depth += 1
        cur = right

        if depth > 1_000_000:
            return (False, -1)

    # Must end on L0 and start on L(depth-1)
    if last_i != 0:
        return (False, -1)
    if first_i != depth - 1:
        return (False, -1)

    return (True, depth)

# -----------------------------
# Macro wire format: [0xC9][variant=1][depth varint]
# (Depth < 128 => varint is 1 byte => total 3 bytes.)
# -----------------------------
_MACRO_MAGIC = 0xC9
_MACRO_VARIANT = 1

def pack_macro(depth: int) -> bytes:
    return bytes([_MACRO_MAGIC, _MACRO_VARIANT]) + _varint(depth)

def unpack_macro(buf: bytes) -> int:
    if len(buf) < 3:
        raise ValueError("macro too short")
    if buf[0] != _MACRO_MAGIC or buf[1] != _MACRO_VARIANT:
        raise ValueError("bad macro header")
    depth, i = _read_varint(buf, 2)
    if i != len(buf):
        raise ValueError("trailing macro bytes")
    return depth

def pack_v9(tree: Any, macro_enabled: bool) -> Tuple[bytes, bool, str, int]:
    if macro_enabled:
        ok, depth = _match_and_extract_depth(tree)
        if ok:
            return pack_macro(depth), True, "v9-macro(depth)", depth
    return pack_fallback(tree), False, "fallback(v5-ish)", -1

def unpack_v9(buf: bytes) -> Any:
    if len(buf) >= 2 and buf[0] == _MACRO_MAGIC and buf[1] == _MACRO_VARIANT:
        depth = unpack_macro(buf)
        return make_glyph_tree(depth)
    return unpack_fallback(buf)

# -----------------------------
# Mutations (macro MUST NOT match)
# -----------------------------
def mutate_one_leaf(tree: Any) -> Any:
    t = json.loads(json.dumps(tree, ensure_ascii=False))
    t["↔"][0]["⊕"][0]["⊕"][0] = "A1x"
    return t

def mutate_label_scheme(tree: Any) -> Any:
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

def mutate_random_L_leaf(tree: Any, rng: random.Random) -> Any:
    t = json.loads(json.dumps(tree, ensure_ascii=False))

    # collect references to list parents that contain L* leaves
    slots: List[Tuple[List[Any], int]] = []

    def walk(n: Any) -> None:
        if isinstance(n, list):
            for i, x in enumerate(n):
                if isinstance(x, str) and x.startswith("L") and (x.endswith("_1") or x.endswith("_2")):
                    slots.append((n, i))
                else:
                    walk(x)
            return
        if isinstance(n, dict):
            for _, v in n.items():
                walk(v)
            return

    walk(t)
    if slots:
        parent, i = rng.choice(slots)
        parent[i] = parent[i] + "x"  # break macro match
    return t

# -----------------------------
# Results
# -----------------------------
@dataclass
class DepthStats:
    depth: int
    macro_hits: int
    misses_on_canonical: int
    bad_hits: int
    roundtrip_fail: int
    avg_pack: float
    avg_gz: float
    hit_rate: float

def main() -> None:
    macro_enabled = os.environ.get("GLYPHOS_MACRO", "1").strip() not in {"0", "false", "False"}
    seed = int(os.environ.get("GLYPHOS_SEED", "1"))
    trials = int(os.environ.get("GLYPHOS_TRIALS", "200"))
    depth_env = os.environ.get("GLYPHOS_BENCH_DEPTHS", "30")
    depths = [int(x.strip()) for x in depth_env.split(",") if x.strip()]

    rng = random.Random(seed)
    t0 = time.perf_counter()

    print("\n=== ✅ GlyphOS WirePack v9 Macro Roundtrip + Fuzz Benchmark ===")
    print(f"Macro enabled (GLYPHOS_MACRO):     {1 if macro_enabled else 0}")
    print(f"Seed (GLYPHOS_SEED):               {seed}")
    print(f"Trials per depth (GLYPHOS_TRIALS): {trials}")
    print(f"Depths (GLYPHOS_BENCH_DEPTHS):     {depths}\n")

    stats: List[DepthStats] = []

    for depth in depths:
        # Preflight: macro matcher MUST recognize canonical tree for this depth
        ok, d = _match_and_extract_depth(make_glyph_tree(depth))
        if macro_enabled and not (ok and d == depth):
            print(f"⚠️  WARNING: macro matcher failed preflight at depth={depth} (got {(ok,d)}). Forcing macro OFF.\n")
            macro_enabled_local = False
        else:
            macro_enabled_local = macro_enabled

        macro_hits = 0
        misses_on_canonical = 0
        bad_hits = 0
        roundtrip_fail = 0
        pack_sizes: List[int] = []
        gz_sizes: List[int] = []

        for _ in range(trials):
            canonical = make_glyph_tree(depth)

            r = rng.random()
            if r < 0.25:
                tree = canonical
                expect_macro = True
            elif r < 0.50:
                tree = mutate_one_leaf(canonical)
                expect_macro = False
            elif r < 0.75:
                tree = mutate_label_scheme(canonical)
                expect_macro = False
            else:
                tree = mutate_random_L_leaf(canonical, rng)
                expect_macro = False

            # Canonical correctness accounting (no identity tricks)
            if expect_macro:
                ok2, d2 = _match_and_extract_depth(tree)
                if not ok2 or d2 != depth:
                    misses_on_canonical += 1

            packed, used_macro, variant, extracted = pack_v9(tree, macro_enabled_local)

            if used_macro:
                macro_hits += 1
                if not expect_macro:
                    bad_hits += 1

            pack_sizes.append(len(packed))
            gz_sizes.append(len(gzip_bytes(packed)))

            # Roundtrip must reconstruct the exact same tree
            try:
                decoded = unpack_v9(packed)
                if decoded != tree:
                    roundtrip_fail += 1
            except Exception:
                roundtrip_fail += 1

        avg_pack = sum(pack_sizes) / len(pack_sizes) if pack_sizes else 0.0
        avg_gz = sum(gz_sizes) / len(gz_sizes) if gz_sizes else 0.0
        hit_rate = macro_hits / trials if trials else 0.0

        stats.append(
            DepthStats(
                depth=depth,
                macro_hits=macro_hits,
                misses_on_canonical=misses_on_canonical,
                bad_hits=bad_hits,
                roundtrip_fail=roundtrip_fail,
                avg_pack=avg_pack,
                avg_gz=avg_gz,
                hit_rate=hit_rate,
            )
        )

        print(
            f"- depth={depth:4d}  macro_hits={macro_hits:4d}  "
            f"misses_on_canonical={misses_on_canonical:4d}  BAD_hits={bad_hits:4d}  "
            f"roundtrip_fail={roundtrip_fail:4d}  avg_pack={avg_pack:7.3f}B  avg_gz={avg_gz:7.3f}B  "
            f"hit_rate={hit_rate:.3f}"
        )

    dur_ms = (time.perf_counter() - t0) * 1000.0

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "macro_enabled": 1 if macro_enabled else 0,
        "seed": seed,
        "trials": trials,
        "depths": depths,
        "runtime_ms": round(dur_ms, 3),
        "stats": [s.__dict__ for s in stats],
    }

    os.makedirs("./benchmarks", exist_ok=True)
    out_path = "./benchmarks/glyphos_wirepack_v9_macro_roundtrip_fuzz_latest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f"\nRuntime:                            {round(dur_ms, 3)} ms")
    print(f"Saved:                              {out_path}\n")

if __name__ == "__main__":
    main()
