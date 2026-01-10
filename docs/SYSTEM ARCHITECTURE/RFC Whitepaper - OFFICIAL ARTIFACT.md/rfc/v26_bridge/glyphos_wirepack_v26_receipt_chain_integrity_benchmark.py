#!/usr/bin/env python3
"""
v26 — Receipt Chain Integrity (Authenticated Delta Receipt + ancestry binding)

Design goals:
- Canonical bytes (stable): JSON canonicalization via sort_keys + tight separators.
- Receipt digest: H(alg_id || template_hash || delta_hash || parent || phase_id || schema_ver)
  but encoded unambiguously with fixed-width fields.
- Authentication: HMAC-SHA256 over receipt_digest (symmetric trust domain, cheap).
- Ancestry binding: parent = previous receipt_hash (sha256(receipt_digest || tag)).
- Bench: measure overhead for template+delta vs template+delta+receipt (raw + gzip).
"""

import gzip
import hmac
import hashlib
import json
import struct
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


def canon_bytes(obj: Any) -> bytes:
    # Stable canonical JSON bytes.
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def hmac_sha256(key: bytes, msg: bytes) -> bytes:
    return hmac.new(key, msg, hashlib.sha256).digest()


def gz_len(b: bytes) -> int:
    return len(gzip.compress(b, compresslevel=9))


def u32le(x: int) -> bytes:
    return struct.pack("<I", x)


ZERO32 = b"\x00" * 32


@dataclass(frozen=True)
class Receipt:
    alg_id: int          # u8
    schema_ver: int      # u32
    phase_id: int        # u32
    template_hash: bytes # 32
    delta_hash: bytes    # 32
    parent: bytes        # 32
    tag: bytes           # 32 (HMAC)

    def preimage(self) -> bytes:
        # Fixed, unambiguous layout:
        # u8 alg_id || u32 schema_ver || u32 phase_id || 32 template_hash || 32 delta_hash || 32 parent
        return bytes([self.alg_id]) + u32le(self.schema_ver) + u32le(self.phase_id) + self.template_hash + self.delta_hash + self.parent

    def digest(self) -> bytes:
        return sha256(self.preimage())

    def receipt_hash(self) -> bytes:
        # Hash of authenticated receipt material (what gets chained).
        return sha256(self.digest() + self.tag)

    def bytes_on_wire(self) -> bytes:
        # What we actually ship per-message: preimage + tag
        return self.preimage() + self.tag


def make_template(depth: int, headers: int) -> Dict[str, Any]:
    # Deterministic big-ish structure with repeated keys.
    steps: List[Dict[str, Any]] = []
    for i in range(depth):
        steps.append({
            "op": "step",
            "i": i,
            "cfg": {"mode": "run", "k": i % 7, "label": f"S{i % 16}"},
        })
    hdr = {f"h{i}": "X-REPEATED-HEADER-VALUE" for i in range(headers)}
    return {"op": "plan", "headers": hdr, "steps": steps}


def make_delta(msg_i: int, muts: int, depth: int) -> Dict[str, Any]:
    # Small delta touching only a few fields.
    # (Modeled as patch-like payload; your real codec can differ.)
    edits: List[Dict[str, Any]] = []
    for j in range(muts):
        idx = (msg_i * 131 + j * 17) % depth
        edits.append({"path": ["steps", idx, "cfg", "k"], "set": (msg_i + j) % 97})
    return {"op": "delta", "msg": msg_i, "edits": edits}


def apply_delta(template: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
    # Shallow “apply” for structural validity checks (optional but cheap here).
    out = json.loads(json.dumps(template))  # deterministic deep copy via JSON
    for e in delta.get("edits", []):
        path = e["path"]
        v = e["set"]
        # Only supports the exact path shape we emit above.
        assert path[:2] == ["steps", path[1]]
        out["steps"][path[1]]["cfg"][path[3]] = v
    return out


def build_chain(
    depth: int,
    headers: int,
    n_msgs: int,
    muts: int,
    phase_id: int,
    schema_ver: int,
    alg_id: int,
    key: bytes,
) -> Tuple[bytes, List[bytes], List[Receipt]]:
    template = make_template(depth, headers)
    template_b = canon_bytes(template)
    th = sha256(template_b)

    deltas_b: List[bytes] = []
    receipts: List[Receipt] = []

    parent = ZERO32
    for i in range(n_msgs):
        d = make_delta(i, muts, depth)
        d_b = canon_bytes(d)
        dh = sha256(d_b)
        pre = bytes([alg_id]) + u32le(schema_ver) + u32le(phase_id) + th + dh + parent
        dig = sha256(pre)
        tag = hmac_sha256(key, dig)
        r = Receipt(
            alg_id=alg_id,
            schema_ver=schema_ver,
            phase_id=phase_id,
            template_hash=th,
            delta_hash=dh,
            parent=parent,
            tag=tag,
        )
        receipts.append(r)
        deltas_b.append(d_b)
        parent = r.receipt_hash()

    return template_b, deltas_b, receipts


def verify_chain(template_b: bytes, deltas_b: List[bytes], receipts: List[Receipt], key: bytes) -> bool:
    th = sha256(template_b)
    parent = ZERO32
    if len(deltas_b) != len(receipts):
        return False

    for d_b, r in zip(deltas_b, receipts):
        if r.template_hash != th:
            return False
        if r.parent != parent:
            return False

        dh = sha256(d_b)
        if r.delta_hash != dh:
            return False

        dig = sha256(r.preimage())
        exp_tag = hmac_sha256(key, dig)
        if not hmac.compare_digest(exp_tag, r.tag):
            return False

        parent = r.receipt_hash()

    return True


def main() -> None:
    # Deterministic params (keep stable for locks).
    seed = 26026  # informational (generator is deterministic anyway)
    depth = 96
    headers = 96
    n_msgs = 512
    muts = 3

    phase_id = 7
    schema_ver = 1
    alg_id = 1  # 1=sha256 in this harness

    key = b"v26-demo-key-32bytes--change-me!"  # 32 bytes recommended (this is 32)

    template_b, deltas_b, receipts = build_chain(
        depth=depth, headers=headers, n_msgs=n_msgs, muts=muts,
        phase_id=phase_id, schema_ver=schema_ver, alg_id=alg_id, key=key
    )

    ok = verify_chain(template_b, deltas_b, receipts, key)

    # Streams:
    stream_td = template_b + b"".join(deltas_b)
    stream_td_receipt = template_b + b"".join(d + r.bytes_on_wire() for d, r in zip(deltas_b, receipts))

    # Receipt metrics:
    one_receipt_len = len(receipts[0].bytes_on_wire())
    drift = sha256(b"".join(r.receipt_hash() for r in receipts)).hex()

    print("v26_receipt_chain_integrity")
    print(f"seed={seed}")
    print(f"depth={depth} headers={headers} n_msgs={n_msgs} muts={muts}")
    print(f"alg_id={alg_id} schema_ver={schema_ver} phase_id={phase_id}")
    print(f"template_bytes={len(template_b)}")
    print(f"delta_bytes_avg={sum(len(d) for d in deltas_b)//len(deltas_b)}")
    print(f"receipt_bytes_each={one_receipt_len}")
    print(f"verify_ok={ok}")

    raw_td = len(stream_td)
    raw_auth = len(stream_td_receipt)
    gz_td = gz_len(stream_td)
    gz_auth = gz_len(stream_td_receipt)

    print(f"raw_template_delta={raw_td}")
    print(f"raw_template_delta_receipt_auth={raw_auth}")
    print(f"raw_overhead_ratio={(raw_auth / raw_td):.6f}")

    print(f"gz_template_delta={gz_td}")
    print(f"gz_template_delta_receipt_auth={gz_auth}")
    print(f"gz_overhead_ratio={(gz_auth / gz_td):.6f}")

    print(f"drift_sha256(receipt_hash_chain)={drift}")


if __name__ == "__main__":
    main()