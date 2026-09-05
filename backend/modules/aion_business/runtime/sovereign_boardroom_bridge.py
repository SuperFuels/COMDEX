from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Dict

from backend.modules.aion_business.contracts.business_containers import (
    BusinessContainerMeta,
    BusinessIdentityContainer,
    BusinessMapContainer,
    BusinessStructureContainer,
    DepartmentIntelligenceContainer,
)
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.sovereign_brain_boundary import SovereignBrainBoundary
from backend.modules.aion_fabric.canonical import canonical_hash, utc_now_iso


BRIDGE_VERSION = "aion.sovereign_boardroom_bridge.v1"
CORE_CONTAINER_KINDS = (
    "business_identity",
    "business_structure",
    "business_map",
    "department_intelligence",
)
_WORKSPACE_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")


class SovereignBoardroomBridge:
    """Make Boardroom's persisted BusinessMapContainer the sovereign source of truth."""

    def __init__(self, brain_root: str | Path, boardroom_runtime_root: str | Path | None = None) -> None:
        self.brain_root = Path(brain_root).resolve()
        self.boundary = SovereignBrainBoundary(self.brain_root / "brain")
        self.boardroom_runtime_root = (
            Path(boardroom_runtime_root).resolve()
            if boardroom_runtime_root is not None
            else self.brain_root / "AION_BUSINESS"
        )
        self.repository = BusinessContainerRepository(
            base_dir=self.boardroom_runtime_root / "business_containers"
        )

    @staticmethod
    def _workspace_id(value: str) -> str:
        workspace_id = str(value or "").strip().lower()
        if not _WORKSPACE_ID.fullmatch(workspace_id):
            raise ValueError("workspace_id_invalid")
        return workspace_id

    def initialize(self) -> Dict[str, Any]:
        if not self.boundary.identity_path.exists():
            raise RuntimeError("sovereign_brain_not_initialized")
        record = {
            "schema_version": BRIDGE_VERSION,
            "kind": "boardroom_business_map_registry",
            "source_of_truth": "boardroom_business_containers",
            "repository_binding": "brain_local_boardroom",
            "container_contract": "BusinessMapContainer",
            "parallel_business_map_allowed": False,
            "workspace_ids": self._workspace_ids(),
            "updated_at": utc_now_iso(),
        }
        self.boundary.upsert_store_record(
            "business_map", record, record_id="canonical_boardroom_business_maps"
        )
        return self.status()

    def create_empty_workspace(self, workspace_id: str, *, owner_id: str) -> Dict[str, Any]:
        """Create an evidence-empty Boardroom shell; onboarding adds all business facts later."""
        key = self._workspace_id(workspace_id)
        now = utc_now_iso()
        meta = lambda kind: BusinessContainerMeta(  # noqa: E731 - compact typed factory
            workspace_id=key, container_key=kind, updated_at=now, source="sovereign_empty_brain"
        )
        if not self.repository.exists(key, "business_identity"):
            self.repository.save_model(BusinessIdentityContainer(
                id=f"{key}.business_identity", workspace_id=key,
                meta=meta("business_identity"), owner=owner_id,
                source_refs=["sovereign_empty_brain"],
            ))
        if not self.repository.exists(key, "business_structure"):
            self.repository.save_model(BusinessStructureContainer(
                id=f"{key}.business_structure", workspace_id=key,
                meta=meta("business_structure"),
            ))
        if not self.repository.exists(key, "business_map"):
            self.repository.save_model(BusinessMapContainer(
                id=f"{key}.business_map", workspace_id=key,
                meta=meta("business_map"), source_refs=["sovereign_empty_brain"], revision=0,
            ))
        if not self.repository.exists(key, "department_intelligence"):
            self.repository.save_model(DepartmentIntelligenceContainer(
                id=f"{key}.department_intelligence", workspace_id=key,
                meta=meta("department_intelligence"), departments={}, revision=0,
            ))
        return self.register_workspace(key)

    def register_workspace(self, workspace_id: str) -> Dict[str, Any]:
        key = self._workspace_id(workspace_id)
        model = self.repository.load_business_map(key)
        if model.workspace_id != key or model.kind != "business_map":
            raise RuntimeError("boardroom_business_map_identity_mismatch")
        self.initialize()
        registry = self.boundary.store("business_map")
        record = next(
            item for item in registry["records"]
            if item.get("record_id") == "canonical_boardroom_business_maps"
        )
        record["workspace_ids"] = sorted(set(record.get("workspace_ids", [])) | {key})
        record["updated_at"] = utc_now_iso()
        self.boundary.upsert_store_record(
            "business_map", record, record_id="canonical_boardroom_business_maps"
        )
        return self.workspace_status(key)

    def workspace_status(self, workspace_id: str) -> Dict[str, Any]:
        key = self._workspace_id(workspace_id)
        model = self.repository.load_business_map(key)
        present = [kind for kind in CORE_CONTAINER_KINDS if self.repository.exists(key, kind)]
        payload = model.model_dump(mode="json")
        return {
            "ok": len(present) == len(CORE_CONTAINER_KINDS),
            "schema_version": BRIDGE_VERSION,
            "workspace_id": key,
            "source_of_truth": "boardroom_business_containers",
            "business_map_id": model.id,
            "business_map_revision": model.revision,
            "business_map_hash": canonical_hash(payload),
            "container_kinds": present,
            "fact_count": len(model.facts),
            "relationship_count": len(model.relationships),
            "assumption_count": len(model.assumptions),
            "unknown_count": len(model.unknowns),
            "conflict_count": len(model.conflicts),
            "unanswered_field_count": len(model.unanswered_fields),
            "department_gap_count": len(model.department_discovery_gaps),
            "evidence_empty": not any((model.facts, model.assumptions, model.unknowns, model.conflicts)),
        }

    def status(self) -> Dict[str, Any]:
        store = self.boundary.store("business_map")
        binding = next(
            (item for item in store.get("records", []) if item.get("record_id") == "canonical_boardroom_business_maps"),
            None,
        )
        workspaces = []
        for workspace_id in self._workspace_ids():
            try:
                workspaces.append(self.workspace_status(workspace_id))
            except (FileNotFoundError, ValueError):
                continue
        return {
            "ok": binding is not None,
            "schema_version": BRIDGE_VERSION,
            "source_of_truth": "boardroom_business_containers",
            "parallel_business_map_allowed": False,
            "workspace_count": len(workspaces),
            "workspaces": workspaces,
        }

    def _workspace_ids(self) -> list[str]:
        base = self.repository.base_dir
        if not base.exists():
            return []
        return sorted(
            path.name for path in base.iterdir()
            if path.is_dir() and _WORKSPACE_ID.fullmatch(path.name)
            and (path / "business_map.json").is_file()
        )
