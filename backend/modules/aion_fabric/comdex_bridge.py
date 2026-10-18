from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


class ReadOnlyComdexBridge:
    """Metadata-only projection of existing COMDEX intelligence into Fabric."""

    def __init__(self, repository_root: str | Path) -> None:
        self.root = Path(repository_root).resolve()

    def snapshot(self) -> Dict[str, Any]:
        meetings_root = self.root / ".runtime" / "local_node" / "boardroom_meetings"
        meetings = sorted(meetings_root.glob("*.json")) if meetings_root.is_dir() else []
        latest = max((path.stat().st_mtime for path in meetings), default=None)
        intelligence_roots = [self.root / "backend" / "AION", self.root / "backend" / "modules" / "hexcore"]
        intelligence_files = sum(
            1
            for base in intelligence_roots
            if base.is_dir()
            for path in base.rglob("*.py")
            if path.is_file()
        )
        return {
            "mode": "metadata_only_read_only",
            "boardroom_sessions": len(meetings),
            "boardroom_ids": [path.stem[:80] for path in meetings[:12]],
            "latest_boardroom_update": (
                datetime.fromtimestamp(latest, tz=timezone.utc).isoformat() if latest is not None else None
            ),
            "intelligence_modules_present": intelligence_files,
            "content_exposed_to_tv": False,
            "credentials_exposed_to_tv": False,
        }
