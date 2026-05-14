# 📁 backend/tests/glyphos_wirepack_v10_template_delta_benchmark.py
from __future__ import annotations

import gzip
import json
import os
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, Optional

# -----------------------------
# Config / helpers
# -----------------------------
OPS = {"↔", "⊕", "⟲", "->", "⧖"}
OP_TAG = {"↔": 1, "⊕": 2, "⟲": 3, "->": 4, "⧖": 5}
TAG_OP = {v: k for k, v in OP_TAG.items()}

def to_wire_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=False).encode("utf-8")

def gzip_bytes(b: bytes, level: int = 9) -> bytes:
    return gzip.compress(b, compresslevel=level)

# -----------------------------
# Canonical generator (same family)
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
# Template matcher: SAME SHAPE FAMILY, but ignores constant literal values.
# (This is what makes v10 powerful: structure is recognized even when args vary.)
# -----------------------------
_L_RE = re.compile(r"^L(\d+)_([12])$")

def _is_base_tail(node: Any) -> bool:
    # {"->": [{"->": [Z1, Z2]}, {"⟲": [Z3, Z4]}]} but literals may vary (strings)
    if not (isinstance(node, dict) and len(node) == 1 and "->" in node):
        return False
    v = node["->"]
    if not (isinstance(v, list) and len(v) == 2):
        return False
    a, b = v[0], v[1]
    if not (isinstance(a, dict) and len(a) == 1 and "->" in a):
        return False
    av = a["->"]
    if not (isinstance(av, list) and len(av) == 2 and all(isinstance(x, str) for x in av)):
        return False
    if not (isinstance(b, dict) and len(b) == 1 and "⟲" in b):
        return False
    bv = b["⟲"]
    if not (isinstance(bv, list) and len(bv) == 2 and all(isinstance(x, str) for x in bv)):
        return False
    return True

def _match_and_extract_depth_loose(tree: Any) -> Tuple[bool, int]:
    # Root
    if not isinstance(tree, dict) or len(tree) != 1 or "↔" not in tree:
        return (False, -1)
    pair = tree["↔"]
    if not (isinstance(pair, list) and len(pair) == 2):
        return (False, -1)
    branch1, cur = pair[0], pair[1]

    # branch1 shape only (literals can vary)
    if not (isinstance(branch1, dict) and len(branch1) == 1 and "⊕" in branch1):
        return (False, -1)
    b1 = branch1["⊕"]
    if not (isinstance(b1, list) and len(b1) == 2):
        return (False, -1)
    if not (isinstance(b1[0], dict) and b1[0].get("⊕") and isinstance(b1[0]["⊕"], list) and len(b1[0]["⊕"]) == 2):
        return (False, -1)
    if not (isinstance(b1[1], dict) and b1[1].get("⟲") and isinstance(b1[1]["⟲"], list) and len(b1[1]["⟲"]) == 2):
        return (False, -1)

    # Walk the -> spine counting wrappers until we hit the base tail
    depth = 0
    start_i: Optional[int] = None
    prev_i: Optional[int] = None
    last_i: Optional[int] = None

    while not _is_base_tail(cur):
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

        # op cycle must match generator (based on i%5)
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

        if start_i is None:
            start_i = i0
        if prev_i is not None and i0 != prev_i - 1:
            return (False, -1)

        prev_i = i0
        last_i = i0
        depth += 1
        cur = right

        if depth > 1_000_000:
            return (False, -1)

    # strict depth identity: must end at L0 and start at L(depth-1)
    if last_i != 0:
        return (False, -1)
    if start_i != depth - 1:
        return (False, -1)

    return (True, depth)

# -----------------------------
# v10 Template+Delta wire format
# -----------------------------
# [0xCA][variant=1][depth varint][delta_count varint] then deltas:
#   [slot_id varint][value_len varint][utf8 bytes]
#
# Slots are fixed paths in the canonical tree. This keeps decoding deterministic.
_V10_MAGIC = 0xCA
_V10_VARIANT = 1

# Slot mapping (constants in make_glyph_tree)
# 0:A1 1:B1 2:A2 3:B2 4:Z1 5:Z2 6:Z3 7:Z4
def _find_base_tail_node(tree: Any) -> Dict[str, Any]:
    cur = tree["↔"][1]
    for _ in range(2_000_000):
        if _is_base_tail(cur):
            return cur
        cur = cur["->"][1]
    raise ValueError("base tail not found")

def _get_slots(tree: Any) -> List[str]:
    # branch1 slots
    a1 = tree["↔"][0]["⊕"][0]["⊕"][0]
    b1 = tree["↔"][0]["⊕"][0]["⊕"][1]
    a2 = tree["↔"][0]["⊕"][1]["⟲"][0]
    b2 = tree["↔"][0]["⊕"][1]["⟲"][1]

    base = _find_base_tail_node(tree)
    z1 = base["->"][0]["->"][0]
    z2 = base["->"][0]["->"][1]
    z3 = base["->"][1]["⟲"][0]
    z4 = base["->"][1]["⟲"][1]
    return [a1, b1, a2, b2, z1, z2, z3, z4]

def _set_slot(tree: Any, slot: int, value: str) -> None:
    if slot == 0:
        tree["↔"][0]["⊕"][0]["⊕"][0] = value
    elif slot == 1:
        tree["↔"][0]["⊕"][0]["⊕"][1] = value
    elif slot == 2:
        tree["↔"][0]["⊕"][1]["⟲"][0] = value
    elif slot == 3:
        tree["↔"][0]["⊕"][1]["⟲"][1] = value
    else:
        base = _find_base_tail_node(tree)
        if slot == 4:
            base["->"][0]["->"][0] = value
        elif slot == 5:
            base["->"][0]["->"][1] = value
        elif slot == 6:
            base["->"][1]["⟲"][0] = value
        elif slot == 7:
            base["->"][1]["⟲"][1] = value
        else:
            raise ValueError("bad slot id")

def pack_v10_template_delta(tree: Any) -> Tuple[bytes, bool, int, int]:
    ok, depth = _match_and_extract_depth_loose(tree)
    if not ok:
        return pack_fallback(tree), False, -1, 0

    # default template values (baseline) for this depth
    templ = make_glyph_tree(depth)
    want = _get_slots(templ)
    have = _get_slots(tree)

    deltas: List[Tuple[int, str]] = []
    for i, (w, h) in enumerate(zip(want, have)):
        if h != w:
            deltas.append((i, h))

    out = bytearray()
    out.append(_V10_MAGIC)
    out.append(_V10_VARIANT)
    out += _varint(depth)
    out += _varint(len(deltas))
    for sid, sval in deltas:
        vb = sval.encode("utf-8")
        out += _varint(sid)
        out += _varint(len(vb))
        out += vb

    return bytes(out), True, depth, len(deltas)

def unpack_v10(buf: bytes) -> Any:
    if len(buf) >= 2 and buf[0] == _V10_MAGIC and buf[1] == _V10_VARIANT:
        i = 2
        depth, i = _read_varint(buf, i)
        n, i = _read_varint(buf, i)
        t = make_glyph_tree(depth)
        for _ in range(n):
            sid, i = _read_varint(buf, i)
            ln, i = _read_varint(buf, i)
            s = buf[i : i + ln].decode("utf-8")
            i += ln
            _set_slot(t, sid, s)
        if i != len(buf):
            raise ValueError("trailing bytes")
        return t
    return unpack_fallback(buf)

# -----------------------------
# Message generator: same shape, varying literals
# -----------------------------
def _rand_token(rng: random.Random, msg_idx: int, slot: int) -> str:
    # Short-ish tokens so we measure structure savings, not giant strings.
    # (Real systems often have short args/ids; long blobs should be chunked elsewhere.)
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    n = rng.randint(4, 10)
    core = "".join(rng.choice(alphabet) for _ in range(n))
    return f"v{slot}_{msg_idx}_{core}"

def make_message(depth: int, rng: random.Random, mutate_rate: float) -> Dict[str, Any]:
    t = make_glyph_tree(depth)
    # mutate only the 8 constant slots; keep L{i}_1/2 intact so we stay in-family
    for sid in range(8):
        if rng.random() < mutate_rate:
            _set_slot(t, sid, _rand_token(rng, msg_idx=rng.randint(0, 1_000_000_000), slot=sid))
    return t

# -----------------------------
# Benchmark
# -----------------------------
@dataclass
class Result:
    timestamp: str
    depth: int
    messages: int
    mutate_rate: float

    avg_json: float
    avg_json_gz: float

    avg_fallback: float
    avg_fallback_gz: float

    avg_v10: float
    avg_v10_gz: float

    savings_vs_fallback_raw_pct: float
    savings_vs_fallback_gz_pct: float
    savings_vs_json_gz_pct: float

    template_hits: int
    roundtrip_fail: int

def _pct_savings(a: float, b: float) -> float:
    # savings of b vs a: 1 - b/a
    if a <= 0:
        return 0.0
    return (1.0 - (b / a)) * 100.0

def run(depth: int, messages: int, mutate_rate: float, seed: int) -> Result:
    rng = random.Random(seed)
    t0 = time.perf_counter()

    json_sizes: List[int] = []
    json_gz_sizes: List[int] = []
    fb_sizes: List[int] = []
    fb_gz_sizes: List[int] = []
    v10_sizes: List[int] = []
    v10_gz_sizes: List[int] = []

    hits = 0
    rt_fail = 0

    # preflight: canonical (no mutations) must match family + extract correct depth
    ok, d = _match_and_extract_depth_loose(make_glyph_tree(depth))
    if not ok or d != depth:
        raise RuntimeError(f"(preflight) template matcher failed for depth={depth}: ok={ok} extract={d}")

    for _ in range(messages):
        tree = make_message(depth, rng, mutate_rate)

        j = to_wire_json_bytes(tree)
        jg = gzip_bytes(j)

        fb = pack_fallback(tree)
        fbg = gzip_bytes(fb)

        packed, is_template, _, _ = pack_v10_template_delta(tree)
        pg = gzip_bytes(packed)

        if is_template:
            hits += 1

        # roundtrip must hold
        try:
            decoded = unpack_v10(packed)
            if decoded != tree:
                rt_fail += 1
        except Exception:
            rt_fail += 1

        json_sizes.append(len(j))
        json_gz_sizes.append(len(jg))
        fb_sizes.append(len(fb))
        fb_gz_sizes.append(len(fbg))
        v10_sizes.append(len(packed))
        v10_gz_sizes.append(len(pg))

    dur_ms = (time.perf_counter() - t0) * 1000.0

    avg_json = sum(json_sizes) / len(json_sizes)
    avg_json_gz = sum(json_gz_sizes) / len(json_gz_sizes)
    avg_fb = sum(fb_sizes) / len(fb_sizes)
    avg_fb_gz = sum(fb_gz_sizes) / len(fb_gz_sizes)
    avg_v10 = sum(v10_sizes) / len(v10_sizes)
    avg_v10_gz = sum(v10_gz_sizes) / len(v10_gz_sizes)

    return Result(
        timestamp=datetime.now(timezone.utc).isoformat(),
        depth=depth,
        messages=messages,
        mutate_rate=mutate_rate,

        avg_json=avg_json,
        avg_json_gz=avg_json_gz,

        avg_fallback=avg_fb,
        avg_fallback_gz=avg_fb_gz,

        avg_v10=avg_v10,
        avg_v10_gz=avg_v10_gz,

        savings_vs_fallback_raw_pct=_pct_savings(avg_fb, avg_v10),
        savings_vs_fallback_gz_pct=_pct_savings(avg_fb_gz, avg_v10_gz),
        savings_vs_json_gz_pct=_pct_savings(avg_json_gz, avg_v10_gz),

        template_hits=hits,
        roundtrip_fail=rt_fail,
    )

def main() -> None:
    depth = int(os.environ.get("GLYPHOS_BENCH_DEPTH", "30"))
    messages = int(os.environ.get("GLYPHOS_MESSAGES", "1000"))
    mutate_rate = float(os.environ.get("GLYPHOS_MUTATE_RATE", "0.95"))
    seed = int(os.environ.get("GLYPHOS_SEED", "1"))

    res = run(depth=depth, messages=messages, mutate_rate=mutate_rate, seed=seed)

    print("\n=== ✅ GlyphOS WirePack v10 Template+Delta Benchmark ===")
    print(f"Depth (GLYPHOS_BENCH_DEPTH):        {depth}")
    print(f"Messages (GLYPHOS_MESSAGES):        {messages}")
    print(f"Mutate rate (GLYPHOS_MUTATE_RATE):  {mutate_rate}")
    print(f"Seed (GLYPHOS_SEED):                {seed}\n")

    print(f"Avg JSON:                           {res.avg_json:.3f} B")
    print(f"Avg JSON (gzip):                    {res.avg_json_gz:.3f} B\n")

    print(f"Avg Fallback (v5-ish):              {res.avg_fallback:.3f} B")
    print(f"Avg Fallback (gzip):               {res.avg_fallback_gz:.3f} B\n")

    print(f"Avg v10 (template+delta):           {res.avg_v10:.3f} B")
    print(f"Avg v10 (gzip):                    {res.avg_v10_gz:.3f} B\n")

    print(f"✅ Savings vs fallback (raw):        {res.savings_vs_fallback_raw_pct:.2f}%")
    print(f"✅ Savings vs fallback (gzip):       {res.savings_vs_fallback_gz_pct:.2f}%")
    print(f"✅ Savings vs JSON (gzip):           {res.savings_vs_json_gz_pct:.2f}%\n")

    print(f"Template hits:                      {res.template_hits}/{messages}")
    print(f"Roundtrip failures:                 {res.roundtrip_fail}/{messages}\n")

    out = {
        **res.__dict__,
        "runtime_note": "avg sizes only; see printed output",
    }
    os.makedirs("./benchmarks", exist_ok=True)
    out_path = "./benchmarks/glyphos_wirepack_v10_template_delta_latest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(f"Saved:                              {out_path}\n")

if __name__ == "__main__":
    main()
