from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
    guardian_mode_requested,
)
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore


class FinanceOperationsStore:
    """Vault-aware JSON store for internal Finance operating records."""

    MARKER = "__tessaris_guardian_finance_operations__"

    def __init__(self, *, domain_store: VaultDomainStore | None = None) -> None:
        self.domain_store = domain_store
        if domain_store is None and guardian_mode_requested():
            runtime = configured_business_vault_runtime()
            self.domain_store = VaultDomainStore(
                runtime.guardian, actor_id="finance-operations-runtime",
            )

    def root(self, workspace_id: str, category: str) -> Path:
        if self.domain_store is not None:
            return Path("/") / self.MARKER / workspace_id / category
        path = AIONBusinessPaths.business_container_dir(workspace_id) / "finance" / category
        path.mkdir(parents=True, exist_ok=True)
        return path

    def identity(self, path: Path) -> tuple[str, str]:
        parts = path.parts
        marker = parts.index(self.MARKER)
        workspace_id = parts[marker + 1]
        relative = Path(*parts[marker + 2:]).with_suffix("").as_posix()
        return workspace_id, relative

    def read_json(self, path: Path, fallback: Any = None) -> Any:
        if self.domain_store is None:
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return fallback
        try:
            workspace_id, entity_id = self.identity(path)
            return self.domain_store.get(
                "finance.operations_records", workspace_id=workspace_id, entity_id=entity_id,
            )["payload"]
        except (KeyError, ValueError):
            return fallback

    def write_json(self, path: Path, payload: dict[str, Any]) -> None:
        if self.domain_store is None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return
        workspace_id, entity_id = self.identity(path)
        current = self.domain_store.get_optional(
            "finance.operations_records", workspace_id=workspace_id, entity_id=entity_id,
        )
        self.domain_store.put(
            "finance.operations_records", workspace_id=workspace_id, entity_id=entity_id,
            payload=payload, expected_version=int(current["version"]) if current else None,
            actor_id="finance-operations-runtime",
        )

    def exists(self, path: Path) -> bool:
        if self.domain_store is None:
            return path.exists()
        workspace_id, entity_id = self.identity(path)
        return self.domain_store.get_optional(
            "finance.operations_records", workspace_id=workspace_id, entity_id=entity_id,
        ) is not None

    def list_json(self, directory: Path) -> list[dict[str, Any]]:
        if self.domain_store is None:
            return [
                self.read_json(path, {})
                for path in sorted(directory.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            ] if directory.exists() else []
        workspace_id, prefix = self.identity(directory / "placeholder.json")
        prefix = prefix.rsplit("/placeholder", 1)[0].rstrip("/") + "/"
        rows = [
            row for row in self.domain_store.list(
                "finance.operations_records", workspace_id=workspace_id,
            )
            if str(row.get("entity_id") or "").startswith(prefix)
            and "/" not in str(row.get("entity_id") or "")[len(prefix):]
        ]
        rows.sort(key=lambda row: str(row.get("updated_at") or row.get("created_at") or ""), reverse=True)
        return [dict(row["payload"]) for row in rows]

    def reference(self, path: Path) -> dict[str, str]:
        if self.domain_store is None:
            return {"storage_path": str(path)}
        _workspace_id, entity_id = self.identity(path)
        return {"vault_domain_id": "finance.operations_records", "vault_entity_id": entity_id}
