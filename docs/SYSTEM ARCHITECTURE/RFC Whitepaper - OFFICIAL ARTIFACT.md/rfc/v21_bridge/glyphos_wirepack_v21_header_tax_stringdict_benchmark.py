import gzip
import json
import math
import hashlib

MTU_PAYLOAD = 1200  # used only to estimate packet counts

COMMON_HEADERS = [
    ("Authorization", "Bearer"),
    ("Content-Type", "application/json"),
    ("Accept", "application/json"),
    ("User-Agent", "glyphos-agent/1.0"),
    ("x-forwarded-proto", "https"),
    ("x-forwarded-for", "203.0.113.9"),
    ("x-env", "prod"),
    ("x-service", "gateway"),
    ("x-region", "eu-west"),
    ("x-trace-sampled", "1"),
]

def json_bytes(obj) -> bytes:
    # stable encoding for lock reproducibility
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")

def gz_len(b: bytes) -> int:
    return len(gzip.compress(b, compresslevel=9))

def pkt_count(nbytes: int) -> int:
    return math.ceil(nbytes / MTU_PAYLOAD) if nbytes > 0 else 0

def build_stream(n_msgs: int, headers: list[tuple[str, str]]):
    msgs = []
    for i in range(n_msgs):
        # variable parts to keep this realistic
        req = {
            "method": "POST",
            "path": "/v1/infer",
            "headers": {k: v for (k, v) in headers},
            "body": {
                "model": "glyphos",
                "input": "ping",
                "x-request-id": f"req-{i:06d}",
                "jwt": f"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.{i:06d}.sig",
            },
        }
        msgs.append(req)
    return msgs

def build_dict_encoding(msgs):
    """
    v13-style stream dict:
      - dict: unique repeated strings (header keys + common header values + some stable literals)
      - msgs: per-message structure uses integer refs for dict strings, plus raw variable fields
    """
    dict_strings = []

    def intern(s: str) -> int:
        try:
            return dict_strings.index(s)
        except ValueError:
            dict_strings.append(s)
            return len(dict_strings) - 1

    # Intern header keys/values + a few stable literals (method/path keys)
    for m in msgs:
        for k, v in m["headers"].items():
            intern(k)
            intern(v)
    intern("POST")
    intern("/v1/infer")
    intern("glyphos")
    intern("ping")

    encoded_msgs = []
    for m in msgs:
        hdr_refs = []
        for k, v in m["headers"].items():
            hdr_refs.append([intern(k), intern(v)])
        encoded_msgs.append({
            "m": intern(m["method"]),
            "p": intern(m["path"]),
            "h": hdr_refs,
            # keep the varying fields raw (they are the “deltas”)
            "rid": m["body"]["x-request-id"],
            "jwt": m["body"]["jwt"],
        })

    return {"dict": dict_strings, "msgs": encoded_msgs}

def main():
    print("=== ✅ Bridge Benchmark v21: Header tax (JWT/microservice headers) via stream StringDict ===")
    print("Model: request stream with repeated HTTP header strings; per-request id + jwt vary.\n")
    print(f"Assumption: mtu_payload={MTU_PAYLOAD} bytes (used only to estimate packet counts)\n")

    print("n_msgs | headers | json_gz | dict_gz | gz_ratio(json/dict) | pkts_json | pkts_dict | pkts_ratio")
    print("-----:|--------:|-------:|-------:|---------------------:|---------:|---------:|----------:")

    regimes = [64, 128, 256, 512]
    headers = COMMON_HEADERS + [("x-request-id", "STATIC_PLACEHOLDER")]  # key repeats; value is effectively delta

    for n in regimes:
        msgs = build_stream(n, headers)

        # Plain JSON stream: concatenate as a list
        plain = {"msgs": msgs}
        plain_b = json_bytes(plain)
        plain_gz = gz_len(plain_b)

        # Dict encoding (v13-style), then gzip
        d = build_dict_encoding(msgs)
        dict_b = json_bytes(d)
        dict_gz = gz_len(dict_b)

        ratio = (plain_gz / dict_gz) if dict_gz else float("inf")

        pk_plain = pkt_count(plain_gz)
        pk_dict = pkt_count(dict_gz)
        pk_ratio = (pk_plain / pk_dict) if pk_dict else float("inf")

        print(
            f"{n:5d} | {len(headers):7d} | {plain_gz:7d} | {dict_gz:7d} | {ratio:21.2f} |"
            f" {pk_plain:9d} | {pk_dict:9d} | {pk_ratio:10.2f}"
        )

if __name__ == "__main__":
    main()