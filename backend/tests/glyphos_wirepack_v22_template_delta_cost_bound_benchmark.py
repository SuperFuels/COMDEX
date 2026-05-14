#!/usr/bin/env python3
"""
v22 — Template+Delta as a formal cost bound (measured)

Workload: a stable "plan template" (large) with small per-step parameter changes.
We compare:
  - naive_json_gz: each message sends full JSON (template+values)
  - delta_json_gz: send template once + per-message delta (only changed literals), gzipped together

Goal: demonstrate bytes scale with #mutations, not template depth/size.

This is a measurement harness (not the WirePack engine); it models the same transport shape.
"""

from __future__ import annotations

import gzip
import json
import random
import string
from dataclasses import dataclass
from typing import Dict, List, Tuple


MTU_PAYLOAD = 1200  # for packet-count estimate only


def gz_len(b: bytes) -> int:
    return len(gzip.compress(b, compresslevel=9))


def pkt_count(n_bytes: int, mtu_payload: int = MTU_PAYLOAD) -> int:
    return (n_bytes + mtu_payload - 1) // mtu_payload


def rand_ascii(rng: random.Random, n: int) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(rng.choice(alphabet) for _ in range(n))


@dataclass(frozen=True)
class Template:
    # stable schema / scaffolding / plan structure
    msg: Dict


@dataclass(frozen=True)
class Delta:
    # only the changed literals (path -> value)
    # paths are strings like "steps[17].params.alpha"
    changes: Dict[str, object]


def apply_delta(base: Dict, delta: Delta) -> Dict:
    """
    Apply a delta expressed as dotted-ish paths to a deep-copied dict.
    We keep this intentionally simple and deterministic for benchmarking.
    Supported path forms:
      - "k1.k2.k3"
      - "steps[17].params.alpha"
    """
    obj = json.loads(json.dumps(base))  # deterministic deep copy
    for path, value in delta.changes.items():
        cur = obj
        parts = path.split(".")
        for i, p in enumerate(parts):
            if "[" in p and p.endswith("]"):
                # e.g., steps[17]
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


def build_plan_template(depth_steps: int, header_kv: int, rng: random.Random) -> Template:
    """
    Build a large, stable plan template with many steps and a "scaffolding" header block.
    Only a few numeric/string literals will vary per message.
    """
    headers = {f"x-h{i}": f"v{rand_ascii(rng, 12)}" for i in range(header_kv)}
    plan = {
        "system": {
            "name": "GlyphOS-Plan",
            "version": "v22",
            "tooling": {"schemas": [rand_ascii(rng, 24) for _ in range(16)]},
            "headers": headers,
        },
        "plan": {
            "id": "PLAN-" + rand_ascii(rng, 16),
            "steps": [],
        },
    }

    # big structured scaffold: many steps with nested params
    for i in range(depth_steps):
        step = {
            "op": "compute",
            "idx": i,
            "params": {
                "alpha": 0.001,
                "beta": 0.1,
                "gamma": 10,
                "mode": "fast",
                "salt": rand_ascii(rng, 8),
            },
            "policy": {
                "retry": {"max": 3, "backoff_ms": 20},
                "timeout_ms": 250,
                "region": "edge-eu",
            },
        }
        plan["plan"]["steps"].append(step)

    return Template(msg=plan)


def mk_delta_for_message(
    rng: random.Random,
    depth_steps: int,
    n_mutations: int,
    msg_index: int,
) -> Delta:
    """
    Create a delta that changes only n_mutations literals.
    We vary:
      - a few step params (alpha/beta/gamma/mode)
      - plus a per-message nonce/request id (fixed path)
    """
    changes: Dict[str, object] = {}

    # per-message varying nonce: always present (counts as 1 "mutation" if you want)
    # but we keep it separate so n_mutations means "extra mutations" beyond the nonce.
    changes["plan.request_id"] = f"REQ-{msg_index:06d}"

    # choose some step indices and fields
    fields = ["alpha", "beta", "gamma", "mode"]
    for _ in range(n_mutations):
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
        changes[f"plan.steps[{si}].params.{f}"] = v

    return Delta(changes=changes)


def bench(depth_steps: int, header_kv: int, n_msgs: int, muts: int, seed: int) -> Tuple[int, int]:
    rng = random.Random(seed)
    t = build_plan_template(depth_steps=depth_steps, header_kv=header_kv, rng=rng)

    # naive: full msg every time
    naive_msgs: List[bytes] = []
    # delta stream: template once + per-msg deltas
    deltas: List[bytes] = []

    for i in range(n_msgs):
        d = mk_delta_for_message(rng=rng, depth_steps=depth_steps, n_mutations=muts, msg_index=i)
        full = apply_delta(t.msg, d)
        naive_msgs.append(json.dumps(full, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        deltas.append(json.dumps(d.changes, separators=(",", ":"), sort_keys=True).encode("utf-8"))

    # gzip "stream"
    naive_stream = b"\n".join(naive_msgs)
    template_bytes = json.dumps(t.msg, separators=(",", ":"), sort_keys=True).encode("utf-8")
    delta_stream = template_bytes + b"\n" + b"\n".join(deltas)

    naive_gz = gz_len(naive_stream)
    delta_gz = gz_len(delta_stream)
    return naive_gz, delta_gz


def main() -> None:
    print("=== ✅ Bridge Benchmark v22: Template+Delta cost bound (mutations not depth) ===")
    print("Model: large stable plan template; per-message only 1–5 literals change.")
    print("")
    print(f"Assumption: mtu_payload={MTU_PAYLOAD} bytes (used only to estimate packet counts)")
    print("")

    # You can tune these; keep deterministic for locks
    seed = 22022
    header_kv = 128
    n_msgs = 256

    # depth sweep: shows template size growth
    depths = [32, 64, 128]

    # mutation sweep: key claim
    muts_list = [1, 2, 3, 5]

    print("depth | muts | n_msgs | naive_gz | delta_gz | gz_ratio(naive/delta) | pkts_naive | pkts_delta | pkts_ratio")
    print("-----:|-----:|------:|---------:|---------:|----------------------:|-----------:|-----------:|----------:")

    for depth in depths:
        for muts in muts_list:
            naive_gz, delta_gz = bench(
                depth_steps=depth,
                header_kv=header_kv,
                n_msgs=n_msgs,
                muts=muts,
                seed=seed + depth * 10 + muts,
            )
            ratio = (naive_gz / delta_gz) if delta_gz else float("inf")
            pk_n = pkt_count(naive_gz)
            pk_d = pkt_count(delta_gz)
            pk_ratio = (pk_n / pk_d) if pk_d else float("inf")
            print(
                f"{depth:5d} | {muts:4d} | {n_msgs:5d} | {naive_gz:8d} | {delta_gz:8d} | {ratio:22.2f} | "
                f"{pk_n:10d} | {pk_d:10d} | {pk_ratio:10.2f}"
            )


if __name__ == "__main__":
    main()