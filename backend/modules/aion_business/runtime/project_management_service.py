"""Durable, business-neutral project and delivery control records."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
from typing import Any, Mapping
from uuid import uuid4

from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.business_data_domain_registry import (
    BusinessDataDomainRegistryError,
    department_vault_namespaces,
)
from backend.modules.aion_business.runtime.business_vault_runtime import configured_business_vault_runtime, guardian_mode_requested
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.providers.router import ProviderRouter


PROJECT_TYPES = {
    "client_job", "internal_initiative", "refurbishment", "research_development",
    "department_target", "implementation", "campaign", "product_development",
    "software_project", "operations", "change_programme", "event", "compliance",
    "recruitment", "education", "personal", "other",
}
PROJECT_STATUSES = {"draft", "planned", "active", "at_risk", "blocked", "completed", "cancelled"}
TASK_STATUSES = {"not_started", "in_progress", "blocked", "done"}
DEPARTMENTS = {
    "marketing", "sales", "finance", "operations", "support", "people",
    "products", "legal", "cybersecurity", "projects",
}
EXTERNAL_ACTION_PATTERNS = (
    r"\bsend\b.*\binvoice\b", r"\bissue\b.*\binvoice\b", r"\bpay\b",
    r"\bbook\b", r"\border\b", r"\bpublish\b", r"\bsend\b.*\bemail\b",
)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _text(value: Any, limit: int = 1000) -> str:
    return " ".join(str(value or "").split())[:limit]


def _money(value: Any) -> str:
    if value in (None, ""):
        return "0.00"
    try:
        return str(Decimal(str(value).replace(",", "").replace("£", "").strip()).quantize(Decimal("0.01")))
    except InvalidOperation as exc:
        raise ValueError("invalid_money_amount") from exc


class ProjectManagementService:
    """Owns a simple portfolio model shared by small jobs and strategic projects."""

    schema_version = "aion.project-management.v1"

    def __init__(
        self,
        repository: BusinessContainerRepository | None = None,
        *,
        root: str | Path | None = None,
        provider_router: ProviderRouter | None = None,
        domain_store: VaultDomainStore | None = None,
    ) -> None:
        self.repository = repository or BusinessContainerRepository(base_dir=root)
        self.provider_router = provider_router or ProviderRouter()
        self.domain_store = domain_store
        if repository is None and root is None and domain_store is None and guardian_mode_requested():
            runtime = configured_business_vault_runtime()
            self.domain_store = VaultDomainStore(
                runtime.guardian, actor_id="project-management-runtime"
            )

    def _path(self, workspace_id: str) -> Path:
        if self.domain_store is not None:
            return Path("/__tessaris_guardian_project_management__") / workspace_id / "project_management.json"
        directory = Path(self.repository.base_dir) / workspace_id
        directory.mkdir(parents=True, exist_ok=True)
        return directory / "project_management.json"

    def empty(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "revision": 0,
            "updated_at": "",
            "projects": [],
            "agent_drafts": {},
        }

    def load(self, workspace_id: str) -> dict[str, Any]:
        state = self.empty()
        raw: Any = None
        if self.domain_store is not None:
            row = self.domain_store.get_optional(
                "departments.operational_records", workspace_id=workspace_id,
                entity_id="projects/project_management/portfolio",
            )
            raw = dict(row["payload"]) if row is not None else None
        else:
            path = self._path(workspace_id)
            if path.exists():
                try:
                    raw = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, TypeError, ValueError):
                    raw = None
        if raw is not None:
            try:
                if isinstance(raw, Mapping):
                    state["revision"] = int(raw.get("revision") or 0)
                    state["updated_at"] = _text(raw.get("updated_at"), 80)
                    state["projects"] = [
                        self._normalise_project(row)
                        for row in raw.get("projects", [])
                        if isinstance(row, Mapping)
                    ][:500]
                    state["agent_drafts"] = {
                        _text(key, 160): dict(value)
                        for key, value in dict(raw.get("agent_drafts") or {}).items()
                        if isinstance(value, Mapping)
                    }
            except (TypeError, ValueError):
                state = self.empty()
        state["summary"] = self._summary(state["projects"])
        return state

    def create_project(self, workspace_id: str, payload: Mapping[str, Any], *, actor_id: str) -> dict[str, Any]:
        title = _text(payload.get("title"), 240)
        outcome = _text(payload.get("outcome"), 3000)
        if not title:
            raise ValueError("project_title_required")
        if not outcome:
            raise ValueError("project_outcome_required")
        state = self.load(workspace_id)
        project = self._normalise_project({
            **dict(payload),
            "id": f"project_{uuid4().hex}",
            "created_at": _now(),
            "created_by": actor_id,
            "activity": [{
                "id": f"event_{uuid4().hex}", "kind": "project_created",
                "message": "Project created", "at": _now(), "by": actor_id,
            }],
        })
        state["projects"].append(project)
        return self._write(workspace_id, state, actor_id=actor_id)

    def apply_action(
        self,
        workspace_id: str,
        project_id: str,
        operation: str,
        fields: Mapping[str, Any],
        *,
        actor_id: str,
    ) -> dict[str, Any]:
        state = self.load(workspace_id)
        project = next((row for row in state["projects"] if row["id"] == project_id), None)
        if project is None:
            raise LookupError("project_not_found")
        op = _text(operation, 80).casefold()
        message = "Project updated"
        if op == "update":
            allowed = {
                "title", "outcome", "project_type", "status", "priority", "owner", "sponsor",
                "customer", "start_date", "target_date", "currency", "budget_total", "contingency",
            }
            merged = {**project, **{key: value for key, value in fields.items() if key in allowed}}
            replacement = self._normalise_project(merged)
            state["projects"][state["projects"].index(project)] = replacement
            project = replacement
        elif op == "add_task":
            title = _text(fields.get("title"), 240)
            if not title:
                raise ValueError("task_title_required")
            status = _text(fields.get("status") or "not_started", 40).casefold()
            if status not in TASK_STATUSES:
                raise ValueError("invalid_task_status")
            project["tasks"].append({
                "id": f"task_{uuid4().hex}", "title": title,
                "status": status, "priority": _text(fields.get("priority") or "normal", 20),
                "description": _text(fields.get("description"), 3000),
                "assignee": _text(fields.get("assignee"), 160),
                "start_date": _text(fields.get("start_date"), 40),
                "due_date": _text(fields.get("due_date"), 40),
                "estimated_cost": _money(fields.get("estimated_cost")),
                "dependency_ids": [
                    _text(value, 120) for value in fields.get("dependency_ids", [])
                    if _text(value, 120)
                ][:100],
                "work_mode": self._work_mode(fields.get("work_mode")),
                "execution_status": _text(fields.get("execution_status") or "tracked", 40),
                "assigned_department": self._department(fields.get("assigned_department")),
                "agent_instruction": _text(fields.get("agent_instruction"), 3000),
                "approval_required": bool(fields.get("approval_required", False)),
                "created_at": _now(), "created_by": actor_id,
            })
            message = f"Task added: {title}"
        elif op == "task_status":
            task = self._find(project["tasks"], fields.get("task_id"), "task_not_found")
            status = _text(fields.get("status"), 40).casefold()
            if status not in TASK_STATUSES:
                raise ValueError("invalid_task_status")
            task["status"] = status
            task["updated_at"] = _now()
            message = f"Task status changed: {task['title']}"
        elif op == "update_task":
            task = self._find(project["tasks"], fields.get("task_id"), "task_not_found")
            allowed = {
                "title", "description", "priority", "assignee", "start_date", "due_date",
                "estimated_cost", "execution_status", "agent_instruction",
            }
            for key, value in fields.items():
                if key not in allowed:
                    continue
                task[key] = _money(value) if key == "estimated_cost" else _text(value, 240)
            if "status" in fields:
                status = _text(fields.get("status"), 40).casefold()
                if status not in TASK_STATUSES:
                    raise ValueError("invalid_task_status")
                task["status"] = status
            if "dependency_ids" in fields:
                task["dependency_ids"] = [
                    _text(value, 120) for value in fields.get("dependency_ids", [])
                    if _text(value, 120) and _text(value, 120) != task["id"]
                ][:100]
            if "work_mode" in fields:
                task["work_mode"] = self._work_mode(fields.get("work_mode"))
            if "assigned_department" in fields:
                task["assigned_department"] = self._department(fields.get("assigned_department"))
            if "approval_required" in fields:
                task["approval_required"] = bool(fields.get("approval_required"))
            task["updated_at"] = _now()
            task["updated_by"] = actor_id
            message = f"Task updated: {task['title']}"
        elif op == "add_milestone":
            title = _text(fields.get("title"), 240)
            if not title:
                raise ValueError("milestone_title_required")
            project["milestones"].append({
                "id": f"milestone_{uuid4().hex}", "title": title,
                "due_date": _text(fields.get("due_date"), 40), "owner": _text(fields.get("owner"), 160),
                "status": "planned", "created_at": _now(), "created_by": actor_id,
            })
            message = f"Milestone added: {title}"
        elif op == "record_cost":
            description = _text(fields.get("description"), 300)
            amount = _money(fields.get("amount"))
            if not description or Decimal(amount) <= 0:
                raise ValueError("cost_description_and_positive_amount_required")
            project["costs"].append({
                "id": f"cost_{uuid4().hex}", "description": description, "amount": amount,
                "category": _text(fields.get("category") or "other", 80),
                "committed": bool(fields.get("committed", False)), "at": _now(), "by": actor_id,
            })
            message = f"Cost recorded: {description}"
        elif op == "add_resource":
            name = _text(fields.get("name"), 240)
            if not name:
                raise ValueError("resource_name_required")
            project["resources"].append({
                "id": f"resource_{uuid4().hex}", "name": name,
                "kind": _text(fields.get("kind") or "person", 40),
                "quantity": _text(fields.get("quantity") or "1", 60),
                "owner": _text(fields.get("owner"), 160), "status": "required",
            })
            message = f"Resource added: {name}"
        elif op == "add_risk":
            title = _text(fields.get("title"), 240)
            if not title:
                raise ValueError("risk_title_required")
            project["risks"].append({
                "id": f"risk_{uuid4().hex}", "title": title,
                "likelihood": _text(fields.get("likelihood") or "medium", 20),
                "impact": _text(fields.get("impact") or "medium", 20),
                "mitigation": _text(fields.get("mitigation"), 2000), "owner": _text(fields.get("owner"), 160),
                "status": "open", "created_at": _now(),
            })
            message = f"Risk added: {title}"
        elif op == "add_decision":
            decision = _text(fields.get("decision"), 3000)
            if not decision:
                raise ValueError("decision_required")
            project["decisions"].append({
                "id": f"decision_{uuid4().hex}", "decision": decision,
                "reason": _text(fields.get("reason"), 3000), "at": _now(), "by": actor_id,
            })
            message = "Decision recorded"
        elif op == "add_file":
            name = _text(fields.get("name"), 300)
            if not name:
                raise ValueError("file_name_required")
            project["files"].append({
                "id": f"file_{uuid4().hex}", "name": name,
                "mime_type": _text(fields.get("mime_type") or "application/octet-stream", 160),
                "size": max(0, int(fields.get("size") or 0)),
                "source": _text(fields.get("source") or "desktop", 80),
                "note": _text(fields.get("note"), 1000),
                "added_at": _now(), "added_by": actor_id,
            })
            message = f"File linked: {name}"
        elif op == "add_update":
            update = _text(fields.get("message"), 4000)
            if not update:
                raise ValueError("project_update_required")
            message = update
        else:
            raise ValueError("unsupported_project_operation")
        project["activity"].append({
            "id": f"event_{uuid4().hex}", "kind": op, "message": message, "at": _now(), "by": actor_id,
        })
        return self._write(workspace_id, state, actor_id=actor_id)

    def investigate(self, workspace_id: str, question: str) -> dict[str, Any]:
        state = self.load(workspace_id)
        summary = state["summary"]
        projects = state["projects"]
        at_risk = [row for row in projects if row["status"] in {"at_risk", "blocked"}]
        due = [row for row in projects if row.get("target_date") and row["status"] not in {"completed", "cancelled"}]
        answer = (
            f"The portfolio has {summary['active_projects']} active project(s), "
            f"{summary['at_risk_projects']} at risk or blocked, and {summary['open_tasks']} open task(s). "
            f"Recorded spend is {summary['currency']} {summary['spent_total']} against "
            f"{summary['currency']} {summary['budget_total']}."
        )
        if at_risk:
            answer += " Immediate review: " + "; ".join(row["title"] for row in at_risk[:5]) + "."
        elif due:
            answer += " No project is explicitly marked at risk; target dates still need active owner review."
        else:
            answer += " No live project evidence has been recorded yet."
        return {"answer": answer, "project_ids": [row["id"] for row in projects[:50]], "question": _text(question, 4000)}

    def agent_turn(
        self,
        workspace_id: str,
        text: str,
        *,
        project_id: str = "",
        task_id: str = "",
        actor_id: str,
    ) -> dict[str, Any]:
        """Plan a conversational turn, then apply only validated project actions."""
        instruction = _text(text, 4000)
        if not instruction:
            raise ValueError("project_pilot_instruction_required")
        state = self.load(workspace_id)
        project = next((row for row in state["projects"] if row["id"] == project_id), None)
        lowered = instruction.casefold()
        pending = dict((state.get("agent_drafts") or {}).get(actor_id) or {})
        plan, model = self._plan_agent_turn(
            instruction=instruction, project=project, pending=pending,
            task_id=task_id, actor_id=actor_id,
        )
        intent = plan.get("intent")

        if intent == "complete_task":
            if project is None:
                return self._agent_no_project(state)
            task = self._resolve_task(project, _text(plan.get("referenced_task") or lowered, 500).casefold(), task_id)
            if task is None:
                return {
                    "state": state, "action": "needs_task", "changed": False,
                    "reply": _text(plan.get("question"), 500) or "Which task should I mark as completed? Name it, or select it and ask again.",
                    "planner": model,
                }
            state = self.apply_action(
                workspace_id, project["id"], "task_status",
                {"task_id": task["id"], "status": "done"}, actor_id=actor_id,
            )
            return {
                "state": state, "action": "task_completed", "changed": True,
                "task_id": task["id"],
                "reply": f"Done — I marked ‘{task['title']}’ as completed and updated project progress.",
                "planner": model,
            }

        if intent in {"create_task", "delegate_task"}:
            if project is None:
                return self._agent_no_project(state)
            title = _text(plan.get("task_title"), 240)
            due_date = _text(plan.get("due_date"), 40)
            department = self._department(plan.get("department"))
            external = bool(plan.get("external_action"))
            work_mode = self._work_mode(plan.get("work_mode") or ("delegated" if department else "manual"))
            assignee = _text(plan.get("assignee"), 160)
            missing = [
                item for item in plan.get("missing_fields", [])
                if item in {"task_title", "due_date", "assignee"}
                and not ((item == "task_title" and title) or (item == "due_date" and due_date) or (item == "assignee" and assignee))
            ]
            if not title and "task_title" not in missing:
                missing.insert(0, "task_title")
            if not due_date and "due_date" not in missing:
                missing.append("due_date")
            if work_mode == "manual" and not assignee and "assignee" not in missing:
                missing.append("assignee")
            if missing:
                question = self._clarification_question(missing[0], plan)
                draft = {
                    "project_id": project["id"], "intent": intent, "task_title": title,
                    "due_date": due_date, "assignee": assignee, "department": department,
                    "work_mode": work_mode, "external_action": external,
                    "agent_instruction": _text(plan.get("agent_instruction") or instruction, 3000),
                    "missing_fields": missing, "asked_field": missing[0], "updated_at": _now(),
                }
                state.setdefault("agent_drafts", {})[actor_id] = draft
                state = self._write(workspace_id, state, actor_id=actor_id)
                return {
                    "state": state, "action": "needs_clarification", "changed": False,
                    "reply": question, "draft": draft, "planner": model,
                }
            fields = {
                "title": title,
                "due_date": due_date,
                "work_mode": work_mode,
                "assigned_department": department,
                "assignee": assignee or (f"{department.title()} Pilot" if department else ("Project Pilot" if work_mode == "agent" else "")),
                "agent_instruction": _text(plan.get("agent_instruction") or instruction, 3000) if work_mode != "manual" else "",
                "approval_required": external,
                "execution_status": "awaiting_approval" if external else ("delegated" if department else "tracked"),
            }
            state = self.apply_action(
                workspace_id, project["id"], "add_task", fields, actor_id=actor_id,
            )
            task = state["projects"][[row["id"] for row in state["projects"]].index(project["id"])]["tasks"][-1]
            if actor_id in (state.get("agent_drafts") or {}):
                state["agent_drafts"].pop(actor_id, None)
                state = self._write(workspace_id, state, actor_id=actor_id)
            date_text = f" for {due_date}" if due_date else ""
            if external:
                reply = (
                    f"I added ‘{title}’{date_text} as agent work. It is waiting for approval and a connected "
                    "delivery route before anything is sent or executed. I’ll keep it visible and alert you if it cannot run."
                )
            elif department:
                reply = f"I added ‘{title}’{date_text} and delegated it to the {department.title()} Pilot."
            else:
                reply = f"I added ‘{title}’{date_text} to the project plan. The Gantt and calendar will update automatically."
            return {
                "state": state, "action": "task_added", "changed": True,
                "task_id": task["id"], "reply": reply, "planner": model,
            }

        investigation = self.investigate(workspace_id, instruction)
        return {
            "state": state, "action": "investigation", "changed": False,
            "reply": investigation["answer"], "investigation": investigation, "planner": model,
        }

    def _plan_agent_turn(
        self, *, instruction: str, project: Mapping[str, Any] | None,
        pending: Mapping[str, Any], task_id: str, actor_id: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        system = (
            "You are Tessaris Project Pilot. Understand an ordinary-language project instruction and return one JSON object only. "
            "Never copy command scaffolding such as 'pilot create a new task to' into task_title. Extract the concise real work. "
            "Supported intents: create_task, delegate_task, complete_task, query. For task creation return task_title, due_date "
            "(YYYY-MM-DD or empty), assignee, department, work_mode (manual, agent, delegated), external_action, agent_instruction, "
            "missing_fields, question, referenced_task and confidence. Preserve facts from pending_draft. Do not invent dates, owners, "
            "departments or completion. A manual task needs a due_date and accountable assignee; ask one concise follow-up for the first "
            "missing field. Agent/delegated work needs a due_date. Sending, paying, booking, ordering or publishing is external_action=true."
        )
        prompt = json.dumps({
            "today": datetime.now(UTC).date().isoformat(), "instruction": instruction,
            "actor_id": actor_id, "selected_task_id": task_id,
            "pending_draft": dict(pending),
            "project": None if project is None else {
                "id": project.get("id"), "title": project.get("title"),
                "owner": project.get("owner"), "target_date": project.get("target_date"),
                "tasks": [{"id": row.get("id"), "title": row.get("title"), "status": row.get("status"), "assignee": row.get("assignee"), "due_date": row.get("due_date")} for row in project.get("tasks", [])[:100]],
            },
        }, ensure_ascii=False, default=str)
        result = None
        try:
            result = self.provider_router.generate(
                prompt=prompt, system_prompt=system, capability="reasoning", role_type="PROJECTS",
                metadata={"operation": "project_pilot_action_planning", "read_only": True}, max_tokens=700,
            )
        except Exception:
            result = None
        parsed = self._parse_model_plan(getattr(result, "content", "")) if getattr(result, "ok", False) else None
        plan = self._validate_model_plan(parsed, instruction, pending)
        source = "project_pilot_model" if plan is not None else "deterministic_offline_fallback"
        if plan is None:
            plan = self._fallback_plan(instruction, pending, actor_id)
        return plan, {
            "source": source,
            "provider": getattr(result, "provider", None) if result else None,
            "model": getattr(result, "model", None) if result else None,
            "provider_error": getattr(result, "error_code", None) if result else "provider_unavailable",
        }

    @staticmethod
    def _parse_model_plan(content: str) -> dict[str, Any] | None:
        raw = str(content or "").strip()
        fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
        if fenced:
            raw = fenced.group(1).strip()
        try:
            value = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    def _validate_model_plan(
        self, value: Mapping[str, Any] | None, instruction: str, pending: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        if not value:
            return None
        intent = _text(value.get("intent"), 40).casefold()
        if pending and intent == "query":
            intent = _text(pending.get("intent") or "create_task", 40).casefold()
        if intent not in {"create_task", "delegate_task", "complete_task", "query"}:
            return None
        plan = {
            "intent": intent,
            "task_title": self._task_title(_text(value.get("task_title") or pending.get("task_title"), 240)),
            "due_date": _text(value.get("due_date") or pending.get("due_date"), 40),
            "assignee": _text(value.get("assignee") or pending.get("assignee") or self._extract_assignee(instruction, ""), 160),
            "department": self._department(value.get("department") or pending.get("department")),
            "work_mode": self._work_mode(value.get("work_mode") or pending.get("work_mode")),
            "external_action": bool(value.get("external_action", pending.get("external_action", False))),
            "agent_instruction": _text(value.get("agent_instruction") or pending.get("agent_instruction") or instruction, 3000),
            "referenced_task": _text(value.get("referenced_task"), 240),
            "missing_fields": [str(item) for item in value.get("missing_fields", []) if str(item) in {"task_title", "due_date", "assignee"}],
            "question": _text(value.get("question"), 500),
            "confidence": max(0.0, min(1.0, float(value.get("confidence") or 0))),
        }
        if plan["due_date"] and not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", plan["due_date"]):
            plan["due_date"] = self._extract_due_date(plan["due_date"])
        return plan

    def _fallback_plan(self, instruction: str, pending: Mapping[str, Any], actor_id: str) -> dict[str, Any]:
        lowered = instruction.casefold()
        if self._looks_like_completion(lowered):
            return {"intent": "complete_task", "referenced_task": instruction, "question": "", "missing_fields": []}
        if pending:
            plan = dict(pending)
            plan["intent"] = _text(plan.get("intent") or "create_task", 40)
            asked = plan.get("asked_field")
            due_date = self._extract_due_date(instruction)
            if due_date:
                plan["due_date"] = due_date
            assignee = self._extract_assignee(instruction, actor_id)
            if assignee:
                plan["assignee"] = assignee
            elif asked == "assignee" and len(instruction.split()) <= 6:
                plan["assignee"] = _text(instruction, 160)
            plan["missing_fields"] = []
            return plan
        if self._looks_like_task_command(lowered):
            department = self._extract_department(lowered)
            external = any(re.search(pattern, lowered) for pattern in EXTERNAL_ACTION_PATTERNS)
            work_mode = "delegated" if department else ("agent" if external else "manual")
            return {
                "intent": "delegate_task" if department else "create_task",
                "task_title": self._task_title(instruction), "due_date": self._extract_due_date(instruction),
                "assignee": self._extract_assignee(instruction, actor_id), "department": department,
                "work_mode": work_mode, "external_action": external,
                "agent_instruction": instruction, "missing_fields": [], "question": "", "confidence": 0.65,
            }
        return {"intent": "query", "missing_fields": [], "question": "", "confidence": 0.5}

    @staticmethod
    def _extract_assignee(text: str, actor_id: str) -> str:
        if re.search(r"\b(?:i|me|myself)\b.*\b(?:own|responsible|do it)\b", text, re.IGNORECASE):
            return _text(actor_id, 160)
        match = re.search(r"\b(?:assign(?:ed)?\s+to|owner\s+is|responsible\s+is)\s+([A-Za-z][A-Za-z .'-]{1,80})", text, re.IGNORECASE)
        return _text(match.group(1), 160) if match else ""

    @staticmethod
    def _clarification_question(field: str, plan: Mapping[str, Any]) -> str:
        title = _text(plan.get("task_title") or "this task", 120)
        if field == "task_title":
            return "What exactly should be done?"
        if field == "due_date":
            return f"When should ‘{title}’ be completed?"
        if field == "assignee":
            return f"Who is accountable for ‘{title}’?"
        return "What detail should I add before creating this task?"

    @staticmethod
    def _agent_no_project(state: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "state": state, "action": "needs_project", "changed": False,
            "reply": "Select a project first, then tell me the task in one sentence. I will add and organise it for you.",
        }

    @staticmethod
    def _looks_like_completion(text: str) -> bool:
        return bool(re.search(r"\b(?:mark|set|make|show)\b.*\b(?:complete|completed|done|finished)\b", text))

    @staticmethod
    def _looks_like_task_command(text: str) -> bool:
        return bool(re.search(
            r"\b(?:add|create|remember|schedule|plan|task|remind|delegate|ask|send|issue|prepare|book|order|publish|pay)\b",
            text,
        ))

    @staticmethod
    def _work_mode(value: Any) -> str:
        mode = _text(value or "manual", 30).casefold()
        return mode if mode in {"manual", "agent", "delegated"} else "manual"

    @staticmethod
    def _department(value: Any) -> str:
        department = _text(value, 40).casefold()
        if not department:
            return ""
        try:
            department_vault_namespaces(department)
        except BusinessDataDomainRegistryError:
            return ""
        return department

    @staticmethod
    def _extract_department(text: str) -> str:
        aliases = {"accounts": "finance", "hr": "people", "security": "cybersecurity", "project": "projects"}
        for name in DEPARTMENTS:
            if re.search(rf"\b(?:delegate\s+(?:this\s+)?to|ask|assign\s+(?:this\s+)?to)\s+(?:the\s+)?{re.escape(name)}(?:\s+pilot|\s+agent|\s+team)?\b", text):
                return name
        for alias, target in aliases.items():
            if re.search(rf"\b(?:delegate\s+(?:this\s+)?to|ask|assign\s+(?:this\s+)?to)\s+(?:the\s+)?{alias}\b", text):
                return target
        if "invoice" in text:
            return "finance"
        return ""

    @staticmethod
    def _extract_due_date(text: str, *, reference: date | None = None) -> str:
        base = reference or datetime.now(UTC).date()
        lowered = text.casefold()
        if "today" in lowered:
            return base.isoformat()
        if "tomorrow" in lowered:
            return (base + timedelta(days=1)).isoformat()
        iso = re.search(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", lowered)
        if iso:
            try:
                return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3))).isoformat()
            except ValueError:
                return ""
        numeric = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](20\d{2}|\d{2}))?\b", lowered)
        if numeric:
            day, month = int(numeric.group(1)), int(numeric.group(2))
            year = int(numeric.group(3)) if numeric.group(3) else base.year
            if year < 100:
                year += 2000
            try:
                candidate = date(year, month, day)
                if not numeric.group(3) and candidate < base:
                    candidate = date(year + 1, month, day)
                return candidate.isoformat()
            except ValueError:
                return ""
        ordinal = re.search(r"\b(?:on\s+(?:the\s+)?)?(\d{1,2})(?:st|nd|rd|th)\b", lowered)
        if ordinal:
            day = int(ordinal.group(1))
            for offset in range(0, 14):
                month = (base.month - 1 + offset) % 12 + 1
                year = base.year + (base.month - 1 + offset) // 12
                try:
                    candidate = date(year, month, day)
                    if candidate >= base:
                        return candidate.isoformat()
                except ValueError:
                    continue
        return ""

    @staticmethod
    def _task_title(text: str) -> str:
        title = re.sub(
            r"^\s*(?:(?:project\s+)?pilot|aion)?[\s,.:;-]*(?:please\s+)?(?:can\s+you\s+|could\s+you\s+)?(?:add|create|schedule|plan|remember|remind\s+me\s+to)\s+(?:a\s+)?(?:new\s+)?(?:task\s+)?(?:to\s+)?",
            "", text, flags=re.IGNORECASE,
        )
        title = re.sub(r"\s+\b(?:on|by)\s+(?:the\s+)?(?:\d{1,2}(?:st|nd|rd|th)?|20\d{2}-\d{1,2}-\d{1,2}|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\s*$", "", title, flags=re.IGNORECASE)
        return _text(title.strip(" .,:;-") or text, 240)

    @staticmethod
    def _resolve_task(project: Mapping[str, Any], text: str, task_id: str) -> dict[str, Any] | None:
        tasks = [row for row in project.get("tasks", []) if row.get("status") != "done"]
        if task_id:
            return next((row for row in tasks if row.get("id") == task_id), None)
        cleaned = re.sub(r"\b(?:mark|set|make|show|this|task|as|complete|completed|done|finished|please)\b", " ", text)
        needle = " ".join(cleaned.split())
        matches = [row for row in tasks if needle and (needle in row.get("title", "").casefold() or row.get("title", "").casefold() in needle)]
        return matches[0] if len(matches) == 1 else (tasks[-1] if "this" in text and len(tasks) == 1 else None)

    def _normalise_project(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        project_type = _text(raw.get("project_type") or "other", 60).casefold().replace(" ", "_")
        status = _text(raw.get("status") or "planned", 40).casefold()
        if project_type not in PROJECT_TYPES:
            project_type = "other"
        if status not in PROJECT_STATUSES:
            status = "planned"
        project = {
            "id": _text(raw.get("id") or f"project_{uuid4().hex}", 120),
            "title": _text(raw.get("title"), 240), "outcome": _text(raw.get("outcome"), 3000),
            "project_type": project_type, "status": status,
            "priority": _text(raw.get("priority") or "normal", 20),
            "owner": _text(raw.get("owner"), 160), "sponsor": _text(raw.get("sponsor"), 160),
            "customer": _text(raw.get("customer"), 240),
            "start_date": _text(raw.get("start_date"), 40), "target_date": _text(raw.get("target_date"), 40),
            "currency": _text(raw.get("currency") or "GBP", 8).upper(),
            "budget_total": _money(raw.get("budget_total")), "contingency": _money(raw.get("contingency")),
            "team": self._list(raw, "team"), "tasks": self._list(raw, "tasks"),
            "milestones": self._list(raw, "milestones"), "resources": self._list(raw, "resources"),
            "costs": self._list(raw, "costs"), "risks": self._list(raw, "risks"),
            "decisions": self._list(raw, "decisions"), "files": self._list(raw, "files"),
            "activity": self._list(raw, "activity")[-500:],
            "created_at": _text(raw.get("created_at") or _now(), 80),
            "created_by": _text(raw.get("created_by") or "desktop_user", 160),
        }
        return self._derive(project)

    @staticmethod
    def _list(raw: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
        return [deepcopy(dict(row)) for row in raw.get(key, []) if isinstance(row, Mapping)][:2000]

    @staticmethod
    def _find(rows: list[dict[str, Any]], row_id: Any, error: str) -> dict[str, Any]:
        row = next((item for item in rows if item.get("id") == str(row_id or "")), None)
        if row is None:
            raise LookupError(error)
        return row

    def _derive(self, project: dict[str, Any]) -> dict[str, Any]:
        spent = sum((Decimal(_money(row.get("amount"))) for row in project["costs"] if not row.get("committed")), Decimal("0"))
        committed = sum((Decimal(_money(row.get("amount"))) for row in project["costs"] if row.get("committed")), Decimal("0"))
        budget = Decimal(project["budget_total"])
        open_tasks = [row for row in project["tasks"] if row.get("status") != "done"]
        done_tasks = len(project["tasks"]) - len(open_tasks)
        project["financials"] = {
            "spent": _money(spent), "committed": _money(committed),
            "forecast_total": _money(spent + committed), "remaining": _money(budget - spent - committed),
        }
        project["progress_percent"] = round((done_tasks / len(project["tasks"]) * 100) if project["tasks"] else 0)
        project["open_task_count"] = len(open_tasks)
        project["open_risk_count"] = sum(1 for row in project["risks"] if row.get("status") != "closed")
        return project

    def _summary(self, projects: list[dict[str, Any]]) -> dict[str, Any]:
        live = [row for row in projects if row["status"] not in {"completed", "cancelled"}]
        currency = next((row["currency"] for row in live if row.get("currency")), "GBP")
        budget = sum((Decimal(row["budget_total"]) for row in live if row["currency"] == currency), Decimal("0"))
        spent = sum((Decimal(row["financials"]["spent"]) for row in live if row["currency"] == currency), Decimal("0"))
        committed = sum((Decimal(row["financials"]["committed"]) for row in live if row["currency"] == currency), Decimal("0"))
        return {
            "project_count": len(projects), "active_projects": len(live),
            "at_risk_projects": sum(1 for row in live if row["status"] in {"at_risk", "blocked"}),
            "open_tasks": sum(row["open_task_count"] for row in live),
            "open_risks": sum(row["open_risk_count"] for row in live),
            "currency": currency, "budget_total": _money(budget), "spent_total": _money(spent),
            "committed_total": _money(committed), "remaining_total": _money(budget - spent - committed),
        }

    def _write(self, workspace_id: str, state: Mapping[str, Any], *, actor_id: str) -> dict[str, Any]:
        projects = [self._derive(deepcopy(row)) for row in state.get("projects", [])]
        payload = {
            "schema_version": self.schema_version,
            "revision": int(state.get("revision") or 0) + 1,
            "updated_at": _now(), "updated_by": _text(actor_id, 160), "projects": projects,
            "agent_drafts": {
                _text(key, 160): dict(value)
                for key, value in dict(state.get("agent_drafts") or {}).items()
                if isinstance(value, Mapping)
            },
        }
        if self.domain_store is not None:
            entity_id = "projects/project_management/portfolio"
            current = self.domain_store.get_optional(
                "departments.operational_records", workspace_id=workspace_id,
                entity_id=entity_id,
            )
            self.domain_store.put(
                "departments.operational_records", workspace_id=workspace_id,
                entity_id=entity_id, payload=payload,
                expected_version=int(current["version"]) if current else None,
                actor_id=_text(actor_id, 160) or "project-management-runtime",
            )
        else:
            path = self._path(workspace_id)
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            temporary.replace(path)
        payload["summary"] = self._summary(projects)
        return payload
