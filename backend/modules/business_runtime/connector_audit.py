from __future__ import annotations

from pathlib import Path
import json
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class ConnectorAudit:
    def __init__(self, base_dir: Path | str = ".runtime/COMDEX_MOVE/data/business_runtime") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.base_dir / "connector_audit.jsonl"

    def log(
        self,
        workspace_id: str,
        operator_id: str,
        connector_key: str,
        action: str,
        ok: bool = True,
        meta: dict | None = None,
    ) -> None:
        row = {
            "ts": utc_now_iso(),
            "workspace_id": workspace_id,
            "operator_id": operator_id,
            "connector_key": connector_key,
            "action": action,
            "ok": ok,
            "meta": meta or {},
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")