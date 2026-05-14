from __future__ import annotations

import gzip
import json
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

OPS = {"↔", "⊕", "⟲", "->", "⧖"}
OP_TAG = {"↔": 1, "⊕": 2, "⟲": 3, "->": 4, "⧖": 5}
TAG_OP = {v: k for k, v in OP_TAG.items()}

# -----------------------------
# Helpers
# -----------------------------
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
        out.append((0x80 | b) if n else b)
        if not n:
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

def _enc_str(s: str) -> bytes:
    b = s.encode("utf-8")
    return _varint(len(b)) + b

def _dec_str(buf: bytes, i: int) -> Tuple[str, int]:
    n, i = _read_varint(buf, i)
    s = buf[i:i+n].decode("utf-8")
    return s, i + n

# -----------------------------
# Canonical-ish family generator (K variants)
# Variants differ by:
# - branch1 constants
# - base tail constants
# - op-cycle phase offset
# -----------------------------
def make_glyph_tree(depth_steps: int, variant: int) -> Dict[str, Any]:
    # variant-dependent constants
    A1 = f"A{variant+1}"
    B1 = f"B{variant+1}"
    A2 = f"C{variant+1}"
    B2 = f"D{variant+1}"

    Z1 = f"Z{variant}_1"
    Z2 = f"Z{variant}_2"
    Z3 = f"Z{variant}_3"
    Z4 = f"Z{variant}_4"

    branch1 = {
        "⊕": [
            {"⊕": [A1, B1]},
            {"⟲": [A2, B2]},
        ]
    }

    subtree: Any = {"⟲": [Z3, Z4]}
    subtree = {"->": [{"->": [Z1, Z2]}, subtree]}

    # op-cycle phase offset to create families
    phase = variant % 5

    for i in range(depth_steps):
        a = f"L{i}_1"
        b = f"L{i}_2"
        mod = (i + phase) % 5
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
# Fallback binary pack (v5-ish): arity=2 elision + strings
# -----------------------------
def _encode_node_fallback(node: Any) -> bytes:
    if isinstance(node, str):
        return b"\x53" + _enc_str(node)  # 'S'
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
        if len(children) != 2:
            out.append(0xA0)
            out += _varint(len(children))
        for ch in children:
            out += _encode_node_fallback(ch)
        return bytes(out)
    if isinstance(node, list):
        # encode list as sequence with explicit arity
        out = bytearray([0xD0, OP_TAG["->"], 0xA0]) + _varint(len(node))
        for ch in node:
            out += _encode_node_fallback(ch)
        return bytes(out)
    return b"\x53" + _enc_str("null")

def pack_fallback(tree: Any) -> bytes:
    return _encode_node_fallback(tree)

# -----------------------------
# Template skeletonization:
# replace *all leaves* with placeholder marker "$"
# values are emitted in traversal order.
# -----------------------------
PLACEHOLDER = "$"

def make_skeleton_and_values(tree: Any) -> Tuple[Any, List[str]]:
    vals: List[str] = []

    def walk(n: Any) -> Any:
        if isinstance(n, str):
            vals.append(n)
            return PLACEHOLDER
        if isinstance(n, list):
            return [walk(x) for x in n]
        if isinstance(n, dict):
            return {k: walk(v) for k, v in n.items()}
        vals.append("null")
        return PLACEHOLDER

    skel = walk(tree)
    return skel, vals

def fill_skeleton(skel: Any, vals: List[str]) -> Any:
    it = iter(vals)

    def walk(n: Any) -> Any:
        if isinstance(n, str):
            if n == PLACEHOLDER:
                return next(it)
            return n
        if isinstance(n, list):
            return [walk(x) for x in n]
        if isinstance(n, dict):
            return {k: walk(v) for k, v in n.items()}
        return n

    out = walk(skel)
    # ensure fully consumed
    try:
        next(it)
        raise ValueError("extra values")
    except StopIteration:
        return out

# -----------------------------
# Catalog encoding:
# [0xE2][template_id(varint)][count(varint)][values...]
# Optional one-time catalog handshake: send K skeletons once.
# -----------------------------
CAT_MAGIC = 0xE2

def pack_catalog_msg(template_id: int, vals: List[str]) -> bytes:
    out = bytearray([CAT_MAGIC])
    out += _varint(template_id)
    out += _varint(len(vals))
    for s in vals:
        out += _enc_str(s)
    return bytes(out)

def unpack_catalog_msg(buf: bytes) -> Tuple[int, List[str]]:
    if not buf or buf[0] != CAT_MAGIC:
        raise ValueError("not catalog msg")
    i = 1
    tid, i = _read_varint(buf, i)
    n, i = _read_varint(buf, i)
    vals: List[str] = []
    for _ in range(n):
        s, i = _dec_str(buf, i)
        vals.append(s)
    if i != len(buf):
        raise ValueError("trailing bytes")
    return tid, vals

# -----------------------------
# Benchmark
# -----------------------------
@dataclass
class Result:
    depth: int
    families: int
    messages: int
    mutate_rate: float
    avg_json_gz: float
    avg_fallback_gz: float
    avg_catalog_gz: float
    savings_vs_json_gz: float
    savings_vs_fallback_gz: float
    handshake_overhead_gz: int
    roundtrip_fail: int

def mutate_values(vals: List[str], rng: random.Random, rate: float) -> List[str]:
    out = vals[:]
    for i in range(len(out)):
        if rng.random() < rate:
            out[i] = out[i] + "x"
    return out

def main() -> None:
    depth = int(os.environ.get("GLYPHOS_BENCH_DEPTH", "30"))
    families = int(os.environ.get("GLYPHOS_FAMILIES", "8"))
    messages = int(os.environ.get("GLYPHOS_MESSAGES", "5000"))
    mutate_rate = float(os.environ.get("GLYPHOS_MUTATE_RATE", "0.95"))
    seed = int(os.environ.get("GLYPHOS_SEED", "1"))
    skew = float(os.environ.get("GLYPHOS_SKEW", "0.8"))  # probability mass on top family
    rng = random.Random(seed)

    # Build catalog skeletons (K families)
    skeletons: List[Any] = []
    base_vals: List[List[str]] = []
    for v in range(families):
        t = make_glyph_tree(depth, v)
        sk, vals = make_skeleton_and_values(t)
        skeletons.append(sk)
        base_vals.append(vals)

    # Handshake overhead = send skeletons once (packed via fallback + gzip)
    handshake_raw = b"".join(pack_fallback(sk) for sk in skeletons)
    handshake_gz = len(gzip_bytes(handshake_raw))

    # Traffic distribution: heavy head
    weights = [skew] + [(1.0 - skew) / max(1, families - 1)] * (families - 1)

    json_gz_sizes: List[int] = []
    fb_gz_sizes: List[int] = []
    cat_gz_sizes: List[int] = []
    roundtrip_fail = 0

    t0 = time.perf_counter()
    for _ in range(messages):
        # choose family
        r = rng.random()
        acc = 0.0
        fam = 0
        for i, w in enumerate(weights):
            acc += w
            if r <= acc:
                fam = i
                break

        # make message by mutating values on that family
        vals = mutate_values(base_vals[fam], rng, mutate_rate)
        tree = fill_skeleton(skeletons[fam], vals)

        # JSON gz
        jgz = gzip_bytes(to_wire_json_bytes(tree))
        json_gz_sizes.append(len(jgz))

        # fallback gz
        fbgz = gzip_bytes(pack_fallback(tree))
        fb_gz_sizes.append(len(fbgz))

        # catalog gz
        cat = pack_catalog_msg(fam, vals)
        catgz = gzip_bytes(cat)
        cat_gz_sizes.append(len(catgz))

        # roundtrip
        try:
            tid, vals2 = unpack_catalog_msg(cat)
            tree2 = fill_skeleton(skeletons[tid], vals2)
            if tree2 != tree:
                roundtrip_fail += 1
        except Exception:
            roundtrip_fail += 1

    dur_ms = (time.perf_counter() - t0) * 1000.0

    avg_json_gz = sum(json_gz_sizes) / len(json_gz_sizes)
    avg_fb_gz = sum(fb_gz_sizes) / len(fb_gz_sizes)
    avg_cat_gz = sum(cat_gz_sizes) / len(cat_gz_sizes)

    savings_vs_json = 1.0 - (avg_cat_gz / avg_json_gz)
    savings_vs_fb = 1.0 - (avg_cat_gz / avg_fb_gz)

    print("\n=== ✅ GlyphOS WirePack v12 Multi-Template Catalog Benchmark ===")
    print(f"Depth (GLYPHOS_BENCH_DEPTH):        {depth}")
    print(f"Families (GLYPHOS_FAMILIES):        {families}")
    print(f"Messages (GLYPHOS_MESSAGES):        {messages}")
    print(f"Mutate rate (GLYPHOS_MUTATE_RATE):  {mutate_rate}")
    print(f"Skew (GLYPHOS_SKEW):                {skew}")
    print(f"Seed (GLYPHOS_SEED):                {seed}\n")

    print(f"Avg JSON (gzip):                    {avg_json_gz:.3f} B")
    print(f"Avg Fallback (gzip):                {avg_fb_gz:.3f} B")
    print(f"Avg Catalog msg (gzip):             {avg_cat_gz:.3f} B\n")

    print(f"✅ Savings vs JSON (gzip):           {savings_vs_json*100:.2f}%")
    print(f"✅ Savings vs fallback (gzip):       {savings_vs_fb*100:.2f}%\n")

    print(f"Handshake overhead (catalog, gzip): {handshake_gz} B  (one-time)")
    print(f"Roundtrip failures:                 {roundtrip_fail}/{messages}")
    print(f"Runtime:                            {dur_ms:.3f} ms\n")

    os.makedirs("./benchmarks", exist_ok=True)
    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "depth": depth,
        "families": families,
        "messages": messages,
        "mutate_rate": mutate_rate,
        "skew": skew,
        "seed": seed,
        "avg_json_gz": avg_json_gz,
        "avg_fallback_gz": avg_fb_gz,
        "avg_catalog_gz": avg_cat_gz,
        "savings_vs_json_gz": savings_vs_json,
        "savings_vs_fallback_gz": savings_vs_fb,
        "handshake_overhead_gz": handshake_gz,
        "roundtrip_fail": roundtrip_fail,
        "runtime_ms": dur_ms,
    }
    out_path = "./benchmarks/glyphos_wirepack_v12_multitemplate_catalog_latest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Saved:                              {out_path}\n")

if __name__ == "__main__":
    main()
