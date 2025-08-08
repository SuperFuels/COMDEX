# backend/modules/lean/lean_audit.py
import json, os, hashlib, time
from typing import Any, Dict, List

DEFAULT_PATH = "data/lean_audit.jsonl"

def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def audit_event(event: Dict[str, Any], path: str = DEFAULT_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

def build_inject_event(
    *,
    container_path: str,
    container_id: str | None,
    lean_path: str,
    num_items: int,
    previews: List[str] | None = None,
    extra: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    evt: Dict[str, Any] = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "kind": "lean.inject",
        "container_path": container_path,
        "container_id": container_id,
        "lean_path": lean_path,
        "count": num_items,
        "previews": previews or [],
        "hash": _sha1(f"{container_path}|{lean_path}|{num_items}|{previews}"),
    }
    if extra:
        evt.update(extra)
    return evt