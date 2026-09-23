from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import json

from backend.modules.workflow_capsules.glyph_store.workflow_glyph_schema import (
    WorkflowGlyph,
)


DEFAULT_GLYPH_DIR = Path(".runtime/workflow_capsules/glyph_store/items")
DEFAULT_INDEX_PATH = Path(".runtime/workflow_capsules/glyph_store/workflow_glyph_index.json")


def _safe_file_key(value: str) -> str:
    return str(value or "glyph.unknown").replace(":", "_").replace("/", "_").replace("\\", "_")


class WorkflowGlyphRepository:
    """
    Filesystem-backed Workflow Glyph registry.

    This is the first backend storage layer for the Master Glyph Library.
    It is intentionally simple and deterministic before DB/API integration.
    """

    def __init__(
        self,
        *,
        glyph_dir: Path | str = DEFAULT_GLYPH_DIR,
        index_path: Path | str = DEFAULT_INDEX_PATH,
    ) -> None:
        self.glyph_dir = Path(glyph_dir)
        self.index_path = Path(index_path)

    def path_for(self, glyph_code: str, glyph_version: str = "v1") -> Path:
        safe = _safe_file_key(f"{glyph_code}.{glyph_version}")
        return self.glyph_dir / f"{safe}.json"

    def save(self, glyph: WorkflowGlyph) -> Dict[str, Any]:
        glyph.finalize()
        path = self.path_for(glyph.glyph_code, glyph.glyph_version)
        glyph.save(path)
        self.rebuild_index()
        return {
            "ok": True,
            "glyph_code": glyph.glyph_code,
            "glyph_version": glyph.glyph_version,
            "glyph_id": glyph.glyph_id,
            "path": str(path),
            "version_hash": glyph.meta.get("version_hash"),
        }

    def load(self, glyph_code: str, glyph_version: Optional[str] = None) -> Optional[WorkflowGlyph]:
        code = str(glyph_code or "").strip().upper()
        if not code:
            return None

        if glyph_version:
            path = self.path_for(code, glyph_version)
            if not path.exists():
                return None
            return WorkflowGlyph.load(path)

        matches = sorted(self.glyph_dir.glob(f"{_safe_file_key(code)}.*.json"))
        if not matches:
            # fallback for older direct filenames
            matches = sorted(self.glyph_dir.glob(f"{_safe_file_key(code)}*.json"))

        if not matches:
            return None

        return WorkflowGlyph.load(matches[-1])

    def require(self, glyph_code: str, glyph_version: Optional[str] = None) -> WorkflowGlyph:
        glyph = self.load(glyph_code, glyph_version)
        if glyph is None:
            suffix = f"@{glyph_version}" if glyph_version else ""
            raise FileNotFoundError(f"Workflow glyph not found: {glyph_code}{suffix}")
        return glyph

    def list(self, *, scope: Optional[str] = None, callable_only: bool = False) -> List[WorkflowGlyph]:
        if not self.glyph_dir.exists():
            return []

        out: List[WorkflowGlyph] = []
        for path in sorted(self.glyph_dir.glob("*.json")):
            try:
                glyph = WorkflowGlyph.load(path)
            except Exception:
                continue

            if scope and glyph.scope != scope:
                continue
            if callable_only and glyph.callable is not True:
                continue

            out.append(glyph)

        return out

    def search(
        self,
        query: str,
        *,
        scope: Optional[str] = None,
        callable_only: bool = False,
        limit: int = 50,
    ) -> List[WorkflowGlyph]:
        q = str(query or "").strip().lower()
        items = self.list(scope=scope, callable_only=callable_only)

        if not q:
            return items[:limit]

        matches: List[WorkflowGlyph] = []
        for glyph in items:
            haystack = " ".join([
                glyph.glyph_code,
                glyph.name,
                glyph.workflow_id,
                glyph.workflow_version,
                glyph.glyph_version,
                glyph.scope,
                glyph.risk_tier,
                " ".join(glyph.required_connectors or []),
                " ".join(glyph.tags or []),
                glyph.description,
            ]).lower()

            if q in haystack:
                matches.append(glyph)

        return matches[:limit]

    def rebuild_index(self) -> Dict[str, Any]:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        items = self.list()

        payload = {
            "schema_version": "aion.workflow_glyph_index.v1",
            "count": len(items),
            "entries": [
                {
                    "glyph_code": g.glyph_code,
                    "glyph_version": g.glyph_version,
                    "glyph_id": g.glyph_id,
                    "name": g.name,
                    "workflow_id": g.workflow_id,
                    "scope": g.scope,
                    "callable": g.callable,
                    "risk_tier": g.risk_tier,
                    "required_connectors": g.required_connectors,
                    "tags": g.tags,
                    "version_hash": g.meta.get("version_hash"),
                    "checksum": g.meta.get("checksum"),
                    "path": str(self.path_for(g.glyph_code, g.glyph_version)),
                }
                for g in items
            ],
        }

        self.index_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return {
            "ok": True,
            "path": str(self.index_path),
            "count": len(items),
        }
