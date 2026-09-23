from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable

from backend.modules.aion_fabric.canonical import canonical_hash, utc_now_iso


SENSITIVE_KEYS = re.compile(r"(password|secret|token|private_key|api_key|cvv|card_number|salary|medical)", re.I)


class MediumBusinessOperatingService:
    """Group, division, project and delegated-authority extension for Boardroom."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.root / "medium_business_operating_model.json"
        self.audit_path = self.root / "medium_business_audit.json"

    def configure(self, payload: Dict[str, Any], *, expected_revision: int | None = None, changed_by: str) -> Dict[str, Any]:
        if not changed_by.strip():
            raise ValueError("changed_by_required")
        current = self.state()
        revision = int(current.get("revision") or 0)
        if expected_revision is not None and int(expected_revision) != revision:
            raise ValueError("medium_business_revision_conflict")
        value = self._normalise(payload)
        self._validate(value)
        value.update({"schema_version": "aion.medium_business_operating_model.v1", "revision": revision + 1, "updated_at": utc_now_iso(), "changed_by": changed_by})
        value["model_hash"] = canonical_hash(value)
        self._write(self.state_path, value)
        self._audit("configuration_changed", changed_by, {"revision": value["revision"], "model_hash": value["model_hash"]})
        return value

    def state(self) -> Dict[str, Any]:
        if not self.state_path.exists():
            return {"schema_version": "aion.medium_business_operating_model.v1", "revision": 0, "group": {}, "entities": [], "units": [], "locations": [], "people": [], "roles": [], "projects": [], "workflows": [], "policies": {}}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def access_decision(self, *, person_id: str, capability: str, entity_id: str = "", unit_id: str = "", location_id: str = "", project_id: str = "", amount: float | None = None, action_history: Iterable[Dict[str, Any]] = ()) -> Dict[str, Any]:
        state = self.state()
        person = self._by_id(state["people"], person_id)
        if not person or person.get("status") != "active":
            return self._decision(False, "person_not_active")
        roles = [item for item in state["roles"] if item["id"] in set(person.get("role_ids") or [])]
        granting = [item for item in roles if capability in set(item.get("capabilities") or [])]
        if not granting:
            return self._decision(False, "capability_not_granted")
        scopes = dict(person.get("scopes") or {})
        checks = (("entity_ids", entity_id), ("unit_ids", unit_id), ("location_ids", location_id), ("project_ids", project_id))
        for key, requested in checks:
            permitted = set(scopes.get(key) or [])
            if requested and "*" not in permitted and requested not in permitted:
                return self._decision(False, f"{key[:-1]}_out_of_scope")
        limits = [item.get("approval_limit") for item in granting]
        if amount is not None and None not in limits and float(amount) > max(float(item or 0) for item in limits):
            return self._decision(False, "approval_limit_exceeded")
        sod = list((state.get("policies") or {}).get("separation_of_duty") or [])
        previous = [item for item in action_history if item.get("person_id") == person_id]
        for rule in sod:
            if capability == rule.get("approval_capability") and any(item.get("capability") == rule.get("request_capability") for item in previous):
                return self._decision(False, "separation_of_duty_conflict")
        return self._decision(True, "granted", accountable_person=person_id)

    def project_position(self, project_id: str) -> Dict[str, Any]:
        project = self._by_id(self.state()["projects"], project_id)
        if not project:
            raise KeyError("project_not_found")
        budget = float(project.get("budget") or 0)
        committed = float(project.get("committed") or 0)
        actual = float(project.get("actual") or 0)
        forecast = float(project.get("forecast_at_completion") or max(committed, actual))
        return {
            "project_id": project_id,
            "currency": project.get("currency"),
            "budget": budget,
            "committed": committed,
            "actual": actual,
            "remaining_after_commitments": budget - committed,
            "forecast_at_completion": forecast,
            "forecast_variance": budget - forecast,
            "over_budget": forecast > budget,
            "team_size": len(project.get("team") or []),
            "milestones": list(project.get("milestones") or []),
            "objectives": list(project.get("objectives") or []),
            "metrics": list(project.get("metrics") or []),
            "work_items": list(project.get("work_items") or []),
            "risks": list(project.get("risks") or []),
            "model_expenditure": float(project.get("model_expenditure") or 0),
        }

    def portfolio_dashboard(self, *, viewer_id: str) -> Dict[str, Any]:
        state = self.state()
        person = self._by_id(state["people"], viewer_id)
        if not person or person.get("status") != "active":
            raise PermissionError("portfolio_viewer_not_active")
        scopes = dict(person.get("scopes") or {})
        allowed_projects = set(scopes.get("project_ids") or [])
        allowed_entities = set(scopes.get("entity_ids") or [])
        projects = [item for item in state["projects"] if "*" in allowed_projects or item["id"] in allowed_projects]
        entities = [item for item in state["entities"] if "*" in allowed_entities or item["id"] in allowed_entities]
        positions = [self.project_position(item["id"]) for item in projects]
        totals_by_currency: Dict[str, Dict[str, float]] = {}
        for item in positions:
            currency = str(item.get("currency") or "UNSPECIFIED").upper()
            bucket = totals_by_currency.setdefault(currency, {"budget": 0.0, "committed": 0.0, "actual": 0.0, "forecast_at_completion": 0.0})
            for key in bucket:
                bucket[key] += float(item.get(key) or 0)
        return {
            "schema_version": "aion.medium_business_portfolio.v1",
            "viewer_id": viewer_id,
            "entities": [{"id": item["id"], "name": item["name"], "status": item.get("status")} for item in entities],
            "projects": positions,
            "totals_by_currency": totals_by_currency,
            "cross_currency_total_suppressed": len(totals_by_currency) > 1,
            "risks": [item for project in projects for item in (project.get("risks") or []) if item.get("status") != "closed"],
            "model_expenditure_by_currency": {
                currency: sum(float(item.get("model_expenditure") or 0) for item in projects if str(item.get("currency") or "UNSPECIFIED").upper() == currency)
                for currency in totals_by_currency
            },
        }

    def department_route(self, *, person_id: str, entity_id: str, unit_id: str, department: str, task_class: str) -> Dict[str, Any]:
        """Create a bounded hand-off to the existing department router and shared business map."""
        state = self.state()
        decision = self.access_decision(person_id=person_id, capability="department.route", entity_id=entity_id, unit_id=unit_id)
        if not decision["allowed"]:
            return {"allowed": False, "reason": decision["reason"]}
        entity = self._by_id(state["entities"], entity_id)
        unit = self._by_id(state["units"], unit_id)
        if not entity or not unit or unit.get("entity_id") != entity_id:
            return {"allowed": False, "reason": "department_route_scope_invalid"}
        return {
            "allowed": True,
            "schema_version": "aion.medium_business_department_route.v1",
            "person_id": person_id,
            "entity_id": entity_id,
            "unit_id": unit_id,
            "department": str(department).strip().lower(),
            "task_class": str(task_class).strip().lower(),
            "boardroom_workspace_id": entity["boardroom_workspace_id"],
            "business_map_ref": entity["business_map_ref"],
            "authority": "existing_boardroom_department_router",
        }

    def workflow_decision(self, *, workflow_id: str, requester_id: str, approver_id: str, amount: float, action_history: Iterable[Dict[str, Any]] = ()) -> Dict[str, Any]:
        """Resolve an organisation workflow without allowing requesters to approve themselves."""
        state = self.state()
        workflow = self._by_id(state["workflows"], workflow_id)
        if not workflow:
            return {"allowed": False, "reason": "workflow_not_found"}
        project_id = str(workflow.get("project_id") or "")
        project = self._by_id(state["projects"], project_id) if project_id else None
        scope = {
            "entity_id": str((project or {}).get("entity_id") or workflow.get("entity_id") or ""),
            "unit_id": str((project or {}).get("unit_id") or workflow.get("unit_id") or ""),
            "project_id": project_id,
        }
        requested = self.access_decision(person_id=requester_id, capability=workflow["request_capability"], **scope)
        if not requested["allowed"]:
            return {"allowed": False, "reason": f"requester_{requested['reason']}"}
        workflow_limit = workflow.get("approval_limit")
        if workflow_limit is not None and float(amount) > float(workflow_limit):
            return {"allowed": False, "reason": "workflow_escalation_required", "escalate_to": workflow.get("escalate_above"), "amount": float(amount)}
        history = list(action_history) + [{"person_id": requester_id, "capability": workflow["request_capability"]}]
        approved = self.access_decision(person_id=approver_id, capability=workflow["approval_capability"], amount=amount, action_history=history, **scope)
        if not approved["allowed"]:
            return {"allowed": False, "reason": f"approver_{approved['reason']}"}
        return {"allowed": True, "reason": "workflow_authorized", "workflow_id": workflow_id, "requester_id": requester_id, "approver_id": approver_id, "amount": float(amount)}

    def resolve_identity(self, *, provider: str, subject: str) -> Dict[str, Any]:
        """Map an authenticated enterprise subject to one active Boardroom person."""
        state = self.state()
        configured = self._by_id(state.get("identity_providers") or [], provider)
        if not configured or configured.get("status") != "active":
            return {"allowed": False, "reason": "identity_provider_not_active"}
        matches = [
            person for person in state["people"]
            if person.get("status") == "active" and {"provider": provider, "subject": subject} in list(person.get("identity_subjects") or [])
        ]
        if len(matches) != 1:
            return {"allowed": False, "reason": "identity_subject_not_uniquely_resolved"}
        person = matches[0]
        return {"allowed": True, "person_id": person["id"], "position_title": person.get("position_title"), "assurance": configured.get("assurance", "external")}

    def workspace_projection(self, *, person_id: str) -> Dict[str, Any]:
        state = self.state()
        person = self._by_id(state["people"], person_id)
        if not person or person.get("status") != "active":
            return {"allowed": False, "reason": "person_not_active"}
        scopes = dict(person.get("scopes") or {})
        return {
            "allowed": True,
            "person": {"id": person["id"], "name": person["name"], "position_title": person.get("position_title"), "engagement_type": person.get("engagement_type")},
            "scopes": scopes,
            "entities": self._select(state["entities"], scopes.get("entity_ids") or []),
            "units": self._select(state["units"], scopes.get("unit_ids") or []),
            "locations": self._select(state["locations"], scopes.get("location_ids") or []),
            "projects": self._select(state["projects"], scopes.get("project_ids") or []),
            "private_other_people_excluded": True,
        }

    def route_policy(self, *, data_classification: str, residency: str, provider: str, region: str) -> Dict[str, Any]:
        policy = dict(self.state().get("policies") or {})
        allowed_residencies = set((policy.get("data_residency") or {}).get(data_classification) or [])
        provider_regions = dict(policy.get("provider_regions") or {})
        allowed_regions = set(provider_regions.get(provider) or [])
        reasons = []
        if not allowed_residencies:
            reasons.append("data_classification_policy_missing")
        if allowed_residencies and residency not in allowed_residencies:
            reasons.append("data_residency_not_allowed")
        if provider not in provider_regions:
            reasons.append("provider_not_approved")
        if allowed_regions and region not in allowed_regions:
            reasons.append("provider_region_not_allowed")
        retention = dict(policy.get("retention_days") or {})
        return {"allowed": not reasons, "reasons": reasons, "data_classification": data_classification, "residency": residency, "provider": provider, "region": region, "retention_days": retention.get(data_classification)}

    def support_bundle(self, *, viewer_id: str) -> Dict[str, Any]:
        projection = self.workspace_projection(person_id=viewer_id)
        permission = self.access_decision(person_id=viewer_id, capability="support.bundle.export")
        if projection.get("allowed") is not True or permission.get("allowed") is not True:
            raise PermissionError("support_bundle_viewer_not_allowed")
        state = self.state()
        bundle = {
            "schema_version": "aion.redacted_support_bundle.v1",
            "model_hash": state.get("model_hash"),
            "revision": state.get("revision"),
            "counts": {key: len(state.get(key) or []) for key in ("entities", "units", "locations", "people", "projects", "workflows")},
            "viewer_scope_hash": canonical_hash(projection.get("scopes") or {}),
            "generated_at": utc_now_iso(),
            "secrets_included": False,
            "customer_content_included": False,
        }
        bundle["bundle_hash"] = canonical_hash(bundle)
        return bundle

    def audit_export(self, *, viewer_id: str) -> Dict[str, Any]:
        projection = self.workspace_projection(person_id=viewer_id)
        permission = self.access_decision(person_id=viewer_id, capability="audit.export")
        if projection.get("allowed") is not True or permission.get("allowed") is not True:
            raise PermissionError("audit_export_viewer_not_allowed")
        events = self._read_audit()
        return {"schema_version": "aion.customer_audit_export.v1", "viewer_id": viewer_id, "events": [self._redact(item) for item in events], "event_count": len(events), "generated_at": utc_now_iso()}

    def _normalise(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {key: list(payload.get(key) or []) for key in ("entities", "units", "locations", "people", "roles", "projects", "workflows", "identity_providers")} | {"group": dict(payload.get("group") or {}), "policies": dict(payload.get("policies") or {})}

    def _validate(self, value: Dict[str, Any]) -> None:
        for key in ("entities", "units", "locations", "people", "roles", "projects", "workflows", "identity_providers"):
            identifiers = [str(item.get("id") or "") for item in value[key]]
            if any(not item for item in identifiers) or len(identifiers) != len(set(identifiers)):
                raise ValueError(f"{key}_identifiers_invalid_or_duplicate")
        entity_ids = {item["id"] for item in value["entities"]}
        unit_ids = {item["id"] for item in value["units"]}
        location_ids = {item["id"] for item in value["locations"]}
        people_ids = {item["id"] for item in value["people"]}
        role_ids = {item["id"] for item in value["roles"]}
        project_ids = {item["id"] for item in value["projects"]}
        identity_provider_ids = {item["id"] for item in value["identity_providers"]}
        for item in value["entities"]:
            if not str(item.get("boardroom_workspace_id") or "").strip() or not str(item.get("business_map_ref") or "").strip():
                raise ValueError("entity_boardroom_map_binding_required")
        for item in value["units"]:
            if item.get("entity_id") not in entity_ids or (item.get("parent_unit_id") and item["parent_unit_id"] not in unit_ids):
                raise ValueError("unit_parent_scope_invalid")
        self._reject_cycles(value["units"], "parent_unit_id", "unit_hierarchy_cycle")
        for item in value["locations"]:
            if item.get("entity_id") not in entity_ids:
                raise ValueError("location_entity_invalid")
        for item in value["people"]:
            if item.get("manager_id") and item["manager_id"] not in people_ids:
                raise ValueError("person_manager_invalid")
            if not set(item.get("role_ids") or []) <= role_ids:
                raise ValueError("person_role_invalid")
            if not set(item.get("dotted_line_manager_ids") or []) <= people_ids:
                raise ValueError("person_dotted_line_manager_invalid")
            for binding in item.get("identity_subjects") or []:
                if binding.get("provider") not in identity_provider_ids or not str(binding.get("subject") or "").strip():
                    raise ValueError("person_identity_subject_invalid")
            scopes = dict(item.get("scopes") or {})
            self._validate_scope(scopes.get("entity_ids") or [], entity_ids, "person_entity_scope_invalid")
            self._validate_scope(scopes.get("unit_ids") or [], unit_ids, "person_unit_scope_invalid")
            self._validate_scope(scopes.get("location_ids") or [], location_ids, "person_location_scope_invalid")
            self._validate_scope(scopes.get("project_ids") or [], project_ids, "person_project_scope_invalid")
        self._reject_cycles(value["people"], "manager_id", "reporting_hierarchy_cycle")
        for item in value["projects"]:
            if item.get("entity_id") not in entity_ids or item.get("unit_id") not in unit_ids:
                raise ValueError("project_business_scope_invalid")
            if float(item.get("budget") or 0) < 0 or float(item.get("committed") or 0) < 0 or float(item.get("actual") or 0) < 0:
                raise ValueError("project_financial_values_invalid")
            for member in item.get("team") or []:
                if member.get("person_id") not in people_ids or not member.get("project_role"):
                    raise ValueError("project_team_member_invalid")
                allocation = float(member.get("allocation_percent") or 0)
                if allocation < 0 or allocation > 100:
                    raise ValueError("project_team_allocation_invalid")
        capability_names = {capability for role in value["roles"] for capability in (role.get("capabilities") or [])}
        for item in value["workflows"]:
            if item.get("request_capability") not in capability_names or item.get("approval_capability") not in capability_names:
                raise ValueError("workflow_capability_invalid")
            if item.get("escalate_above") and item["escalate_above"] not in people_ids:
                raise ValueError("workflow_escalation_person_invalid")
        subjects = [(binding["provider"], binding["subject"]) for person in value["people"] for binding in (person.get("identity_subjects") or [])]
        if len(subjects) != len(set(subjects)):
            raise ValueError("identity_subject_duplicate")

    @staticmethod
    def _validate_scope(requested, valid, error):
        if "*" not in requested and not set(requested) <= set(valid):
            raise ValueError(error)

    @staticmethod
    def _reject_cycles(items, parent_key, error):
        parents = {item["id"]: item.get(parent_key) for item in items}
        for start in parents:
            seen = set()
            current = start
            while current:
                if current in seen:
                    raise ValueError(error)
                seen.add(current)
                current = parents.get(current)

    @staticmethod
    def _by_id(items, identifier):
        return next((item for item in items if item.get("id") == identifier), None)

    @staticmethod
    def _select(items, allowed):
        permitted = set(allowed)
        return [item for item in items if "*" in permitted or item.get("id") in permitted]

    @staticmethod
    def _decision(allowed, reason, **extra):
        return {"allowed": bool(allowed), "reason": reason, **extra}

    def _audit(self, event, actor, detail):
        events = self._read_audit()
        record = {"event": event, "actor": actor, "detail": detail, "at": utc_now_iso()}
        record["event_hash"] = canonical_hash(record)
        events.append(record)
        self._write(self.audit_path, {"events": events})

    def _read_audit(self):
        if not self.audit_path.exists():
            return []
        return list(json.loads(self.audit_path.read_text(encoding="utf-8")).get("events") or [])

    @classmethod
    def _redact(cls, value):
        if isinstance(value, dict):
            return {key: "[REDACTED]" if SENSITIVE_KEYS.search(str(key)) else cls._redact(item) for key, item in value.items()}
        if isinstance(value, list):
            return [cls._redact(item) for item in value]
        return value

    @staticmethod
    def _write(path: Path, payload: Dict[str, Any]) -> None:
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
