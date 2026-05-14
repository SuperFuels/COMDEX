from __future__ import annotations

import gzip
import hashlib
import io
import json
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

# Canonical JSON: stable bytes
def jdump(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))

def gz_bytes(data: bytes, level: int = 9) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=level) as f:
        f.write(data)
    return buf.getvalue()

def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

@dataclass
class Params:
    seed: int = 38038
    n_agents: int = 4096
    k_updates: int = 1024
    m_edits_per_update: int = 1

def run(p: Params) -> Dict[str, object]:
    rng = random.Random(p.seed)

    # initial state (template)
    state: List[int] = [0 for _ in range(p.n_agents)]
    template_obj = {"n": p.n_agents, "state": state}
    template_line = (jdump(template_obj) + "\n").encode("utf-8")

    # delta stream (NDJSON): one line per tick: list of edits
    # each edit: {"idx": j, "val": v}
    delta_lines: List[bytes] = []
    snapshots: List[bytes] = []

    for t in range(p.k_updates):
        edits: List[Dict[str, int]] = []
        for _ in range(p.m_edits_per_update):
            j = rng.randrange(0, p.n_agents)
            v = rng.randrange(-2**31, 2**31 - 1)
            state[j] = v
            edits.append({"idx": j, "val": v})

        delta_lines.append((jdump({"t": t, "edits": edits}) + "\n").encode("utf-8"))
        snapshots.append((jdump({"t": t, "state": state}) + "\n").encode("utf-8"))

    raw_snapshot_stream = b"".join(snapshots)
    raw_delta_stream = template_line + b"".join(delta_lines)

    gz_snapshot_stream = gz_bytes(raw_snapshot_stream, level=9)
    gz_delta_stream = gz_bytes(raw_delta_stream, level=9)

    # projection query test: compare snapshot-last vs scanning deltas
    def snapshot_query(i: int) -> int:
        last = json.loads(snapshots[-1].decode("utf-8"))
        return int(last["state"][i])

    def delta_stream_query(i: int) -> int:
        tmpl = json.loads(template_line.decode("utf-8"))
        acc = int(tmpl["state"][i])
        for ln in delta_lines:
            obj = json.loads(ln.decode("utf-8"))
            for e in obj["edits"]:
                if int(e["idx"]) == i:
                    acc = int(e["val"])
        return acc

    indices = [0, 1, 17, 999, 2048, p.n_agents - 1]
    queries_ok = True
    for i in indices:
        if snapshot_query(i) != delta_stream_query(i):
            queries_ok = False
            break

    # anchors
    final_state_sha = sha256_hex(jdump({"state": state}).encode("utf-8"))
    drift_sha = sha256_hex(raw_delta_stream)

    return {
        "seed": p.seed,
        "n_agents": p.n_agents,
        "k_updates": p.k_updates,
        "m_edits_per_update": p.m_edits_per_update,
        "raw_snapshot_stream_bytes": len(raw_snapshot_stream),
        "raw_delta_stream_bytes": len(raw_delta_stream),
        "raw_ratio(snapshot/delta)": (len(raw_snapshot_stream) / max(1, len(raw_delta_stream))),
        "gz_snapshot_stream_bytes": len(gz_snapshot_stream),
        "gz_delta_stream_bytes": len(gz_delta_stream),
        "gz_ratio(snapshot/delta)": (len(gz_snapshot_stream) / max(1, len(gz_delta_stream))),
        "queries_ok": queries_ok,
        "query_indices": indices,
        "final_state_sha256": final_state_sha,
        "drift_sha256": drift_sha,
    }

if __name__ == "__main__":
    out = run(Params())
    for k, v in out.items():
        print(f"{k}={v}")