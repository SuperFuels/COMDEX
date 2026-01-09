#!/usr/bin/env python3
"""
v25 — Cross-format comparison harness (measurement only)

Harness emits apples-to-apples sizes for a structured "program traffic" stream:
  - JSON (raw + gzip)
  - (optional) CBOR (raw + gzip)   [disabled by default for lock stability]
  - (optional) Protobuf            [disabled by default]
  - WirePack-mode models:
      * WP-StringDict (dictionary once + per-message refs), raw + gzip
      * WP-Template+Delta (template once + per-message deltas), raw + gzip

This is a workload+transport-shaped measurement harness (not the production encoder).
It is deterministic under fixed seeds and prints a drift_sha256 for regression tracking.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import random
import string
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple

MTU_PAYLOAD = 1200  # packet-count estimate only


def _gz_compress(data: bytes, level: int = 9) -> bytes:
    # Prefer deterministic gzip output (mtime=0) if available.
    try:
        return gzip.compress(data, compresslevel=level, mtime=0)  # py3.8+
    except TypeError:
        return gzip.compress(data, compresslevel=level)


def gz_len(data: bytes) -> int:
    return len(_gz_compress(data, level=9))


def pkt_count(n_bytes: int, mtu_payload: int = MTU_PAYLOAD) -> int:
    return (n_bytes + mtu_payload - 1) // mtu_payload


def rand_ascii(rng: random.Random, n: int) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(rng.choice(alphabet) for _ in range(n))


# -------------------------
# Workload: structured stream
# -------------------------

@dataclass(frozen=True)
class Workload:
    template: Dict[str, Any]
    deltas: List[Dict[str, Any]]  # per-message sparse updates (paths -> value)


def build_workload(seed: int, depth_steps: int, header_kv: int, n_msgs: int, muts_per_msg: int) -> Workload:
    rng = random.Random(seed)

    # Stable repeated headers / keys / scaffolding (gives JSON+CBOR something real to compress)
    headers = {
        "Authorization": "Bearer",
        "Content-Type": "application/json",
        "x-service": "glyphos-edge",
        "x-region": "eu",
        "x-trace-mode": "full",
    }
    # Add extra stable header-ish kv to increase vocab/entropy (still stable)
    for i in range(header_kv):
        headers[f"x-h{i}"] = f"v{rand_ascii(rng, 12)}"

    template: Dict[str, Any] = {
        "system": {
            "name": "GlyphOS-ProgramStream",
            "version": "v25",
            "headers": headers,
            "schemas": [rand_ascii(rng, 24) for _ in range(16)],
        },
        "plan": {
            "id": "PLAN-" + rand_ascii(rng, 16),
            "steps": [],
            "request_id": "REQ-000000",  # overwritten per msg
            "jwt": "JWT-" + ("A" * 64),  # overwritten per msg
        },
    }

    for i in range(depth_steps):
        template["plan"]["steps"].append(
            {
                "op": "compute",
                "idx": i,
                "params": {
                    "alpha": 0.001,
                    "beta": 0.1,
                    "gamma": 10,
                    "mode": "fast",
                    "salt": rand_ascii(rng, 8),  # stable but random-looking
                },
                "policy": {
                    "retry": {"max": 3, "backoff_ms": 20},
                    "timeout_ms": 250,
                    "region": "edge-eu",
                },
            }
        )

    # Per-message deltas: always include request_id + jwt, plus muts_per_msg step tweaks
    fields = ["alpha", "beta", "gamma", "mode"]
    deltas: List[Dict[str, Any]] = []
    for msg_i in range(n_msgs):
        d: Dict[str, Any] = {
            "plan.request_id": f"REQ-{msg_i:06d}",
            "plan.jwt": f"JWT-{rand_ascii(rng, 128)}",
        }
        for _ in range(muts_per_msg):
            si = rng.randrange(depth_steps)
            f = rng.choice(fields)
            if f == "alpha":
                v = round(0.0001 + rng.random() * 0.01, 6)
            elif f == "beta":
                v = round(0.05 + rng.random() * 0.5, 4)
            elif f == "gamma":
                v = rng.randrange(1, 200)
            else:
                v = rng.choice(["fast", "safe", "turbo"])
            d[f"plan.steps[{si}].params.{f}"] = v
        deltas.append(d)

    return Workload(template=template, deltas=deltas)


def apply_delta(base: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
    # deterministic deep copy via JSON (keys sorted later at encode time)
    obj = json.loads(json.dumps(base))
    for path, value in delta.items():
        cur: Any = obj
        parts = path.split(".")
        for i, p in enumerate(parts):
            if "[" in p and p.endswith("]"):
                key, idx_s = p[:-1].split("[", 1)
                idx = int(idx_s)
                if i == len(parts) - 1:
                    cur[key][idx] = value
                else:
                    cur = cur[key][idx]
            else:
                if i == len(parts) - 1:
                    cur[p] = value
                else:
                    cur = cur[p]
    return obj


# -------------------------
# Encoders
# -------------------------

def encode_json_stream(msgs: List[Dict[str, Any]]) -> bytes:
    lines = [json.dumps(m, separators=(",", ":"), sort_keys=True) for m in msgs]
    return ("\n".join(lines)).encode("utf-8")


def encode_template_delta_stream(template: Dict[str, Any], deltas: List[Dict[str, Any]]) -> bytes:
    t = json.dumps(template, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ds = [json.dumps(d, separators=(",", ":"), sort_keys=True).encode("utf-8") for d in deltas]
    return t + b"\n" + b"\n".join(ds)


def gather_strings(obj: Any, out: set) -> None:
    # Collect all string atoms + all dict keys
    if isinstance(obj, str):
        out.add(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str):
                out.add(k)
            gather_strings(v, out)
    elif isinstance(obj, list):
        for x in obj:
            gather_strings(x, out)


def build_string_dict(template: Dict[str, Any]) -> List[str]:
    s: set = set()
    gather_strings(template, s)
    return sorted(s)


def dict_blob(strings: List[str]) -> bytes:
    # very simple deterministic dictionary blob:
    #   N\n
    #   <len>:<utf8>\n ...
    # (not the production wire format; just a stable size proxy)
    chunks = [f"{len(strings)}\n".encode("utf-8")]
    for st in strings:
        b = st.encode("utf-8")
        chunks.append(f"{len(b)}:".encode("utf-8") + b + b"\n")
    return b"".join(chunks)


def replace_with_refs(obj: Any, s2i: Dict[str, int]) -> Any:
    # Replace strings with small ints for stable tokens (keys + values).
    if isinstance(obj, str):
        return {"$s": s2i.get(obj, -1), "$v": obj} if obj not in s2i else s2i[obj]
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            kk = s2i.get(k, None)
            k_out = str(kk) if kk is not None else k  # keys become small numeric strings
            out[k_out] = replace_with_refs(v, s2i)
        return out
    if isinstance(obj, list):
        return [replace_with_refs(x, s2i) for x in obj]
    return obj  # numbers/bools/null unchanged


def encode_stringdict_stream(template: Dict[str, Any], msgs: List[Dict[str, Any]]) -> bytes:
    strings = build_string_dict(template)
    s2i = {s: i for i, s in enumerate(strings)}
    dblob = dict_blob(strings)

    # Per-message: JSON of the ref-rewritten object (still deterministic).
    # This models “dictionary once + small refs per message”.
    lines = []
    for m in msgs:
        mr = replace_with_refs(m, s2i)
        lines.append(json.dumps(mr, separators=(",", ":"), sort_keys=True).encode("utf-8"))

    return dblob + b"\n" + b"\n".join(lines)


def encode_cbor_stream(msgs: List[Dict[str, Any]]) -> bytes:
    # optional; only used if enabled and dependency exists
    import cbor2  # type: ignore
    # pack as an array of msgs for deterministic framing
    return cbor2.dumps(msgs)


# -------------------------
# Benchmark
# -------------------------

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fmt_int_or_na(x: int | None) -> str:
    return "n/a" if x is None else str(x)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=25025)
    ap.add_argument("--depth", type=int, default=96)
    ap.add_argument("--headers", type=int, default=96)
    ap.add_argument("--n", type=int, default=512)
    ap.add_argument("--muts", type=int, default=3)
    ap.add_argument("--enable-cbor", action="store_true", default=False)
    args = ap.parse_args()

    w = build_workload(
        seed=args.seed,
        depth_steps=args.depth,
        header_kv=args.headers,
        n_msgs=args.n,
        muts_per_msg=args.muts,
    )

    msgs = [apply_delta(w.template, d) for d in w.deltas]

    print("=== ✅ Bridge Benchmark v25: Cross-format comparison harness (JSON/CBOR optional + WirePack modes) ===")
    print(f"seed={args.seed} depth={args.depth} headers={args.headers} n_msgs={args.n} muts={args.muts}")
    print(f"Assumption: mtu_payload={MTU_PAYLOAD} bytes (used only to estimate packet counts)")
    print("")

    # Canonical stream drift hash (regression anchor)
    json_stream = encode_json_stream(msgs)
    print(f"drift_sha256(json_stream)= {sha256_hex(json_stream)}")
    print("")

    rows: List[Tuple[str, bytes]] = []

    rows.append(("json_raw", json_stream))
    rows.append(("json_gz", _gz_compress(json_stream)))

    # CBOR optional
    cbor_raw: bytes | None = None
    cbor_gz: bytes | None = None
    if args.enable_cbor:
        try:
            cbor_raw = encode_cbor_stream(msgs)
            cbor_gz = _gz_compress(cbor_raw)
        except Exception as e:
            print(f"CBOR disabled (import/encode failed): {e}")
    # WirePack-mode models
    wp_dict_raw = encode_stringdict_stream(w.template, msgs)
    wp_delta_raw = encode_template_delta_stream(w.template, w.deltas)

    rows.append(("wp_stringdict_raw", wp_dict_raw))
    rows.append(("wp_stringdict_gz", _gz_compress(wp_dict_raw)))

    rows.append(("wp_template_delta_raw", wp_delta_raw))
    rows.append(("wp_template_delta_gz", _gz_compress(wp_delta_raw)))

    # Print table
    print("encoder | bytes | pkts")
    print("-------:|------:|----:")
    for name, blob in rows:
        print(f"{name:21s} | {len(blob):5d} | {pkt_count(len(blob)):4d}")

    # Add CBOR rows consistently (even when disabled)
    print("")
    print("cbor_encoder | bytes | pkts")
    print("-----------:|------:|----:")
    if cbor_raw is None or cbor_gz is None:
        print("cbor_raw     | n/a   | n/a")
        print("cbor_gz      | n/a   | n/a")
    else:
        print(f"cbor_raw     | {len(cbor_raw):5d} | {pkt_count(len(cbor_raw)):4d}")
        print(f"cbor_gz      | {len(cbor_gz):5d} | {pkt_count(len(cbor_gz)):4d}")

    # Ratios vs json_gz for quick “receipts”
    print("")
    json_gz_len = len(_gz_compress(json_stream))
    print("ratio_vs_json_gz")
    print("--------------:")
    for name, blob in rows:
        if name.endswith("_gz"):
            r = (json_gz_len / len(blob)) if len(blob) else float("inf")
            print(f"{name:21s}: {r:0.2f}x")


if __name__ == "__main__":
    main()