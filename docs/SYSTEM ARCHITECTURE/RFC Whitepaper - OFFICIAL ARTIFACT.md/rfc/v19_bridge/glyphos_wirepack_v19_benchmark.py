#!/usr/bin/env python3
import gzip
import json

def gz_len(b: bytes) -> int:
    return len(gzip.compress(b, compresslevel=9))

def make_template(depth: int, header_kv: int) -> dict:
    # A nested "shape" with many repeated keys/structure to simulate prompt boilerplate.
    node = {"type": "root", "meta": {f"k{i}": f"v{i}" for i in range(header_kv)}}
    cur = node
    for i in range(depth):
        nxt = {"op": "call", "name": "tool", "args": {"x": 1, "y": 2}, "next": None}
        cur["next"] = nxt
        cur = nxt
    return node

def make_delta(i: int) -> dict:
    # Only a tiny varying part per message.
    return {"delta": {"msg_id": i, "value": i % 7}}

def naive_payload(template: dict, delta: dict) -> dict:
    # Naive: resend everything.
    return {"template": template, "delta": delta}

def glyph_payload_once(template: dict) -> bytes:
    # Template transmitted once (simulated).
    return json.dumps({"template": template}, separators=(",", ":"), sort_keys=True).encode("utf-8")

def glyph_payload_delta(delta: dict) -> bytes:
    # Then only deltas each message.
    return json.dumps({"delta": delta}, separators=(",", ":"), sort_keys=True).encode("utf-8")

def main():
    print("=== ✅ Bridge Benchmark v19: Context/token amortization (template+delta vs naive) ===")
    print("Model: k messages repeat a large template; only small deltas vary.\n")
    print("depth | header_kv | k_msgs | naive_raw | naive_gz | glyph_raw | glyph_gz | gz_ratio(naive/glyph)")
    print("-----:|----------:|------:|----------:|---------:|----------:|---------:|-------------------:")

    # Keep these stable for lock files.
    cases = [
        (8,   64,  64),
        (16,  64, 128),
        (32, 128, 128),
        (64, 128, 256),
    ]

    for depth, header_kv, k in cases:
        tmpl = make_template(depth, header_kv)

        # naive: sum over k full messages
        naive_msgs = []
        for i in range(k):
            payload = naive_payload(tmpl, make_delta(i))
            naive_msgs.append(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        naive_raw = sum(len(m) for m in naive_msgs)
        naive_gz = gz_len(b"".join(naive_msgs))

        # glyph: template once + k deltas
        tmpl_bytes = glyph_payload_once(tmpl)
        delta_bytes = [glyph_payload_delta(make_delta(i)) for i in range(k)]
        glyph_raw = len(tmpl_bytes) + sum(len(b) for b in delta_bytes)
        glyph_gz = gz_len(tmpl_bytes + b"".join(delta_bytes))

        ratio = (naive_gz / glyph_gz) if glyph_gz else float("inf")
        print(f"{depth:5d} | {header_kv:9d} | {k:5d} | {naive_raw:10d} | {naive_gz:8d} | {glyph_raw:10d} | {glyph_gz:8d} | {ratio:19.2f}")

if __name__ == "__main__":
    main()