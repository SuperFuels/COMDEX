from __future__ import annotations

from typing import Any, Dict, Iterable, List
from pathlib import Path
import hashlib

from .stable_json import stable_stringify


def extract_sqi_kg_writes(trace: Any) -> List[Dict[str, Any]]:
    """
    Extract deterministic KG write intents from sqi_fabric_result records.
    Returns a stable-sorted list of dicts (no side effects).
    """
    if not isinstance(trace, list):
        return []

    out: List[Dict[str, Any]] = []
    for ev in trace:
        if not isinstance(ev, dict):
            continue
        if str(ev.get("trace_kind") or "") != "sqi_fabric_result":
            continue

        # Allow either nested {result:{kg_writes:[...]}} or flat {kg_writes:[...]}
        res = ev.get("result")
        if isinstance(res, dict) and isinstance(res.get("kg_writes"), list):
            for w in res.get("kg_writes") or []:
                if isinstance(w, dict):
                    out.append(w)
            continue

        if isinstance(ev.get("kg_writes"), list):
            for w in ev.get("kg_writes") or []:
                if isinstance(w, dict):
                    out.append(w)

    # Stable sort: id/kind/payload_digest
    out = sorted(
        out,
        key=lambda w: (
            str(w.get("id", "")),
            str(w.get("kind", "")),
            str(w.get("payload_digest", "")),
        ),
    )
    return out


def write_sqi_kg_writes_jsonl(path: str | Path, kg_writes: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Write KG write-intents as JSONL (stable JSON per line).
    Returns {"count": int, "sha256": str}.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = list(kg_writes)
    rows = sorted(
        rows,
        key=lambda w: (
            str(w.get("id", "")),
            str(w.get("kind", "")),
            str(w.get("payload_digest", "")),
        ),
    )

    with p.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(stable_stringify(row))
            f.write("\n")

    blob = stable_stringify(rows).encode("utf-8")
    return {
        "count": int(len(rows)),
        "sha256": hashlib.sha256(blob).hexdigest(),
    }
