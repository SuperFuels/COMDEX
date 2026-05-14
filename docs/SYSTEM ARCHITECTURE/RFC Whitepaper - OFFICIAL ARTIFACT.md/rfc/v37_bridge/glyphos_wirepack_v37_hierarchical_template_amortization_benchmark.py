#!/usr/bin/env python3
"""
v37 — Hierarchical Template Amortization (fleet → model → per-unit delta)

Goal:
Compare baseline "snapshot-per-unit" vs hierarchical encoding:
- ship fleet template once
- ship model templates once per subgroup
- ship per-unit deltas

Outputs:
- raw bytes and gzip bytes (level 9)
- ratio(snapshot/hier)
- verify_ok (reconstruction matches snapshots for fixed sample indices)
- drift_sha256 (audit stability)
"""

import gzip
import hashlib
import json
from typing import Any, Dict, List, Tuple


def canon_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def gz_len(b: bytes) -> int:
    return len(gzip.compress(b, compresslevel=9))


def sha256(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def deep_merge(a: Any, b: Any) -> Any:
    # Dict-recursive merge; b overrides a.
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            if k in out:
                out[k] = deep_merge(out[k], v)
            else:
                out[k] = v
        return out
    return b


def make_fleet_template(depth: int, headers: int) -> Dict[str, Any]:
    # Big repeated scaffolding to make amortization obvious.
    steps: List[Dict[str, Any]] = []
    for i in range(depth):
        steps.append(
            {
                "op": "step",
                "i": i,
                "cfg": {"mode": "run", "k": i % 7, "label": f"S{i % 16}"},
            }
        )
    hdr = {f"h{i}": "X-REPEATED-HEADER-VALUE" for i in range(headers)}
    return {"fleet_ver": 1, "headers": hdr, "steps": steps, "shared": {"policy": "default", "ttl": 60}}


def make_model_template(model_id: int, model_depth: int) -> Dict[str, Any]:
    # Medium repeated content per model subgroup.
    params: List[Dict[str, Any]] = []
    for j in range(model_depth):
        params.append({"p": j, "mode": "M", "tag": f"M{model_id % 8}", "gain": (model_id + j) % 97})
    return {"model": {"id": model_id, "params": params, "limits": {"vmax": 12, "imax": 3}}}


def make_unit_delta(unit_id: int, model_id: int) -> Dict[str, Any]:
    # Small per-unit overrides (the “changes scale with m not n” piece).
    return {
        "unit": {
            "id": unit_id,
            "model": model_id,
            "serial": f"U{unit_id:05d}",
            "cal": {"bias": unit_id % 13, "scale": (unit_id * 17) % 101},
        }
    }


def materialize(fleet_t: Dict[str, Any], model_t: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
    return deep_merge(deep_merge(fleet_t, model_t), delta)


def build(
    n_units: int,
    n_models: int,
    depth: int,
    headers: int,
    model_depth: int,
) -> Tuple[bytes, List[bytes], List[bytes], List[bytes]]:
    fleet_t = make_fleet_template(depth=depth, headers=headers)
    fleet_b = canon_bytes(fleet_t)

    model_bs: List[bytes] = []
    models: List[Dict[str, Any]] = []
    for mid in range(n_models):
        mt = make_model_template(mid, model_depth=model_depth)
        models.append(mt)
        model_bs.append(canon_bytes(mt))

    # unit snapshots + unit deltas
    snapshot_bs: List[bytes] = []
    delta_bs: List[bytes] = []

    for uid in range(n_units):
        mid = uid % n_models
        d = make_unit_delta(uid, mid)
        s = materialize(fleet_t, models[mid], d)
        snapshot_bs.append(canon_bytes(s))
        delta_bs.append(canon_bytes(d))

    return fleet_b, model_bs, delta_bs, snapshot_bs


def main() -> None:
    # Deterministic parameters (keep stable for locks)
    seed = 37037  # informational (generation is deterministic)
    n_units = 4096
    n_models = 64

    # Scaffolding sizes
    depth = 192
    headers = 96
    model_depth = 48

    fleet_b, model_bs, delta_bs, snapshot_bs = build(
        n_units=n_units, n_models=n_models, depth=depth, headers=headers, model_depth=model_depth
    )

    # Streams:
    stream_snapshot = b"".join(snapshot_bs)
    stream_hier = fleet_b + b"".join(model_bs) + b"".join(delta_bs)

    # Verify reconstruction for fixed sample units
    samples = [0, 1, 17, 999, 2048, 4095]
    fleet_t = json.loads(fleet_b.decode("utf-8"))
    models = [json.loads(b.decode("utf-8")) for b in model_bs]
    verify_ok = True
    for uid in samples:
        mid = uid % n_models
        d = json.loads(delta_bs[uid].decode("utf-8"))
        mat = materialize(fleet_t, models[mid], d)
        if canon_bytes(mat) != snapshot_bs[uid]:
            verify_ok = False
            break

    raw_snapshot = len(stream_snapshot)
    raw_hier = len(stream_hier)

    gz_snapshot = gz_len(stream_snapshot)
    gz_hier = gz_len(stream_hier)

    drift = sha256(
        sha256(fleet_b)
        + sha256(b"".join(model_bs))
        + sha256(b"".join(delta_bs[:256]))  # fixed prefix for stability check
        + sha256(b"".join(snapshot_bs[:64]))
    ).hex()

    model_avg = sum(len(b) for b in model_bs) // len(model_bs)
    delta_avg = sum(len(b) for b in delta_bs) // len(delta_bs)
    snap_avg = sum(len(b) for b in snapshot_bs) // len(snapshot_bs)

    print("v37_hierarchical_template_amortization")
    print(f"seed={seed}")
    print(f"n_units={n_units} n_models={n_models} units_per_model={n_units//n_models}")
    print(f"depth={depth} headers={headers} model_depth={model_depth}")
    print(f"fleet_template_bytes={len(fleet_b)}")
    print(f"model_template_bytes_each_avg={model_avg}")
    print(f"unit_delta_bytes_each_avg={delta_avg}")
    print(f"unit_snapshot_bytes_each_avg={snap_avg}")
    print(f"verify_ok={verify_ok}")

    print(f"raw_snapshot_total={raw_snapshot}")
    print(f"raw_hier_total={raw_hier}")
    print(f"raw_ratio(snapshot/hier)={(raw_snapshot / raw_hier):.6f}")

    print(f"gz_snapshot_total={gz_snapshot}")
    print(f"gz_hier_total={gz_hier}")
    print(f"gz_ratio(snapshot/hier)={(gz_snapshot / gz_hier):.6f}")

    print(f"drift_sha256={drift}")


if __name__ == "__main__":
    main()