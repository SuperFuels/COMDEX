from __future__ import annotations

from pathlib import Path
import base64
import json


class ConnectorVault:
    """
    Minimal starter version.
    Replace base64 with real encryption next pass.
    """

    def __init__(self, base_dir: Path | str = ".runtime/COMDEX_MOVE/data/business_runtime") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.base_dir / "connector_secrets.json"

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

    def put_secret(self, workspace_id: str, connector_key: str, secret_value: str) -> None:
        doc = self._load()
        doc.setdefault(workspace_id, {})
        doc[workspace_id][connector_key] = base64.b64encode(secret_value.encode("utf-8")).decode("utf-8")
        self._save(doc)

    def get_secret(self, workspace_id: str, connector_key: str) -> str | None:
        doc = self._load()
        raw = doc.get(workspace_id, {}).get(connector_key)
        if not raw:
            return None
        try:
            return base64.b64decode(raw.encode("utf-8")).decode("utf-8")
        except Exception:
            return None