# 📁 backend/tests/glyphos_wirepack_v11_subtree_intern_benchmark.py
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

def gzip_bytes(b: bytes, level: int = 9) -> bytes:
    return gzip.compress(b, compresslevel=level)

def to_wire_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=False).encode("utf-8")

# -----------------------------
# Canonical generator + controlled variation
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

def mutate_values(tree: Any, rng: random.Random, mutate_rate: float) -> Any:
    t = json.loads(json.dumps(tree, ensure_ascii=False))
    def walk(n: Any) -> Any:
        if isinstance(n, str):
            if rng.random() < mutate_rate:
                return n + "_" + str(rng.randrange(10_000))
            return n
        if isinstance(n, list):
            return [walk(x) for x in n]
        if isinstance(n, dict):
            return {k: walk(v) for k, v in n.items()}
        return n
    return walk(t)

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

# -----------------------------
# Fallback pack (v5-ish)
# -----------------------------
def _encode_string_raw(s: str) -> bytes:
    b = s.encode("utf-8")
    return bytes([0x53]) + _varint(len(b)) + b

def _encode_node(node: Any) -> bytes:
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
            out += _encode_node(ch)
        return bytes(out)
    if isinstance(node, list):
        out = bytearray()
        out.append(0xD0)
        out.append(OP_TAG["->"])
        out.append(0xA0)
        out += _varint(len(node))
        for ch in node:
            out += _encode_node(ch)
        return bytes(out)
    return _encode_string_raw("null")

def pack_fallback(tree: Any) -> bytes:
    return _encode_node(tree)

# -----------------------------
# Subtree interning encoder (stream-level)
# - define: [0xF2][id varint][len varint][subtree_bytes]
# - ref:    [0xF3][id varint]
# -----------------------------
def pack_intern_stream(trees: List[Any], max_dict: int = 50_000) -> bytes:
    table: Dict[bytes, int] = {}
    next_id = 1
    out = bytearray()
    out.append(0xE2)  # stream magic
    out.append(0x01)  # version

    for tree in trees:
        # naive but effective: intern whole-message bytes first (fast win),
        # then you can extend later to intern mid-subtrees.
        b = pack_fallback(tree)
        if b in table:
            out.append(0xF3)
            out += _varint(table[b])
        else:
            if len(table) < max_dict:
                table[b] = next_id
                out.append(0xF2)
                out += _varint(next_id)
                out += _varint(len(b))
                out += b
                next_id += 1
            else:
                # dict full: just write raw subtree bytes in a "define" with id=0 (no intern)
                out.append(0xF2)
                out += _varint(0)
                out += _varint(len(b))
                out += b

    return bytes(out)

@dataclass
class Result:
    timestamp: str
    depth: int
    messages: int
    mutate_rate: float
    avg_json_gz: float
    avg_fallback_gz: float
    stream_intern_bytes: int
    stream_intern_gz_bytes: int
    avg_stream_intern_gz: float
    improvement_vs_json_gz: float
    improvement_vs_fallback_gz: float

def main() -> None:
    depth = int(os.environ.get("GLYPHOS_BENCH_DEPTH", "30"))
    messages = int(os.environ.get("GLYPHOS_MESSAGES", "5000"))
    seed = int(os.environ.get("GLYPHOS_SEED", "1"))
    mutate_rate = float(os.environ.get("GLYPHOS_MUTATE_RATE", "0.90"))
    canonical_share = float(os.environ.get("GLYPHOS_CANONICAL_SHARE", "0.10"))

    rng = random.Random(seed)
    base = make_glyph_tree(depth)

    trees: List[Any] = []
    for _ in range(messages):
        if rng.random() < canonical_share:
            trees.append(base)
        else:
            trees.append(mutate_values(base, rng, mutate_rate))

    t0 = time.perf_counter()

    json_gz_total = sum(len(gzip_bytes(to_wire_json_bytes(t))) for t in trees)
    fb_gz_total = sum(len(gzip_bytes(pack_fallback(t))) for t in trees)

    stream = pack_intern_stream(trees)
    stream_gz = gzip_bytes(stream)

    dur_ms = (time.perf_counter() - t0) * 1000.0

    avg_json_gz = json_gz_total / messages
    avg_fb_gz = fb_gz_total / messages
    avg_stream_gz = len(stream_gz) / messages

    res = Result(
        timestamp=datetime.now(timezone.utc).isoformat(),
        depth=depth,
        messages=messages,
        mutate_rate=mutate_rate,
        avg_json_gz=avg_json_gz,
        avg_fallback_gz=avg_fb_gz,
        stream_intern_bytes=len(stream),
        stream_intern_gz_bytes=len(stream_gz),
        avg_stream_intern_gz=avg_stream_gz,
        improvement_vs_json_gz=(avg_json_gz / avg_stream_gz) if avg_stream_gz else 0.0,
        improvement_vs_fallback_gz=(avg_fb_gz / avg_stream_gz) if avg_stream_gz else 0.0,
    )

    print("\n=== ✅ GlyphOS WirePack v11 Subtree Intern (Stream) Benchmark ===")
    print(f"Depth (GLYPHOS_BENCH_DEPTH):           {depth}")
    print(f"Messages (GLYPHOS_MESSAGES):           {messages}")
    print(f"Mutate rate (GLYPHOS_MUTATE_RATE):     {mutate_rate}")
    print(f"Canonical share (GLYPHOS_CANONICAL_SHARE): {canonical_share}")
    print(f"Seed (GLYPHOS_SEED):                   {seed}\n")

    print(f"Avg per-message JSON gzip:             {avg_json_gz:.3f} B")
    print(f"Avg per-message fallback gzip:         {avg_fb_gz:.3f} B")
    print(f"Stream intern total (raw):             {len(stream)} B")
    print(f"Stream intern total (gzip):            {len(stream_gz)} B")
    print(f"Avg per-message stream intern gzip:    {avg_stream_gz:.3f} B\n")

    print(f"✅ Improvement vs JSON gzip (avg):      {res.improvement_vs_json_gz:.3f}x")
    print(f"✅ Improvement vs fallback gzip (avg):  {res.improvement_vs_fallback_gz:.3f}x")
    print(f"Runtime:                               {dur_ms:.3f} ms\n")

    os.makedirs("./benchmarks", exist_ok=True)
    out_path = "./benchmarks/glyphos_wirepack_v11_subtree_intern_latest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res.__dict__, f, indent=2)
    print(f"Saved:                                 {out_path}\n")

if __name__ == "__main__":
    main()
