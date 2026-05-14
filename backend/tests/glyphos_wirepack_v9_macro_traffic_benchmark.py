# 📁 backend/tests/glyphos_wirepack_v9_macro_traffic_benchmark.py
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
# JSON helpers
# -----------------------------
def to_wire_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=False).encode("utf-8")

def gzip_bytes(b: bytes, level: int = 9) -> bytes:
    return gzip.compress(b, compresslevel=level)

# -----------------------------
# Canonical generator (same family you’ve been using)
# -----------------------------
OPS = {"↔", "⊕", "⟲", "->", "⧖"}
OP_TAG = {"↔": 1, "⊕": 2, "⟲": 3, "->": 4, "⧖": 5}
TAG_OP = {v: k for k, v in OP_TAG.items()}

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
# Varint (binary encoding)
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
# Fallback pack (v5-ish): arity=2 elision
# -----------------------------
def _encode_string_raw(s: str) -> bytes:
    b = s.encode("utf-8")
    return bytes([0x53]) + _varint(len(b)) + b  # 'S'

def _decode_string_raw(buf: bytes, i: int) -> Tuple[str, int]:
    if buf[i] != 0x53:
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

        # arity=2 default unless marker
        if len(children) != 2:
            out.append(0xA0)
            out += _varint(len(children))

        for ch in children:
            out += _encode_node_fallback(ch)
        return bytes(out)

    if isinstance(node, list):
        # encode list as "->" with explicit arity
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
        return _decode_string_raw(buf, i)

    if t == 0xD0:
        i += 1
        if i >= len(buf):
            raise ValueError("truncated op tag")
        tag = buf[i]
        i += 1
        op = TAG_OP.get(tag)
        if op is None:
            raise ValueError(f"unknown op tag: {tag}")

        # arity=2 default unless 0xA0 marker
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
# Macro matcher: matches EXACT make_glyph_tree(depth)
# -----------------------------
_L_RE = re.compile(r"^L(\d+)_([12])$")

def _match_and_extract_depth(tree: Any) -> Tuple[bool, int]:
    # Root: {"↔":[branch1, chain]}
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

    depth = 0
    outer_i: int | None = None

    while cur != base:
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

        # op must match generator based on i%5
        mod = i0 % 5
        expected_op = (
            "↔" if mod == 0 else
            "⊕" if mod == 1 else
            "⧖" if mod == 2 else
            "⟲" if mod == 3 else
            "->"
        )
        if op != expected_op:
            return (False, -1)

        # outermost i must be depth-1 and then strictly decrement each wrap
        if outer_i is None:
            outer_i = i0
        else:
            expected_i = outer_i - depth
            if i0 != expected_i:
                return (False, -1)

        depth += 1
        cur = right

        if depth > 1_000_000:
            return (False, -1)

    if outer_i is None:
        return (False, -1)
    if outer_i != depth - 1:
        return (False, -1)

    return (True, depth)

# Macro wire format: [0xC9][variant=1][depth varint]
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
# Traffic mutations (should NOT match macro)
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

    leaves: List[Tuple[List[Any], int]] = []

    def walk(n: Any, parent: Any = None, idx: int = -1) -> None:
        if isinstance(n, str) and n.startswith("L") and ("_1" in n or "_2" in n):
            if isinstance(parent, list) and idx >= 0:
                leaves.append((parent, idx))
            return
        if isinstance(n, list):
            for i, x in enumerate(n):
                walk(x, n, i)
        if isinstance(n, dict):
            for _, v in n.items():
                walk(v, None, -1)

    walk(t)
    if leaves:
        parent, i = rng.choice(leaves)
        parent[i] = parent[i] + "x"
    return t

# -----------------------------
# Results
# -----------------------------
@dataclass
class TrafficStats:
    depth: int
    samples: int
    macro_enabled: int

    macro_hits: int
    canonical_misses: int
    bad_macro_hits: int
    roundtrip_fail: int

    avg_json: float
    avg_json_gz: float

    avg_pack: float
    avg_pack_gz: float

    avg_fallback_pack: float
    avg_fallback_gz: float

    savings_vs_fallback_raw: float
    savings_vs_fallback_gz: float

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__

def _avg(xs: List[int]) -> float:
    return (sum(xs) / len(xs)) if xs else 0.0

def main() -> None:
    macro_enabled = os.environ.get("GLYPHOS_MACRO", "1").strip() not in {"0", "false", "False"}
    seed = int(os.environ.get("GLYPHOS_SEED", "1"))
    samples = int(os.environ.get("GLYPHOS_SAMPLES", "1000"))
    depth_env = os.environ.get("GLYPHOS_BENCH_DEPTHS", "30,200")
    depths = [int(x.strip()) for x in depth_env.split(",") if x.strip()]

    # Traffic mix:
    #   canonical share is key to “realistic traffic”
    #   ex: 0.10 => 10% canonical, 90% mutated
    canonical_share = float(os.environ.get("GLYPHOS_CANONICAL_SHARE", "0.10"))

    rng = random.Random(seed)
    t0 = time.perf_counter()

    print("\n=== ✅ GlyphOS WirePack v9 Macro Traffic Benchmark ===")
    print(f"Macro enabled (GLYPHOS_MACRO):     {1 if macro_enabled else 0}")
    print(f"Seed (GLYPHOS_SEED):               {seed}")
    print(f"Samples per depth (GLYPHOS_SAMPLES): {samples}")
    print(f"Depths (GLYPHOS_BENCH_DEPTHS):     {depths}")
    print(f"Canonical share (GLYPHOS_CANONICAL_SHARE): {canonical_share}\n")

    # Preflight: matcher must hit canonical at least for first depth
    ok, d = _match_and_extract_depth(make_glyph_tree(depths[0]))
    print(f"(preflight) matcher canonical depth={depths[0]} -> ok={ok} extract={d}\n")

    stats: List[TrafficStats] = []

    for depth in depths:
        json_sizes: List[int] = []
        json_gz_sizes: List[int] = []

        pack_sizes: List[int] = []
        pack_gz_sizes: List[int] = []

        fb_sizes: List[int] = []
        fb_gz_sizes: List[int] = []

        macro_hits = 0
        canonical_misses = 0
        bad_macro_hits = 0
        roundtrip_fail = 0

        for _ in range(samples):
            canonical = make_glyph_tree(depth)

            # Decide traffic kind
            r = rng.random()
            if r < canonical_share:
                tree = canonical
                expect_macro = True
            else:
                # mutated traffic: split across mutation types
                r2 = rng.random()
                if r2 < 0.33:
                    tree = mutate_one_leaf(canonical)
                elif r2 < 0.66:
                    tree = mutate_label_scheme(canonical)
                else:
                    tree = mutate_random_L_leaf(canonical, rng)
                expect_macro = False

            # Canonical miss check (should always match)
            if tree is canonical:
                mok, md = _match_and_extract_depth(tree)
                if (not mok) or (md != depth):
                    canonical_misses += 1

            # Measure JSON
            jb = to_wire_json_bytes(tree)
            json_sizes.append(len(jb))
            json_gz_sizes.append(len(gzip_bytes(jb)))

            # Fallback baseline (always)
            fb = pack_fallback(tree)
            fb_sizes.append(len(fb))
            fb_gz_sizes.append(len(gzip_bytes(fb)))

            # v9 pack (macro or fallback)
            packed, used_macro, variant, extracted = pack_v9(tree, macro_enabled)
            pack_sizes.append(len(packed))
            pack_gz_sizes.append(len(gzip_bytes(packed)))

            if used_macro:
                macro_hits += 1
                if not expect_macro:
                    bad_macro_hits += 1

            # roundtrip correctness: decode must equal original tree
            try:
                decoded = unpack_v9(packed)
                if decoded != tree:
                    roundtrip_fail += 1
            except Exception:
                roundtrip_fail += 1

        avg_json = _avg(json_sizes)
        avg_json_gz = _avg(json_gz_sizes)
        avg_pack = _avg(pack_sizes)
        avg_pack_gz = _avg(pack_gz_sizes)
        avg_fb = _avg(fb_sizes)
        avg_fb_gz = _avg(fb_gz_sizes)

        # savings vs fallback-only (positive means improvement)
        savings_raw = (avg_fb - avg_pack) / avg_fb if avg_fb else 0.0
        savings_gz = (avg_fb_gz - avg_pack_gz) / avg_fb_gz if avg_fb_gz else 0.0

        s = TrafficStats(
            depth=depth,
            samples=samples,
            macro_enabled=1 if macro_enabled else 0,
            macro_hits=macro_hits,
            canonical_misses=canonical_misses,
            bad_macro_hits=bad_macro_hits,
            roundtrip_fail=roundtrip_fail,
            avg_json=round(avg_json, 3),
            avg_json_gz=round(avg_json_gz, 3),
            avg_pack=round(avg_pack, 3),
            avg_pack_gz=round(avg_pack_gz, 3),
            avg_fallback_pack=round(avg_fb, 3),
            avg_fallback_gz=round(avg_fb_gz, 3),
            savings_vs_fallback_raw=round(savings_raw, 6),
            savings_vs_fallback_gz=round(savings_gz, 6),
        )
        stats.append(s)

        # Print a compact line
        hit_rate = macro_hits / samples if samples else 0.0
        print(
            f"- depth={depth:4d}  hit_rate={hit_rate:6.3f}  "
            f"macro_hits={macro_hits:4d}  bad_hits={bad_macro_hits:3d}  canon_miss={canonical_misses:3d}  "
            f"rt_fail={roundtrip_fail:3d}  "
            f"avg_pack={avg_pack:7.3f}B (gz {avg_pack_gz:7.3f}B)  "
            f"savings_vs_fb={savings_raw*100:6.2f}% (gz {savings_gz*100:6.2f}%)"
        )

    dur_ms = (time.perf_counter() - t0) * 1000.0

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "macro_enabled": 1 if macro_enabled else 0,
        "seed": seed,
        "samples": samples,
        "depths": depths,
        "canonical_share": canonical_share,
        "runtime_ms": round(dur_ms, 3),
        "stats": [x.to_dict() for x in stats],
    }

    os.makedirs("./benchmarks", exist_ok=True)
    out_path = "./benchmarks/glyphos_wirepack_v9_macro_traffic_latest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f"\nRuntime:                            {round(dur_ms, 3)} ms")
    print(f"Saved:                              {out_path}\n")


if __name__ == "__main__":
    main()
