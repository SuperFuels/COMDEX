from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Union
import json
import os
import re

from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_agents.runtime.vault_repository_backend import (
    AgentVaultRepositoryBackend,
    configured_agent_domain_store,
)

from backend.modules.workflow_capsules.global_registry.industry_pack_schema import (
    IndustryWorkflowPack,
)
from backend.modules.workflow_capsules.global_registry.local_binding_schema import (
    LocalWorkflowBinding,
)


SAFE_KEY_RE = re.compile(r"[^a-zA-Z0-9_.:-]+")


def _safe_filename(value: str, fallback: str = "item") -> str:
    raw = str(value or fallback).strip() or fallback
    raw = SAFE_KEY_RE.sub("_", raw).replace(":", "_")
    return raw.strip("._-") or fallback


class GlobalWorkflowRegistryStore:
    """
    Filesystem-backed store for global industry packs and local workflow bindings.

    Global packs:
      reusable workflow patterns, no credentials.

    Local bindings:
      workspace/business-specific connector and vault handle mapping, no credentials.
    """

    def __init__(
        self,
        *,
        global_root: Union[str, Path] = "data/workflow_capsules/global_registry",
        local_root: Union[str, Path, None] = None,
        domain_store: VaultDomainStore | None = None,
        workspace_id: str | None = None,
    ) -> None:
        self.global_root = Path(global_root)
        self.local_root = Path(
            local_root or ".runtime/workflow_capsules/local_bindings"
        )
        store = domain_store or (
            configured_agent_domain_store() if local_root is None else None
        )
        self.vault = (
            AgentVaultRepositoryBackend(
                store,
                kind="workflow_capsule_local_bindings",
            )
            if store
            else None
        )
        self.workspace_id = str(
            workspace_id
            or os.environ.get("TESSARIS_BUSINESS_STABLE_ID")
            or ""
        ).strip()
        if self.vault is not None and not self.workspace_id:
            raise ValueError("workflow_capsule_local_binding_workspace_id_required")

    @staticmethod
    def _binding_from_data(data: Dict[str, object]) -> LocalWorkflowBinding:
        return LocalWorkflowBinding(
            binding_key=str(data.get("binding_key") or ""),
            workspace_id=str(data.get("workspace_id") or ""),
            business_id=str(data.get("business_id") or ""),
            pattern_key=str(data.get("pattern_key") or ""),
            workflow_canonical_key=str(data.get("workflow_canonical_key") or ""),
            connector_bindings=dict(data.get("connector_bindings") or {}),
            vault_bindings=dict(data.get("vault_bindings") or {}),
            business_context=dict(data.get("business_context") or {}),
            enabled=bool(data.get("enabled") is True),
            meta=dict(data.get("meta") or {}),
        )

    @staticmethod
    def _binding_item_id(binding_key: str) -> str:
        return _safe_filename(binding_key)

    def _vault_binding_path(self, binding_key: str) -> str:
        return (
            "vault://train_agent.automations/"
            "workflow_capsule_local_bindings/"
            + self._binding_item_id(binding_key)
        )

    @property
    def industry_pack_root(self) -> Path:
        return self.global_root / "industry_packs"

    @property
    def local_binding_root(self) -> Path:
        return self.local_root

    def industry_pack_path(self, pack_key: str) -> Path:
        return self.industry_pack_root / f"{_safe_filename(pack_key)}.json"

    def local_binding_path(self, binding_key: str) -> Path:
        return self.local_binding_root / f"{_safe_filename(binding_key)}.json"

    def save_industry_pack(
        self,
        pack: IndustryWorkflowPack,
        *,
        overwrite: bool = True,
    ) -> Dict[str, object]:
        pack.finalize()
        path = self.industry_pack_path(pack.pack_key)

        if path.exists() and not overwrite:
            return {
                "ok": False,
                "reason": "industry_pack_already_exists",
                "pack_key": pack.pack_key,
                "path": str(path),
            }

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(pack.to_dict(), indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )

        return {
            "ok": True,
            "pack_key": pack.pack_key,
            "industry": pack.industry,
            "path": str(path),
            "checksum": pack.meta.get("checksum"),
        }

    def load_industry_pack(self, pack_key: str) -> Optional[IndustryWorkflowPack]:
        path = self.industry_pack_path(pack_key)
        if not path.exists():
            return None

        data = json.loads(path.read_text(encoding="utf-8"))
        patterns = data.get("patterns") or []

        from backend.modules.workflow_capsules.global_registry.industry_pack_schema import (
            GlobalWorkflowPattern,
        )

        return IndustryWorkflowPack(
            pack_key=str(data.get("pack_key") or ""),
            industry=str(data.get("industry") or ""),
            display_name=str(data.get("display_name") or ""),
            meaning=str(data.get("meaning") or ""),
            patterns=[
                GlobalWorkflowPattern(
                    pattern_key=str(item.get("pattern_key") or ""),
                    display_name=str(item.get("display_name") or ""),
                    industry=str(item.get("industry") or ""),
                    meaning=str(item.get("meaning") or ""),
                    workflow_canonical_key=str(item.get("workflow_canonical_key") or ""),
                    display_glyph=item.get("display_glyph"),
                    required_connectors=list(item.get("required_connectors") or []),
                    required_vault_handles=list(item.get("required_vault_handles") or []),
                    local_binding_slots=list(item.get("local_binding_slots") or []),
                    template=dict(item.get("template") or {}),
                    tags=list(item.get("tags") or []),
                    meta=dict(item.get("meta") or {}),
                )
                for item in patterns
            ],
            required_connectors=list(data.get("required_connectors") or []),
            required_vault_handles=list(data.get("required_vault_handles") or []),
            tags=list(data.get("tags") or []),
            meta=dict(data.get("meta") or {}),
        )

    def require_industry_pack(self, pack_key: str) -> IndustryWorkflowPack:
        pack = self.load_industry_pack(pack_key)
        if pack is None:
            raise FileNotFoundError(f"Industry workflow pack not found: {pack_key}")
        return pack

    def list_industry_packs(self) -> List[Dict[str, object]]:
        if not self.industry_pack_root.exists():
            return []

        rows: List[Dict[str, object]] = []
        for path in sorted(self.industry_pack_root.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                rows.append(
                    {
                        "ok": True,
                        "pack_key": data.get("pack_key"),
                        "industry": data.get("industry"),
                        "display_name": data.get("display_name"),
                        "path": str(path),
                        "checksum": (data.get("meta") or {}).get("checksum"),
                    }
                )
            except Exception as exc:
                rows.append({"ok": False, "path": str(path), "error": str(exc)})

        return rows

    def save_local_binding(
        self,
        binding: LocalWorkflowBinding,
        *,
        overwrite: bool = True,
    ) -> Dict[str, object]:
        binding.finalize()
        if self.vault is not None:
            if binding.workspace_id != self.workspace_id:
                raise ValueError("workflow_capsule_local_binding_workspace_mismatch")
            item_id = self._binding_item_id(binding.binding_key)
            if not overwrite and self.vault.exists(
                workspace_id=self.workspace_id,
                item_id=item_id,
            ):
                return {
                    "ok": False,
                    "reason": "local_binding_already_exists",
                    "binding_key": binding.binding_key,
                    "path": self._vault_binding_path(binding.binding_key),
                }
            self.vault.put(
                workspace_id=self.workspace_id,
                item_id=item_id,
                payload=binding.to_dict(),
            )
            return {
                "ok": True,
                "binding_key": binding.binding_key,
                "workspace_id": binding.workspace_id,
                "business_id": binding.business_id,
                "pattern_key": binding.pattern_key,
                "workflow_canonical_key": binding.workflow_canonical_key,
                "path": self._vault_binding_path(binding.binding_key),
                "checksum": binding.meta.get("checksum"),
            }
        path = self.local_binding_path(binding.binding_key)

        if path.exists() and not overwrite:
            return {
                "ok": False,
                "reason": "local_binding_already_exists",
                "binding_key": binding.binding_key,
                "path": str(path),
            }

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(binding.to_dict(), indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )

        return {
            "ok": True,
            "binding_key": binding.binding_key,
            "workspace_id": binding.workspace_id,
            "business_id": binding.business_id,
            "pattern_key": binding.pattern_key,
            "workflow_canonical_key": binding.workflow_canonical_key,
            "path": str(path),
            "checksum": binding.meta.get("checksum"),
        }

    def load_local_binding(self, binding_key: str) -> Optional[LocalWorkflowBinding]:
        if self.vault is not None:
            data = self.vault.get(
                workspace_id=self.workspace_id,
                item_id=self._binding_item_id(binding_key),
            )
            return self._binding_from_data(data) if data is not None else None
        path = self.local_binding_path(binding_key)
        if not path.exists():
            return None

        data = json.loads(path.read_text(encoding="utf-8"))
        return self._binding_from_data(data)

    def require_local_binding(self, binding_key: str) -> LocalWorkflowBinding:
        binding = self.load_local_binding(binding_key)
        if binding is None:
            raise FileNotFoundError(f"Local workflow binding not found: {binding_key}")
        return binding

    def list_local_bindings(
        self,
        *,
        workspace_id: Optional[str] = None,
        business_id: Optional[str] = None,
    ) -> List[Dict[str, object]]:
        rows: List[Dict[str, object]] = []
        if self.vault is not None:
            selected_workspace = str(workspace_id or self.workspace_id)
            if selected_workspace != self.workspace_id:
                return []
            sources = [
                (data, self._vault_binding_path(str(data.get("binding_key") or "")))
                for data in self.vault.list(workspace_id=self.workspace_id)
            ]
        else:
            if not self.local_binding_root.exists():
                return []
            sources = []
            for path in sorted(self.local_binding_root.glob("*.json")):
                try:
                    sources.append((json.loads(path.read_text(encoding="utf-8")), str(path)))
                except Exception as exc:
                    rows.append({"ok": False, "path": str(path), "error": str(exc)})

        for data, source_path in sources:
            try:
                if workspace_id and data.get("workspace_id") != workspace_id:
                    continue
                if business_id and data.get("business_id") != business_id:
                    continue

                rows.append(
                    {
                        "ok": True,
                        "binding_key": data.get("binding_key"),
                        "workspace_id": data.get("workspace_id"),
                        "business_id": data.get("business_id"),
                        "pattern_key": data.get("pattern_key"),
                        "workflow_canonical_key": data.get("workflow_canonical_key"),
                        "enabled": data.get("enabled") is True,
                        "path": source_path,
                        "checksum": (data.get("meta") or {}).get("checksum"),
                    }
                )
            except Exception as exc:
                rows.append({"ok": False, "path": source_path, "error": str(exc)})

        return rows
