from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import mimetypes
from pathlib import Path
import sqlite3
from typing import Any

from backend.modules.aion_business.runtime.business_container_repository import (
    BusinessContainerRepository,
)
from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.guardian_business_container_repository import (
    GuardianBusinessContainerRepository,
)
from backend.modules.aion_business.runtime.guardian_container_migration import (
    GuardianContainerMigration,
)
from backend.modules.aion_business.runtime.business_container_repository import _CONTAINER_FILE_MAP
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_object_store import VaultObjectStore
from backend.modules.aion_business.runtime.business_data_domain_registry import (
    PROTECTED_CONTINUITY_SURFACE_DOMAINS,
    department_vault_namespaces,
)
from backend.modules.workflow_capsules.foundations.workflow_capsule_schema import (
    WorkflowCapsule,
)
from backend.modules.workflow_capsules.repository.workflow_capsule_repository import (
    _safe_filename as _safe_workflow_capsule_key,
)


def _canonical_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(raw.encode("utf-8")).hexdigest()


class BusinessVaultCoverageMigrationError(ValueError):
    pass


def _discover_department_ids(value: Any, discovered: set[str]) -> None:
    """Collect department identities from known structured business records.

    A later release may create a department in Train Agent before it appears in
    the aggregate map.  The migration receipt must still provision and report
    the complete per-department Vault contract instead of silently omitting it.
    """

    if isinstance(value, list):
        for item in value:
            _discover_department_ids(item, discovered)
        return
    if not isinstance(value, dict):
        return
    department_id = value.get("department_id")
    if isinstance(department_id, str) and department_id.strip():
        candidate = department_id.strip().lower()
        try:
            department_vault_namespaces(candidate)
        except ValueError as exc:
            raise BusinessVaultCoverageMigrationError(
                f"legacy_department_identity_invalid:{candidate}"
            ) from exc
        discovered.add(candidate)
    department_ids = value.get("department_ids")
    if isinstance(department_ids, list):
        for department in department_ids:
            if isinstance(department, str) and department.strip():
                candidate = department.strip().lower()
                try:
                    department_vault_namespaces(candidate)
                except ValueError as exc:
                    raise BusinessVaultCoverageMigrationError(
                        f"legacy_department_identity_invalid:{candidate}"
                    ) from exc
                discovered.add(candidate)
    departments = value.get("departments")
    if isinstance(departments, dict):
        for department in departments:
            candidate = str(department).strip().lower()
            if not candidate:
                continue
            try:
                department_vault_namespaces(candidate)
            except ValueError as exc:
                raise BusinessVaultCoverageMigrationError(
                    f"legacy_department_identity_invalid:{candidate}"
                ) from exc
            discovered.add(candidate)
    for nested in value.values():
        if isinstance(nested, (dict, list)):
            _discover_department_ids(nested, discovered)


class BusinessVaultCoverageMigration:
    """Copy and verify all currently known cross-cutting business-data surfaces.

    Legacy sources are deliberately retained.  Authority may be switched only
    after every candidate copied in this run has been read back and verified.
    """

    def __init__(
        self,
        *,
        legacy_root: str | Path,
        local_node_root: str | Path | None = None,
        workflow_capsule_root: str | Path | None = None,
        aion_learning_root: str | Path | None = None,
        aion_resonance_root: str | Path | None = None,
        aion_resonance_data_root: str | Path | None = None,
        pal_snapshot_log_path: str | Path | None = None,
        aion_knowledge_db_path: str | Path | None = None,
        concept_reinforcement_log_path: str | Path | None = None,
        concept_evolution_log_path: str | Path | None = None,
        glyphnet_thread_db_path: str | Path | None = None,
        aion_flow_model_bindings_path: str | Path | None = None,
        domain_store: VaultDomainStore,
        object_store: VaultObjectStore,
        guardian_containers: GuardianBusinessContainerRepository,
    ) -> None:
        self.legacy_root = Path(legacy_root).resolve()
        self.local_node_root = Path(local_node_root or legacy_root).resolve()
        self.workflow_capsule_root = Path(
            workflow_capsule_root or legacy_root
        ).resolve()
        self.aion_learning_root = Path(
            aion_learning_root or legacy_root
        ).resolve()
        self.aion_resonance_root = Path(
            aion_resonance_root or aion_learning_root or legacy_root
        ).resolve()
        self.aion_resonance_data_root = Path(
            aion_resonance_data_root or aion_learning_root or legacy_root
        ).resolve()
        self.pal_snapshot_log_path = (
            Path(pal_snapshot_log_path).resolve()
            if pal_snapshot_log_path is not None else None
        )
        self.aion_knowledge_db_path = (
            Path(aion_knowledge_db_path).resolve()
            if aion_knowledge_db_path is not None else None
        )
        self.concept_reinforcement_log_path = (
            Path(concept_reinforcement_log_path).resolve()
            if concept_reinforcement_log_path is not None else None
        )
        self.concept_evolution_log_path = (
            Path(concept_evolution_log_path).resolve()
            if concept_evolution_log_path is not None else None
        )
        self.glyphnet_thread_db_path = (
            Path(glyphnet_thread_db_path).resolve()
            if glyphnet_thread_db_path is not None else None
        )
        self.aion_flow_model_bindings_path = (
            Path(aion_flow_model_bindings_path).resolve()
            if aion_flow_model_bindings_path is not None else None
        )
        self.domain_store = domain_store
        self.object_store = object_store
        self.guardian_containers = guardian_containers

    def _safe_legacy_file(self, value: str | Path) -> Path:
        path = Path(value)
        if path.is_absolute():
            resolved = path.resolve()
        elif str(path).startswith(".runtime/AION_BUSINESS/"):
            resolved = (self.legacy_root.parent.parent / path).resolve()
        else:
            resolved = (self.legacy_root / path).resolve()
        try:
            resolved.relative_to(self.legacy_root)
        except ValueError as exc:
            raise BusinessVaultCoverageMigrationError("legacy_artifact_outside_business_root") from exc
        if not resolved.is_file():
            raise BusinessVaultCoverageMigrationError("legacy_artifact_missing")
        return resolved

    def _copy_json(
        self,
        *,
        domain_id: str,
        workspace_id: str,
        entity_id: str,
        payload: dict[str, Any],
        actor_id: str,
        execute: bool,
    ) -> str:
        source_hash = _canonical_hash(payload)
        existing = self.domain_store.get_optional(
            domain_id, workspace_id=workspace_id, entity_id=entity_id
        )
        if existing is not None:
            if _canonical_hash(existing["payload"]) != source_hash:
                raise BusinessVaultCoverageMigrationError(
                    f"migration_target_conflict:{domain_id}:{entity_id}"
                )
            return "already_verified"
        if not execute:
            return "ready"
        self.domain_store.put(
            domain_id,
            workspace_id=workspace_id,
            entity_id=entity_id,
            payload=payload,
            expected_version=None,
            idempotency_key=f"coverage-{source_hash[:32]}",
            actor_id=actor_id,
        )
        copied = self.domain_store.get(
            domain_id, workspace_id=workspace_id, entity_id=entity_id
        )["payload"]
        if _canonical_hash(copied) != source_hash:
            raise RuntimeError(f"migration_verification_failed:{domain_id}:{entity_id}")
        return "migrated_verified"

    def migrate_workspace(
        self,
        workspace_id: str,
        *,
        actor_id: str,
        execute: bool = False,
    ) -> dict[str, Any]:
        workspace_id = canonical_business_id(workspace_id)
        candidates: list[dict[str, Any]] = []
        discovered_departments: set[str] = set()

        container_result = GuardianContainerMigration(
            legacy=BusinessContainerRepository(self.legacy_root / "business_containers"),
            guardian=self.guardian_containers,
        ).migrate_workspace(
            workspace_id,
            kinds=[kind for kind in _CONTAINER_FILE_MAP if kind != "finance_inbox"],
            actor_id=actor_id,
            execute=execute,
        )
        for row in container_result["candidates"]:
            candidates.append({"domain_id": f"business_container.{row['kind']}", **row})

        legacy_department_intelligence = (
            self.legacy_root / "business_containers" / workspace_id
            / "department_intelligence.json"
        )
        if legacy_department_intelligence.is_file():
            payload = json.loads(
                legacy_department_intelligence.read_text(encoding="utf-8")
            )
            departments = payload.get("departments") if isinstance(payload, dict) else None
            if isinstance(departments, dict):
                discovered_departments.update(
                    str(value).strip() for value in departments if str(value).strip()
                )

        brand_asset_root = (
            self.legacy_root / "business_containers" / workspace_id / "brand_assets"
        )
        if brand_asset_root.is_dir():
            for source in sorted(path for path in brand_asset_root.iterdir() if path.is_file()):
                raw = source.read_bytes()
                if not raw:
                    continue
                object_id = source.stem
                if not object_id.startswith("brand_"):
                    object_id = "brandmig-" + sha256(
                        f"{workspace_id}\0{source.name}\0{sha256(raw).hexdigest()}".encode("utf-8")
                    ).hexdigest()[:48]
                state = "ready"
                if execute:
                    self.object_store.put_bytes(
                        object_id=object_id,
                        data=raw,
                        original_name=source.name,
                        content_type=mimetypes.guess_type(source.name)[0] or "application/octet-stream",
                        idempotency_key=f"brand-asset-migration-{object_id}",
                        actor_id=actor_id,
                        recorded_at="1970-01-01T00:00:00+00:00",
                    )
                    _metadata, copied = self.object_store.get_bytes(object_id=object_id)
                    if sha256(copied).digest() != sha256(raw).digest():
                        raise RuntimeError("brand_asset_object_migration_verification_failed")
                    state = "migrated_verified"
                candidates.append({
                    "domain_id": "business.knowledge_files",
                    "entity_id": object_id,
                    "source_sha256": sha256(raw).hexdigest(),
                    "state": state,
                    "legacy_source_retained": True,
                })

        finance_inbox_path = self.legacy_root / "business_containers" / workspace_id / "finance_inbox.json"
        if finance_inbox_path.is_file():
            source_inbox = json.loads(finance_inbox_path.read_text(encoding="utf-8"))
            migrated_inbox = deepcopy(source_inbox)
            for document in migrated_inbox.get("documents") or []:
                source_meta = document.get("source") if isinstance(document, dict) else None
                if not isinstance(source_meta, dict) or source_meta.get("vault_object_id"):
                    continue
                storage_path = str(source_meta.get("storage_path") or "").strip()
                if not storage_path:
                    continue
                source = self._safe_legacy_file(storage_path)
                raw = source.read_bytes()
                object_id = "finmig-" + sha256(
                    f"{workspace_id}\0{document.get('id')}\0{sha256(raw).hexdigest()}".encode("utf-8")
                ).hexdigest()[:48]
                if execute:
                    self.object_store.put_bytes(
                        object_id=object_id, data=raw,
                        original_name=str(source_meta.get("filename") or source.name),
                        content_type=str(source_meta.get("mime_type") or mimetypes.guess_type(source.name)[0] or "application/octet-stream"),
                        idempotency_key=f"finance-inbox-migration-{object_id}",
                        actor_id=actor_id,
                        recorded_at=str(source_meta.get("received_at") or "1970-01-01T00:00:00+00:00"),
                    )
                    _metadata, copied = self.object_store.get_bytes(object_id=object_id)
                    if sha256(copied).digest() != sha256(raw).digest():
                        raise RuntimeError("finance_inbox_object_migration_verification_failed")
                source_meta.pop("storage_path", None)
                source_meta["vault_object_id"] = object_id
            target = self.guardian_containers.load_optional_dict(workspace_id, "finance_inbox")
            source_hash = _canonical_hash(migrated_inbox)
            if target is not None and _canonical_hash(target) != source_hash:
                raise BusinessVaultCoverageMigrationError("migration_target_conflict:business_container.finance_inbox")
            state = "already_verified" if target is not None else "ready"
            if execute and target is None:
                self.guardian_containers.save_dict(
                    workspace_id, "finance_inbox", migrated_inbox,
                    actor_id=actor_id,
                    idempotency_key=f"coverage-finance-inbox-{source_hash[:24]}",
                    expected_version=None,
                )
                copied = self.guardian_containers.load_dict(workspace_id, "finance_inbox")
                if _canonical_hash(copied) != source_hash:
                    raise RuntimeError("finance_inbox_container_migration_verification_failed")
                state = "migrated_verified"
            candidates.append({
                "domain_id": "business_container.finance_inbox", "kind": "finance_inbox",
                "source_sha256": source_hash, "state": state, "legacy_source_retained": True,
            })

        onboarding = self.legacy_root / "foundation_onboarding" / f"{workspace_id}.json"
        if onboarding.is_file():
            payload = json.loads(onboarding.read_text(encoding="utf-8"))
            state = self._copy_json(
                domain_id="onboarding.foundation_session",
                workspace_id=workspace_id,
                entity_id="foundation-session",
                payload=payload,
                actor_id=actor_id,
                execute=execute,
            )
            candidates.append({"domain_id": "onboarding.foundation_session", "entity_id": "foundation-session", "state": state})
        onboarding_receipts = onboarding.with_name(f"{workspace_id}.receipts.jsonl")
        if onboarding_receipts.is_file():
            for position, raw in enumerate(onboarding_receipts.read_text(encoding="utf-8").splitlines(), start=1):
                if not raw.strip():
                    continue
                payload = json.loads(raw)
                entity_id = f"legacy-receipt-{position:08d}"
                state = self._copy_json(
                    domain_id="onboarding.receipts", workspace_id=workspace_id,
                    entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                )
                candidates.append({"domain_id": "onboarding.receipts", "entity_id": entity_id, "state": state})

        for feature, folder_name, id_keys in (
            ("skills", "browser_skills", ("skill_id", "id")),
            ("chains", "browser_chains", ("chain_id", "id")),
        ):
            folder = self.legacy_root / folder_name / workspace_id
            if not folder.is_dir():
                continue
            for path in sorted(folder.glob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                record_id = next(
                    (str(payload.get(key)).strip() for key in id_keys if str(payload.get(key) or "").strip()),
                    path.stem,
                )
                entity_id = f"browser_automation/{feature}/{record_id}"
                state = self._copy_json(
                    domain_id="train_agent.automations", workspace_id=workspace_id,
                    entity_id=entity_id,
                    payload={**payload, "legacy_source_retained": True},
                    actor_id=actor_id, execute=execute,
                )
                candidates.append({
                    "domain_id": "train_agent.automations", "entity_id": entity_id,
                    "state": state,
                })

        # Legacy Local Node/AION Agent repositories used two historical path
        # layouts.  Copy both into the exact entity namespace now used by the
        # Guardian-backed compatibility repositories.  Definitions and
        # triggers are authoritative automation state; approvals and runs are
        # retained as execution/audit evidence.
        legacy_agent_sources = (
            (
                "workflow_definitions",
                self.legacy_root / "aion_agents" / "workflow_definitions" / workspace_id,
                "train_agent.automations",
            ),
            (
                "workflow_runs",
                self.legacy_root / "aion_agents" / "workflow_runs" / workspace_id,
                "train_agent.runs_and_audit",
            ),
            (
                "approval_requests",
                self.legacy_root / "aion_agents" / "approval_requests" / workspace_id,
                "train_agent.runs_and_audit",
            ),
            (
                "agent_definitions",
                self.legacy_root / workspace_id / "aion_agents" / "agent_definitions",
                "train_agent.automations",
            ),
            (
                "trigger_definitions",
                self.legacy_root / workspace_id / "aion_agents" / "trigger_definitions",
                "train_agent.automations",
            ),
        )
        for kind, folder, domain_id in legacy_agent_sources:
            if not folder.is_dir():
                continue
            for path in sorted(folder.glob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                payload_workspace = str(payload.get("workspace_id") or workspace_id)
                if canonical_business_id(payload_workspace) != workspace_id:
                    raise BusinessVaultCoverageMigrationError(
                        f"legacy_agent_workspace_mismatch:{kind}:{path.stem}"
                    )
                _discover_department_ids(payload, discovered_departments)
                item_id = str(
                    payload.get("id")
                    or payload.get("agent_id")
                    or payload.get("trigger_id")
                    or path.stem
                )
                entity_id = f"legacy_aion_agents/{kind}/{item_id}"
                state = self._copy_json(
                    domain_id=domain_id,
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append(
                    {"domain_id": domain_id, "entity_id": entity_id, "state": state}
                )

        # The workflow canvas predates the AION Agent repositories and used a
        # separate Local Node tree.  Preserve its diagrams, approval state and
        # append-only execution history in the same Train Agent Vault domains
        # used by the Guardian-backed workflow repositories.
        workflow_glyph_root = self.local_node_root / workspace_id / "aion_workflows"
        if workflow_glyph_root.is_dir():
            for path in sorted(workflow_glyph_root.glob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                payload_workspace = str(payload.get("business_container") or workspace_id)
                if canonical_business_id(payload_workspace) != workspace_id:
                    raise BusinessVaultCoverageMigrationError(
                        f"legacy_workflow_workspace_mismatch:glyph:{path.stem}"
                    )
                _discover_department_ids(payload, discovered_departments)
                workflow_id = str(payload.get("workflow_id") or path.stem)
                entity_id = f"legacy_aion_agents/workflow_glyphs/{workflow_id}"
                state = self._copy_json(
                    domain_id="train_agent.automations",
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "train_agent.automations",
                    "entity_id": entity_id,
                    "state": state,
                })

        workflow_approval_root = (
            self.local_node_root / workspace_id / "aion_workflow_approvals"
        )
        if workflow_approval_root.is_dir():
            for path in sorted(workflow_approval_root.rglob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                payload_workspace = str(payload.get("business_container") or workspace_id)
                if canonical_business_id(payload_workspace) != workspace_id:
                    raise BusinessVaultCoverageMigrationError(
                        f"legacy_workflow_workspace_mismatch:approval:{path.stem}"
                    )
                _discover_department_ids(payload, discovered_departments)
                approval_id = str(payload.get("approval_id") or path.stem)
                entity_id = f"legacy_aion_agents/workflow_approvals/{approval_id}"
                state = self._copy_json(
                    domain_id="train_agent.runs_and_audit",
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "train_agent.runs_and_audit",
                    "entity_id": entity_id,
                    "state": state,
                })

        workflow_audit_root = self.local_node_root / workspace_id / "aion_workflow_audit"
        if workflow_audit_root.is_dir():
            for path in sorted(workflow_audit_root.glob("*.jsonl")):
                for position, raw in enumerate(
                    path.read_text(encoding="utf-8").splitlines(), start=1
                ):
                    if not raw.strip():
                        continue
                    payload = json.loads(raw)
                    payload_workspace = str(
                        payload.get("business_container") or workspace_id
                    )
                    if canonical_business_id(payload_workspace) != workspace_id:
                        raise BusinessVaultCoverageMigrationError(
                            f"legacy_workflow_workspace_mismatch:audit:{path.stem}"
                        )
                    _discover_department_ids(payload, discovered_departments)
                    workflow_id = str(payload.get("workflow_id") or path.stem)
                    kind = (
                        "workflow_resume_runs"
                        if str(payload.get("mode") or "").startswith("resume_")
                        else "workflow_dry_runs"
                    )
                    item_id = f"{workflow_id}/legacy-{position:08d}"
                    entity_id = f"legacy_aion_agents/{kind}/{item_id}"
                    state = self._copy_json(
                        domain_id="train_agent.runs_and_audit",
                        workspace_id=workspace_id,
                        entity_id=entity_id,
                        payload=payload,
                        actor_id=actor_id,
                        execute=execute,
                    )
                    candidates.append({
                        "domain_id": "train_agent.runs_and_audit",
                        "entity_id": entity_id,
                        "state": state,
                    })

        # The Master Glyph Library mixes signed universal product templates
        # with customer-authored "my" glyphs.  Only the latter are business
        # data.  The index is derived and is intentionally not migrated.
        capsule_glyph_root = self.workflow_capsule_root / "glyph_store" / "items"
        if capsule_glyph_root.is_dir():
            for path in sorted(capsule_glyph_root.glob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                scope = str(payload.get("scope") or "my").strip().lower()
                if scope == "universal":
                    continue
                if scope != "my":
                    raise BusinessVaultCoverageMigrationError(
                        f"legacy_workflow_glyph_scope_invalid:{path.stem}"
                    )
                _discover_department_ids(payload, discovered_departments)
                glyph_code = str(payload.get("glyph_code") or path.stem).strip().upper()
                glyph_version = str(payload.get("glyph_version") or "v1").strip()
                item_id = f"{glyph_code}/{glyph_version}"
                entity_id = (
                    "legacy_aion_agents/workflow_capsule_glyphs/" + item_id
                )
                state = self._copy_json(
                    domain_id="train_agent.automations",
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "train_agent.automations",
                    "entity_id": entity_id,
                    "state": state,
                })

        # Customer workspace capsules are business-authored automation state;
        # core capsules remain signed, replaceable application content.
        capsule_workspace_root = (
            self.workflow_capsule_root / "workspace" / workspace_id
        )
        if capsule_workspace_root.is_dir():
            for path in sorted(capsule_workspace_root.glob("*.workflow.wiki.phn")):
                capsule = WorkflowCapsule.from_text(path.read_text(encoding="utf-8"))
                payload = capsule.to_dict()
                _discover_department_ids(payload, discovered_departments)
                item_id = _safe_workflow_capsule_key(capsule.canonical_key)
                entity_id = (
                    "legacy_aion_agents/workflow_capsule_workspace_capsules/"
                    + item_id
                )
                state = self._copy_json(
                    domain_id="train_agent.automations",
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "train_agent.automations",
                    "entity_id": entity_id,
                    "state": state,
                })

        capsule_approval_items = self.workflow_capsule_root / "approvals" / "items"
        if capsule_approval_items.is_dir():
            for path in sorted(capsule_approval_items.glob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                _discover_department_ids(payload, discovered_departments)
                approval_id = str(payload.get("approval_id") or path.stem)
                entity_id = (
                    "legacy_aion_agents/workflow_capsule_approvals/"
                    + approval_id
                )
                state = self._copy_json(
                    domain_id="train_agent.runs_and_audit",
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "train_agent.runs_and_audit",
                    "entity_id": entity_id,
                    "state": state,
                })

        capsule_jsonl_sources = (
            (
                self.workflow_capsule_root / "approvals" / "workflow_approvals.jsonl",
                "workflow_capsule_approval_events",
                "approval_id",
            ),
            (
                self.workflow_capsule_root / "runs" / "workflow_execution_log.jsonl",
                "workflow_capsule_traces",
                "run_id",
            ),
            (
                self.workflow_capsule_root / "feedback" / "workflow_capsule_feedback.jsonl",
                "workflow_capsule_feedback",
                "run_id",
            ),
            (
                self.workflow_capsule_root / "habits" / "habit_promotion_log.jsonl",
                "workflow_capsule_habit_promotion_events",
                "source_workflow_key",
            ),
        )
        for path, kind, id_key in capsule_jsonl_sources:
            if not path.is_file():
                continue
            for position, raw in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if not raw.strip():
                    continue
                payload = json.loads(raw)
                _discover_department_ids(payload, discovered_departments)
                id_source = payload
                if kind == "workflow_capsule_approval_events":
                    id_source = payload.get("approval") or payload
                base_id = str(id_source.get(id_key) or kind).replace("/", "_")
                item_id = f"{base_id}-legacy-{position:08d}"
                entity_id = f"legacy_aion_agents/{kind}/{item_id}"
                state = self._copy_json(
                    domain_id="train_agent.runs_and_audit",
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "train_agent.runs_and_audit",
                    "entity_id": entity_id,
                    "state": state,
                })

        capsule_habit_root = self.workflow_capsule_root / "habits"
        if capsule_habit_root.is_dir():
            for path in sorted(capsule_habit_root.glob("habit_*.json")):
                if path.name == "habit_capsule_registry.json":
                    continue
                payload = json.loads(path.read_text(encoding="utf-8"))
                _discover_department_ids(payload, discovered_departments)
                habit_key = str(payload.get("habit_key") or path.stem).replace("/", "_")
                entity_id = (
                    "legacy_aion_agents/workflow_capsule_habits/" + habit_key
                )
                state = self._copy_json(
                    domain_id="train_agent.automations",
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "train_agent.automations",
                    "entity_id": entity_id,
                    "state": state,
                })

        capsule_local_binding_root = self.workflow_capsule_root / "local_bindings"
        if capsule_local_binding_root.is_dir():
            for path in sorted(capsule_local_binding_root.glob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                payload_workspace = canonical_business_id(
                    str(payload.get("workspace_id") or workspace_id)
                )
                if payload_workspace != workspace_id:
                    raise BusinessVaultCoverageMigrationError(
                        f"legacy_workflow_local_binding_workspace_mismatch:{path.stem}"
                    )
                _discover_department_ids(payload, discovered_departments)
                binding_key = str(payload.get("binding_key") or path.stem)
                item_id = _safe_workflow_capsule_key(binding_key)
                entity_id = (
                    "legacy_aion_agents/workflow_capsule_local_bindings/"
                    + item_id
                )
                state = self._copy_json(
                    domain_id="train_agent.automations",
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "train_agent.automations",
                    "entity_id": entity_id,
                    "state": state,
                })

        work_schedule_path = self.legacy_root / "business_containers" / workspace_id / "work_schedule.json"
        if work_schedule_path.is_file():
            schedule = json.loads(work_schedule_path.read_text(encoding="utf-8"))
            migrated_schedule = deepcopy(schedule)
            for item in migrated_schedule.get("items") or migrated_schedule.get("jobs") or []:
                if not isinstance(item, dict):
                    continue
                for document in item.get("documents") or []:
                    if not isinstance(document, dict) or document.get("vault_object_id"):
                        continue
                    stored_name = Path(str(document.get("stored_name") or "")).name
                    if not stored_name:
                        continue
                    source = self._safe_legacy_file(
                        self.legacy_root / "business_containers" / workspace_id
                        / "work_schedule_files" / str(item.get("id") or "work") / stored_name
                    )
                    raw = source.read_bytes()
                    object_id = "workmig-" + sha256(
                        f"{workspace_id}\0{item.get('id')}\0{document.get('id')}\0{sha256(raw).hexdigest()}".encode("utf-8")
                    ).hexdigest()[:48]
                    if execute:
                        self.object_store.put_bytes(
                            object_id=object_id, data=raw,
                            original_name=str(document.get("name") or source.name),
                            content_type=str(document.get("content_type") or mimetypes.guess_type(source.name)[0] or "application/octet-stream"),
                            idempotency_key=f"work-schedule-migration-{object_id}",
                            actor_id=actor_id,
                            recorded_at=str(document.get("created_at") or schedule.get("updated_at") or "1970-01-01T00:00:00+00:00"),
                        )
                        metadata, copied = self.object_store.get_bytes(object_id=object_id)
                        if sha256(copied).digest() != sha256(raw).digest():
                            raise RuntimeError(f"migration_verification_failed:work_schedule.files:{object_id}")
                        document["vault_plaintext_sha256"] = metadata["plaintext_sha256"]
                        document["vault_receipt_hash"] = metadata.get("receipt_hash")
                    document["vault_object_id"] = object_id
                    candidates.append({
                        "domain_id": "work_schedule.files", "entity_id": object_id,
                        "state": "migrated_verified" if execute else "ready",
                    })
            state = self._copy_json(
                domain_id="work_schedule.records", workspace_id=workspace_id,
                entity_id="schedule", payload=migrated_schedule,
                actor_id=actor_id, execute=execute,
            )
            candidates.append({"domain_id": "work_schedule.records", "entity_id": "schedule", "state": state})

        department_root = self.legacy_root / "department_pilot_runtime" / workspace_id
        if department_root.is_dir():
            for department in sorted(path for path in department_root.iterdir() if path.is_dir()):
                discovered_departments.add(department.name)
                for task_path in sorted((department / "tasks").glob("*.json")):
                    payload = json.loads(task_path.read_text(encoding="utf-8"))
                    entity_id = f"{department.name}/{task_path.stem}"
                    state = self._copy_json(
                        domain_id="departments.pilot_tasks", workspace_id=workspace_id,
                        entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                    )
                    candidates.append({"domain_id": "departments.pilot_tasks", "entity_id": entity_id, "state": state})
                audit = department / "audit.jsonl"
                if audit.is_file():
                    for position, raw in enumerate(audit.read_text(encoding="utf-8").splitlines(), start=1):
                        if not raw.strip():
                            continue
                        payload = json.loads(raw)
                        entity_id = f"{department.name}/legacy-event-{position:08d}"
                        state = self._copy_json(
                            domain_id="departments.pilot_audit", workspace_id=workspace_id,
                            entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                        )
                        candidates.append({"domain_id": "departments.pilot_audit", "entity_id": entity_id, "state": state})

        finance_conversation = (
            department_root / "finance" / "conversations" / "finance_terminal.json"
        )
        if finance_conversation.is_file():
            payload = json.loads(finance_conversation.read_text(encoding="utf-8"))
            entity_id = "pilot/conversation"
            state = self._copy_json(
                domain_id="finance.operations_records", workspace_id=workspace_id,
                entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
            )
            candidates.append({
                "domain_id": "finance.operations_records", "entity_id": entity_id,
                "state": state,
            })

        specialist_root = self.legacy_root / "external_specialists" / workspace_id
        if specialist_root.is_dir():
            for path in sorted(specialist_root.glob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                specialist_id = str(payload.get("id") or path.stem)
                entity_id = f"business_operations/external_specialists/{specialist_id}"
                state = self._copy_json(
                    domain_id="departments.operational_records",
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "departments.operational_records",
                    "entity_id": entity_id,
                    "state": state,
                })

        work_order_root = self.legacy_root / "external_work_orders" / workspace_id
        if work_order_root.is_dir():
            for path in sorted(work_order_root.glob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                record_id = str(payload.get("id") or path.stem)
                entity_id = f"business_operations/external_work_orders/{record_id}"
                state = self._copy_json(
                    domain_id="departments.operational_records", workspace_id=workspace_id,
                    entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                )
                candidates.append({
                    "domain_id": "departments.operational_records", "entity_id": entity_id,
                    "state": state,
                })

        project_management_path = (
            self.legacy_root / "business_containers" / workspace_id
            / "project_management.json"
        )
        if project_management_path.is_file():
            payload = json.loads(project_management_path.read_text(encoding="utf-8"))
            entity_id = "projects/project_management/portfolio"
            state = self._copy_json(
                domain_id="departments.operational_records",
                workspace_id=workspace_id,
                entity_id=entity_id,
                payload=payload,
                actor_id=actor_id,
                execute=execute,
            )
            candidates.append({
                "domain_id": "departments.operational_records",
                "entity_id": entity_id,
                "state": state,
            })

        founder_review_trigger = (
            self.legacy_root / "founder_review_triggers" / f"{workspace_id}.json"
        )
        if founder_review_trigger.is_file():
            payload = json.loads(founder_review_trigger.read_text(encoding="utf-8"))
            entity_id = "founder_review/triggers/config"
            state = self._copy_json(
                domain_id="train_agent.automations",
                workspace_id=workspace_id,
                entity_id=entity_id,
                payload=payload,
                actor_id=actor_id,
                execute=execute,
            )
            candidates.append({
                "domain_id": "train_agent.automations",
                "entity_id": entity_id,
                "state": state,
            })

        improvement_root = self.legacy_root / "governed_improvement" / workspace_id
        improvement_domains = {
            "corrections": "train_agent.runs_and_audit",
            "verified_outcomes": "train_agent.runs_and_audit",
            "customer_change_log": "train_agent.runs_and_audit",
            "route_preferences": "train_agent.automations",
            "automation_proposals": "train_agent.automations",
            "curated_datasets": "train_agent.automations",
            "model_releases": "train_agent.automations",
        }
        for stem, domain_id in improvement_domains.items():
            path = improvement_root / f"{stem}.json"
            if not path.is_file():
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            entity_id = f"governed_improvement/{stem}"
            state = self._copy_json(
                domain_id=domain_id, workspace_id=workspace_id,
                entity_id=entity_id, payload=payload, actor_id=actor_id,
                execute=execute,
            )
            candidates.append({
                "domain_id": domain_id, "entity_id": entity_id, "state": state,
            })

        model_catalogue_root = self.legacy_root / "signed_model_catalogue" / workspace_id
        for filename, domain_id, entity_id in (
            ("model_catalogue.json", "train_agent.automations", "model_catalogue/state"),
            (
                "customer_private_outcomes.json", "train_agent.runs_and_audit",
                "model_catalogue/customer_private_outcomes",
            ),
        ):
            path = model_catalogue_root / filename
            if not path.is_file():
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            state = self._copy_json(
                domain_id=domain_id, workspace_id=workspace_id,
                entity_id=entity_id, payload=payload, actor_id=actor_id,
                execute=execute,
            )
            candidates.append({
                "domain_id": domain_id, "entity_id": entity_id, "state": state,
            })

        telephony_metadata = (
            self.legacy_root / "business_containers" / workspace_id
            / "integrations" / "sales_telephony.json"
        )
        if telephony_metadata.is_file():
            payload = json.loads(telephony_metadata.read_text(encoding="utf-8"))
            entity_id = "sales/integrations/telephony"
            state = self._copy_json(
                domain_id="departments.operational_records",
                workspace_id=workspace_id, entity_id=entity_id, payload=payload,
                actor_id=actor_id, execute=execute,
            )
            candidates.append({
                "domain_id": "departments.operational_records",
                "entity_id": entity_id, "state": state,
            })

        medium_root = self.legacy_root / "business_containers" / workspace_id / "medium_business"
        medium_model = medium_root / "medium_business_operating_model.json"
        if medium_model.is_file():
            payload = json.loads(medium_model.read_text(encoding="utf-8"))
            entity_id = "business_operations/medium_business_operating_model/model"
            state = self._copy_json(
                domain_id="departments.operational_records", workspace_id=workspace_id,
                entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
            )
            candidates.append({
                "domain_id": "departments.operational_records", "entity_id": entity_id,
                "state": state,
            })
        medium_audit = medium_root / "medium_business_audit.json"
        if medium_audit.is_file():
            audit_payload = json.loads(medium_audit.read_text(encoding="utf-8"))
            for position, payload in enumerate(audit_payload.get("events") or [], start=1):
                entity_id = f"business_operations/medium_business_operating_model/legacy-event-{position:08d}"
                state = self._copy_json(
                    domain_id="departments.operational_audit", workspace_id=workspace_id,
                    entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                )
                candidates.append({
                    "domain_id": "departments.operational_audit", "entity_id": entity_id,
                    "state": state,
                })

        runtime_audit_root = self.legacy_root / "audit" / workspace_id
        if runtime_audit_root.is_dir():
            for path in sorted(runtime_audit_root.glob("*.jsonl")):
                for position, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                    if not raw.strip():
                        continue
                    payload = json.loads(raw)
                    event_id = str(payload.get("id") or f"legacy-event-{position:08d}")
                    entity_id = f"business_operations/runtime_audit/{path.stem}/{event_id}"
                    state = self._copy_json(
                        domain_id="departments.operational_audit", workspace_id=workspace_id,
                        entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                    )
                    candidates.append({
                        "domain_id": "departments.operational_audit", "entity_id": entity_id,
                        "state": state,
                    })

        legacy_operational_records = (
            (
                self.legacy_root / "workspaces" / f"{workspace_id}.json",
                "workspaces/workspace",
            ),
            (
                self.legacy_root / "topologies" / f"{workspace_id}.json",
                "topologies/topology",
            ),
        )
        for path, suffix in legacy_operational_records:
            if not path.is_file():
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            entity_id = f"business_operations/{suffix}"
            state = self._copy_json(
                domain_id="departments.operational_records", workspace_id=workspace_id,
                entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
            )
            candidates.append({
                "domain_id": "departments.operational_records", "entity_id": entity_id,
                "state": state,
            })
        binding_root = self.legacy_root / "container_bindings" / workspace_id
        if binding_root.is_dir():
            for path in sorted(binding_root.glob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                record_id = str(payload.get("id") or path.stem)
                entity_id = f"business_operations/container_bindings/{record_id}"
                state = self._copy_json(
                    domain_id="departments.operational_records", workspace_id=workspace_id,
                    entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                )
                candidates.append({
                    "domain_id": "departments.operational_records", "entity_id": entity_id,
                    "state": state,
                })
        for feature_id in ("agents", "roles", "tasks", "learning"):
            feature_root = self.legacy_root / feature_id / workspace_id
            if not feature_root.is_dir():
                continue
            for path in sorted(feature_root.glob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                record_id = str(payload.get("id") or path.stem)
                entity_id = f"business_operations/{feature_id}/{record_id}"
                state = self._copy_json(
                    domain_id="departments.operational_records", workspace_id=workspace_id,
                    entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                )
                candidates.append({
                    "domain_id": "departments.operational_records", "entity_id": entity_id,
                    "state": state,
                })

        # AION's early learning loop stored customer-derived teaching memory,
        # skill-run evidence and the weakness model in a single-installation
        # data tree.  Copy those records into the dedicated customer learning
        # domains.  Explicit product models, algorithms and rebuildable caches
        # are intentionally not imported by this pass.
        teaching_memory_path = self.aion_learning_root / "logs" / "phase0_learning_memory.json"
        if teaching_memory_path.is_file():
            payload = json.loads(teaching_memory_path.read_text(encoding="utf-8"))
            state = self._copy_json(
                domain_id="learning.customer_state",
                workspace_id=workspace_id,
                entity_id="teaching_memory",
                payload=payload,
                actor_id=actor_id,
                execute=execute,
            )
            candidates.append({
                "domain_id": "learning.customer_state",
                "entity_id": "teaching_memory",
                "state": state,
            })

        weakness_path = self.aion_learning_root / "learning" / "aion_weakness_signals.json"
        if weakness_path.is_file():
            payload = json.loads(weakness_path.read_text(encoding="utf-8"))
            state = self._copy_json(
                domain_id="learning.customer_state",
                workspace_id=workspace_id,
                entity_id="weakness_signals",
                payload=payload,
                actor_id=actor_id,
                execute=execute,
            )
            candidates.append({
                "domain_id": "learning.customer_state",
                "entity_id": "weakness_signals",
                "state": state,
            })

        learning_events_path = self.aion_learning_root / "learning" / "aion_learning_events.jsonl"
        if learning_events_path.is_file():
            for position, raw in enumerate(
                learning_events_path.read_text(encoding="utf-8").splitlines(),
                start=1,
            ):
                if not raw.strip():
                    continue
                payload = json.loads(raw)
                event_id = str(payload.get("event_id") or f"legacy-event-{position:012d}")
                state = self._copy_json(
                    domain_id="learning.audit",
                    workspace_id=workspace_id,
                    entity_id=event_id,
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "learning.audit",
                    "entity_id": event_id,
                    "state": state,
                })

        decision_weights_path = (
            self.aion_learning_root / "trading" / "decision_influence_weights.json"
        )
        if decision_weights_path.is_file():
            payload = json.loads(decision_weights_path.read_text(encoding="utf-8"))
            state = self._copy_json(
                domain_id="learning.customer_state",
                workspace_id=workspace_id,
                entity_id="decision_influence_weights",
                payload=payload,
                actor_id=actor_id,
                execute=execute,
            )
            candidates.append({
                "domain_id": "learning.customer_state",
                "entity_id": "decision_influence_weights",
                "state": state,
            })

        decision_audit_path = (
            self.aion_learning_root / "trading" / "decision_influence_audit.jsonl"
        )
        if decision_audit_path.is_file():
            for position, raw in enumerate(
                decision_audit_path.read_text(encoding="utf-8").splitlines(),
                start=1,
            ):
                if not raw.strip():
                    continue
                payload = json.loads(raw)
                audit_id = str(payload.get("audit_id") or f"legacy-audit-{position:012d}")
                payload.setdefault("event_type", "decision_influence_audit")
                payload.setdefault("vault_order_ns", position)
                state = self._copy_json(
                    domain_id="learning.audit",
                    workspace_id=workspace_id,
                    entity_id=f"decision-influence-{audit_id}",
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "learning.audit",
                    "entity_id": f"decision-influence-{audit_id}",
                    "state": state,
                })

        resonance_state_path = (
            self.aion_learning_root / "predictive" / "resonance_state.json"
        )
        if resonance_state_path.is_file():
            payload = json.loads(resonance_state_path.read_text(encoding="utf-8"))
            state = self._copy_json(
                domain_id="learning.customer_state",
                workspace_id=workspace_id,
                entity_id="resonance_state",
                payload=payload,
                actor_id=actor_id,
                execute=execute,
            )
            candidates.append({
                "domain_id": "learning.customer_state",
                "entity_id": "resonance_state",
                "state": state,
            })

        resonance_log_path = self.aion_learning_root / "analysis" / "resonance_delta.jsonl"
        if resonance_log_path.is_file():
            for position, raw in enumerate(
                resonance_log_path.read_text(encoding="utf-8").splitlines(),
                start=1,
            ):
                if not raw.strip():
                    continue
                payload = json.loads(raw)
                entity_id = f"gradient-correction-legacy-{position:012d}"
                payload.setdefault("event_id", entity_id)
                payload.setdefault("event_type", "gradient_correction")
                state = self._copy_json(
                    domain_id="learning.audit",
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "learning.audit",
                    "entity_id": entity_id,
                    "state": state,
                })

        llm_accuracy_path = self.aion_learning_root / "trading" / "llm_accuracy_log.jsonl"
        if llm_accuracy_path.is_file():
            for position, raw in enumerate(
                llm_accuracy_path.read_text(encoding="utf-8").splitlines(),
                start=1,
            ):
                if not raw.strip():
                    continue
                payload = json.loads(raw)
                entity_id = f"llm-accuracy-legacy-{position:012d}"
                payload.setdefault("event_id", entity_id)
                payload.setdefault("record_type", "llm_accuracy")
                state = self._copy_json(
                    domain_id="learning.audit",
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "learning.audit",
                    "entity_id": entity_id,
                    "state": state,
                })

        # AION Prediction historically mixed customer temporal observations,
        # private learned transition state and evaluation evidence below the
        # application-relative data tree.  Copy authoritative private state
        # and immutable evidence into the same business-scoped learning
        # boundary used by the live prediction runtime.
        temporal_buffer_path = (
            self.aion_learning_root / "predictive" / "temporal_buffer.json"
        )
        if temporal_buffer_path.is_file():
            for position, raw in enumerate(
                temporal_buffer_path.read_text(encoding="utf-8").splitlines(),
                start=1,
            ):
                if not raw.strip():
                    continue
                payload = json.loads(raw)
                entity_id = f"temporal-sequence-legacy-{position:012d}"
                payload.setdefault("event_id", entity_id)
                payload.setdefault("event_type", "temporal_sequence")
                payload.setdefault("vault_order_ns", position)
                state = self._copy_json(
                    domain_id="learning.audit",
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "learning.audit",
                    "entity_id": entity_id,
                    "state": state,
                })

        temporal_model_path = (
            self.aion_learning_root / "prediction" / "temporal_model.json"
        )
        if temporal_model_path.is_file():
            payload = json.loads(temporal_model_path.read_text(encoding="utf-8"))
            if "markov_graph" not in payload:
                payload = {"markov_graph": payload}
            state = self._copy_json(
                domain_id="learning.customer_state",
                workspace_id=workspace_id,
                entity_id="temporal_coherence_model",
                payload=payload,
                actor_id=actor_id,
                execute=execute,
            )
            candidates.append({
                "domain_id": "learning.customer_state",
                "entity_id": "temporal_coherence_model",
                "state": state,
            })

        predictive_bias_path = (
            self.aion_learning_root / "predictive" / "predictive_bias_state.json"
        )
        if predictive_bias_path.is_file():
            payload = json.loads(predictive_bias_path.read_text(encoding="utf-8"))
            state = self._copy_json(
                domain_id="learning.customer_state",
                workspace_id=workspace_id,
                entity_id="predictive_bias_state",
                payload=payload,
                actor_id=actor_id,
                execute=execute,
            )
            candidates.append({
                "domain_id": "learning.customer_state",
                "entity_id": "predictive_bias_state",
                "state": state,
            })

        predictive_log_path = (
            self.aion_learning_root / "predictive" / "predictive_transitions.jsonl"
        )
        if predictive_log_path.is_file():
            for position, raw in enumerate(
                predictive_log_path.read_text(encoding="utf-8").splitlines(),
                start=1,
            ):
                if not raw.strip():
                    continue
                payload = json.loads(raw)
                event_type = str(payload.get("event_type") or "predictive_transition")
                entity_id = f"{event_type}-legacy-{position:012d}"
                payload.setdefault("event_id", entity_id)
                payload.setdefault("event_type", event_type)
                payload.setdefault("vault_order_ns", position)
                state = self._copy_json(
                    domain_id="learning.audit",
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "learning.audit",
                    "entity_id": entity_id,
                    "state": state,
                })

        phi_state_path = self.aion_resonance_root / "resonance_state.json"
        if phi_state_path.is_file():
            payload = json.loads(phi_state_path.read_text(encoding="utf-8"))
            state = self._copy_json(
                domain_id="learning.customer_state",
                workspace_id=workspace_id,
                entity_id="aion_phi_state",
                payload=payload,
                actor_id=actor_id,
                execute=execute,
            )
            candidates.append({
                "domain_id": "learning.customer_state",
                "entity_id": "aion_phi_state",
                "state": state,
            })

        legacy_lexicon_path = self.aion_resonance_root / "boot_config.json"
        if legacy_lexicon_path.is_file():
            legacy_lexicon = json.loads(
                legacy_lexicon_path.read_text(encoding="utf-8")
            )
            overrides = {
                str(term): dict(signature)
                for term, signature in (
                    legacy_lexicon.items()
                    if isinstance(legacy_lexicon, dict) else []
                )
                if isinstance(signature, dict)
            }
            payload = {
                "overrides": overrides,
                "base_lexicon_is_application_content": True,
                "legacy_full_map_imported": True,
                "requires_baseline_review": True,
            }
            state = self._copy_json(
                domain_id="learning.customer_state",
                workspace_id=workspace_id,
                entity_id="resonance_lexicon_overrides",
                payload=payload,
                actor_id=actor_id,
                execute=execute,
            )
            candidates.append({
                "domain_id": "learning.customer_state",
                "entity_id": "resonance_lexicon_overrides",
                "state": state,
            })

        conversation_memory_path = (
            self.aion_resonance_data_root / "conversation_memory.json"
        )
        if conversation_memory_path.is_file():
            entries = json.loads(conversation_memory_path.read_text(encoding="utf-8"))
            payload = {"entries": entries if isinstance(entries, list) else []}
            state = self._copy_json(
                domain_id="learning.customer_state",
                workspace_id=workspace_id,
                entity_id="conversation_memory",
                payload=payload,
                actor_id=actor_id,
                execute=execute,
            )
            candidates.append({
                "domain_id": "learning.customer_state",
                "entity_id": "conversation_memory",
                "state": state,
            })

        reinforce_state_path = (
            self.aion_resonance_data_root / "phi_reinforce_state.json"
        )
        if reinforce_state_path.is_file():
            payload = json.loads(reinforce_state_path.read_text(encoding="utf-8"))
            state = self._copy_json(
                domain_id="learning.customer_state",
                workspace_id=workspace_id,
                entity_id="phi_reinforce_state",
                payload=payload if isinstance(payload, dict) else {},
                actor_id=actor_id,
                execute=execute,
            )
            candidates.append({
                "domain_id": "learning.customer_state",
                "entity_id": "phi_reinforce_state",
                "state": state,
            })

        phi_graph_path = self.aion_resonance_data_root / "phi_graph.json"
        if phi_graph_path.is_file():
            payload = json.loads(phi_graph_path.read_text(encoding="utf-8"))
            state = self._copy_json(
                domain_id="learning.customer_state",
                workspace_id=workspace_id,
                entity_id="phi_relationship_graph",
                payload=payload if isinstance(payload, dict) else {},
                actor_id=actor_id,
                execute=execute,
            )
            candidates.append({
                "domain_id": "learning.customer_state",
                "entity_id": "phi_relationship_graph",
                "state": state,
            })

        for filename, event_type, prefix in (
            ("phi_trace.json", "phi_learning_trace", "phi-learning-legacy"),
            ("phi_drift_log.json", "phi_drift", "phi-drift-legacy"),
        ):
            event_path = self.aion_resonance_data_root / filename
            if not event_path.is_file():
                continue
            entries = json.loads(event_path.read_text(encoding="utf-8"))
            for position, entry in enumerate(
                entries if isinstance(entries, list) else [], start=1
            ):
                if not isinstance(entry, dict):
                    continue
                entity_id = f"{prefix}-{position:012d}"
                payload = {
                    **entry,
                    "event_id": entity_id,
                    "event_type": event_type,
                    "ts_utc": str(
                        entry.get("timestamp_readable")
                        or entry.get("timestamp")
                        or ""
                    ),
                    "vault_order_ns": position,
                }
                state = self._copy_json(
                    domain_id="learning.audit",
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "learning.audit",
                    "entity_id": entity_id,
                    "state": state,
                })

        symbolic_memory_path = self.aion_resonance_data_root / "symbolic_memory.json"
        if symbolic_memory_path.is_file():
            entries = json.loads(symbolic_memory_path.read_text(encoding="utf-8"))
            for position, entry in enumerate(
                entries if isinstance(entries, list) else [], start=1
            ):
                if not isinstance(entry, dict):
                    continue
                entity_id = f"symbolic-reflection-legacy-{position:012d}"
                payload = {
                    **entry,
                    "event_id": entity_id,
                    "event_type": "symbolic_reflection",
                    "ts_utc": str(entry.get("timestamp") or ""),
                    "vault_order_ns": position,
                }
                state = self._copy_json(
                    domain_id="learning.audit",
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "learning.audit",
                    "entity_id": entity_id,
                    "state": state,
                })

        symatic_log_path = self.aion_resonance_data_root / "symatic_log.json"
        if symatic_log_path.is_file():
            entries = json.loads(symatic_log_path.read_text(encoding="utf-8"))
            if isinstance(entries, dict):
                entries = entries.get("log", [])
            for position, entry in enumerate(
                entries if isinstance(entries, list) else [], start=1
            ):
                if not isinstance(entry, dict):
                    continue
                entity_id = f"symatic-equation-legacy-{position:012d}"
                payload = {
                    **entry,
                    "event_id": entity_id,
                    "event_type": "symatic_equation",
                    "ts_utc": str(entry.get("timestamp") or ""),
                    "vault_order_ns": position,
                }
                state = self._copy_json(
                    domain_id="learning.audit",
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "learning.audit",
                    "entity_id": entity_id,
                    "state": state,
                })

        # Per-engine reinforcement histories contain customer-derived outcomes
        # and operator notes.  They are durable learning evidence, not
        # disposable heartbeat telemetry, despite their historical folder.
        reinforcement_root = self.aion_resonance_data_root / "telemetry"
        if reinforcement_root.is_dir():
            for history_path in sorted(
                reinforcement_root.glob("*_resonance_history.json")
            ):
                engine_name = history_path.name.removesuffix(
                    "_resonance_history.json"
                )
                entries = json.loads(history_path.read_text(encoding="utf-8"))
                for position, entry in enumerate(
                    entries if isinstance(entries, list) else [], start=1
                ):
                    if not isinstance(entry, dict):
                        continue
                    entity_id = (
                        f"resonance-reinforcement-{engine_name}-legacy-"
                        f"{position:012d}"
                    )
                    payload = {
                        **entry,
                        "event_id": entity_id,
                        "event_type": "resonance_reinforcement_snapshot",
                        "engine_name": engine_name,
                        "ts_utc": entry.get("timestamp") or "",
                        "vault_order_ns": position,
                    }
                    state = self._copy_json(
                        domain_id="learning.audit",
                        workspace_id=workspace_id,
                        entity_id=entity_id,
                        payload=payload,
                        actor_id=actor_id,
                        execute=execute,
                    )
                    candidates.append({
                        "domain_id": "learning.audit",
                        "entity_id": entity_id,
                        "state": state,
                    })

        # PAL snapshots may contain customer prompts, learned choices and
        # knowledge-graph links. Copy the retained JSONL evidence into the
        # encrypted learning audit domain before any source retirement.
        if (
            self.pal_snapshot_log_path is not None
            and self.pal_snapshot_log_path.is_file()
        ):
            for position, raw in enumerate(
                self.pal_snapshot_log_path.read_text(
                    encoding="utf-8"
                ).splitlines(),
                start=1,
            ):
                if not raw.strip():
                    continue
                payload = json.loads(raw)
                entity_id = str(
                    payload.get("event_id")
                    or f"pal-snapshot-legacy-{position:012d}"
                )
                payload.setdefault("event_id", entity_id)
                payload.setdefault("event_type", "pal_learning_snapshot")
                payload.setdefault(
                    "ts_utc", str(payload.get("timestamp") or "")
                )
                payload.setdefault("vault_order_ns", position)
                state = self._copy_json(
                    domain_id="learning.audit",
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "learning.audit",
                    "entity_id": entity_id,
                    "state": state,
                    "legacy_source_retained": True,
                })

        # Model-binding metadata is customer automation configuration. Raw
        # credentials stay in the separate encrypted secrets store; Guardian
        # receives only the opaque locator and binding lifecycle metadata.
        if (
            self.aion_flow_model_bindings_path is not None
            and self.aion_flow_model_bindings_path.is_file()
        ):
            source_state = json.loads(
                self.aion_flow_model_bindings_path.read_text(encoding="utf-8")
            )
            if (
                source_state.get("schema_version")
                != "aion.flow.model_bindings.v1"
                or not isinstance(source_state.get("bindings"), dict)
            ):
                raise BusinessVaultCoverageMigrationError(
                    "legacy_aion_flow_model_binding_state_invalid"
                )
            for binding_id, source_record in sorted(
                source_state["bindings"].items()
            ):
                if not isinstance(source_record, dict):
                    raise BusinessVaultCoverageMigrationError(
                        "legacy_aion_flow_model_binding_state_invalid"
                    )
                payload = {
                    **source_record,
                    "schema_version": "aion.flow.model_binding.v2",
                    "binding_id": str(binding_id),
                    "legacy_source_retained": True,
                }
                entity_id = f"aion_flow/model_binding/{binding_id}"
                state = self._copy_json(
                    domain_id="train_agent.automations",
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "train_agent.automations",
                    "entity_id": entity_id,
                    "state": state,
                    "legacy_source_retained": True,
                    "credential_material_migrated": False,
                })

        # The historical AION knowledge graph mixed customer-learned triplets
        # into an application-relative SQLite database. Copy each triplet into
        # its deterministic encrypted business.knowledge identity and retain
        # the database until a governed authority switch and retirement.
        if (
            self.aion_knowledge_db_path is not None
            and self.aion_knowledge_db_path.is_file()
        ):
            connection = sqlite3.connect(
                f"file:{self.aion_knowledge_db_path}?mode=ro", uri=True
            )
            try:
                tables = {
                    str(row[0])
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                table = "triplets" if "triplets" in tables else "knowledge"
                columns = {
                    str(row[1])
                    for row in connection.execute(
                        f"PRAGMA table_info({table})"
                    ).fetchall()
                }
                if not {"subject", "predicate", "object", "strength"}.issubset(
                    columns
                ):
                    raise BusinessVaultCoverageMigrationError(
                        "legacy_aion_knowledge_schema_invalid"
                    )
                vec_expression = "vec" if "vec" in columns else "NULL"
                timestamp_expression = (
                    "timestamp" if "timestamp" in columns else "NULL"
                )
                rows = connection.execute(
                    "SELECT subject,predicate,object,strength,"
                    f"{vec_expression},{timestamp_expression} FROM {table} "
                    "ORDER BY subject,predicate,object"
                ).fetchall()
            finally:
                connection.close()
            for position, row in enumerate(rows, start=1):
                subject = str(row[0])
                predicate = str(row[1])
                object_value = str(row[2])
                identity = sha256(
                    f"{subject}\0{predicate}\0{object_value}".encode("utf-8")
                ).hexdigest()
                entity_id = f"aion-knowledge-triplet-{identity}"
                vector = None
                if row[4] not in (None, ""):
                    try:
                        vector = json.loads(str(row[4]))
                    except json.JSONDecodeError:
                        vector = {"legacy_unparsed_vector": str(row[4])}
                payload = {
                    "schema_version": "aion.knowledge-triplet.v1",
                    "record_type": "aion_knowledge_triplet",
                    "subject": subject,
                    "predicate": predicate,
                    "object": object_value,
                    "strength": float(row[3] or 0.0),
                    "vec": vector,
                    "timestamp": str(row[5] or ""),
                    "provenance_class": "legacy_unclassified",
                    "legacy_order": position,
                }
                state = self._copy_json(
                    domain_id="business.knowledge",
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "business.knowledge",
                    "entity_id": entity_id,
                    "state": state,
                    "legacy_source_retained": True,
                })

        # Retain customer concept reinforcement and evolution history as
        # immutable learning evidence. Malformed legacy lines are rejected so
        # a migration cannot silently claim complete coverage.
        if (
            self.concept_reinforcement_log_path is not None
            and self.concept_reinforcement_log_path.is_file()
        ):
            for position, raw in enumerate(
                self.concept_reinforcement_log_path.read_text(
                    encoding="utf-8"
                ).splitlines(),
                start=1,
            ):
                if not raw.strip():
                    continue
                try:
                    timestamp, message = raw.strip().split(" ", 1)
                    action, concept_name = message.split(" ", 1)
                    timestamp_value = float(timestamp)
                except (TypeError, ValueError) as exc:
                    raise BusinessVaultCoverageMigrationError(
                        "legacy_concept_reinforcement_invalid"
                    ) from exc
                entity_id = f"concept-reinforcement-legacy-{position:012d}"
                payload = {
                    "event_id": entity_id,
                    "event_type": "concept_reinforcement",
                    "timestamp": timestamp_value,
                    "action": action,
                    "concept_name": concept_name,
                    "vault_order_ns": position,
                }
                state = self._copy_json(
                    domain_id="learning.audit",
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "learning.audit",
                    "entity_id": entity_id,
                    "state": state,
                    "legacy_source_retained": True,
                })

        if (
            self.concept_evolution_log_path is not None
            and self.concept_evolution_log_path.is_file()
        ):
            for position, raw in enumerate(
                self.concept_evolution_log_path.read_text(
                    encoding="utf-8"
                ).splitlines(),
                start=1,
            ):
                if not raw.strip():
                    continue
                payload = json.loads(raw)
                entity_id = str(
                    payload.get("event_id")
                    or f"concept-evolution-legacy-{position:012d}"
                )
                payload.setdefault("event_id", entity_id)
                payload.setdefault("event_type", "concept_evolution_snapshot")
                payload.setdefault("vault_order_ns", position)
                state = self._copy_json(
                    domain_id="learning.audit",
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "learning.audit",
                    "entity_id": entity_id,
                    "state": state,
                    "legacy_source_retained": True,
                })

        # GlyphNet historically stored complete text/voice payloads, sender and
        # recipient identities in an application-relative SQLite database.
        # Copy those immutable communication events into encrypted business
        # knowledge audit records and retain the database as the migration
        # source until a later governed retirement.
        if (
            self.glyphnet_thread_db_path is not None
            and self.glyphnet_thread_db_path.is_file()
        ):
            connection = sqlite3.connect(
                f"file:{self.glyphnet_thread_db_path}?mode=ro", uri=True
            )
            try:
                columns = {
                    str(row[1])
                    for row in connection.execute(
                        "PRAGMA table_info(events)"
                    ).fetchall()
                }
                user_expression = "user_id" if "user_id" in columns else "NULL"
                rows = connection.execute(
                    "SELECT id, topic, graph, type, ts, direction, sender, "
                    f"recipient, {user_expression}, payload FROM events "
                    "ORDER BY ts, id"
                ).fetchall()
            finally:
                connection.close()
            for position, row in enumerate(rows, start=1):
                legacy_id = int(row[0])
                entity_id = f"glyphnet-thread-legacy-{legacy_id:012d}"
                try:
                    event_payload = json.loads(row[9] or "{}")
                except json.JSONDecodeError:
                    event_payload = {"legacy_unparsed_payload": str(row[9] or "")}
                payload = {
                    "record_type": "glyphnet_thread_event",
                    "topic": str(row[1]),
                    "graph": str(row[2]),
                    "type": str(row[3]),
                    "ts": float(row[4]),
                    "direction": str(row[5]),
                    "sender": row[6],
                    "recipient": row[7],
                    "user_id": str(row[8] or "legacy"),
                    "payload": event_payload,
                    "legacy_row_id": legacy_id,
                    "vault_order_ns": position,
                }
                state = self._copy_json(
                    domain_id="business.knowledge_audit",
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "business.knowledge_audit",
                    "entity_id": entity_id,
                    "state": state,
                    "legacy_source_retained": True,
                })

        operating_root = self.legacy_root / "business_containers" / workspace_id / "pilot" / "operating_team"
        if operating_root.is_dir():
            for path in sorted(operating_root.rglob("*.json")):
                relative = path.relative_to(operating_root).with_suffix("").as_posix()
                payload = json.loads(path.read_text(encoding="utf-8"))
                _discover_department_ids(payload, discovered_departments)
                state = self._copy_json(
                    domain_id="train_agent.automations", workspace_id=workspace_id,
                    entity_id=relative, payload=payload, actor_id=actor_id, execute=execute,
                )
                candidates.append({"domain_id": "train_agent.automations", "entity_id": relative, "state": state})
            audit = operating_root / "audit.jsonl"
            if audit.is_file():
                for position, raw in enumerate(audit.read_text(encoding="utf-8").splitlines(), start=1):
                    if not raw.strip():
                        continue
                    payload = json.loads(raw)
                    entity_id = f"legacy-event-{position:012d}"
                    state = self._copy_json(
                        domain_id="train_agent.runs_and_audit", workspace_id=workspace_id,
                        entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                    )
                    candidates.append({"domain_id": "train_agent.runs_and_audit", "entity_id": entity_id, "state": state})

        scheduled_root = self.legacy_root / "business_containers" / workspace_id / "pilot" / "scheduled_work"
        schedules_path = scheduled_root / "schedules.json"
        if schedules_path.is_file():
            payload = json.loads(schedules_path.read_text(encoding="utf-8"))
            _discover_department_ids(payload, discovered_departments)
            state = self._copy_json(
                domain_id="train_agent.automations", workspace_id=workspace_id,
                entity_id="scheduled_work/schedules", payload=payload,
                actor_id=actor_id, execute=execute,
            )
            candidates.append({
                "domain_id": "train_agent.automations",
                "entity_id": "scheduled_work/schedules", "state": state,
            })
        for category in ("runs", "artifacts"):
            for path in sorted((scheduled_root / category).glob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                _discover_department_ids(payload, discovered_departments)
                entity_id = f"scheduled_work/{category}/{path.stem}"
                state = self._copy_json(
                    domain_id="train_agent.runs_and_audit", workspace_id=workspace_id,
                    entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                )
                candidates.append({
                    "domain_id": "train_agent.runs_and_audit",
                    "entity_id": entity_id, "state": state,
                })

        aion_flow_root = self.legacy_root.parent / "aion_flow"
        aion_flow_policy = aion_flow_root / "policies" / f"{workspace_id}.json"
        if aion_flow_policy.is_file():
            payload = json.loads(aion_flow_policy.read_text(encoding="utf-8"))
            state = self._copy_json(
                domain_id="train_agent.automations", workspace_id=workspace_id,
                entity_id="aion_flow/policy", payload=payload,
                actor_id=actor_id, execute=execute,
            )
            candidates.append({
                "domain_id": "train_agent.automations", "entity_id": "aion_flow/policy",
                "state": state,
            })
        for path in sorted((aion_flow_root / "evaluations").glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            authority = payload.get("authority_context") or {}
            if str(authority.get("workspace_id") or "") != workspace_id:
                continue
            experiment_id = str(payload.get("experiment_id") or path.stem)
            entity_id = f"aion_flow/evaluations/{experiment_id}"
            state = self._copy_json(
                domain_id="train_agent.runs_and_audit", workspace_id=workspace_id,
                entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
            )
            candidates.append({
                "domain_id": "train_agent.runs_and_audit", "entity_id": entity_id,
                "state": state,
            })
        template_installations_path = aion_flow_root / "templates" / "organisation-installations.json"
        if template_installations_path.is_file():
            legacy_installations = json.loads(template_installations_path.read_text(encoding="utf-8"))
            installations = legacy_installations.get("installations") or {}
            if not isinstance(installations, dict):
                raise BusinessVaultCoverageMigrationError("legacy_aion_flow_template_installations_invalid")
            for installation_id, installation in sorted(installations.items()):
                if not isinstance(installation, dict):
                    continue
                if str(installation.get("organisation_id") or "") != workspace_id:
                    continue
                entity_id = f"aion_flow/template_installations/{installation_id}"
                state = self._copy_json(
                    domain_id="train_agent.automations", workspace_id=workspace_id,
                    entity_id=entity_id, payload=installation, actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "train_agent.automations", "entity_id": entity_id,
                    "state": state,
                })
        harness_path = aion_flow_root / "harnesses" / workspace_id / "harnesses.json"
        if harness_path.is_file():
            payload = json.loads(harness_path.read_text(encoding="utf-8"))
            state = self._copy_json(
                domain_id="train_agent.automations", workspace_id=workspace_id,
                entity_id="aion_flow/harnesses", payload=payload, actor_id=actor_id,
                execute=execute,
            )
            candidates.append({
                "domain_id": "train_agent.automations", "entity_id": "aion_flow/harnesses",
                "state": state,
            })
        capability_path = (
            aion_flow_root / "capability_packages" / workspace_id / "capability_packages.json"
        )
        if capability_path.is_file():
            payload = json.loads(capability_path.read_text(encoding="utf-8"))
            state = self._copy_json(
                domain_id="train_agent.automations", workspace_id=workspace_id,
                entity_id="aion_flow/capability_packages", payload=payload,
                actor_id=actor_id, execute=execute,
            )
            candidates.append({
                "domain_id": "train_agent.automations",
                "entity_id": "aion_flow/capability_packages", "state": state,
            })
        for path in sorted((aion_flow_root / "runs").glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            authority = payload.get("authority_context") or {}
            if str(authority.get("workspace_id") or "") != workspace_id:
                continue
            run_id = str(payload.get("run_id") or path.stem)
            entity_id = f"aion_flow/runs/{run_id}"
            state = self._copy_json(
                domain_id="train_agent.runs_and_audit", workspace_id=workspace_id,
                entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
            )
            candidates.append({
                "domain_id": "train_agent.runs_and_audit", "entity_id": entity_id, "state": state,
            })
        for path in sorted((aion_flow_root / "prepared").glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            actor = (payload.get("authorization_context") or {}).get("actor") or {}
            if str(actor.get("workspace_id") or "") != workspace_id:
                continue
            preparation_id = str(payload.get("preparation_id") or path.stem)
            entity_id = f"aion_flow/prepared/{preparation_id}"
            state = self._copy_json(
                domain_id="train_agent.automations", workspace_id=workspace_id,
                entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
            )
            candidates.append({
                "domain_id": "train_agent.automations", "entity_id": entity_id, "state": state,
            })

        revision_path = aion_flow_root / "production" / "workflow-revisions.json"
        if revision_path.is_file():
            legacy_revisions = json.loads(revision_path.read_text(encoding="utf-8"))
            workflows = legacy_revisions.get("workflows") or {}
            if not isinstance(workflows, dict):
                raise BusinessVaultCoverageMigrationError("legacy_aion_flow_revisions_invalid")
            workspace_workflows: dict[str, Any] = {}
            prefix = f"{workspace_id}:"
            for workflow_key, workflow_record in workflows.items():
                if str(workflow_key).startswith(prefix):
                    workspace_workflows[str(workflow_key)] = deepcopy(workflow_record)
                    continue
                history = workflow_record.get("history") if isinstance(workflow_record, dict) else None
                if history and all(
                    isinstance(item, dict) and str(item.get("workspace_id") or "") == workspace_id
                    for item in history
                ):
                    workspace_workflows[str(workflow_key)] = deepcopy(workflow_record)
            if workspace_workflows:
                payload = {
                    "schema_version": "aion.flow.production_revisions.v1",
                    "workflows": workspace_workflows,
                }
                entity_id = "aion_flow/production_revisions"
                state = self._copy_json(
                    domain_id="train_agent.automations", workspace_id=workspace_id,
                    entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                )
                candidates.append({
                    "domain_id": "train_agent.automations", "entity_id": entity_id, "state": state,
                })

        knowledge_root = self.legacy_root / "business_containers" / workspace_id / "business_knowledge"
        knowledge_index = knowledge_root / "index.json"
        if knowledge_index.is_file():
            migrated_knowledge = json.loads(knowledge_index.read_text(encoding="utf-8"))
            for source_record in migrated_knowledge.get("sources") or []:
                if not isinstance(source_record, dict) or source_record.get("vault_object_id"):
                    continue
                raw_local_path = str(source_record.get("raw_local_path") or "").strip()
                if not raw_local_path:
                    continue
                source_path = self._safe_legacy_file(raw_local_path)
                raw = source_path.read_bytes()
                source_id = str(source_record.get("source_id") or source_path.stem)
                object_id = "knowmig-" + sha256(
                    f"{workspace_id}\0{source_id}\0{sha256(raw).hexdigest()}".encode("utf-8")
                ).hexdigest()[:48]
                object_metadata: dict[str, Any] = {}
                if execute:
                    object_metadata = self.object_store.put_bytes(
                        object_id=object_id, data=raw,
                        original_name=str(source_record.get("filename") or source_path.name),
                        content_type=mimetypes.guess_type(source_path.name)[0] or "application/octet-stream",
                        idempotency_key=f"business-knowledge-migration-{object_id}",
                        actor_id=actor_id,
                        recorded_at=str(source_record.get("created_at") or "1970-01-01T00:00:00+00:00"),
                    )
                    _, copied = self.object_store.get_bytes(object_id=object_id)
                    if sha256(copied).digest() != sha256(raw).digest():
                        raise RuntimeError(f"migration_verification_failed:business.knowledge_files:{object_id}")
                source_record.pop("raw_local_path", None)
                source_record["vault_object_id"] = object_id
                source_record["vault_reference"] = f"vault://business.knowledge_files/{workspace_id}/{object_id}"
                if object_metadata:
                    source_record["vault_object_version"] = object_metadata["version"]
                candidates.append({
                    "domain_id": "business.knowledge_files", "entity_id": object_id,
                    "state": "migrated_verified" if execute else "ready",
                })
            state = self._copy_json(
                domain_id="business.knowledge", workspace_id=workspace_id,
                entity_id="index", payload=migrated_knowledge,
                actor_id=actor_id, execute=execute,
            )
            candidates.append({"domain_id": "business.knowledge", "entity_id": "index", "state": state})
        knowledge_receipts = knowledge_root / "governance_receipts.jsonl"
        if knowledge_receipts.is_file():
            for position, raw in enumerate(knowledge_receipts.read_text(encoding="utf-8").splitlines(), start=1):
                if not raw.strip():
                    continue
                payload = json.loads(raw)
                receipt_id = str(payload.get("receipt_id") or f"legacy-receipt-{position:08d}")
                entity_id = f"governance_receipts/{receipt_id}"
                state = self._copy_json(
                    domain_id="business.knowledge_audit", workspace_id=workspace_id,
                    entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                )
                candidates.append({"domain_id": "business.knowledge_audit", "entity_id": entity_id, "state": state})

        security_root = self.legacy_root / "cybersecurity_guard" / workspace_id
        security_state = security_root / "state.json"
        if security_state.is_file():
            payload = json.loads(security_state.read_text(encoding="utf-8"))
            state = self._copy_json(
                domain_id="security.records", workspace_id=workspace_id,
                entity_id="guard/state", payload=payload, actor_id=actor_id, execute=execute,
            )
            candidates.append({"domain_id": "security.records", "entity_id": "guard/state", "state": state})
        vulnerability_feed = security_root / "vulnerability-feed.json"
        if vulnerability_feed.is_file():
            payload = json.loads(vulnerability_feed.read_text(encoding="utf-8"))
            state = self._copy_json(
                domain_id="security.records", workspace_id=workspace_id,
                entity_id="guard/vulnerability-feed", payload=payload,
                actor_id=actor_id, execute=execute,
            )
            candidates.append({
                "domain_id": "security.records", "entity_id": "guard/vulnerability-feed", "state": state,
            })
        security_events = security_root / "events.jsonl"
        if security_events.is_file():
            for position, raw in enumerate(security_events.read_text(encoding="utf-8").splitlines(), start=1):
                if not raw.strip():
                    continue
                payload = json.loads(raw)
                event_id = str(payload.get("event_id") or f"legacy-event-{position:08d}")
                entity_id = f"events/{event_id}"
                state = self._copy_json(
                    domain_id="security.audit", workspace_id=workspace_id,
                    entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                )
                candidates.append({"domain_id": "security.audit", "entity_id": entity_id, "state": state})

        support_root = self.legacy_root / "business_containers" / workspace_id / "support" / "case_management"
        if support_root.is_dir():
            support_objects: dict[Path, str] = {}
            for path in sorted(source for source in support_root.rglob("*") if source.is_file() and source.suffix != ".json"):
                raw = path.read_bytes()
                relative = path.relative_to(support_root).as_posix()
                object_id = "supportmig-" + sha256(
                    f"{workspace_id}\0{relative}\0{sha256(raw).hexdigest()}".encode("utf-8")
                ).hexdigest()[:48]
                support_objects[path.resolve()] = object_id
                if execute:
                    self.object_store.put_bytes(
                        object_id=object_id, data=raw, original_name=path.name,
                        content_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                        idempotency_key=f"support-migration-{object_id}", actor_id=actor_id,
                        recorded_at="1970-01-01T00:00:00+00:00",
                    )
                    _, copied = self.object_store.get_bytes(object_id=object_id)
                    if sha256(copied).digest() != sha256(raw).digest():
                        raise RuntimeError(f"migration_verification_failed:support.files:{object_id}")
                candidates.append({
                    "domain_id": "support.files", "entity_id": object_id,
                    "state": "migrated_verified" if execute else "ready",
                })

            def rewrite_support_paths(value: Any) -> Any:
                if isinstance(value, dict):
                    rewritten = {key: rewrite_support_paths(item) for key, item in value.items() if key != "protected_path"}
                    protected = value.get("protected_path")
                    if protected:
                        try:
                            source = self._safe_legacy_file(str(protected)).resolve()
                        except BusinessVaultCoverageMigrationError:
                            source = None
                        if source in support_objects:
                            rewritten["vault_object_id"] = support_objects[source]
                    return rewritten
                if isinstance(value, list):
                    return [rewrite_support_paths(item) for item in value]
                return value

            config_entities = {
                "polling": "configuration/polling",
                "whatsapp": "configuration/whatsapp",
                "agent_setup": "configuration/agent_setup",
            }
            for path in sorted(support_root.rglob("*.json")):
                payload = rewrite_support_paths(json.loads(path.read_text(encoding="utf-8")))
                relative = path.relative_to(support_root).with_suffix("").as_posix()
                entity_id = config_entities.get(relative, relative)
                state = self._copy_json(
                    domain_id="support.records", workspace_id=workspace_id,
                    entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                )
                candidates.append({"domain_id": "support.records", "entity_id": entity_id, "state": state})

        support_voice_root = self.legacy_root / "business_containers" / workspace_id / "support" / "voice"
        if support_voice_root.is_dir():
            for path in sorted(support_voice_root.rglob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                entity_id = "voice/" + path.relative_to(support_voice_root).with_suffix("").as_posix()
                state = self._copy_json(
                    domain_id="support.records", workspace_id=workspace_id,
                    entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                )
                candidates.append({"domain_id": "support.records", "entity_id": entity_id, "state": state})

        sales_root = self.legacy_root / "business_containers" / workspace_id / "sales" / "revenue_spine"
        if sales_root.is_dir():
            sales_objects: dict[tuple[str, str], str] = {}
            for path in sorted(source for source in sales_root.rglob("*") if source.is_file() and source.suffix not in {".json", ".jsonl"}):
                raw = path.read_bytes()
                relative = path.relative_to(sales_root).as_posix()
                object_id = "salesmig-" + sha256(
                    f"{workspace_id}\0{relative}\0{sha256(raw).hexdigest()}".encode("utf-8")
                ).hexdigest()[:48]
                sales_objects[(path.parent.relative_to(sales_root).as_posix(), path.stem)] = object_id
                if execute:
                    self.object_store.put_bytes(
                        object_id=object_id, data=raw, original_name=path.name,
                        content_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                        idempotency_key=f"sales-migration-{object_id}", actor_id=actor_id,
                        recorded_at="1970-01-01T00:00:00+00:00",
                    )
                    _, copied = self.object_store.get_bytes(object_id=object_id)
                    if sha256(copied).digest() != sha256(raw).digest():
                        raise RuntimeError(f"migration_verification_failed:sales.files:{object_id}")
                candidates.append({
                    "domain_id": "sales.files", "entity_id": object_id,
                    "state": "migrated_verified" if execute else "ready",
                })
            for path in sorted(sales_root.rglob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                relative_path = path.relative_to(sales_root)
                entity_id = relative_path.with_suffix("").as_posix()
                object_id = sales_objects.get((relative_path.parent.as_posix(), relative_path.stem))
                if object_id:
                    payload["vault_object_id"] = object_id
                state = self._copy_json(
                    domain_id="sales.records", workspace_id=workspace_id,
                    entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                )
                candidates.append({"domain_id": "sales.records", "entity_id": entity_id, "state": state})
            sales_audit = sales_root / "audit.jsonl"
            if sales_audit.is_file():
                for position, raw in enumerate(sales_audit.read_text(encoding="utf-8").splitlines(), start=1):
                    if not raw.strip():
                        continue
                    payload = json.loads(raw)
                    entity_id = f"legacy-event-{position:012d}"
                    state = self._copy_json(
                        domain_id="sales.audit", workspace_id=workspace_id,
                        entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                    )
                    candidates.append({"domain_id": "sales.audit", "entity_id": entity_id, "state": state})

        sales_completion_root = self.legacy_root / "business_containers" / workspace_id / "sales" / "completion"
        if sales_completion_root.is_dir():
            for path in sorted(sales_completion_root.rglob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                entity_id = path.relative_to(sales_completion_root).with_suffix("").as_posix()
                state = self._copy_json(
                    domain_id="sales.completion_records", workspace_id=workspace_id,
                    entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                )
                candidates.append({
                    "domain_id": "sales.completion_records",
                    "entity_id": entity_id,
                    "state": state,
                })

        finance_sales_root = self.legacy_root / "business_containers" / workspace_id / "finance" / "sales"
        if finance_sales_root.is_dir():
            for path in sorted(finance_sales_root.rglob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                entity_id = path.relative_to(finance_sales_root).with_suffix("").as_posix()
                state = self._copy_json(
                    domain_id="finance.sales_records", workspace_id=workspace_id,
                    entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                )
                candidates.append({"domain_id": "finance.sales_records", "entity_id": entity_id, "state": state})

        bookkeeping_root = self.legacy_root / "business_containers" / workspace_id / "finance" / "bookkeeping"
        if bookkeeping_root.is_dir():
            for path in sorted((bookkeeping_root / "drafts").glob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                entity_id = f"drafts/{path.stem}"
                state = self._copy_json(
                    domain_id="finance.bookkeeping_records", workspace_id=workspace_id,
                    entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                )
                candidates.append({"domain_id": "finance.bookkeeping_records", "entity_id": entity_id, "state": state})
            journal = bookkeeping_root / "internal_journal.jsonl"
            if journal.is_file():
                for position, raw in enumerate(journal.read_text(encoding="utf-8").splitlines(), start=1):
                    if not raw.strip():
                        continue
                    payload = json.loads(raw)
                    entity_id = str(payload.get("entry_id") or f"legacy-entry-{position:012d}")
                    state = self._copy_json(
                        domain_id="finance.bookkeeping_journal", workspace_id=workspace_id,
                        entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                    )
                    candidates.append({"domain_id": "finance.bookkeeping_journal", "entity_id": entity_id, "state": state})

        recurring_root = self.legacy_root / "business_containers" / workspace_id / "finance" / "recurring"
        if recurring_root.is_dir():
            for path in sorted(recurring_root.rglob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                entity_id = path.relative_to(recurring_root).with_suffix("").as_posix()
                state = self._copy_json(
                    domain_id="finance.recurring_records", workspace_id=workspace_id,
                    entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                )
                candidates.append({"domain_id": "finance.recurring_records", "entity_id": entity_id, "state": state})

        reconciliation_root = self.legacy_root / "business_containers" / workspace_id / "finance" / "transaction_reconciliations"
        if reconciliation_root.is_dir():
            for path in sorted(reconciliation_root.glob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                entity_id = path.stem
                state = self._copy_json(
                    domain_id="finance.reconciliation_records", workspace_id=workspace_id,
                    entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                )
                candidates.append({"domain_id": "finance.reconciliation_records", "entity_id": entity_id, "state": state})

        xero_handoff_root = (
            self.legacy_root / "business_containers" / workspace_id
            / "finance" / "xero_reconciliation_handoffs"
        )
        if xero_handoff_root.is_dir():
            for path in sorted(xero_handoff_root.glob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                if path.name.endswith(".blocked-receipt.json"):
                    handoff_id = str(payload.get("handoff_id") or path.name.removesuffix(".blocked-receipt.json"))
                    entity_id = f"xero_handoffs/{handoff_id}/blocked_receipt"
                else:
                    handoff_id = str(payload.get("handoff_id") or path.stem)
                    entity_id = f"xero_handoffs/{handoff_id}"
                state = self._copy_json(
                    domain_id="finance.reconciliation_records", workspace_id=workspace_id,
                    entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                )
                candidates.append({
                    "domain_id": "finance.reconciliation_records",
                    "entity_id": entity_id, "state": state,
                })

        xero_export_roots = (
            (
                "xero_bookkeeping_exports",
                "xero/bookkeeping_exports",
            ),
            (
                "xero_sales_invoice_exports",
                "xero/sales_invoice_exports",
            ),
        )
        for directory_name, entity_prefix in xero_export_roots:
            export_root = (
                self.legacy_root / "business_containers" / workspace_id
                / "finance" / directory_name
            )
            if not export_root.is_dir():
                continue
            for path in sorted(export_root.glob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                export_id = str(payload.get("export_id") or path.stem)
                entity_id = f"{entity_prefix}/{export_id}"
                state = self._copy_json(
                    domain_id="finance.integration_records",
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "finance.integration_records",
                    "entity_id": entity_id,
                    "state": state,
                })

        ledger_root = self.legacy_root / "business_containers" / workspace_id / "finance" / "ledger"
        if ledger_root.is_dir():
            for path in sorted(ledger_root.rglob("ledger.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                ledger_id = path.parent.name
                entity_id = f"ledgers/{ledger_id}/ledger"
                state = self._copy_json(
                    domain_id="finance.ledger_records", workspace_id=workspace_id,
                    entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                )
                candidates.append({"domain_id": "finance.ledger_records", "entity_id": entity_id, "state": state})
            for path in sorted(ledger_root.rglob("*.jsonl")):
                records = [json.loads(raw) for raw in path.read_text(encoding="utf-8").splitlines() if raw.strip()]
                ledger_id = path.parent.name
                entity_id = f"ledgers/{ledger_id}/collections/{path.stem}"
                payload = {"schema_version": "aion.finance.ledger_collection.v1",
                           "workspace_id": workspace_id, "ledger_id": ledger_id,
                           "collection": path.stem, "records": records}
                state = self._copy_json(
                    domain_id="finance.ledger_records", workspace_id=workspace_id,
                    entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                )
                candidates.append({"domain_id": "finance.ledger_records", "entity_id": entity_id, "state": state})

        integrations_root = self.legacy_root / "business_containers" / workspace_id / "integrations"
        if integrations_root.is_dir():
            for path in sorted(integrations_root.rglob("*.json")):
                relative = path.relative_to(integrations_root).with_suffix("")
                if relative.parts and relative.parts[0] == "marketing":
                    continue
                if relative.as_posix() == "sales_telephony":
                    continue
                payload = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    payload = {"value": payload}
                entity_id = relative.as_posix()
                state = self._copy_json(
                    domain_id="finance.integration_records", workspace_id=workspace_id,
                    entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                )
                candidates.append({
                    "domain_id": "finance.integration_records",
                    "entity_id": entity_id,
                    "state": state,
                })

        marketing_root = integrations_root / "marketing"
        if marketing_root.is_dir():
            for path in sorted(marketing_root.glob("*/*.json")):
                provider = path.parent.name
                kind = path.stem
                if kind not in {"connection", "metrics", "pending"}:
                    raise BusinessVaultCoverageMigrationError(
                        f"legacy_marketing_record_kind_unknown:{kind}"
                    )
                payload = json.loads(path.read_text(encoding="utf-8"))
                entity_id = f"marketing/connections/{provider}/{kind}"
                state = self._copy_json(
                    domain_id="departments.operational_records",
                    workspace_id=workspace_id,
                    entity_id=entity_id,
                    payload=payload,
                    actor_id=actor_id,
                    execute=execute,
                )
                candidates.append({
                    "domain_id": "departments.operational_records",
                    "entity_id": entity_id,
                    "state": state,
                })

        finance_root = self.legacy_root / "business_containers" / workspace_id / "finance"
        for category in ("bank_activity", "counterparty_intelligence", "director_models", "month_end", "scenarios", "reports"):
            category_root = finance_root / category
            if not category_root.is_dir():
                continue
            for path in sorted(category_root.rglob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    payload = {"value": payload}
                entity_id = f"{category}/{path.relative_to(category_root).with_suffix('').as_posix()}"
                state = self._copy_json(
                    domain_id="finance.operations_records", workspace_id=workspace_id,
                    entity_id=entity_id, payload=payload, actor_id=actor_id, execute=execute,
                )
                candidates.append({
                    "domain_id": "finance.operations_records",
                    "entity_id": entity_id,
                    "state": state,
                })

        cabinet_path = self.legacy_root / "workflow_file_cabinets" / workspace_id / "tree.json"
        if cabinet_path.is_file():
            tree = json.loads(cabinet_path.read_text(encoding="utf-8"))
            migrated_tree = deepcopy(tree)
            nodes = migrated_tree.get("folders") or (migrated_tree.get("root") or {}).get("children") or []
            stack = list(nodes)
            while stack:
                node = stack.pop()
                if not isinstance(node, dict):
                    continue
                stack.extend(node.get("children") or [])
                target = node.get("target") if isinstance(node.get("target"), dict) else {}
                storage_path = str(target.get("storage_path") or "").strip()
                if not storage_path:
                    continue
                source = self._safe_legacy_file(storage_path)
                raw = source.read_bytes()
                object_id = "cabmig-" + sha256(
                    f"{workspace_id}\0{source.relative_to(self.legacy_root).as_posix()}".encode("utf-8")
                ).hexdigest()[:48]
                if execute:
                    self.object_store.put_bytes(
                        object_id=object_id,
                        data=raw,
                        original_name=source.name,
                        content_type=mimetypes.guess_type(source.name)[0] or "application/octet-stream",
                        idempotency_key=f"cabinet-migration-{object_id}",
                        actor_id=actor_id,
                        recorded_at=str((tree.get("metadata") or {}).get("updated_at") or "1970-01-01T00:00:00+00:00"),
                    )
                    _, copied = self.object_store.get_bytes(object_id=object_id)
                    if sha256(copied).digest() != sha256(raw).digest():
                        raise RuntimeError(f"migration_verification_failed:file_cabinet.originals:{object_id}")
                target.pop("storage_path", None)
                target["vault_object_id"] = object_id
                node["target"] = target
                candidates.append({
                    "domain_id": "file_cabinet.originals",
                    "entity_id": object_id,
                    "state": "migrated_verified" if execute else "ready",
                })
            state = self._copy_json(
                domain_id="file_cabinet.tree", workspace_id=workspace_id,
                entity_id="tree", payload=migrated_tree, actor_id=actor_id, execute=execute,
            )
            candidates.append({"domain_id": "file_cabinet.tree", "entity_id": "tree", "state": state})

        verified_states = {"already_verified", "migrated_verified"}
        verified_count = sum(row.get("state") in verified_states for row in candidates)
        # Guardian business containers are the canonical storage adapters for
        # the whole-business map and the aggregate current/future department map.
        continuity_aliases = {
            "business.map": "business_container.business_map",
            "departments.map": "business_container.department_intelligence",
            "departments.intelligence": "business_container.department_intelligence",
        }
        protected_surface_coverage: dict[str, Any] = {}
        for surface_id, domain_ids in PROTECTED_CONTINUITY_SURFACE_DOMAINS.items():
            rows: list[dict[str, Any]] = []
            for domain_id in sorted(domain_ids):
                migration_domain_id = continuity_aliases.get(domain_id, domain_id)
                matches = [
                    row for row in candidates
                    if str(row.get("domain_id") or "") == migration_domain_id
                ]
                rows.append(
                    {
                        "domain_id": domain_id,
                        "migration_domain_id": migration_domain_id,
                        "candidate_count": len(matches),
                        "verified_count": sum(
                            row.get("state") in verified_states for row in matches
                        ),
                        "source_state": (
                            "verified"
                            if matches and all(
                                row.get("state") in verified_states for row in matches
                            )
                            else "pending"
                            if matches
                            else "no_legacy_source_detected"
                        ),
                    }
                )
            protected_surface_coverage[surface_id] = rows
        department_contracts = {
            department_id: department_vault_namespaces(department_id)
            for department_id in sorted(discovered_departments)
        }
        report = {
            "schema_version": "tessaris.business-vault-coverage-migration.v1",
            "workspace_id": workspace_id,
            "mode": "execute" if execute else "dry_run",
            "candidate_count": len(candidates),
            "verified_count": verified_count,
            "legacy_sources_deleted": 0,
            "legacy_sources_retained": True,
            "authority_switch_allowed": bool(candidates) and verified_count == len(candidates),
            "protected_surface_scan_complete": True,
            "protected_surface_coverage": protected_surface_coverage,
            "discovered_department_ids": sorted(discovered_departments),
            "department_vault_contracts": department_contracts,
            "candidates": candidates,
        }
        if execute:
            report_hash = _canonical_hash(report)
            self.domain_store.put(
                "vault.migration_receipts",
                workspace_id=workspace_id,
                entity_id=f"coverage-{report_hash[:32]}",
                payload=report,
                expected_version=None,
                idempotency_key=f"coverage-receipt-{report_hash[:32]}",
                actor_id=actor_id,
            )
        return report
