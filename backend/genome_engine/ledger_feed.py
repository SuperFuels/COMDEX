from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import hashlib
from pathlib import Path

from .stable_json import stable_hash, stable_stringify


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _find_first_trace_record(trace: Any, kind: str) -> Optional[Dict[str, Any]]:
    if not isinstance(trace, list):
        return None
    for ev in trace:
        if isinstance(ev, dict) and ev.get("trace_kind") == kind:
            return ev
    return None


def build_ledger_rows(
    *,
    run_id: str,
    seed: int,
    mode: str,
    scenario_summaries: Dict[str, Any],
    trace: Any,
) -> List[Dict[str, Any]]:
    """
    Deterministic LEDGER rows (JSONL):
      - one row per scenario_summary (digest-only)
      - optional rows for SQI fabric kg_write intents if present in trace
    NO wall-clock time. Stable order.
    """
    rows: List[Dict[str, Any]] = []

    # 1) Scenario summary rows (always)
    for sid in sorted([str(k) for k in (scenario_summaries or {}).keys()]):
        summary = scenario_summaries.get(sid, {}) if sid else {}
        payload_digest = stable_hash({"scenario_id": sid, "summary": summary})
        rows.append(
            {
                "schemaVersion": "GX1_LEDGER_ROW_V0",
                "run_id": str(run_id),
                "seed": int(seed),
                "mode": str(mode),
                "scenario_id": str(sid),
                "kind": "scenario_summary",
                "id": f"ledger:{run_id}:{sid}:scenario_summary",
                "payload_digest": str(payload_digest),
            }
        )

    # 2) SQI fabric kg_write intent rows (if trace contains sqi_fabric_result)
    fab_res = _find_first_trace_record(trace, "sqi_fabric_result")
    if isinstance(fab_res, dict):
        res = fab_res.get("result")
        if isinstance(res, dict):
            kg_writes = res.get("kg_writes")
            if isinstance(kg_writes, list):
                # stable sort by (id, kind, payload_digest)
                kws: List[Tuple[str, str, str]] = []
                for w in kg_writes:
                    if not isinstance(w, dict):
                        continue
                    wid = str(w.get("id") or "")
                    wkind = str(w.get("kind") or "")
                    pd = str(w.get("payload_digest") or "")
                    if wid:
                        kws.append((wid, wkind, pd))
                kws.sort()

                for wid, wkind, pd in kws:
                    rows.append(
                        {
                            "schemaVersion": "GX1_LEDGER_ROW_V0",
                            "run_id": str(run_id),
                            "seed": int(seed),
                            "mode": str(mode),
                            "scenario_id": str(wid.split(":")[-1]) if ":" in wid else "",
                            "kind": "kg_write_intent",
                            "id": str(wid),
                            "kg_kind": str(wkind),
                            "payload_digest": str(pd),
                        }
                    )

    # final deterministic sort
    rows = sorted(
        rows,
        key=lambda r: (
            str(r.get("scenario_id", "")),
            str(r.get("kind", "")),
            str(r.get("id", "")),
        ),
    )
    return rows


def ledger_digest(rows: List[Dict[str, Any]]) -> str:
    return sha256_bytes(stable_stringify(rows).encode("utf-8"))


def write_ledger_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(stable_stringify(row) + "\n")


def build_ledger_exports(*, rows: List[Dict[str, Any]], ledger_path: str) -> Dict[str, Any]:
    return {
        "enabled": True,
        "ledger_path": str(ledger_path),
        "ledger_count": int(len(rows)),
        "ledger_digest": str(ledger_digest(rows)),
    }