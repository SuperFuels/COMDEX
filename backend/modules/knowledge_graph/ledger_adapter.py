# backend/modules/knowledge_graph/ledger_adapter.py
import os, json, time
from typing import Dict, Any, List, Optional
import urllib.request

LEDGER_URL = os.getenv("KG_LEDGER_URL", "http://localhost:3000/api/kg/events")
LEDGER_ENABLED = os.getenv("KG_LEDGER_ENABLED", "1") == "1"

def _post_json(url: str, body: Dict[str, Any]) -> None:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=3) as _:
        return

def log_events(
    *,
    kg: str,                    # "personal" | "work"
    owner: str,                 # owner WA (e.g., "kevin@wave.tp")
    events: List[Dict[str, Any]]
) -> None:
    """Best-effort batch append to the SQL ledger. Safe no-op if disabled/unavailable."""
    if not LEDGER_ENABLED or not events:
        return
    payload = {"kg": kg, "owner": owner, "events": events}
    try:
        _post_json(LEDGER_URL, payload)
    except Exception:
        # Never fail the KG because of the ledger
        pass

def make_event(
    *,
    type: str,                  # 'message'|'visit'|'file'|'call'|'ptt_session'|'floor_lock'|...
    kind: Optional[str] = None,
    thread_id: Optional[str] = None,
    topic_wa: Optional[str] = None,
    size: Optional[int] = None,
    sha256: Optional[str] = None,
    payload: Dict[str, Any] = {},
    ts_ms: Optional[int] = None,
    id: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "id": id,  # if None, server will assign
        "thread_id": thread_id,
        "topic_wa": topic_wa,
        "type": type,
        "kind": kind,
        "ts": int(ts_ms or time.time() * 1000),
        "size": size,
        "sha256": sha256,
        "payload": payload or {},
    }