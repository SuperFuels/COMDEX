"""Canonical organisation, people and Tessaris authority model.

The model is deliberately smaller than an HRIS.  It records only what Tessaris
needs to scope data, approvals and work safely.  Payroll, medical, performance
and other sensitive HR records do not belong here.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
import json
import re
from typing import Any

from backend.modules.aion_business.contracts.business_containers import (
    BusinessContainerMeta,
    OrganizationAuthorityContainer,
)
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _slug(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")


def _stable_id(prefix: str, value: Any, index: int) -> str:
    current = str((value or {}).get("id") or "").strip() if isinstance(value, dict) else ""
    if current:
        return current
    record = value if isinstance(value, dict) else {}
    seed = record.get("email") or record.get("name") or record.get("title") or str(index + 1)
    digest = sha256(str(seed).lower().encode("utf-8")).hexdigest()[:8]
    return f"{prefix}.{_slug(seed) or index + 1}.{digest}"


ROLE_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "role.owner_director", "name": "Owner / Director", "template": True,
        "description": "Full business authority, including people and permission administration.",
        "scope": "business", "approval_limit": None,
        "capabilities": [
            "people.read_directory", "people.manage", "permissions.manage", "assets.manage",
            "expenses.submit", "expenses.read_all", "expenses.approve",
            "finance.read_summary", "finance.read_transactions", "finance.prepare",
            "finance.approve_posting", "boardroom.view_summary", "boardroom.view_full",
            "sales.read", "sales.manage", "sales.qualify", "sales.approve_communication",
            "marketing.read", "marketing.manage", "marketing.connect_accounts",
            "marketing.approve_publish", "marketing.approve_spend",
            "support.read", "support.manage", "support.approve_communication", "support.approve_remedy",
            "department.view_all", "department.manage_all",
            "aion_flow.review", "aion_flow.author", "aion_flow.commit",
            "aion_flow.export", "aion_flow.import", "aion_flow.benchmark",
            "aion_flow.prepare", "aion_flow.execute", "aion_flow.approve",
            "aion_flow.control", "aion_flow.view_runs", "aion_flow.evaluate",
            "aion_flow.template_manage", "aion_flow.policy_manage",
        ],
    },
    {
        "id": "role.marketing_manager", "name": "Marketing Manager", "template": True,
        "description": "Campaign, channel and publishing authority; advertising spend remains owner-gated.",
        "scope": "assigned_departments", "approval_limit": 0,
        "capabilities": [
            "people.read_directory", "marketing.read", "marketing.manage",
            "marketing.connect_accounts", "marketing.approve_publish",
            "boardroom.view_department", "department.view_assigned",
        ],
    },
    {
        "id": "role.marketing_contributor", "name": "Marketing Contributor", "template": True,
        "description": "Creates campaigns and assets without connection, publishing or spend authority.",
        "scope": "assigned_departments", "approval_limit": 0,
        "capabilities": ["marketing.read", "marketing.manage", "department.view_assigned"],
    },
    {
        "id": "role.finance_controller", "name": "Finance Controller", "template": True,
        "description": "Detailed Finance access and preparation authority; external posting remains approval-gated.",
        "scope": "business", "approval_limit": 10000,
        "capabilities": [
            "people.read_directory", "expenses.submit", "expenses.read_all", "expenses.approve",
            "finance.read_summary", "finance.read_transactions", "finance.prepare",
            "boardroom.view_summary", "department.view_assigned",
        ],
    },
    {
        "id": "role.sales_manager", "name": "Sales Manager", "template": True,
        "description": "Sales pipeline, qualification, assignment and controlled communication authority.",
        "scope": "assigned_departments", "approval_limit": 0,
        "capabilities": [
            "people.read_directory", "sales.read", "sales.manage", "sales.qualify",
            "sales.approve_communication", "boardroom.view_department", "department.view_assigned",
        ],
    },
    {
        "id": "role.sales_representative", "name": "Sales Representative", "template": True,
        "description": "Assigned opportunities, qualification and draft follow-up without external approval authority.",
        "scope": "assigned_departments", "approval_limit": 0,
        "capabilities": ["sales.read", "sales.qualify", "department.view_assigned"],
    },
    {
        "id": "role.support_manager", "name": "Support Manager", "template": True,
        "description": "Support case, escalation and controlled communication authority.",
        "scope": "assigned_departments", "approval_limit": 250,
        "capabilities": [
            "people.read_directory", "support.read", "support.manage",
            "support.approve_communication", "support.approve_remedy",
            "boardroom.view_department", "department.view_assigned",
        ],
    },
    {
        "id": "role.support_agent", "name": "Support Agent", "template": True,
        "description": "Assigned support cases, evidence collection and response drafting without approval authority.",
        "scope": "assigned_departments", "approval_limit": 0,
        "capabilities": ["support.read", "support.manage", "department.view_assigned"],
    },
    {
        "id": "role.department_manager", "name": "Department Manager", "template": True,
        "description": "Team and departmental operating visibility with bounded expense approval.",
        "scope": "assigned_departments", "approval_limit": 2500,
        "capabilities": [
            "people.read_directory", "expenses.submit", "expenses.read_team", "expenses.approve",
            "finance.read_department_summary", "boardroom.view_department", "department.view_assigned",
        ],
    },
    {
        "id": "role.employee", "name": "Employee", "template": True,
        "description": "Own work and expense access only unless another role is assigned.",
        "scope": "self", "approval_limit": 0,
        "capabilities": ["expenses.submit", "expenses.read_own", "department.view_assigned"],
    },
    {
        "id": "role.self_employed_contractor", "name": "Self-employed / Contractor", "template": True,
        "description": "External or self-employed contributor with tightly scoped access.",
        "scope": "self", "approval_limit": 0,
        "capabilities": ["expenses.submit", "expenses.read_own", "department.view_assigned"],
    },
    {
        "id": "role.external_accountant", "name": "External Accountant", "template": True,
        "description": "Finance evidence and transaction access without unrelated Boardroom or people authority.",
        "scope": "business", "approval_limit": 0,
        "capabilities": [
            "people.read_directory", "expenses.read_all", "finance.read_summary",
            "finance.read_transactions", "finance.prepare",
        ],
    },
]


STANDARD_DEPARTMENTS = [
    ("department.executive", "Leadership", None),
    ("department.finance", "Finance", "department.executive"),
    ("department.operations", "Operations", "department.executive"),
    ("department.sales", "Sales", "department.executive"),
    ("department.marketing", "Marketing", "department.executive"),
    ("department.support", "Support", "department.executive"),
    ("department.hr", "People & HR", "department.executive"),
]


class OrganizationAuthorityService:
    def __init__(self, repository: BusinessContainerRepository | None = None) -> None:
        self.repository = repository or BusinessContainerRepository()

    def get(self, workspace_id: str) -> dict[str, Any]:
        existing = self.repository.load_optional_dict(workspace_id, "organization_authority")
        if not existing:
            return self.empty(workspace_id)
        model = deepcopy(existing)
        model.setdefault("people_operations", {
            "leave_requests": [], "appraisals": [], "escalations": [], "onboarding_templates": [],
            "governance": {
                "human_employment_decisions_required": True,
                "sensitive_detail_excluded_from_dashboard": True,
                "external_messages_approval_required": True,
            },
        })
        templates = {item["id"]: item for item in ROLE_TEMPLATES}
        for role in model.get("roles") or []:
            template = templates.get(role.get("id"))
            if template and role.get("template") is True:
                role["capabilities"] = sorted(set(template.get("capabilities") or []) |
                                              set(role.get("capabilities") or []))
        return model

    def empty(self, workspace_id: str) -> dict[str, Any]:
        now = _now()
        model = OrganizationAuthorityContainer(
            id=f"organization-authority-{workspace_id}", workspace_id=workspace_id,
            meta=BusinessContainerMeta(
                workspace_id=workspace_id, container_key="organization_authority",
                updated_at=now, source="hr_pilot",
            ),
            roles=deepcopy(ROLE_TEMPLATES),
            governance={
                "default_posture": "deny", "least_privilege": True,
                "job_title_does_not_grant_access": True,
                "exact_action_approval_required": True,
                "sensitive_hr_data_excluded": True,
                "viewer_context_source": "authenticated_person",
            },
            people_operations={
                "leave_requests": [], "appraisals": [], "escalations": [],
                "onboarding_templates": [],
                "governance": {
                    "human_employment_decisions_required": True,
                    "sensitive_detail_excluded_from_dashboard": True,
                    "external_messages_approval_required": True,
                },
            },
            provenance={"created_at": now, "source": "hr_pilot_manual_setup"},
            revision=0,
        ).model_dump(mode="json")
        model["summary"] = self._summary(model)
        return model

    def save(self, workspace_id: str, payload: dict[str, Any], *, expected_revision: int | None = None,
             changed_by: str = "current_user") -> dict[str, Any]:
        current = self.repository.load_optional_dict(workspace_id, "organization_authority")
        current_revision = int((current or {}).get("revision") or 0)
        if expected_revision is not None and current_revision != int(expected_revision):
            raise ValueError("organization_revision_conflict")

        model = self._normalise(workspace_id, payload)
        model["revision"] = current_revision + 1
        model["meta"]["updated_at"] = _now()
        model["provenance"].update({"updated_at": _now(), "changed_by": changed_by})
        model["summary"] = self._summary(model)
        model["model_status"] = "authority_ready" if model["summary"]["authority_ready"] else "setup_in_progress"
        validated = OrganizationAuthorityContainer(**model).model_dump(mode="json")
        self.repository.save_model(OrganizationAuthorityContainer(**validated))
        self._project(workspace_id, validated)
        self._audit(workspace_id, "organization_saved", {
            "revision": validated["revision"], "changed_by": changed_by,
            "summary": validated["summary"],
        })
        return validated

    def access_decision(self, workspace_id: str, *, person_id: str, capability: str,
                        department_id: str | None = None, amount: float | None = None,
                        subject_person_id: str | None = None) -> dict[str, Any]:
        model = self.get(workspace_id)
        person = next((item for item in model.get("people", []) if item.get("id") == person_id), None)
        if not person or person.get("status") != "active":
            return self._decision(False, person_id, capability, "person_not_active")
        roles = [item for item in model.get("roles", []) if item.get("id") in set(person.get("role_ids") or [])]
        granting = [item for item in roles if capability in set(item.get("capabilities") or [])]
        if not granting:
            return self._decision(False, person_id, capability, "capability_not_granted")

        if department_id and not any(
            role.get("scope") == "business" or department_id in set(person.get("department_ids") or [])
            for role in granting
        ):
            return self._decision(False, person_id, capability, "department_out_of_scope")
        if subject_person_id and capability.endswith("read_own") and subject_person_id != person_id:
            return self._decision(False, person_id, capability, "person_out_of_scope")

        if amount is not None and capability == "expenses.approve":
            limits = [role.get("approval_limit") for role in granting]
            if None not in limits:
                maximum = max(float(value or 0) for value in limits)
                override = person.get("expense_approval_limit")
                if override not in (None, ""):
                    maximum = min(maximum, float(override))
                if float(amount) > maximum:
                    return self._decision(False, person_id, capability, "approval_limit_exceeded", maximum)
        return self._decision(True, person_id, capability, "granted")

    def viewer_projection(self, workspace_id: str, *, person_id: str) -> dict[str, Any]:
        """Return the bounded Boardroom and Finance projection for one person."""
        model = self.get(workspace_id)
        person = next((item for item in model.get("people", []) if item.get("id") == person_id), None)
        if not person or person.get("status") != "active":
            return {
                "person_id": person_id, "allowed": False, "reason": "person_not_active",
                "boardroom_sections": [], "finance_data_classes": [], "department_ids": [],
            }
        role_ids = set(person.get("role_ids") or [])
        roles = [item for item in model.get("roles", []) if item.get("id") in role_ids]
        capabilities = {value for role in roles for value in (role.get("capabilities") or [])}
        boardroom_sections: list[str] = []
        if "boardroom.view_full" in capabilities:
            boardroom_sections = ["executive", "finance", "sales", "marketing", "operations", "support", "people"]
        elif "boardroom.view_summary" in capabilities:
            boardroom_sections = ["executive_summary", "department_summaries", "finance_summary"]
        elif "boardroom.view_department" in capabilities:
            boardroom_sections = ["assigned_department_summary"]
        finance_classes: list[str] = []
        if "finance.read_summary" in capabilities:
            finance_classes.append("financial_summary")
        if "finance.read_department_summary" in capabilities:
            finance_classes.append("assigned_department_finance_summary")
        if "finance.read_transactions" in capabilities:
            finance_classes.append("transaction_detail")
        if "expenses.read_all" in capabilities:
            finance_classes.append("all_expenses")
        elif "expenses.read_team" in capabilities:
            finance_classes.append("team_expenses")
        elif "expenses.read_own" in capabilities:
            finance_classes.append("own_expenses")
        return {
            "person_id": person_id, "person_name": person.get("name"),
            "allowed": bool(boardroom_sections or finance_classes), "reason": "role_scoped_projection",
            "role_ids": sorted(role_ids), "capabilities": sorted(capabilities),
            "boardroom_sections": boardroom_sections, "finance_data_classes": finance_classes,
            "department_ids": list(person.get("department_ids") or []),
            "generated_at": _now(), "decision_source": "organization_authority.v1",
        }

    def _normalise(self, workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        source = deepcopy(payload or {})
        model = self.empty(workspace_id)

        departments: list[dict[str, Any]] = []
        for index, raw in enumerate(source.get("departments") or []):
            if not isinstance(raw, dict) or not str(raw.get("name") or "").strip():
                continue
            item = deepcopy(raw)
            item.update({
                "id": _stable_id("department", item, index), "name": str(item["name"]).strip(),
                "status": str(item.get("status") or "active"),
                "parent_department_id": item.get("parent_department_id") or None,
                "lead_person_id": item.get("lead_person_id") or None,
            })
            departments.append(item)
        department_ids = {item["id"] for item in departments}
        for item in departments:
            if item["parent_department_id"] not in department_ids:
                item["parent_department_id"] = None

        custom_roles = [deepcopy(item) for item in (source.get("roles") or []) if isinstance(item, dict)]
        by_role_id = {item["id"]: deepcopy(item) for item in ROLE_TEMPLATES}
        for index, item in enumerate(custom_roles):
            if not str(item.get("name") or "").strip():
                continue
            role_id = _stable_id("role", item, index)
            template = by_role_id.get(role_id) if item.get("template") is True else None
            item.update({
                "id": role_id, "name": str(item["name"]).strip(),
                "scope": str(item.get("scope") or "self"),
                "capabilities": sorted(
                    set(str(value) for value in (item.get("capabilities") or []) if value) |
                    set((template or {}).get("capabilities") or [])
                ),
            })
            by_role_id[role_id] = item
        roles = list(by_role_id.values())
        role_ids = {item["id"] for item in roles}

        people: list[dict[str, Any]] = []
        for index, raw in enumerate(source.get("people") or []):
            if not isinstance(raw, dict) or not str(raw.get("name") or "").strip():
                continue
            item = deepcopy(raw)
            employment_type = str(item.get("employment_type") or "employee")
            default_role = "role.owner_director" if employment_type == "owner" else (
                "role.self_employed_contractor" if employment_type in {"self_employed", "contractor", "freelancer"}
                else "role.employee"
            )
            item.update({
                "id": _stable_id("person", item, index), "name": str(item["name"]).strip(),
                "email": str(item.get("email") or "").strip().lower(),
                "phone": str(item.get("phone") or "").strip()[:80],
                "address": str(item.get("address") or "").strip()[:500],
                "employment_type": employment_type, "position_title": str(item.get("position_title") or "").strip(),
                "status": str(item.get("status") or "active"), "manager_id": item.get("manager_id") or None,
                "department_ids": sorted(set(value for value in (item.get("department_ids") or []) if value in department_ids)),
                "role_ids": sorted(set(value for value in (item.get("role_ids") or [default_role]) if value in role_ids)),
                "work_location": str(item.get("work_location") or "").strip(),
                "cost_center": str(item.get("cost_center") or "").strip(),
                "project_ids": sorted(set(str(value) for value in (item.get("project_ids") or []) if value)),
            })
            item["workforce_costing"] = self._planning_cost(item.get("workforce_costing"))
            people.append(item)
        people_ids = {item["id"] for item in people}
        for item in people:
            if item["manager_id"] not in people_ids or item["manager_id"] == item["id"]:
                item["manager_id"] = None
        self._validate_reporting_lines(people)

        assets: list[dict[str, Any]] = []
        for index, raw in enumerate(source.get("assets") or []):
            if not isinstance(raw, dict) or not str(raw.get("name") or "").strip():
                continue
            item = deepcopy(raw)
            assigned = item.get("assigned_person_id")
            item.update({
                "id": _stable_id("asset", item, index), "name": str(item["name"]).strip(),
                "asset_type": str(item.get("asset_type") or "company_card"),
                "assigned_person_id": assigned if assigned in people_ids else None,
                "status": str(item.get("status") or "active"),
                "last_four": re.sub(r"\D", "", str(item.get("last_four") or ""))[-4:],
                "transaction_limit": self._optional_number(item.get("transaction_limit")),
                "monthly_limit": self._optional_number(item.get("monthly_limit")),
            })
            assets.append(item)

        model.update({
            "people": people, "departments": departments, "roles": roles, "assets": assets,
            "people_operations": self._normalise_people_operations(source.get("people_operations"), people_ids),
            "authority_policies": [deepcopy(item) for item in (source.get("authority_policies") or []) if isinstance(item, dict)],
            "external_sources": [deepcopy(item) for item in (source.get("external_sources") or []) if isinstance(item, dict)],
            "governance": {**model["governance"], **(source.get("governance") or {})},
            "provenance": {**model["provenance"], **(source.get("provenance") or {})},
        })
        return model

    @staticmethod
    def _normalise_people_operations(value: Any, people_ids: set[str]) -> dict[str, Any]:
        source = deepcopy(value) if isinstance(value, dict) else {}
        result: dict[str, Any] = {
            "leave_requests": [], "appraisals": [], "escalations": [],
            "onboarding_templates": [deepcopy(item) for item in (source.get("onboarding_templates") or []) if isinstance(item, dict)],
            "governance": {
                "human_employment_decisions_required": True,
                "sensitive_detail_excluded_from_dashboard": True,
                "external_messages_approval_required": True,
                **(source.get("governance") or {}),
            },
        }
        for key in ("leave_requests", "appraisals", "escalations"):
            for item in source.get(key) or []:
                if not isinstance(item, dict) or item.get("person_id") not in people_ids:
                    continue
                result[key].append(deepcopy(item))
        return result

    @staticmethod
    def _validate_reporting_lines(people: list[dict[str, Any]]) -> None:
        managers = {item["id"]: item.get("manager_id") for item in people}
        for person_id in managers:
            seen = {person_id}
            cursor = managers.get(person_id)
            while cursor:
                if cursor in seen:
                    raise ValueError("reporting_line_cycle")
                seen.add(cursor)
                cursor = managers.get(cursor)

    @staticmethod
    def _optional_number(value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            return round(float(value), 2)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _planning_cost(cls, value: Any) -> dict[str, Any]:
        """Normalise confidential HR inputs into a planning-cost projection.

        The raw basis and rate remain in the HR container. Other departments
        receive only the effective planning rate needed for job economics.
        """
        source = deepcopy(value) if isinstance(value, dict) else {}
        basis = str(source.get("basis") or "hourly")
        base_rate = cls._optional_number(source.get("base_rate")) or 0.0
        employer_on_cost_percent = cls._optional_number(source.get("employer_on_cost_percent")) or 0.0
        monthly_bonus = cls._optional_number(source.get("monthly_bonus")) or 0.0
        commission_percent = cls._optional_number(source.get("commission_percent")) or 0.0
        productive_hours_month = cls._optional_number(source.get("productive_hours_month")) or 140.0
        hours_per_day = cls._optional_number(source.get("hours_per_day")) or 8.0
        if basis == "monthly":
            monthly_base = base_rate
        elif basis == "daily":
            monthly_base = base_rate * (productive_hours_month / hours_per_day)
        elif basis == "per_job":
            monthly_base = 0.0
        else:
            monthly_base = base_rate * productive_hours_month
        monthly_employer_cost = monthly_base * (employer_on_cost_percent / 100.0)
        effective_monthly = monthly_base + monthly_employer_cost + monthly_bonus
        effective_hourly = effective_monthly / productive_hours_month if productive_hours_month else 0.0
        effective_daily = effective_hourly * hours_per_day
        return {
            "basis": basis,
            "base_rate": round(base_rate, 2),
            "employer_on_cost_percent": round(employer_on_cost_percent, 2),
            "monthly_bonus": round(monthly_bonus, 2),
            "commission_percent": round(commission_percent, 2),
            "productive_hours_month": round(productive_hours_month, 2),
            "hours_per_day": round(hours_per_day, 2),
            "effective_hourly_cost": round(effective_hourly, 2),
            "effective_daily_cost": round(effective_daily, 2),
            "effective_monthly_cost": round(effective_monthly, 2),
            "confidential": True,
        }

    @staticmethod
    def _summary(model: dict[str, Any]) -> dict[str, Any]:
        active = [item for item in model.get("people", []) if item.get("status") == "active"]
        owner_ids = {
            item["id"] for item in active
            if item.get("employment_type") == "owner" or "role.owner_director" in set(item.get("role_ids") or [])
        }
        gaps = []
        if not owner_ids:
            gaps.append("Add an owner or director with authority to administer people and permissions.")
        if any(not item.get("email") for item in active):
            gaps.append("Add work email addresses so identities can be matched reliably.")
        if any(not item.get("role_ids") for item in active):
            gaps.append("Assign an application role to every active person.")
        return {
            "active_people": len(active),
            "employees": sum(item.get("employment_type") == "employee" for item in active),
            "self_employed_and_contractors": sum(item.get("employment_type") in {"self_employed", "contractor", "freelancer"} for item in active),
            "departments": sum(item.get("status") == "active" for item in model.get("departments", [])),
            "assigned_cards": sum(
                bool(item.get("asset_type") == "company_card" and item.get("assigned_person_id"))
                for item in model.get("assets", [])
            ),
            "authority_gaps": gaps,
            "authority_ready": bool(active and owner_ids and not any(not item.get("role_ids") for item in active)),
            "workforce_costing_ready": sum(
                bool((item.get("workforce_costing") or {}).get("base_rate")) for item in active
            ),
            "pending_leave_requests": sum(
                str(item.get("status") or "requested") == "requested"
                for item in (model.get("people_operations") or {}).get("leave_requests", [])
            ),
            "open_people_escalations": sum(
                str(item.get("status") or "open") not in {"resolved", "closed"}
                for item in (model.get("people_operations") or {}).get("escalations", [])
            ),
        }

    @staticmethod
    def _decision(allowed: bool, person_id: str, capability: str, reason: str,
                  limit: float | None = None) -> dict[str, Any]:
        return {
            "allowed": allowed, "person_id": person_id, "capability": capability,
            "reason": reason, "approval_limit": limit, "evaluated_at": _now(),
            "decision_source": "organization_authority.v1",
        }

    def _project(self, workspace_id: str, model: dict[str, Any]) -> None:
        structure = self.repository.load_optional_dict(workspace_id, "business_structure")
        if structure:
            structure["human_agents"] = [
                {key: item.get(key) for key in (
                    "id", "name", "email", "employment_type", "position_title", "status",
                    "manager_id", "department_ids", "role_ids", "cost_center", "project_ids",
                )}
                for item in model["people"]
            ]
            structure["teams"] = [deepcopy(item) for item in model["departments"]]
            structure.setdefault("meta", {})["updated_at"] = _now()
            self.repository.save_dict(workspace_id, "business_structure", structure)

        intelligence = self.repository.load_optional_dict(workspace_id, "department_intelligence")
        if intelligence:
            departments = intelligence.setdefault("departments", {})
            departments["hr"] = {
                "status": model["model_status"], "boardroom_summary": self._boardroom_summary(model),
                "organization_authority_ref": {
                    "container": "organization_authority", "revision": model["revision"],
                },
                "metrics": deepcopy(model["summary"]),
            }
            intelligence["revision"] = int(intelligence.get("revision") or 0) + 1
            intelligence.setdefault("meta", {})["updated_at"] = _now()
            self.repository.save_dict(workspace_id, "department_intelligence", intelligence)

        boardroom = self.repository.load_optional_dict(workspace_id, "boardroom_snapshot")
        if boardroom:
            runtime = boardroom.setdefault("boardroom", {}).setdefault("runtime", {})
            runtime["organization_authority"] = {
                "status": model["model_status"], "summary": deepcopy(model["summary"]),
                "viewer_policy": "person_role_scope_action", "revision": model["revision"],
            }
            boardroom.setdefault("meta", {})["updated_at"] = _now()
            self.repository.save_dict(workspace_id, "boardroom_snapshot", boardroom)

    @staticmethod
    def _boardroom_summary(model: dict[str, Any]) -> str:
        summary = model["summary"]
        if not summary["active_people"]:
            return "Organisation setup is required before people-scoped work or Boardroom visibility can be governed."
        status = "Authority is ready" if summary["authority_ready"] else "Authority setup has gaps"
        return (
            f"{status}: {summary['active_people']} active people across {summary['departments']} departments; "
            f"{summary['assigned_cards']} company cards assigned."
        )

    @staticmethod
    def _audit(workspace_id: str, event_type: str, payload: dict[str, Any]) -> None:
        path = AIONBusinessPaths.audit_file(workspace_id, "organization_authority")
        record = {"event_type": event_type, "occurred_at": _now(), **payload}
        record["event_hash"] = "sha256:" + sha256(
            json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")


def standard_departments() -> list[dict[str, Any]]:
    return [
        {"id": item_id, "name": name, "parent_department_id": parent, "status": "active", "lead_person_id": None}
        for item_id, name, parent in STANDARD_DEPARTMENTS
    ]
