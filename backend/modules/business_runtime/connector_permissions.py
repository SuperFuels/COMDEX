from __future__ import annotations

from pathlib import Path
import json


class ConnectorPermissions:
    def __init__(self, base_dir: Path | str = ".runtime/COMDEX_MOVE/data/business_runtime") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.base_dir / "connector_permissions.json"

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save(self, doc: dict) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def grant(self, workspace_id: str, operator_id: str, connector_key: str) -> None:
        doc = self._load()
        doc.setdefault(workspace_id, {})
        doc[workspace_id].setdefault(operator_id, [])
        if connector_key not in doc[workspace_id][operator_id]:
            doc[workspace_id][operator_id].append(connector_key)
        self._save(doc)

    def is_allowed(self, workspace_id: str, operator_id: str, connector_key: str) -> bool:
        doc = self._load()
        allowed = doc.get(workspace_id, {}).get(operator_id, [])
        return connector_key in allowed