from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from backend.modules.aion_learning.vault_store import AionLearningVaultStore


DEFAULT_SYMATIC_LOG_PATH = Path("data/symatic_log.json")


class SymaticEventStore:
    """Customer-owned Symatic equation history.

    Guardian mode stores each equation as immutable learning evidence.  An
    explicit path selects the retained legacy representation for migration and
    isolated compatibility tests; it never becomes an implicit authority on a
    Guardian-configured node.
    """

    EVENT_TYPE = "symatic_equation"

    def __init__(
        self,
        *,
        vault_store: AionLearningVaultStore | None = None,
        path: str | Path | None = None,
    ) -> None:
        self.path = Path(path or DEFAULT_SYMATIC_LOG_PATH)
        self.vault_store = vault_store or AionLearningVaultStore(
            auto_configure=path is None
        )

    def record(self, operator: str, equation: str, **extra: Any) -> dict[str, Any]:
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operator": str(operator),
            "equation": str(equation),
            **extra,
        }
        return self.append(event)

    def append(self, event: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(event)
        payload.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        if self.vault_store.enabled:
            payload["event_type"] = self.EVENT_TYPE
            payload["ts_utc"] = str(payload.get("timestamp") or "")
            canonical = json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            event_id = f"symatic-equation-{sha256(canonical).hexdigest()}"
            payload["event_id"] = event_id
            self.vault_store.append_event(event_id, payload)
            return payload

        rows = self.list()
        rows.append(payload)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(rows, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return payload

    def list(self) -> list[dict[str, Any]]:
        if self.vault_store.enabled:
            return self.vault_store.list_events(kind=self.EVENT_TYPE)
        if not self.path.exists():
            return []
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return [dict(row) for row in value if isinstance(row, dict)] if isinstance(value, list) else []


SYMATIC_EVENTS = SymaticEventStore()
