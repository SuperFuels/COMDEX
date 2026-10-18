from __future__ import annotations

from pathlib import Path
import json
from datetime import datetime, timezone


def utc_now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


class TriggerRuntime:
    def __init__(self, base_dir: Path | str = ".runtime/COMDEX_MOVE/data/business_runtime") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.base_dir / "trigger_state.json"

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

    def can_fire(self, dedupe_key: str, cooldown_seconds: int) -> bool:
        doc = self._load()
        now = utc_now_ts()
        last_ts = int(doc.get(dedupe_key, 0))
        return (now - last_ts) >= cooldown_seconds

    def mark_fired(self, dedupe_key: str) -> None:
        doc = self._load()
        doc[dedupe_key] = utc_now_ts()
        self._save(doc)