from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
    guardian_mode_requested,
)
from backend.modules.aion_business.runtime.canonical_business_identity import (
    canonical_business_id,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore


DEFAULT_RETELL_DEPLOYMENT_PATH = (
    Path(__file__).resolve().parents[4] / "data" / "local_vault" / "retell_homefixed_agent.json"
)


class RetellDeploymentStore:
    """Customer-owned deployment metadata; provider credentials stay in Keychain."""

    DOMAIN_ID = "departments.operational_records"
    ENTITY_ID = "sales/integrations/retell/deployment"

    def __init__(
        self,
        *,
        domain_store: VaultDomainStore | None = None,
        legacy_path: str | Path = DEFAULT_RETELL_DEPLOYMENT_PATH,
    ) -> None:
        self.domain_store = domain_store
        if domain_store is None and guardian_mode_requested():
            runtime = configured_business_vault_runtime()
            self.domain_store = VaultDomainStore(
                runtime.guardian, actor_id="retell-deployment-runtime"
            )
        self.legacy_path = Path(legacy_path).resolve()

    @staticmethod
    def _workspace(workspace_id: str | None) -> str:
        return canonical_business_id(workspace_id or "Home Fixed")

    def read(self, workspace_id: str | None = None) -> dict[str, Any]:
        workspace = self._workspace(workspace_id)
        if self.domain_store is not None:
            current = self.domain_store.get_optional(
                self.DOMAIN_ID, workspace_id=workspace, entity_id=self.ENTITY_ID
            )
            if current is not None:
                return dict(current["payload"])
            legacy = self._read_legacy()
            if legacy:
                self.domain_store.put(
                    self.DOMAIN_ID,
                    workspace_id=workspace,
                    entity_id=self.ENTITY_ID,
                    payload=legacy,
                    expected_version=None,
                    actor_id="retell-deployment-legacy-import",
                )
                verified = self.domain_store.get(
                    self.DOMAIN_ID, workspace_id=workspace, entity_id=self.ENTITY_ID
                )
                if dict(verified["payload"]) != legacy:
                    raise RuntimeError("retell_deployment_legacy_import_verification_failed")
                return legacy
            return {}
        return self._read_legacy()

    def write(self, record: dict[str, Any], workspace_id: str | None = None) -> None:
        workspace = self._workspace(workspace_id or str(record.get("workspace_id") or ""))
        payload = dict(record)
        payload["workspace_id"] = workspace
        if self.domain_store is not None:
            current = self.domain_store.get_optional(
                self.DOMAIN_ID, workspace_id=workspace, entity_id=self.ENTITY_ID
            )
            self.domain_store.put(
                self.DOMAIN_ID,
                workspace_id=workspace,
                entity_id=self.ENTITY_ID,
                payload=payload,
                expected_version=int(current["version"]) if current else None,
                actor_id="retell-deployment-runtime",
            )
            return
        self.legacy_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.legacy_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.legacy_path)

    def _read_legacy(self) -> dict[str, Any]:
        if not self.legacy_path.is_file():
            return {}
        try:
            value = json.loads(self.legacy_path.read_text(encoding="utf-8"))
            return dict(value) if isinstance(value, dict) else {}
        except Exception:
            return {}
