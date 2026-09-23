from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import re
from threading import RLock
import time
from typing import Any, Callable, Iterable
from uuid import uuid4

from backend.modules.aion_business.contracts.department_pilot import canonical_contract_hash
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.business_container_repository import (
    BusinessContainerRepository,
)
from backend.modules.aion_business.runtime.workflow_file_cabinet_repository import (
    WorkflowFileCabinetRepository,
)
from backend.services.aion_mission_mode.coo_mission import CooMissionService
from backend.services.aion_mission_mode.pilot_capability_adapter import (
    evaluate_department_queue_item_gateway_access,
)


DEPARTMENTS = (
    "coo",
    "finance",
    "people",
    "sales",
    "marketing",
    "support",
    "products_services",
    "operations",
)
CONTROL_STATES = {"pilot", "human", "paused"}
MISSION_STATES = {"queued", "running", "paused", "stopped", "completed", "failed"}
MEMORY_SCOPES = {"authoritative_fact", "approved_preference", "procedure", "mission_context"}
ROUTINE_OUTPUT_TYPES = {
    "capability_default", "summary", "task_list", "report", "spreadsheet_xlsx",
    "csv", "pdf", "email_draft", "notification", "update_records", "action_only",
}
ROUTINE_OUTPUT_DESTINATIONS = {"file_cabinet", "department_workspace", "downloads"}
HIGH_CONSEQUENCE_ACTIONS = {
    "send",
    "publish",
    "purchase",
    "payment",
    "delete",
    "overwrite",
    "permission_change",
    "production_change",
    "legal_acceptance",
}
SECRET_FIELDS = {"password", "passcode", "otp", "token", "secret", "api_key", "authorization"}
_LOCK = RLock()


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _safe(value: Any, fallback: str = "item") -> str:
    result = re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or "")).strip("-._")
    return result or fallback


def _identity(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:16]}"


def _redact(value: Any, key: str = "") -> Any:
    if key.lower() in SECRET_FIELDS:
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): _redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


class PilotOperatingTeamService:
    """Durable native runtime for Pilot's operating team.

    The selected Vault model may propose work, but this service owns durable
    state, identity, policy, approval boundaries, memory and audit evidence.
    It deliberately contains no model-provider name or OpenBot dependency.
    """

    def __init__(
        self,
        *,
        base_dir: str | Path | None = None,
        container_repository: BusinessContainerRepository | None = None,
        coo_mission_service: CooMissionService | None = None,
        workflow_cabinet_loader: Callable[[str], dict[str, Any]] | None = None,
    ) -> None:
        self.base_dir = Path(base_dir) if base_dir else AIONBusinessPaths.BUSINESS_CONTAINERS
        self.containers = container_repository or BusinessContainerRepository(
            base_dir=Path(base_dir) if base_dir else None
        )
        self.coo_missions = coo_mission_service or CooMissionService()
        self.workflow_cabinet_loader = workflow_cabinet_loader or WorkflowFileCabinetRepository.load

    def _root(self, workspace_id: str) -> Path:
        root = self.base_dir / _safe(workspace_id, "default") / "pilot" / "operating_team"
        for folder in (
            "capsules", "skills", "routines", "missions", "completion_packs",
            "memory", "templates", "worker_nodes", "routine_runs", "skill_runs",
            "department_workspaces",
        ):
            (root / folder).mkdir(parents=True, exist_ok=True)
        return root

    def _path(self, workspace_id: str, kind: str, item_id: str) -> Path:
        return self._root(workspace_id) / kind / f"{_safe(item_id)}.json"

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(path.name)
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
        with _LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(path.suffix + ".tmp")
            temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            temporary.replace(path)
        return payload

    def _list(self, workspace_id: str, kind: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for path in sorted((self._root(workspace_id) / kind).glob("*.json")):
            try:
                items.append(self._read(path))
            except (json.JSONDecodeError, OSError):
                continue
        return items

    def _seal(self, payload: dict[str, Any], hash_field: str) -> dict[str, Any]:
        sealed = dict(payload)
        sealed.pop(hash_field, None)
        sealed[hash_field] = canonical_contract_hash(sealed)
        return sealed

    def _audit(self, workspace_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        root = self._root(workspace_id)
        head_path = root / "audit_head.json"
        with _LOCK:
            head = self._read(head_path) if head_path.exists() else {"sequence": 0, "event_hash": "GENESIS"}
            event = {
                "schema_version": "aion.pilot.audit_event.v2",
                "workspace_id": workspace_id,
                "sequence": int(head.get("sequence") or 0) + 1,
                "event_id": _identity("pilot_event"),
                "event_type": event_type,
                "occurred_at": _now(),
                "previous_hash": head.get("event_hash") or "GENESIS",
                "payload": _redact(payload),
            }
            event["event_hash"] = canonical_contract_hash(event)
            with (root / "audit.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, sort_keys=True) + "\n")
                handle.flush()
            self._write(head_path, {"sequence": event["sequence"], "event_hash": event["event_hash"]})
        return event

    def verify_audit(self, workspace_id: str) -> dict[str, Any]:
        path = self._root(workspace_id) / "audit.jsonl"
        previous = "GENESIS"
        count = 0
        if path.exists():
            for raw in path.read_text(encoding="utf-8").splitlines():
                event = json.loads(raw)
                supplied = event.pop("event_hash", None)
                if event.get("previous_hash") != previous or canonical_contract_hash(event) != supplied:
                    return {"ok": False, "count": count, "reason": "audit_chain_mismatch"}
                previous = str(supplied)
                count += 1
        return {"ok": True, "count": count, "head_hash": previous}

    def bootstrap_workspace(
        self,
        workspace_id: str,
        *,
        departments: Iterable[str] = DEPARTMENTS,
        actor_id: str = "founder",
    ) -> dict[str, Any]:
        capsules = []
        for department in departments:
            department_id = _safe(department).lower()
            if department_id not in DEPARTMENTS:
                raise ValueError(f"unsupported_department:{department_id}")
            path = self._path(workspace_id, "capsules", department_id)
            department_workspace = self._root(workspace_id) / "department_workspaces" / department_id
            for folder in ("files", "artifacts", "downloads"):
                (department_workspace / folder).mkdir(parents=True, exist_ok=True)
            if path.exists():
                capsules.append(self._read(path))
                continue
            capsule = {
                "schema_version": "aion.pilot.computer_capsule.v2",
                "capsule_id": f"capsule_{department_id}",
                "workspace_id": workspace_id,
                "department_id": department_id,
                "browser_profile_id": f"pilot-{_safe(workspace_id)}-{department_id}",
                "workspace_path": str(department_workspace.relative_to(self.base_dir / _safe(workspace_id, "default"))),
                "control_state": "pilot",
                "controller_id": f"department_pilot:{department_id}",
                "previous_controller_id": None,
                "network_policy": "deny_unregistered_destinations",
                "connector_policy": "department_grants_only",
                "filesystem_policy": "capsule_and_mission_scoped",
                "secrets_visible_to_model": False,
                "live_view_enabled": True,
                "external_writes_require_exact_approval": True,
                "created_at": _now(),
                "created_by": actor_id,
            }
            capsule = self._seal(capsule, "capsule_hash")
            self._write(path, capsule)
            capsules.append(capsule)
        self._audit(workspace_id, "workspace_bootstrapped", {
            "actor_id": actor_id,
            "capsule_ids": [item["capsule_id"] for item in capsules],
        })
        return {"workspace_id": workspace_id, "capsules": capsules, "model_selection": "vault_selected"}

    def workspace(self, workspace_id: str) -> dict[str, Any]:
        skills = self._list(workspace_id, "skills")
        return {
            "schema_version": "aion.pilot.operating_team_workspace.v2",
            "workspace_id": workspace_id,
            "model_selection": "vault_selected",
            "capsules": self._list(workspace_id, "capsules"),
            "skills": [item for item in skills if item.get("status") != "archived"],
            "archived_skill_count": sum(item.get("status") == "archived" for item in skills),
            "skill_runs": self._list(workspace_id, "skill_runs"),
            "routines": self._list(workspace_id, "routines"),
            "routine_runs": self._list(workspace_id, "routine_runs"),
            "missions": self._list(workspace_id, "missions"),
            "completion_packs": self._list(workspace_id, "completion_packs"),
            "memory": self._list(workspace_id, "memory"),
            "templates": self._list(workspace_id, "templates"),
            "worker_nodes": self._list(workspace_id, "worker_nodes"),
            "audit": self.verify_audit(workspace_id),
        }

    def transfer_control(
        self,
        workspace_id: str,
        department_id: str,
        *,
        control_state: str,
        controller_id: str,
        reason: str,
    ) -> dict[str, Any]:
        if control_state not in CONTROL_STATES:
            raise ValueError("invalid_capsule_control_state")
        path = self._path(workspace_id, "capsules", department_id)
        capsule = self._read(path)
        previous = capsule.get("controller_id")
        capsule.update({
            "previous_controller_id": previous,
            "control_state": control_state,
            "controller_id": controller_id,
            "control_reason": str(reason)[:500],
            "control_changed_at": _now(),
        })
        capsule = self._seal(capsule, "capsule_hash")
        self._write(path, capsule)
        self._audit(workspace_id, "capsule_control_transferred", {
            "department_id": department_id, "from": previous, "to": controller_id,
            "control_state": control_state, "reason": reason,
        })
        return capsule

    @staticmethod
    def _semantic_step(raw: dict[str, Any], position: int) -> dict[str, Any]:
        event = str(raw.get("type") or raw.get("action") or "observe").lower()
        destructive = event in {
            "submit", "send", "delete", "purchase", "publish", "upload",
            "approval_checkpoint",
        }
        target = {
            "role": raw.get("role"),
            "label": raw.get("label") or raw.get("text"),
            "selector": raw.get("selector"),
            "url_pattern": raw.get("url_pattern") or raw.get("url"),
        }
        return _redact({
            "step_id": f"step_{position:03d}",
            "position": position,
            "operation": event,
            "target": {key: value for key, value in target.items() if value not in (None, "")},
            "value_source": raw.get("value_source") or ("runtime_input" if event in {"type", "fill"} else None),
            "wait_for": raw.get("wait_for") or "target_ready",
            "validation": raw.get("validation") or {"kind": "target_state_changed"},
            "approval_required": bool(
                raw.get("approval_required")
                or raw.get("requires_approval")
                or str(raw.get("safety") or "").lower() == "approval_required"
                or destructive
            ),
            "captured_at": raw.get("captured_at") or _now(),
        })

    def create_demonstrated_skill(
        self,
        workspace_id: str,
        *,
        name: str,
        department_id: str,
        outcome: str,
        observed_steps: list[dict[str, Any]],
        created_by: str,
        source_systems: list[str] | None = None,
        failure_policy: str = "stop_and_report",
    ) -> dict[str, Any]:
        if department_id not in DEPARTMENTS:
            raise ValueError("unsupported_skill_department")
        if not observed_steps:
            raise ValueError("demonstration_requires_steps")
        skill_id = _identity("pilot_skill")
        steps = [self._semantic_step(item, index) for index, item in enumerate(observed_steps, 1)]
        skill = {
            "schema_version": "aion.pilot.demonstrated_skill.v2",
            "skill_id": skill_id,
            "workspace_id": workspace_id,
            "department_id": department_id,
            "name": str(name).strip()[:160],
            "outcome": str(outcome).strip()[:2000],
            "status": "draft",
            "source": "teach_by_demonstration",
            "source_systems": list(source_systems or []),
            "steps": steps,
            "required_inputs": sorted({
                str(step["value_source"]) for step in steps if step.get("value_source")
            }),
            "approval_boundaries": [step["step_id"] for step in steps if step["approval_required"]],
            "failure_policy": failure_policy,
            "validation_state": "not_tested",
            "publish_requires_human_review": True,
            "created_by": created_by,
            "created_at": _now(),
        }
        skill = self._seal(skill, "skill_hash")
        self._write(self._path(workspace_id, "skills", skill_id), skill)
        self._audit(workspace_id, "demonstrated_skill_drafted", {
            "skill_id": skill_id, "department_id": department_id,
            "step_count": len(steps), "created_by": created_by,
        })
        return skill

    def validate_skill(
        self,
        workspace_id: str,
        skill_id: str,
        *,
        validated_by: str,
        checks: dict[str, bool],
        publish: bool = False,
    ) -> dict[str, Any]:
        path = self._path(workspace_id, "skills", skill_id)
        skill = self._read(path)
        if skill.get("status") == "archived":
            raise ValueError("archived_skill_cannot_be_validated")
        required = {"safe_inputs", "selectors_resolved", "outputs_verified", "approval_stops_verified"}
        passed = required.issubset(checks) and all(bool(checks[key]) for key in required)
        if publish and not passed:
            raise ValueError("skill_cannot_publish_before_safe_validation")
        skill.update({
            "validation_state": "passed" if passed else "failed",
            "validation_checks": checks,
            "validated_by": validated_by,
            "validated_at": _now(),
            "status": "published" if publish and passed else "draft",
        })
        skill = self._seal(skill, "skill_hash")
        self._write(path, skill)
        self._audit(workspace_id, "demonstrated_skill_validated", {
            "skill_id": skill_id, "passed": passed,
            "published": skill["status"] == "published", "validated_by": validated_by,
        })
        return skill

    def update_demonstrated_skill(
        self,
        workspace_id: str,
        skill_id: str,
        *,
        name: str,
        outcome: str,
        updated_by: str,
    ) -> dict[str, Any]:
        """Edit the human-facing title and description without changing recorded steps."""
        clean_name = str(name).strip()[:160]
        clean_outcome = str(outcome).strip()[:2000]
        if not clean_name:
            raise ValueError("demonstrated_skill_name_required")
        if not clean_outcome:
            raise ValueError("demonstrated_skill_description_required")
        path = self._path(workspace_id, "skills", skill_id)
        skill = self._read(path)
        if skill.get("status") == "archived":
            raise ValueError("archived_skill_cannot_be_edited")
        previous_hash = str(skill.get("skill_hash") or "")
        accepted_hashes = [
            str(value) for value in skill.get("accepted_skill_hashes", []) if value
        ]
        if previous_hash and previous_hash not in accepted_hashes:
            accepted_hashes.append(previous_hash)
        skill.update({
            "name": clean_name,
            "outcome": clean_outcome,
            "metadata_revision": int(skill.get("metadata_revision") or 0) + 1,
            "accepted_skill_hashes": accepted_hashes[-20:],
            "updated_by": updated_by,
            "updated_at": _now(),
        })
        skill = self._seal(skill, "skill_hash")
        self._write(path, skill)
        self._audit(workspace_id, "demonstrated_skill_metadata_updated", {
            "skill_id": skill_id,
            "updated_by": updated_by,
            "metadata_revision": skill["metadata_revision"],
        })
        return skill

    def archive_demonstrated_skill(
        self,
        workspace_id: str,
        skill_id: str,
        *,
        deleted_by: str,
    ) -> dict[str, Any]:
        """Remove a taught process from active use while retaining its audit evidence."""
        path = self._path(workspace_id, "skills", skill_id)
        skill = self._read(path)
        if skill.get("status") == "archived":
            return skill
        skill.update({
            "status": "archived",
            "archived_by": deleted_by,
            "archived_at": _now(),
        })
        skill = self._seal(skill, "skill_hash")
        self._write(path, skill)
        self._audit(workspace_id, "demonstrated_skill_archived", {
            "skill_id": skill_id,
            "department_id": skill.get("department_id"),
            "deleted_by": deleted_by,
        })
        return skill

    def workflow_skill_nodes(self, workspace_id: str) -> dict[str, Any]:
        """Expose published demonstrations as immutable workflow-node contracts."""
        nodes: list[dict[str, Any]] = []
        for skill in self._list(workspace_id, "skills"):
            if skill.get("status") != "published" or skill.get("validation_state") != "passed":
                continue
            approval_boundaries = list(skill.get("approval_boundaries") or [])
            nodes.append({
                "id": f"pilot.skill.{skill['skill_id']}",
                "label": skill.get("name") or "Taught process",
                "kind": "capability",
                "app": "pilot_skill",
                "action_id": "pilot.demonstrated_skill.execute",
                "capability_id": "pilot.demonstrated_skill.execute",
                "description": skill.get("outcome") or "Run a verified taught process.",
                "department_id": skill.get("department_id"),
                "skill_id": skill.get("skill_id"),
                "skill_hash": skill.get("skill_hash"),
                "required_inputs": list(skill.get("required_inputs") or []),
                "output_contract": "verified_skill_result",
                "requires_approval": bool(approval_boundaries),
                "causes_external_effect": bool(approval_boundaries),
                "safety": (
                    "exact_approval_at_recorded_boundaries"
                    if approval_boundaries else "governed_department_computer"
                ),
                "status": "Published",
                "icon": "TP",
            })
        return {
            "schema_version": "aion.pilot.workflow_skill_nodes.v1",
            "workspace_id": workspace_id,
            "nodes": nodes,
            "count": len(nodes),
        }

    def queue_workflow_skill_run(
        self,
        workspace_id: str,
        *,
        skill_id: str,
        skill_hash: str,
        workflow_id: str,
        workflow_node_id: str,
        inputs: dict[str, Any],
        idempotency_key: str,
        requested_by: str,
    ) -> dict[str, Any]:
        """Bind one workflow node to a durable Department Computer job.

        Dispatch is intentionally asynchronous: the workflow must wait until a
        governed browser worker posts verified evidence for this exact run.
        """
        skill = self._read(self._path(workspace_id, "skills", skill_id))
        if skill.get("status") != "published" or skill.get("validation_state") != "passed":
            raise PermissionError("workflow_skill_must_be_published_and_validated")
        accepted_hashes = set(skill.get("accepted_skill_hashes") or [])
        if not skill_hash or (
            skill_hash != skill.get("skill_hash") and skill_hash not in accepted_hashes
        ):
            raise PermissionError("workflow_skill_version_hash_mismatch")

        department_id = str(skill.get("department_id") or "")
        capsule = self._read(self._path(workspace_id, "capsules", department_id))
        if capsule.get("control_state") != "pilot":
            raise PermissionError("department_computer_not_under_pilot_control")

        for existing in self._list(workspace_id, "skill_runs"):
            if existing.get("idempotency_key") != idempotency_key:
                continue
            return {
                "ok": existing.get("state") == "completed",
                "verified": existing.get("state") == "completed" and existing.get("result") == "succeeded",
                "waiting": existing.get("state") in {"queued", "claimed", "running", "waiting_approval"},
                "status": existing.get("state"),
                "workflow_skill_run_id": existing.get("workflow_skill_run_id"),
                "output": existing.get("output") or {},
                "evidence": existing.get("evidence") or [],
                "external_effect_performed": bool(existing.get("external_effect_performed")),
                "idempotency_key": idempotency_key,
            }

        run_id = _identity("workflow_skill_run")
        run = {
            "schema_version": "aion.pilot.workflow_skill_run.v1",
            "workflow_skill_run_id": run_id,
            "workspace_id": workspace_id,
            "workflow_id": str(workflow_id)[:200],
            "workflow_node_id": str(workflow_node_id)[:200],
            "skill_id": skill_id,
            "skill_hash": skill_hash,
            "skill_name": skill.get("name"),
            "department_id": department_id,
            "browser_profile_id": capsule.get("browser_profile_id"),
            "state": "queued",
            "result": None,
            "steps": list(skill.get("steps") or []),
            "required_inputs": list(skill.get("required_inputs") or []),
            "approval_boundaries": list(skill.get("approval_boundaries") or []),
            "inputs": _redact(inputs),
            "idempotency_key": str(idempotency_key)[:500],
            "requested_by": str(requested_by)[:200],
            "created_at": _now(),
            "external_effect_performed": False,
        }
        run = self._seal(run, "workflow_skill_run_hash")
        self._write(self._path(workspace_id, "skill_runs", run_id), run)

        capsule.update({
            "activity_state": "queued",
            "active_workflow_id": str(workflow_id)[:200],
            "active_task_id": run_id,
            "active_capability": "pilot.demonstrated_skill.execute",
            "current_objective": str(skill.get("outcome") or skill.get("name") or "Run taught process")[:2000],
            "last_activity_at": _now(),
        })
        self._write(self._path(workspace_id, "capsules", department_id), self._seal(capsule, "capsule_hash"))
        self._audit(workspace_id, "workflow_skill_run_queued", {
            "workflow_skill_run_id": run_id,
            "workflow_id": workflow_id,
            "workflow_node_id": workflow_node_id,
            "skill_id": skill_id,
            "skill_hash": skill_hash,
            "department_id": department_id,
            "idempotency_key": idempotency_key,
        })
        return {
            "ok": False,
            "verified": False,
            "waiting": True,
            "status": "waiting_for_department_computer",
            "workflow_skill_run_id": run_id,
            "department_id": department_id,
            "external_effect_performed": False,
            "idempotency_key": idempotency_key,
        }

    def complete_workflow_skill_run(
        self,
        workspace_id: str,
        run_id: str,
        *,
        completed_by: str,
        succeeded: bool,
        output: dict[str, Any] | None = None,
        evidence: list[dict[str, Any]] | None = None,
        external_effect_performed: bool = False,
    ) -> dict[str, Any]:
        path = self._path(workspace_id, "skill_runs", run_id)
        run = self._read(path)
        if run.get("state") == "completed":
            return run
        evidence_rows = _redact(list(evidence or []))
        if succeeded and not evidence_rows:
            raise ValueError("successful_workflow_skill_run_requires_evidence")
        if external_effect_performed and run.get("approval_boundaries") and not any(
            bool(item.get("approval_receipt_hash")) for item in evidence_rows if isinstance(item, dict)
        ):
            raise PermissionError("external_effect_requires_approval_receipt_evidence")
        run.update({
            "state": "completed" if succeeded else "failed",
            "result": "succeeded" if succeeded else "failed",
            "output": _redact(dict(output or {})),
            "evidence": evidence_rows,
            "external_effect_performed": bool(external_effect_performed),
            "completed_by": str(completed_by)[:200],
            "completed_at": _now(),
        })
        run = self._seal(run, "workflow_skill_run_hash")
        self._write(path, run)

        department_id = str(run.get("department_id") or "")
        capsule_path = self._path(workspace_id, "capsules", department_id)
        capsule = self._read(capsule_path)
        if capsule.get("active_task_id") == run_id:
            capsule.update({
                "activity_state": "idle",
                "active_task_id": None,
                "active_capability": None,
                "current_objective": None,
                "last_activity_at": _now(),
            })
            self._write(capsule_path, self._seal(capsule, "capsule_hash"))
        self._audit(workspace_id, "workflow_skill_run_completed", {
            "workflow_skill_run_id": run_id,
            "skill_id": run.get("skill_id"),
            "succeeded": succeeded,
            "evidence_count": len(evidence_rows),
            "external_effect_performed": bool(external_effect_performed),
            "completed_by": completed_by,
        })
        return run

    def create_routine(
        self,
        workspace_id: str,
        *,
        title: str,
        department_id: str,
        owner_id: str,
        skill_id: str | None = None,
        workflow_id: str | None = None,
        workflow_name: str | None = None,
        workflow_graph: dict[str, Any] | None = None,
        schedule: dict[str, Any] | None = None,
        event_trigger: dict[str, Any] | None = None,
        input_source: str,
        expected_result: str,
        access_contract: dict[str, Any] | None = None,
        output_contract: dict[str, Any] | None = None,
        approval_policy: str = "exact_payload_for_external_write",
        stale_data_policy: str = "stop_and_report",
        no_data_policy: str = "report_no_data",
    ) -> dict[str, Any]:
        if bool(schedule) == bool(event_trigger):
            raise ValueError("routine_requires_exactly_one_trigger")
        if department_id not in DEPARTMENTS:
            raise ValueError("unsupported_routine_department")
        if skill_id:
            skill = self._read(self._path(workspace_id, "skills", skill_id))
            if skill.get("status") != "published":
                raise ValueError("routine_requires_published_skill")
        if skill_id and workflow_id:
            raise ValueError("routine_cannot_target_skill_and_workflow")
        workflow_target = self._saved_workflow_target(
            workspace_id,
            workflow_id,
            fallback_name=workflow_name,
            fallback_graph=workflow_graph,
        ) if workflow_id else None
        safe_access_contract = dict(access_contract or {})
        if safe_access_contract:
            safe_access_contract.update({
                "mode": "vault_grants_only",
                "department_id": department_id,
                "credentials_policy": "vault_or_user_provided",
            })
            safe_access_contract["required_sources"] = [
                str(item)[:160] for item in safe_access_contract.get("required_sources") or [] if str(item).strip()
            ]
            safe_access_contract["required_inputs"] = [
                str(item)[:160] for item in safe_access_contract.get("required_inputs") or [] if str(item).strip()
            ]
        safe_output_contract = dict(output_contract or {})
        if safe_output_contract:
            output_type = str(safe_output_contract.get("type") or "capability_default")
            if output_type not in ROUTINE_OUTPUT_TYPES:
                raise ValueError("unsupported_routine_output_type")
            destination = safe_output_contract.get("destination")
            if destination and str(destination) not in ROUTINE_OUTPUT_DESTINATIONS:
                raise ValueError("unsupported_routine_output_destination")
            safe_output_contract.update({
                "type": output_type,
                "instructions": str(safe_output_contract.get("instructions") or "")[:2000],
                "destination": str(destination) if destination else None,
                "completion_receipt": True,
            })
        routine_id = _identity("pilot_routine")
        routine = {
            "schema_version": "aion.pilot.routine.v2",
            "routine_id": routine_id,
            "workspace_id": workspace_id,
            "department_id": department_id,
            "title": str(title)[:160],
            "owner_id": owner_id,
            "skill_id": skill_id,
            "workflow_target": workflow_target,
            "trigger": {"kind": "schedule", **(schedule or {})} if schedule else {"kind": "event", **(event_trigger or {})},
            "input_source": input_source,
            "expected_result": expected_result,
            "access_contract": safe_access_contract,
            "output_contract": safe_output_contract,
            "approval_policy": approval_policy,
            "stale_data_policy": stale_data_policy,
            "no_data_policy": no_data_policy,
            "idempotency_scope": "trigger_instance",
            "enabled": False,
            "test_state": "not_tested",
            "run_count": 0,
            "failure_count": 0,
            "created_at": _now(),
        }
        routine = self._seal(routine, "routine_hash")
        self._write(self._path(workspace_id, "routines", routine_id), routine)
        self._audit(workspace_id, "routine_drafted", {"routine_id": routine_id, "owner_id": owner_id})
        return routine

    def _saved_workflow_target(
        self,
        workspace_id: str,
        workflow_id: str,
        *,
        fallback_name: str | None = None,
        fallback_graph: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Resolve a workflow from the workspace cabinet and pin its exact graph."""
        needle = str(workflow_id or "").strip()
        if not needle:
            raise ValueError("workflow_routine_requires_saved_workflow")
        tree = self.workflow_cabinet_loader(workspace_id)
        roots = tree.get("folders") or (tree.get("root") or {}).get("children") or []

        def walk(items: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
            for item in items or []:
                if not isinstance(item, dict):
                    continue
                item_id = str(item.get("workflow_id") or item.get("id") or "")
                if item.get("type") == "workflow" and item_id == needle:
                    return item
                found = walk(item.get("children") or [])
                if found:
                    return found
            return None

        item = walk(roots)
        if not item and isinstance(fallback_graph, dict):
            fallback_id = str(fallback_graph.get("workflow_id") or fallback_graph.get("id") or needle)
            if fallback_id != needle:
                raise ValueError("workflow_snapshot_id_mismatch")
            item = {"name": fallback_name or fallback_graph.get("name") or needle, "graph": fallback_graph}
        if not item:
            raise ValueError("saved_workflow_not_found")
        graph = item.get("graph") if isinstance(item.get("graph"), dict) else {}
        nodes = list(graph.get("nodes") or [])
        if not nodes:
            raise ValueError("workflow_routine_requires_at_least_one_node")
        return {
            "workflow_id": needle,
            "workflow_name": str(item.get("name") or graph.get("name") or needle)[:200],
            "workflow_hash": canonical_contract_hash(graph),
            "node_count": len(nodes),
            "graph": _redact(graph),
            "target_kind": "single_node_workflow" if len(nodes) == 1 else "complete_workflow",
        }

    def test_routine(
        self,
        workspace_id: str,
        routine_id: str,
        *,
        tested_by: str,
        checks: dict[str, bool],
    ) -> dict[str, Any]:
        path = self._path(workspace_id, "routines", routine_id)
        routine = self._read(path)
        required = {
            "current_inputs_selected",
            "output_format_valid",
            "audit_trail_complete",
            "approval_stop_verified",
            "failure_states_explicit",
        }
        target = routine.get("workflow_target")
        if isinstance(target, dict):
            try:
                current = self._saved_workflow_target(
                    workspace_id,
                    str(target.get("workflow_id") or ""),
                    fallback_name=str(target.get("workflow_name") or ""),
                    fallback_graph=target.get("graph") if isinstance(target.get("graph"), dict) else None,
                )
                checks["workflow_source_unchanged"] = current.get("workflow_hash") == target.get("workflow_hash")
            except ValueError:
                checks["workflow_source_unchanged"] = False
            required.add("workflow_source_unchanged")
        passed = required.issubset(checks) and all(bool(checks[key]) for key in required)
        routine.update({
            "test_state": "passed" if passed else "failed",
            "test_checks": checks,
            "tested_by": tested_by,
            "tested_at": _now(),
        })
        routine = self._seal(routine, "routine_hash")
        self._write(path, routine)
        self._audit(workspace_id, "routine_tested", {
            "routine_id": routine_id, "passed": passed, "tested_by": tested_by,
        })
        return routine

    def set_routine_enabled(
        self,
        workspace_id: str,
        routine_id: str,
        *,
        enabled: bool,
        changed_by: str,
    ) -> dict[str, Any]:
        path = self._path(workspace_id, "routines", routine_id)
        routine = self._read(path)
        if enabled and routine.get("test_state") != "passed":
            raise ValueError("routine_cannot_enable_before_test_passes")
        routine["enabled"] = bool(enabled)
        routine["enabled_by"] = changed_by if enabled else None
        routine["enabled_at"] = _now() if enabled else None
        trigger = routine.get("trigger") or {}
        if enabled and trigger.get("kind") == "schedule":
            interval = max(1, int(trigger.get("interval_minutes") or 1440))
            routine["next_run_at"] = (datetime.now(UTC) + timedelta(minutes=interval)).replace(microsecond=0).isoformat()
        else:
            routine["next_run_at"] = None
        routine = self._seal(routine, "routine_hash")
        self._write(path, routine)
        self._audit(workspace_id, "routine_enabled_changed", {
            "routine_id": routine_id, "enabled": enabled, "changed_by": changed_by,
        })
        return routine

    @staticmethod
    def _event_matches(trigger: dict[str, Any], event: dict[str, Any]) -> bool:
        expected_type = str(trigger.get("event_type") or "")
        if expected_type and expected_type != str(event.get("event_type") or ""):
            return False
        for key, expected in dict(trigger.get("match") or {}).items():
            if event.get(key) != expected:
                return False
        return True

    def _queue_routine_run(
        self,
        workspace_id: str,
        routine: dict[str, Any],
        *,
        trigger_instance_id: str,
        trigger_payload: dict[str, Any],
    ) -> dict[str, Any]:
        seen = list(routine.get("recent_trigger_instances") or [])
        if trigger_instance_id in seen:
            return {"status": "duplicate_ignored", "routine_id": routine["routine_id"], "trigger_instance_id": trigger_instance_id}
        workflow_target = routine.get("workflow_target")
        if isinstance(workflow_target, dict):
            run = {
                "schema_version": "aion.pilot.workflow_routine_run.v1",
                "run_id": _identity("routine_run"),
                "workspace_id": workspace_id,
                "routine_id": routine["routine_id"],
                "workflow_id": workflow_target.get("workflow_id"),
                "workflow_name": workflow_target.get("workflow_name"),
                "workflow_hash": workflow_target.get("workflow_hash"),
                "workflow_graph": workflow_target.get("graph"),
                "target_kind": workflow_target.get("target_kind"),
                "trigger_instance_id": trigger_instance_id,
                "trigger_payload": _redact(trigger_payload),
                "status": "workflow_queued",
                "execution_policy": "governed_gateway_with_exact_external_write_approval",
                "access_contract": dict(routine.get("access_contract") or {}),
                "output_contract": dict(routine.get("output_contract") or {}),
                "external_side_effects_completed": 0,
                "queued_at": _now(),
            }
            run = self._seal(run, "run_hash")
            self._write(self._path(workspace_id, "routine_runs", run["run_id"]), run)
            path = self._path(workspace_id, "routines", routine["routine_id"])
            current = self._read(path)
            current["run_count"] = int(current.get("run_count") or 0) + 1
            current["last_run_id"] = run["run_id"]
            current["last_run_at"] = run["queued_at"]
            current["recent_trigger_instances"] = (seen + [trigger_instance_id])[-100:]
            self._write(path, self._seal(current, "routine_hash"))
            self._audit(workspace_id, "workflow_routine_run_queued", {
                "run_id": run["run_id"],
                "routine_id": routine["routine_id"],
                "workflow_id": run["workflow_id"],
                "workflow_hash": run["workflow_hash"],
                "trigger_instance_id": trigger_instance_id,
            })
            return run
        access_contract = dict(routine.get("access_contract") or {})
        output_contract = dict(routine.get("output_contract") or {})
        access_mode = str(access_contract.get("mode") or "department_grants_only")
        output_label = str(output_contract.get("label") or routine["expected_result"])
        output_destination = output_contract.get("destination")
        mission = self.create_mission(
            workspace_id,
            outcome=routine["expected_result"],
            requested_by=f"routine:{routine['routine_id']}",
            constraints=[
                f"Input source: {routine['input_source']}",
                f"Access policy: {access_mode}",
                f"Approval policy: {routine['approval_policy']}",
                f"Stale data: {routine['stale_data_policy']}",
                f"No data: {routine['no_data_policy']}",
            ],
            deliverables=[
                output_label + (f" saved to {output_destination}" if output_destination else ""),
                "Evidence-backed completion pack",
            ],
        )
        self.delegate(
            workspace_id,
            mission["mission_id"],
            department_id=routine["department_id"],
            outcome=routine["expected_result"],
            delegated_by=f"routine:{routine['routine_id']}",
        )
        run = {
            "schema_version": "aion.pilot.routine_run.v2",
            "run_id": _identity("routine_run"),
            "workspace_id": workspace_id,
            "routine_id": routine["routine_id"],
            "mission_id": mission["mission_id"],
            "trigger_instance_id": trigger_instance_id,
            "trigger_payload": _redact(trigger_payload),
            "access_contract": access_contract,
            "output_contract": output_contract,
            "status": "mission_queued",
            "external_side_effects_completed": 0,
            "queued_at": _now(),
        }
        run = self._seal(run, "run_hash")
        self._write(self._path(workspace_id, "routine_runs", run["run_id"]), run)
        path = self._path(workspace_id, "routines", routine["routine_id"])
        current = self._read(path)
        current["run_count"] = int(current.get("run_count") or 0) + 1
        current["last_run_id"] = run["run_id"]
        current["last_run_at"] = run["queued_at"]
        current["recent_trigger_instances"] = (seen + [trigger_instance_id])[-100:]
        current = self._seal(current, "routine_hash")
        self._write(path, current)
        self._audit(workspace_id, "routine_run_queued", run)
        return run

    def dispatch_event(
        self,
        workspace_id: str,
        *,
        event: dict[str, Any],
        trigger_instance_id: str,
    ) -> dict[str, Any]:
        queued = []
        ignored = []
        for routine in self._list(workspace_id, "routines"):
            trigger = routine.get("trigger") or {}
            if not routine.get("enabled") or trigger.get("kind") != "event":
                continue
            if not self._event_matches(trigger, event):
                continue
            result = self._queue_routine_run(
                workspace_id,
                routine,
                trigger_instance_id=trigger_instance_id,
                trigger_payload=event,
            )
            (ignored if result.get("status") == "duplicate_ignored" else queued).append(result)
        return {"workspace_id": workspace_id, "queued": queued, "ignored": ignored}

    def run_due_routines(self, workspace_id: str, *, now: datetime | None = None) -> dict[str, Any]:
        instant = (now or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
        queued = []
        for routine in self._list(workspace_id, "routines"):
            trigger = routine.get("trigger") or {}
            if not routine.get("enabled") or trigger.get("kind") != "schedule":
                continue
            due_raw = routine.get("next_run_at")
            if not due_raw:
                continue
            due = datetime.fromisoformat(str(due_raw).replace("Z", "+00:00"))
            due = due if due.tzinfo else due.replace(tzinfo=UTC)
            if due > instant:
                continue
            result = self._queue_routine_run(
                workspace_id,
                routine,
                trigger_instance_id=f"{routine['routine_id']}:{due.isoformat()}",
                trigger_payload={"kind": "schedule", "due_at": due.isoformat()},
            )
            queued.append(result)
            current_path = self._path(workspace_id, "routines", routine["routine_id"])
            current = self._read(current_path)
            interval = max(1, int(trigger.get("interval_minutes") or 1440))
            current["next_run_at"] = (instant + timedelta(minutes=interval)).isoformat()
            current = self._seal(current, "routine_hash")
            self._write(current_path, current)
        return {"workspace_id": workspace_id, "queued": queued, "checked_at": instant.isoformat()}

    def create_mission(
        self,
        workspace_id: str,
        *,
        outcome: str,
        requested_by: str,
        constraints: list[str] | None = None,
        deliverables: list[str] | None = None,
    ) -> dict[str, Any]:
        mission_id = _identity("coo_mission")
        mission = {
            "schema_version": "aion.pilot.coo_mission_room.v2",
            "mission_id": mission_id,
            "workspace_id": workspace_id,
            "outcome": str(outcome).strip()[:4000],
            "requested_by": requested_by,
            "state": "queued",
            "revision": 1,
            "constraints": list(constraints or []),
            "deliverables": list(deliverables or []),
            "assignments": [],
            "timeline": [{"type": "mission_created", "at": _now(), "actor_id": requested_by}],
            "current_owner": "coo",
            "max_handoff_depth": 4,
            "max_parallel_assignments": 8,
            "created_at": _now(),
        }
        mission = self._seal(mission, "mission_hash")
        self._write(self._path(workspace_id, "missions", mission_id), mission)
        self._audit(workspace_id, "coo_mission_created", {"mission_id": mission_id, "requested_by": requested_by})
        return mission

    def _mission_department_fact(self, workspace_id: str, department_id: str) -> dict[str, Any]:
        """Project authoritative business containers into the COO fact boundary."""
        container_map = {
            "finance": ("business_financial_model", "finance_inbox", "department_intelligence"),
            "sales": ("department_intelligence", "business_operating_model"),
            "marketing": ("brand_foundation", "department_intelligence"),
            "support": ("department_intelligence", "operational_runtime_summary"),
            "people": ("organization_authority", "business_structure"),
            "operations": ("business_operating_model", "operational_runtime_summary", "boardroom_snapshot"),
            "products_services": ("business_map", "business_financial_model"),
        }
        data: dict[str, Any] = {}
        source_ids: list[str] = []
        for kind in container_map.get(department_id, ()):
            try:
                payload = self.containers.load_optional_dict(workspace_id, kind)  # type: ignore[arg-type]
            except (OSError, ValueError, TypeError):
                payload = None
            if payload is None:
                continue
            data[kind] = _redact(payload)
            source_ids.append(f"business_container:{workspace_id}:{kind}")
        return {
            "retrieval_state": "retrieved" if source_ids else "not_published",
            "source_ids": source_ids,
            "retrieved_at": _now(),
            "data": data,
        }

    def _write_department_assignment(
        self,
        workspace_id: str,
        mission: dict[str, Any],
        queue_item: dict[str, Any],
        gateway: dict[str, Any],
    ) -> dict[str, Any]:
        department_id = str(queue_item.get("department_id") or "")
        assignment_id = _identity("assignment")
        evaluation = dict(gateway.get("gateway_evaluation") or {})
        queue_state = str(queue_item.get("status") or "queued")
        if queue_state == "waiting_approval":
            state = "waiting_approval"
        elif evaluation.get("allowed") is True:
            state = "queued"
        else:
            state = "blocked"
        assignment = {
            "assignment_id": assignment_id,
            "department_id": department_id,
            "outcome": str(queue_item.get("objective") or queue_item.get("title") or "")[:2000],
            "capability": queue_item.get("capability"),
            "task_id": queue_item.get("task_id"),
            "delegated_by": "coo",
            "depth": 1,
            "depends_on": [],
            "state": state,
            "queue_item": queue_item,
            "gateway": gateway,
            "created_at": _now(),
        }
        task_path = (
            self._root(workspace_id)
            / "department_workspaces"
            / _safe(department_id)
            / "tasks"
            / f"{_safe(str(queue_item.get('task_id') or assignment_id))}.json"
        )
        self._write(task_path, self._seal(assignment, "assignment_hash"))

        capsule_path = self._path(workspace_id, "capsules", department_id)
        if capsule_path.exists():
            capsule = self._read(capsule_path)
            capsule.update({
                "activity_state": state,
                "active_mission_id": mission["mission_id"],
                "active_task_id": queue_item.get("task_id"),
                "active_capability": queue_item.get("capability"),
                "current_objective": assignment["outcome"],
                "last_activity_at": _now(),
            })
            self._write(capsule_path, self._seal(capsule, "capsule_hash"))
        return assignment

    def launch_mission(
        self,
        workspace_id: str,
        *,
        outcome: str,
        requested_by: str,
        constraints: list[str] | None = None,
        deliverables: list[str] | None = None,
    ) -> dict[str, Any]:
        """Plan and dispatch a COO mission through the existing governed runtime."""
        mission = self.create_mission(
            workspace_id,
            outcome=outcome,
            requested_by=requested_by,
            constraints=constraints,
            deliverables=deliverables,
        )
        path = self._path(workspace_id, "missions", mission["mission_id"])
        try:
            workspace_state = self.containers.load_optional_dict(
                workspace_id, "operational_runtime_summary"
            ) or {}
        except (OSError, ValueError, TypeError):
            workspace_state = {}
        receipt = self.coo_missions.run(
            workspace_id=workspace_id,
            question=outcome,
            workspace_state=workspace_state,
            fact_loader=lambda department: self._mission_department_fact(workspace_id, department),
        )
        mission = self._read(path)
        mission["planner_status"] = receipt.get("status")
        mission["planner_reason"] = receipt.get("reason")
        mission["model_selection"] = _redact(receipt.get("model_selection") or {})
        mission["proposal"] = _redact(receipt.get("proposal") or {})
        mission["approval_request"] = _redact(receipt.get("required_approval") or {})
        mission["external_side_effect_executed"] = False
        mission["planned_at"] = _now()

        assignments: list[dict[str, Any]] = []
        queue = dict(receipt.get("delegation_queue") or {})
        for raw_queue_item in queue.get("items") or []:
            if not isinstance(raw_queue_item, dict):
                continue
            queue_item = {
                **raw_queue_item,
                "business_id": workspace_id,
                "mission_id": mission["mission_id"],
                "mission_run_id": str(raw_queue_item.get("mission_run_id") or f"run_{mission['revision']}"),
            }
            gateway = evaluate_department_queue_item_gateway_access(
                queue_item=queue_item,
                evaluation_time=int(time.time()),
                caller="aion_pilot",
            )
            assignments.append(self._write_department_assignment(workspace_id, mission, queue_item, gateway))

        mission["assignments"] = assignments
        if receipt.get("status") == "proposal_ready" and assignments:
            mission["state"] = "running"
            mission["current_owner"] = "coo"
            timeline_type = "mission_planned_and_dispatched"
        elif receipt.get("status") == "proposal_ready":
            mission["state"] = "queued"
            timeline_type = "mission_planned_no_department_tasks"
        else:
            mission["state"] = "queued"
            timeline_type = "mission_planning_blocked"
        mission["revision"] = int(mission.get("revision") or 1) + 1
        mission["timeline"].append({
            "type": timeline_type,
            "at": _now(),
            "planner_status": receipt.get("status"),
            "reason": receipt.get("reason"),
            "assignment_ids": [item["assignment_id"] for item in assignments],
        })
        mission = self._seal(mission, "mission_hash")
        self._write(path, mission)
        self._audit(workspace_id, timeline_type, {
            "mission_id": mission["mission_id"],
            "planner_status": receipt.get("status"),
            "assignment_ids": [item["assignment_id"] for item in assignments],
            "external_side_effect_executed": False,
        })
        return mission

    def delegate(
        self,
        workspace_id: str,
        mission_id: str,
        *,
        department_id: str,
        outcome: str,
        delegated_by: str,
        depth: int = 1,
        depends_on: list[str] | None = None,
    ) -> dict[str, Any]:
        path = self._path(workspace_id, "missions", mission_id)
        mission = self._read(path)
        if department_id not in DEPARTMENTS:
            raise ValueError("unsupported_handoff_department")
        if depth > int(mission["max_handoff_depth"]):
            raise ValueError("mission_handoff_depth_exceeded")
        if len(mission["assignments"]) >= int(mission["max_parallel_assignments"]):
            raise ValueError("mission_assignment_fanout_exceeded")
        assignment = {
            "assignment_id": _identity("assignment"),
            "department_id": department_id,
            "outcome": str(outcome)[:2000],
            "delegated_by": delegated_by,
            "depth": depth,
            "depends_on": list(depends_on or []),
            "state": "queued",
            "created_at": _now(),
        }
        mission["assignments"].append(assignment)
        mission["timeline"].append({"type": "delegated", "at": _now(), **assignment})
        mission["state"] = "running"
        mission["revision"] += 1
        mission = self._seal(mission, "mission_hash")
        self._write(path, mission)
        self._audit(workspace_id, "mission_delegated", {"mission_id": mission_id, **assignment})
        return assignment

    def control_mission(
        self,
        workspace_id: str,
        mission_id: str,
        *,
        command: str,
        actor_id: str,
        instruction: str = "",
    ) -> dict[str, Any]:
        path = self._path(workspace_id, "missions", mission_id)
        mission = self._read(path)
        transitions = {
            "start": "running", "pause": "paused", "resume": "running",
            "stop": "stopped", "complete": "completed", "fail": "failed",
            "redirect": mission.get("state") if mission.get("state") in MISSION_STATES else "running",
        }
        if command not in transitions:
            raise ValueError("unsupported_mission_control_command")
        previous = mission["state"]
        mission["state"] = transitions[command]
        mission["revision"] += 1
        event = {
            "type": f"mission_{command}", "at": _now(), "actor_id": actor_id,
            "instruction": str(instruction)[:4000],
            "previous_state": previous, "new_state": mission["state"],
        }
        mission["timeline"].append(event)
        mission = self._seal(mission, "mission_hash")
        self._write(path, mission)
        self._audit(workspace_id, "mission_controlled", {"mission_id": mission_id, **event})
        return mission

    def completion_pack(
        self,
        workspace_id: str,
        mission_id: str,
        *,
        facts: list[dict[str, Any]],
        assumptions: list[str],
        actions_completed: list[dict[str, Any]],
        approvals_waiting: list[dict[str, Any]],
        unresolved_questions: list[str],
        artifacts: list[dict[str, Any]],
        prepared_by: str,
    ) -> dict[str, Any]:
        mission = self._read(self._path(workspace_id, "missions", mission_id))
        pack_id = _identity("completion_pack")
        pack = {
            "schema_version": "aion.pilot.completion_pack.v2",
            "pack_id": pack_id,
            "workspace_id": workspace_id,
            "mission_id": mission_id,
            "mission_hash": mission["mission_hash"],
            "facts": facts,
            "assumptions": assumptions,
            "actions_completed": actions_completed,
            "approvals_waiting": approvals_waiting,
            "unresolved_questions": unresolved_questions,
            "artifacts": artifacts,
            "prepared_by": prepared_by,
            "prepared_at": _now(),
        }
        pack = self._seal(pack, "pack_hash")
        self._write(self._path(workspace_id, "completion_packs", pack_id), pack)
        self._audit(workspace_id, "completion_pack_created", {
            "mission_id": mission_id, "pack_id": pack_id,
            "actions_completed": len(actions_completed),
            "approvals_waiting": len(approvals_waiting),
        })
        return pack

    def remember(
        self,
        workspace_id: str,
        *,
        department_id: str,
        scope: str,
        key: str,
        value: Any,
        actor_id: str,
        authority_source: str | None = None,
        mission_id: str | None = None,
    ) -> dict[str, Any]:
        if scope not in MEMORY_SCOPES:
            raise ValueError("invalid_pilot_memory_scope")
        if scope == "authoritative_fact" and not authority_source:
            raise PermissionError("authoritative_fact_requires_source_authority")
        if scope == "mission_context" and not mission_id:
            raise ValueError("mission_context_requires_mission_id")
        memory_id = _identity("memory")
        record = {
            "schema_version": "aion.pilot.scoped_memory.v2",
            "memory_id": memory_id,
            "workspace_id": workspace_id,
            "department_id": department_id,
            "scope": scope,
            "key": str(key)[:300],
            "value": _redact(value),
            "actor_id": actor_id,
            "authority_source": authority_source,
            "mission_id": mission_id,
            "model_may_mutate": False,
            "created_at": _now(),
        }
        record = self._seal(record, "memory_hash")
        self._write(self._path(workspace_id, "memory", memory_id), record)
        self._audit(workspace_id, "scoped_memory_recorded", {
            "memory_id": memory_id, "scope": scope,
            "department_id": department_id, "actor_id": actor_id,
        })
        return record

    def register_worker_node(
        self,
        workspace_id: str,
        *,
        node_id: str,
        label: str,
        registered_by: str,
        capabilities: list[str],
        availability: str = "when_online",
    ) -> dict[str, Any]:
        record = {
            "schema_version": "aion.pilot.worker_node.v2",
            "node_id": _safe(node_id, _identity("worker")),
            "workspace_id": workspace_id,
            "label": str(label)[:160],
            "ownership": "user_owned",
            "availability": availability,
            "capabilities": sorted(set(capabilities)),
            "network_policy": "outbound_registered_destinations_only",
            "can_bypass_approvals": False,
            "registered_by": registered_by,
            "registered_at": _now(),
        }
        record = self._seal(record, "worker_node_hash")
        self._write(self._path(workspace_id, "worker_nodes", record["node_id"]), record)
        self._audit(workspace_id, "worker_node_registered", {
            "node_id": record["node_id"], "registered_by": registered_by,
        })
        return record

    def heartbeat_worker_node(
        self,
        workspace_id: str,
        node_id: str,
        *,
        reported_by: str,
        observed_capabilities: list[str] | None = None,
    ) -> dict[str, Any]:
        path = self._path(workspace_id, "worker_nodes", node_id)
        record = self._read(path)
        registered = set(record.get("capabilities") or [])
        observed = set(observed_capabilities or registered)
        if not observed.issubset(registered):
            raise PermissionError("worker_cannot_self_grant_capabilities")
        record.update({
            "status": "online",
            "last_seen_at": _now(),
            "last_seen_by": reported_by,
            "observed_capabilities": sorted(observed),
        })
        record = self._seal(record, "worker_node_hash")
        self._write(path, record)
        self._audit(workspace_id, "worker_node_heartbeat", {
            "node_id": record["node_id"],
            "reported_by": reported_by,
            "observed_capabilities": record["observed_capabilities"],
        })
        return record

    def _template_blueprint(
        self,
        workspace_id: str,
        template_type: str,
        source_id: str,
    ) -> dict[str, Any] | None:
        if template_type == "skill":
            try:
                source = self._read(self._path(workspace_id, "skills", source_id))
            except FileNotFoundError:
                return None
            return {
                "department_id": source.get("department_id"),
                "name": source.get("name"),
                "outcome": source.get("outcome"),
                "source_systems": source.get("source_systems") or [],
                "steps": source.get("steps") or [],
                "required_inputs": source.get("required_inputs") or [],
                "approval_boundaries": source.get("approval_boundaries") or [],
                "failure_policy": source.get("failure_policy") or "stop_and_report",
            }
        if template_type == "routine":
            try:
                source = self._read(self._path(workspace_id, "routines", source_id))
            except FileNotFoundError:
                return None
            return {
                "department_id": source.get("department_id"),
                "title": source.get("title"),
                "trigger": source.get("trigger") or {},
                "input_source": source.get("input_source"),
                "expected_result": source.get("expected_result"),
                "approval_policy": source.get("approval_policy"),
                "stale_data_policy": source.get("stale_data_policy"),
                "no_data_policy": source.get("no_data_policy"),
            }
        if template_type == "pilot":
            try:
                source = self._read(self._path(workspace_id, "capsules", source_id))
            except FileNotFoundError:
                return None
            return {
                "department_id": source.get("department_id"),
                "network_policy": source.get("network_policy"),
                "connector_policy": source.get("connector_policy"),
                "filesystem_policy": source.get("filesystem_policy"),
                "external_writes_require_exact_approval": True,
            }
        raise ValueError("unsupported_pilot_template_type")

    def save_template(
        self,
        workspace_id: str,
        *,
        name: str,
        template_type: str,
        source_id: str,
        created_by: str,
        include_sensitive_configuration: bool = False,
    ) -> dict[str, Any]:
        if include_sensitive_configuration:
            raise PermissionError("pilot_templates_cannot_include_sensitive_configuration")
        blueprint = self._template_blueprint(workspace_id, template_type, source_id)
        template_id = _identity("pilot_template")
        template = {
            "schema_version": "aion.pilot.template.v2",
            "template_id": template_id,
            "workspace_id": workspace_id,
            "name": str(name)[:160],
            "template_type": template_type,
            "source_id": source_id,
            "source_status": "resolved" if blueprint is not None else "unresolved",
            "blueprint": blueprint,
            "copies_credentials": False,
            "copies_conversation_history": False,
            "copies_authoritative_memory": False,
            "created_by": created_by,
            "created_at": _now(),
        }
        template = self._seal(template, "template_hash")
        self._write(self._path(workspace_id, "templates", template_id), template)
        self._audit(workspace_id, "pilot_template_created", {
            "template_id": template_id, "template_type": template_type, "created_by": created_by,
        })
        return template

    def instantiate_template(
        self,
        workspace_id: str,
        template_id: str,
        *,
        created_by: str,
        name: str | None = None,
        department_id: str | None = None,
    ) -> dict[str, Any]:
        template = self._read(self._path(workspace_id, "templates", template_id))
        blueprint = template.get("blueprint")
        if not isinstance(blueprint, dict):
            raise ValueError("template_source_unavailable")
        kind = str(template.get("template_type") or "")
        department = str(department_id or blueprint.get("department_id") or "operations")
        if kind == "skill":
            skill_id = _identity("pilot_skill")
            skill = {
                "schema_version": "aion.pilot.demonstrated_skill.v2",
                "skill_id": skill_id,
                "workspace_id": workspace_id,
                "department_id": department,
                "name": str(name or blueprint.get("name") or template.get("name"))[:160],
                "outcome": str(blueprint.get("outcome") or "")[:2000],
                "status": "draft",
                "source": "reusable_template",
                "source_template_id": template_id,
                "source_systems": list(blueprint.get("source_systems") or []),
                "steps": list(blueprint.get("steps") or []),
                "required_inputs": list(blueprint.get("required_inputs") or []),
                "approval_boundaries": list(blueprint.get("approval_boundaries") or []),
                "failure_policy": blueprint.get("failure_policy") or "stop_and_report",
                "validation_state": "not_tested",
                "publish_requires_human_review": True,
                "created_by": created_by,
                "created_at": _now(),
            }
            result = self._seal(skill, "skill_hash")
            self._write(self._path(workspace_id, "skills", skill_id), result)
        elif kind == "routine":
            trigger = dict(blueprint.get("trigger") or {})
            trigger_kind = trigger.pop("kind", None)
            result = self.create_routine(
                workspace_id,
                title=str(name or blueprint.get("title") or template.get("name")),
                department_id=department,
                owner_id=f"department_pilot:{department}",
                schedule=trigger if trigger_kind == "schedule" else None,
                event_trigger=trigger if trigger_kind == "event" else None,
                input_source=str(blueprint.get("input_source") or ""),
                expected_result=str(blueprint.get("expected_result") or ""),
                approval_policy=str(blueprint.get("approval_policy") or "exact_payload_for_external_write"),
                stale_data_policy=str(blueprint.get("stale_data_policy") or "stop_and_report"),
                no_data_policy=str(blueprint.get("no_data_policy") or "report_no_data"),
            )
        elif kind == "pilot":
            result = self.bootstrap_workspace(workspace_id, departments=[department], actor_id=created_by)["capsules"][0]
        else:
            raise ValueError("unsupported_pilot_template_type")
        self._audit(workspace_id, "pilot_template_instantiated", {
            "template_id": template_id,
            "template_type": kind,
            "created_by": created_by,
            "department_id": department,
        })
        return result

    def preflight_action(
        self,
        workspace_id: str,
        *,
        department_id: str,
        initiator: dict[str, Any],
        action_type: str,
        target: dict[str, Any],
        payload: dict[str, Any],
        registered_capability: bool,
    ) -> dict[str, Any]:
        if department_id not in DEPARTMENTS:
            raise ValueError("unsupported_action_department")
        exact = {
            "department_id": department_id,
            "initiator": initiator,
            "action_type": action_type,
            "target": target,
            "payload": _redact(payload),
        }
        payload_hash = canonical_contract_hash(exact)
        requires_approval = action_type in HIGH_CONSEQUENCE_ACTIONS
        decision = {
            "schema_version": "aion.pilot.action_preflight.v2",
            "decision_id": _identity("preflight"),
            "workspace_id": workspace_id,
            **exact,
            "payload_hash": payload_hash,
            "allowed": bool(registered_capability),
            "approval_required": requires_approval,
            "execution_state": (
                "denied_unregistered_capability"
                if not registered_capability
                else "exact_approval_required"
                if requires_approval
                else "ready"
            ),
            "decided_at": _now(),
        }
        decision = self._seal(decision, "decision_hash")
        self._audit(workspace_id, "action_preflight_decided", decision)
        return decision
