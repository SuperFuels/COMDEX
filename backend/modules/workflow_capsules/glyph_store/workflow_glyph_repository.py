from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import os

from backend.modules.workflow_capsules.glyph_store.workflow_glyph_schema import (
    WorkflowGlyph,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_agents.runtime.vault_repository_backend import (
    AgentVaultRepositoryBackend,
    configured_agent_domain_store,
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
        glyph_dir: Path | str | None = None,
        index_path: Path | str | None = None,
        domain_store: VaultDomainStore | None = None,
        workspace_id: str | None = None,
    ) -> None:
        explicit_legacy = glyph_dir is not None or index_path is not None
        self.glyph_dir = Path(glyph_dir or DEFAULT_GLYPH_DIR)
        self.index_path = Path(index_path or DEFAULT_INDEX_PATH)
        store = domain_store or (
            configured_agent_domain_store() if not explicit_legacy else None
        )
        self.vault = (
            AgentVaultRepositoryBackend(store, kind="workflow_capsule_glyphs")
            if store
            else None
        )
        self.workspace_id = str(
            workspace_id
            or os.environ.get("TESSARIS_BUSINESS_STABLE_ID")
            or ""
        ).strip()
        if self.vault is not None and not self.workspace_id:
            raise ValueError("workflow_glyph_workspace_id_required")

    @staticmethod
    def _vault_item_id(glyph_code: str, glyph_version: str) -> str:
        return f"{str(glyph_code).strip().upper()}/{str(glyph_version or 'v1')}"

    def path_for(self, glyph_code: str, glyph_version: str = "v1") -> Path:
        safe = _safe_file_key(f"{glyph_code}.{glyph_version}")
        return self.glyph_dir / f"{safe}.json"

    def save(self, glyph: WorkflowGlyph) -> Dict[str, Any]:
        glyph.finalize()
        if glyph.scope == "my" and self.vault is not None:
            item_id = self._vault_item_id(glyph.glyph_code, glyph.glyph_version)
            self.vault.put(
                workspace_id=self.workspace_id,
                item_id=item_id,
                payload=glyph.to_dict(),
            )
            self.rebuild_index()
            return {
                "ok": True,
                "glyph_code": glyph.glyph_code,
                "glyph_version": glyph.glyph_version,
                "glyph_id": glyph.glyph_id,
                "path": (
                    "vault://train_agent.automations/workflow_capsule_glyphs/"
                    + item_id
                ),
                "version_hash": glyph.meta.get("version_hash"),
            }
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
            if self.vault is not None:
                payload = self.vault.get(
                    workspace_id=self.workspace_id,
                    item_id=self._vault_item_id(code, glyph_version),
                )
                if payload is not None:
                    return WorkflowGlyph.from_dict(payload)
            path = self.path_for(code, glyph_version)
            if not path.exists():
                return None
            glyph = WorkflowGlyph.load(path)
            # A retained plaintext customer glyph is a migration source, never
            # an authority once Guardian mode is active.
            if self.vault is not None and glyph.scope == "my":
                return None
            return glyph

        matches = [item for item in self.list() if item.glyph_code == code]
        if not matches:
            return None
        return sorted(matches, key=lambda item: item.glyph_version)[-1]

    def require(self, glyph_code: str, glyph_version: Optional[str] = None) -> WorkflowGlyph:
        glyph = self.load(glyph_code, glyph_version)
        if glyph is None:
            suffix = f"@{glyph_version}" if glyph_version else ""
            raise FileNotFoundError(f"Workflow glyph not found: {glyph_code}{suffix}")
        return glyph

    def list(self, *, scope: Optional[str] = None, callable_only: bool = False) -> List[WorkflowGlyph]:
        out: List[WorkflowGlyph] = []
        if self.glyph_dir.exists():
            for path in sorted(self.glyph_dir.glob("*.json")):
                try:
                    glyph = WorkflowGlyph.load(path)
                    if self.vault is not None and glyph.scope == "my":
                        continue
                    out.append(glyph)
                except Exception:
                    continue

        if self.vault is not None:
            for payload in self.vault.list(workspace_id=self.workspace_id):
                try:
                    out.append(WorkflowGlyph.from_dict(payload))
                except Exception:
                    continue

        deduplicated: Dict[tuple[str, str], WorkflowGlyph] = {}
        for glyph in out:
            deduplicated[(glyph.glyph_code, glyph.glyph_version)] = glyph

        filtered: List[WorkflowGlyph] = []
        for glyph in deduplicated.values():

            if scope and glyph.scope != scope:
                continue
            if callable_only and glyph.callable is not True:
                continue

            filtered.append(glyph)

        return sorted(filtered, key=lambda item: (item.glyph_code, item.glyph_version))

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
                    "path": (
                        "vault://train_agent.automations/workflow_capsule_glyphs/"
                        + self._vault_item_id(g.glyph_code, g.glyph_version)
                        if self.vault is not None and g.scope == "my"
                        else str(self.path_for(g.glyph_code, g.glyph_version))
                    ),
                }
                for g in items
            ],
        }

        if self.vault is not None:
            return {
                "ok": True,
                "path": "memory://workflow-glyph-derived-index",
                "count": len(items),
                "derived_index_persisted": False,
            }

        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return {
            "ok": True,
            "path": str(self.index_path),
            "count": len(items),
            "derived_index_persisted": True,
        }
