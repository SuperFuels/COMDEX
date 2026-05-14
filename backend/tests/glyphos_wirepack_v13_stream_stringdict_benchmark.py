from __future__ import annotations

import gzip
import json
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

# -----------------------------
# Operators (consistent)
# -----------------------------
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

# raw string encoding tag (same flavor as your fallback pack)
def _encode_string_raw(s: str) -> bytes:
    b = s.encode("utf-8")
    return bytes([0x53]) + _varint(len(b)) + b

def _decode_string_raw(buf: bytes, i: int) -> Tuple[str, int]:
    if buf[i] != 0x53:
        raise ValueError("expected string tag 0x53")
    i += 1
    n, i = _read_varint(buf, i)
    s = buf[i : i + n].decode("utf-8")
    return s, i + n

# -----------------------------
# Fallback pack (v5-ish): arity=2 elision
# -----------------------------
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
# Template family generator (same idea as v12)
# -----------------------------
def make_family_template(family_id: int, depth_steps: int) -> Dict[str, Any]:
    branch1 = {"⊕": [{"⊕": ["A1", "B1"]}, {"⟲": ["A2", "B2"]}]}

    subtree: Any = {"⟲": ["Z3", "Z4"]}
    subtree = {"->": [{"->": ["Z1", "Z2"]}, subtree]}

    rot = family_id % 5
    slot = 0
    for i in range(depth_steps):
        mod = (i + rot) % 5
        a = f"${slot}"; slot += 1
        b = f"${slot}"; slot += 1
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

def count_slots(tmpl: Any) -> int:
    mx = -1
    def walk(n: Any) -> None:
        nonlocal mx
        if isinstance(n, str) and n.startswith("$"):
            mx = max(mx, int(n[1:]))
        elif isinstance(n, list):
            for x in n:
                walk(x)
        elif isinstance(n, dict):
            for _, v in n.items():
                walk(v)
    walk(tmpl)
    return mx + 1

def instantiate_template(tmpl: Any, values: List[str]) -> Any:
    if isinstance(tmpl, str):
        if tmpl.startswith("$"):
            idx = int(tmpl[1:])
            return values[idx]
        return tmpl
    if isinstance(tmpl, list):
        return [instantiate_template(x, values) for x in tmpl]
    if isinstance(tmpl, dict):
        return {k: instantiate_template(v, values) for k, v in tmpl.items()}
    return tmpl

# -----------------------------
# Traffic sampler (Zipf-like)
# -----------------------------
def sample_family(rng: random.Random, families: int, skew: float) -> int:
    weights = [1.0 / ((k + 1) ** skew) for k in range(families)]
    total = sum(weights)
    r = rng.random() * total
    acc = 0.0
    for k, w in enumerate(weights):
        acc += w
        if r <= acc:
            return k
    return families - 1

# -----------------------------
# Value model: mixture of "hot" tokens + "cold" unique values
# -----------------------------
def make_value_pool(pool_size: int) -> List[str]:
    # Intentionally “real-ish” repeated tokens
    base = [
        "tool:search", "tool:calc", "tool:fetch", "tool:store",
        "role:user", "role:system", "role:assistant",
        "status:ok", "status:error", "status:retry",
        "domain:payments", "domain:policy", "domain:qa", "domain:infra",
        "region:us", "region:eu", "region:apac",
        "model:gpt", "model:small", "model:large",
        "cache:hit", "cache:miss",
        "auth:ed25519", "auth:none",
    ]
    # Expand deterministically
    out = []
    i = 0
    while len(out) < pool_size:
        out.append(base[i % len(base)] + f":{i}")
        i += 1
    return out

def make_values(rng: random.Random, n: int, mutate_rate: float, hot_pool: List[str], hot_share: float) -> List[str]:
    vals: List[str] = []
    for i in range(n):
        if rng.random() < hot_share:
            vals.append(rng.choice(hot_pool))
        else:
            # cold values: high mutation -> mostly unique
            if rng.random() < mutate_rate:
                vals.append(f"v{i}_{rng.randint(0, 10**9)}")
            else:
                vals.append(f"v{i}_CONST")
    return vals

# -----------------------------
# v12 Stream (templates + raw strings per message)
# -----------------------------
_V12_MAGIC = 0xCC

def encode_v12_stream(templates: Dict[int, Any], messages: List[Tuple[int, List[str]]]) -> bytes:
    out = bytearray()
    out.append(_V12_MAGIC)

    out += _varint(len(templates))
    for tid, tmpl in templates.items():
        tb = pack_fallback(tmpl)
        out += _varint(tid)
        out += _varint(len(tb))
        out += tb

    out += _varint(len(messages))
    for tid, vals in messages:
        out += _varint(tid)
        out += _varint(len(vals))
        for s in vals:
            out += _encode_string_raw(s)
    return bytes(out)

# -----------------------------
# v13 Stream (templates + global string dictionary + varint refs)
# -----------------------------
_V13_MAGIC = 0xCD

def encode_v13_stream(templates: Dict[int, Any], messages: List[Tuple[int, List[str]]]) -> bytes:
    # Build dictionary from all message values
    # (Yes O(total_values) – fine for benchmark; production could cap/evict.)
    freq: Dict[str, int] = {}
    for _, vals in messages:
        for s in vals:
            freq[s] = freq.get(s, 0) + 1

    # Keep strings that occur at least twice (others are cheaper inline)
    dict_strings = [s for s, c in freq.items() if c >= 2]
    dict_strings.sort(key=lambda s: (-freq[s], s))  # stable ordering

    dict_index = {s: i for i, s in enumerate(dict_strings)}

    out = bytearray()
    out.append(_V13_MAGIC)

    # templates block (same as v12)
    out += _varint(len(templates))
    for tid, tmpl in templates.items():
        tb = pack_fallback(tmpl)
        out += _varint(tid)
        out += _varint(len(tb))
        out += tb

    # dictionary block
    out += _varint(len(dict_strings))
    for s in dict_strings:
        out += _encode_string_raw(s)

    # messages block
    out += _varint(len(messages))
    for tid, vals in messages:
        out += _varint(tid)
        out += _varint(len(vals))
        for s in vals:
            idx = dict_index.get(s)
            if idx is None:
                # inline marker 0 + raw string
                out += _varint(0)
                out += _encode_string_raw(s)
            else:
                # dict marker 1 + varint index
                out += _varint(1)
                out += _varint(idx)
    return bytes(out)

def decode_v13_stream(buf: bytes) -> List[Any]:
    if not buf or buf[0] != _V13_MAGIC:
        raise ValueError("bad v13 magic")
    i = 1

    tcount, i = _read_varint(buf, i)
    templates: Dict[int, Any] = {}
    for _ in range(tcount):
        tid, i = _read_varint(buf, i)
        blen, i = _read_varint(buf, i)
        tb = buf[i : i + blen]
        i += blen
        templates[tid] = unpack_fallback(tb)

    dcount, i = _read_varint(buf, i)
    dict_strings: List[str] = []
    for _ in range(dcount):
        s, i = _decode_string_raw(buf, i)
        dict_strings.append(s)

    mcount, i = _read_varint(buf, i)
    out_msgs: List[Any] = []
    for _ in range(mcount):
        tid, i = _read_varint(buf, i)
        vcount, i = _read_varint(buf, i)
        vals: List[str] = []
        for _ in range(vcount):
            kind, i = _read_varint(buf, i)
            if kind == 0:
                s, i = _decode_string_raw(buf, i)
                vals.append(s)
            elif kind == 1:
                idx, i = _read_varint(buf, i)
                vals.append(dict_strings[idx])
            else:
                raise ValueError("bad value kind")
        out_msgs.append(instantiate_template(templates[tid], vals))

    if i != len(buf):
        raise ValueError("trailing bytes")
    return out_msgs

# -----------------------------
# Results
# -----------------------------
@dataclass
class BenchOut:
    timestamp: str
    depth: int
    families: int
    messages: int
    skew: float
    mutate_rate: float
    hot_pool: int
    hot_share: float
    avg_json_gz: float
    avg_fallback_gz: float
    avg_v12_gz: float
    avg_v13_gz: float
    v12_vs_fb: float
    v13_vs_fb: float
    v13_vs_v12: float
    roundtrip_fail: int
    runtime_ms: float

def main() -> None:
    depth = int(os.environ.get("GLYPHOS_BENCH_DEPTH", "30"))
    families = int(os.environ.get("GLYPHOS_FAMILIES", "32"))
    messages_n = int(os.environ.get("GLYPHOS_MESSAGES", "20000"))
    skew = float(os.environ.get("GLYPHOS_SKEW", "0.9"))
    mutate_rate = float(os.environ.get("GLYPHOS_MUTATE_RATE", "0.95"))
    hot_pool_n = int(os.environ.get("GLYPHOS_HOT_POOL", "256"))
    hot_share = float(os.environ.get("GLYPHOS_HOT_SHARE", "0.60"))
    seed = int(os.environ.get("GLYPHOS_SEED", "1"))

    rng = random.Random(seed)
    t0 = time.perf_counter()

    hot_pool = make_value_pool(hot_pool_n)

    # templates
    templates: Dict[int, Any] = {}
    slots: Dict[int, int] = {}
    for fid in range(families):
        tmpl = make_family_template(fid, depth)
        templates[fid] = tmpl
        slots[fid] = count_slots(tmpl)

    # messages
    msgs: List[Any] = []
    msg_meta: List[Tuple[int, List[str]]] = []
    for _ in range(messages_n):
        fid = sample_family(rng, families, skew)
        vals = make_values(rng, slots[fid], mutate_rate, hot_pool, hot_share)
        msg_meta.append((fid, vals))
        msgs.append(instantiate_template(templates[fid], vals))

    # baselines: per-message gzip
    json_gz_sizes: List[int] = []
    fb_gz_sizes: List[int] = []
    for m in msgs:
        json_gz_sizes.append(len(gzip_bytes(to_wire_json_bytes(m))))
        fb_gz_sizes.append(len(gzip_bytes(pack_fallback(m))))

    avg_json_gz = sum(json_gz_sizes) / len(json_gz_sizes)
    avg_fb_gz = sum(fb_gz_sizes) / len(fb_gz_sizes)

    # v12 stream
    v12_raw = encode_v12_stream(templates, msg_meta)
    v12_gz = gzip_bytes(v12_raw)
    avg_v12_gz = len(v12_gz) / messages_n

    # v13 stream
    v13_raw = encode_v13_stream(templates, msg_meta)
    v13_gz = gzip_bytes(v13_raw)
    avg_v13_gz = len(v13_gz) / messages_n

    # roundtrip on v13
    decoded = decode_v13_stream(v13_raw)
    rt_fail = 0
    for a, b in zip(decoded, msgs):
        if a != b:
            rt_fail += 1

    # ratios
    v12_vs_fb = (avg_fb_gz / avg_v12_gz) if avg_v12_gz else 0.0
    v13_vs_fb = (avg_fb_gz / avg_v13_gz) if avg_v13_gz else 0.0
    v13_vs_v12 = (avg_v12_gz / avg_v13_gz) if avg_v13_gz else 0.0

    dur_ms = (time.perf_counter() - t0) * 1000.0

    print("\n=== ✅ GlyphOS WirePack v13 Stream StringDict Benchmark ===")
    print(f"Depth (GLYPHOS_BENCH_DEPTH):        {depth}")
    print(f"Families (GLYPHOS_FAMILIES):        {families}")
    print(f"Messages (GLYPHOS_MESSAGES):        {messages_n}")
    print(f"Skew (GLYPHOS_SKEW):                {skew}")
    print(f"Mutate rate (GLYPHOS_MUTATE_RATE):  {mutate_rate}")
    print(f"Hot pool (GLYPHOS_HOT_POOL):        {hot_pool_n}")
    print(f"Hot share (GLYPHOS_HOT_SHARE):      {hot_share}")
    print(f"Seed (GLYPHOS_SEED):                {seed}\n")

    print(f"Avg per-message JSON gzip:          {avg_json_gz:.3f} B")
    print(f"Avg per-message fallback gzip:      {avg_fb_gz:.3f} B")
    print(f"Avg per-message v12 stream gzip:    {avg_v12_gz:.3f} B")
    print(f"Avg per-message v13 stream gzip:    {avg_v13_gz:.3f} B\n")

    print(f"✅ v12 improvement vs fallback:      {v12_vs_fb:.3f}x")
    print(f"✅ v13 improvement vs fallback:      {v13_vs_fb:.3f}x")
    print(f"✅ v13 improvement vs v12:           {v13_vs_v12:.3f}x")
    print(f"Roundtrip failures (v13):           {rt_fail}/{messages_n}")
    print(f"Runtime:                            {dur_ms:.3f} ms\n")

    out = BenchOut(
        timestamp=datetime.now(timezone.utc).isoformat(),
        depth=depth,
        families=families,
        messages=messages_n,
        skew=skew,
        mutate_rate=mutate_rate,
        hot_pool=hot_pool_n,
        hot_share=hot_share,
        avg_json_gz=avg_json_gz,
        avg_fallback_gz=avg_fb_gz,
        avg_v12_gz=avg_v12_gz,
        avg_v13_gz=avg_v13_gz,
        v12_vs_fb=v12_vs_fb,
        v13_vs_fb=v13_vs_fb,
        v13_vs_v12=v13_vs_v12,
        roundtrip_fail=rt_fail,
        runtime_ms=dur_ms,
    )

    os.makedirs("./benchmarks", exist_ok=True)
    out_path = "./benchmarks/glyphos_wirepack_v13_stream_stringdict_latest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out.__dict__, f, indent=2)

    print(f"Saved:                              {out_path}\n")

if __name__ == "__main__":
    main()
