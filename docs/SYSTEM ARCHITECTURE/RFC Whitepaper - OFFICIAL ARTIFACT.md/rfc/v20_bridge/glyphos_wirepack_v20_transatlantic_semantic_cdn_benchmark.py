import gzip
import json
import math
import random


def gz_len(b: bytes) -> int:
    # deterministic gzip (mtime=0) so lockfiles don't drift
    return len(gzip.compress(b, compresslevel=9, mtime=0))


def packets(n_bytes: int, mtu_payload: int) -> int:
    return int(math.ceil(n_bytes / mtu_payload))


def make_headers(header_kv: int) -> dict:
    # HTTP-ish headers; most are stable across requests in agent loops
    base = {
        "host": "api.example.com",
        "user-agent": "glyphos-gateway/1.0",
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": "Bearer sk-REDACTED",
        "x-region-src": "london",
        "x-region-dst": "newyork",
    }
    # add a bunch of stable-ish KV noise (typical enterprise headers / tracing / feature flags)
    for i in range(header_kv):
        base[f"x-kv-{i:03d}"] = f"val-{i:03d}"
    return base


def make_body_template(depth: int) -> dict:
    # “shape” = tool defs + system prompt scaffolding + structured metadata
    # depth scales the template (simulates larger tool schemas / longer system scaffolds)
    tools = []
    for i in range(max(1, depth // 2)):
        tools.append(
            {
                "name": f"tool_{i}",
                "schema": {
                    "type": "object",
                    "properties": {f"p{j}": {"type": "string"} for j in range(3)},
                    "required": ["p0"],
                },
            }
        )

    system_blocks = [f"SYS_BLOCK_{i}: you MUST follow policy." for i in range(depth)]
    system_prompt = "\n".join(system_blocks)

    # delta fields will vary per request
    return {
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "tools": tools,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "{{USER_PROMPT}}"},
        ],
        "metadata": {
            "trace": {"span": "{{SPAN_ID}}", "parent": "{{PARENT_SPAN}}"},
            "session": "{{SESSION_ID}}",
        },
    }


def instantiate_request(headers: dict, body_template: dict, user_prompt: str, span: str, parent: str, session: str) -> bytes:
    # clone+fill placeholders (string replace is enough for the benchmark)
    body_json = json.dumps(body_template, separators=(",", ":"), ensure_ascii=False)
    body_json = (
        body_json.replace("{{USER_PROMPT}}", user_prompt)
        .replace("{{SPAN_ID}}", span)
        .replace("{{PARENT_SPAN}}", parent)
        .replace("{{SESSION_ID}}", session)
    )
    req = {
        "headers": headers,
        "body": json.loads(body_json),
    }
    return (json.dumps(req, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def make_delta(rng: random.Random, depth: int) -> dict:
    # small delta: user question + ids
    # prompt size scales mildly with depth (simulates deeper reasoning loops adding a bit more content)
    prompt_words = 8 + (depth // 8)
    prompt = " ".join([f"w{rng.randrange(1000)}" for _ in range(prompt_words)])
    return {
        "user_prompt": prompt,
        "span": f"{rng.randrange(10**12):012d}",
        "parent": f"{rng.randrange(10**12):012d}",
        "session": f"s{rng.randrange(10**8):08d}",
    }


def main() -> None:
    print("=== ✅ Bridge Benchmark v20: Transatlantic semantic CDN (template sync + deltas) ===")
    print("Model: repeated HTTP+JSON request shape (headers + tool/system scaffolding); only small deltas vary.\n")

    mtu_payload = 1200  # conservative “safe payload” (TLS + overhead -> you rarely get full 1500B)
    print(f"Assumption: mtu_payload={mtu_payload} bytes (used only to estimate packet counts)\n")

    print(
        "depth | header_kv | k_msgs | naive_gz | glyph_gz | gz_ratio(naive/glyph) | pkts_naive | pkts_glyph | pkts_ratio"
    )
    print("-----:|----------:|------:|---------:|---------:|----------------------:|-----------:|-----------:|----------:")

    # deterministic
    rng = random.Random(1337)

    cases = [
        # (depth, header_kv, k_msgs)
        (8, 64, 64),
        (16, 64, 128),
        (32, 128, 128),
        (64, 128, 256),
    ]

    for depth, header_kv, k in cases:
        headers = make_headers(header_kv)
        body_template = make_body_template(depth)

        # naive stream: send full request k times (gzip at transport)
        naive_stream = b""
        deltas = []
        for _ in range(k):
            d = make_delta(rng, depth)
            deltas.append(d)
            naive_stream += instantiate_request(headers, body_template, d["user_prompt"], d["span"], d["parent"], d["session"])

        naive_gz = gz_len(naive_stream)

        # glyph stream: send template once + deltas list
        template_pkg = {
            "headers": headers,
            "body_template": body_template,
        }
        glyph_pkg = {
            "template": template_pkg,
            "deltas": deltas,
        }
        glyph_stream = (json.dumps(glyph_pkg, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
        glyph_gz = gz_len(glyph_stream)

        ratio = (naive_gz / glyph_gz) if glyph_gz else float("inf")
        pk_naive = packets(naive_gz, mtu_payload)
        pk_glyph = packets(glyph_gz, mtu_payload)
        pk_ratio = (pk_naive / pk_glyph) if pk_glyph else float("inf")

        print(
            f"{depth:5d} | {header_kv:9d} | {k:6d} | {naive_gz:8d} | {glyph_gz:8d} | {ratio:22.2f} |"
            f" {pk_naive:10d} | {pk_glyph:10d} | {pk_ratio:9.2f}"
        )


if __name__ == "__main__":
    main()