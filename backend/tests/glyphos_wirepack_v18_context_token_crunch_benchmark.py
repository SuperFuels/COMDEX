#!/usr/bin/env python3
import gzip
import json

# Deterministic JSON bytes (stable separators + sorted keys)
def js_bytes(obj) -> bytes:
    return json.dumps(obj, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode("utf-8")

def gz_len(b: bytes) -> int:
    return len(gzip.compress(b, compresslevel=9))

def make_template(depth: int, header_kv: int):
    # “Boilerplate” that repeats in every message:
    # - system-ish metadata
    # - schema-ish blobs
    # - tool-ish descriptors
    header = {f"h{j:03d}": f"VAL_{j:03d}" for j in range(header_kv)}
    schema = {
        "role": "system",
        "version": "v18",
        "tool_schema": [{"name": f"tool_{i}", "args": {"a": "int", "b": "str"}} for i in range(depth)],
        "policy": {"allow": ["read", "write"], "deny": []},
    }
    return {"header": header, "schema": schema}

def make_delta(i: int):
    # Small per-message variation
    return {
        "msg_id": i,
        "intent": "call",
        "args": {"x": i, "y": f"str_{i%97}"},
        "trace": f"t{i%13}",
    }

def bench(depth: int, header_kv: int, k_msgs: int):
    template = make_template(depth=depth, header_kv=header_kv)

    # Baseline: naive stream (every message repeats template+delta)
    naive_stream = []
    for i in range(k_msgs):
        naive_stream.append({"template": template, "delta": make_delta(i)})

    # Glyph-style: send template once, then deltas
    glyph_stream = {"template": template, "deltas": [make_delta(i) for i in range(k_msgs)]}

    b_naive = js_bytes(naive_stream)
    b_glyph = js_bytes(glyph_stream)

    return {
        "naive_raw": len(b_naive),
        "naive_gz": gz_len(b_naive),
        "glyph_raw": len(b_glyph),
        "glyph_gz": gz_len(b_glyph),
    }

def main():
    print("=== ✅ Bridge Benchmark v18: Context/token crunch (template+delta vs naive) ===")
    print("Model: k messages repeat a large template; only small deltas vary.\n")
    print("depth | header_kv | k_msgs | naive_raw | naive_gz | glyph_raw | glyph_gz | gz_ratio(naive/glyph)")
    print("-----:|----------:|------:|----------:|---------:|----------:|---------:|-------------------:")

    # Deterministic grid; keep small enough for CI but representative
    cases = [
        (8, 64, 64),
        (16, 64, 128),
        (32, 128, 128),
        (64, 128, 256),
    ]

    for depth, header_kv, k_msgs in cases:
        r = bench(depth=depth, header_kv=header_kv, k_msgs=k_msgs)
        ratio = (r["naive_gz"] / r["glyph_gz"]) if r["glyph_gz"] else float("inf")
        print(
            f"{depth:>5} | {header_kv:>9} | {k_msgs:>5} | "
            f"{r['naive_raw']:>9} | {r['naive_gz']:>8} | "
            f"{r['glyph_raw']:>9} | {r['glyph_gz']:>8} | {ratio:>19.2f}"
        )

if __name__ == "__main__":
    main()