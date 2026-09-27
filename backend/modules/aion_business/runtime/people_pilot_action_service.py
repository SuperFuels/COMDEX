"""Governed People Pilot actions selected from registered capabilities.

The language model does not receive write authority.  It may only select a
capability and populate that capability's declared fields.  AION validates the
plan, checks the signed actor's People authority, applies the internal record
change and returns a receipt.  External messages and employment decisions stay
behind explicit human approval.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import json
from pathlib import Path
import re
from threading import RLock
from typing import Any, Mapping
from uuid import uuid4
from zipfile import ZipFile
from xml.etree import ElementTree

from backend.modules.aion_business.runtime.organization_authority_service import (
    OrganizationAuthorityService,
)


_LOCK = RLock()

_EMPLOYMENT_TYPES = {
    "owner",
    "employee",
    "self_employed",
    "contractor",
    "freelancer",
    "external_adviser",
}

PEOPLE_CAPABILITIES: tuple[dict[str, Any], ...] = (
    {
        "id": "people.create_person",
        "description": "Create an employee, contractor, owner or other person record.",
        "required": ["name"],
        "optional": ["email", "phone", "address", "employment_type", "position_title", "manager_name", "department_name", "start_date", "work_location", "cost_center", "next_appraisal_date", "software_accounts", "onboarding_completed", "expense_approval_limit", "workforce_costing_basis", "workforce_costing_base_rate", "workforce_costing_employer_on_cost_percent", "workforce_costing_monthly_bonus", "workforce_costing_commission_percent", "workforce_costing_productive_hours_month", "workforce_costing_hours_per_day"],
        "authority": "people.manage",
        "external_effect": False,
    },
    {
        "id": "people.update_person",
        "description": "Update an existing person's contact, role, manager, department or employment details.",
        "required": ["person_name"],
        "optional": ["email", "phone", "address", "employment_type", "position_title", "manager_name", "department_name", "start_date", "status", "work_location", "cost_center", "next_appraisal_date", "software_accounts", "onboarding_completed", "expense_approval_limit", "workforce_costing_basis", "workforce_costing_base_rate", "workforce_costing_employer_on_cost_percent", "workforce_costing_monthly_bonus", "workforce_costing_commission_percent", "workforce_costing_productive_hours_month", "workforce_costing_hours_per_day"],
        "authority": "people.manage",
        "external_effect": False,
    },
    {
        "id": "people.record_leave_request",
        "description": "Record requested time away in People Operations. This does not approve the leave or notify anybody.",
        "required": ["person_name", "start_date", "end_date"],
        "optional": ["leave_type", "cover_owner"],
        "authority": "people.manage",
        "external_effect": False,
    },
)


def _clean(value: Any, limit: int = 500) -> str:
    return " ".join(str(value or "").split())[:limit]


def _normalise_date(value: Any) -> str:
    text = _clean(value, 80).strip(".,")
    if not text:
        return ""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        try:
            return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
        except ValueError:
            return ""
    compact = re.sub(r"(?<=\d)(?:st|nd|rd|th)\b", "", text, flags=re.I)
    for pattern in ("%d %B %Y", "%d %b %Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(compact, pattern).date().isoformat()
        except ValueError:
            pass
    return ""


class PeoplePilotActionService:
    """Plan and execute bounded internal People administration."""

    def __init__(self, provider: Any, authority: OrganizationAuthorityService | None = None) -> None:
        self.provider = provider
        self.repository = provider.containers
        self.models = provider.coo_missions
        self.authority = authority or getattr(provider, "organization_authority", None) or OrganizationAuthorityService(self.repository)

    def handle(
        self,
        workspace_id: str,
        text: str,
        *,
        person_id: str,
        attachments: Any = None,
        pending_plan: Mapping[str, Any] | None = None,
        subject_context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        instruction = _clean(text, 2_000)
        document_context, document_names = self._document_context(attachments)
        plan = self._plan(workspace_id, instruction, document_context=document_context)
        if pending_plan and str(plan.get("capability_id") or "") not in {item["id"] for item in PEOPLE_CAPABILITIES}:
            if re.fullmatch(r"(?:cancel|never mind|nevermind|stop|forget it)[.!]?", instruction, re.I):
                return {
                    "handled": True,
                    "status": "cancelled",
                    "content": "Understood. I cancelled that pending People request and changed nothing.",
                    "plan": {"capability_id": "none", "fields": {}, "missing_fields": []},
                    "external_writes_performed": False,
                    "approval_gated": True,
                }
            plan = self._resume_plan(
                workspace_id,
                pending_plan,
                instruction,
                document_context=document_context,
            )
        elif subject_context and str(plan.get("capability_id") or "") not in {item["id"] for item in PEOPLE_CAPABILITIES}:
            if re.fullmatch(r"(?:done|finished|finish|clear profile|stop updating(?: this profile)?)[.!]?", instruction, re.I):
                return {
                    "handled": True,
                    "status": "context_cleared",
                    "content": f"Done. I am no longer updating {_clean(subject_context.get('person_name')) or 'that person'}’s profile.",
                    "plan": {"capability_id": "none", "fields": {}, "missing_fields": []},
                    "external_writes_performed": False,
                    "approval_gated": True,
                }
            plan = self._continue_subject(
                workspace_id,
                subject_context,
                instruction,
                document_context=document_context,
            )
        if document_names:
            plan["source_documents"] = document_names
        capability_id = str(plan.get("capability_id") or "")
        if capability_id not in {item["id"] for item in PEOPLE_CAPABILITIES}:
            return {"handled": False, "plan": plan}
        if subject_context and capability_id in {"people.update_person", "people.record_leave_request"}:
            plan_fields = dict(plan.get("fields") or {})
            if not _clean(plan_fields.get("person_name")):
                context_name = _clean(subject_context.get("person_name"))
                if context_name:
                    plan_fields["person_name"] = context_name
                    plan["fields"] = plan_fields
                    plan["continued_active_profile"] = context_name
        capability = next(item for item in PEOPLE_CAPABILITIES if item["id"] == capability_id)
        fields = self._validated_fields(capability, plan.get("fields"))
        missing = [name for name in capability["required"] if not fields.get(name)]
        if missing:
            return {
                "handled": True,
                "status": "needs_information",
                "content": self._missing_message(capability_id, missing),
                "plan": {**plan, "fields": fields, "missing_fields": missing},
                "external_writes_performed": False,
                "approval_gated": True,
            }

        with _LOCK:
            model = self.authority.get(workspace_id)
            actor = self._authorised_actor(model, person_id, str(capability["authority"]))
            if not actor:
                return {
                    "handled": True,
                    "status": "authority_required",
                    "content": "I prepared that People change, but the signed-in user is not linked to an active person with People administration authority. No record was changed.",
                    "plan": {**plan, "fields": fields},
                    "external_writes_performed": False,
                    "approval_gated": True,
                }
            changed, content, receipt = self._apply(capability_id, model, fields)
            if not changed:
                return {
                    "handled": True, "status": receipt.get("status", "needs_information"),
                    "content": content, "plan": {**plan, "fields": fields},
                    "action_receipt": receipt, "external_writes_performed": False,
                    "approval_gated": True,
                }
            saved = self.authority.save(
                workspace_id, model, expected_revision=int(model.get("revision") or 0),
                changed_by=f"people_pilot:{actor['id']}",
            )
            verified = self.authority.get(workspace_id)
            readback_verified = self._verify_saved_action(capability_id, verified, fields, receipt)
            receipt.update({
                "receipt_id": f"people-action-{uuid4().hex}",
                "capability_id": capability_id,
                "actor_person_id": actor["id"],
                "workspace_id": workspace_id,
                "organization_revision": saved.get("revision"),
                "internal_record_changed": True,
                "readback_verified": readback_verified,
                "external_writes_performed": False,
                "external_notifications_sent": False,
            })
            if not readback_verified:
                return {
                    "handled": True,
                    "status": "verification_failed",
                    "content": (
                        "I attempted that People record change, but the saved record did not confirm the requested values. "
                        "I will not report it as completed. Please review the record or try again."
                    ),
                    "plan": {**plan, "fields": fields},
                    "action_receipt": receipt,
                    "organization": verified,
                    "external_writes_performed": False,
                    "approval_gated": True,
                }
            return {
                "handled": True, "status": "completed", "content": content,
                "plan": {**plan, "fields": fields}, "action_receipt": receipt,
                "organization": verified, "external_writes_performed": False,
                "approval_gated": True,
            }

    @staticmethod
    def _verify_saved_action(
        capability_id: str,
        model: Mapping[str, Any],
        fields: Mapping[str, Any],
        receipt: Mapping[str, Any],
    ) -> bool:
        """Require canonical read-back before the Pilot may claim completion."""
        if capability_id == "people.record_leave_request":
            request_id = str(receipt.get("leave_request_id") or "")
            requests = ((model.get("people_operations") or {}).get("leave_requests") or [])
            return any(
                str(item.get("id") or "") == request_id
                and str(item.get("start_date") or "") == str(fields.get("start_date") or "")
                and str(item.get("end_date") or "") == str(fields.get("end_date") or "")
                for item in requests if isinstance(item, Mapping)
            )

        person_id = str(receipt.get("person_id") or "")
        person = next((
            item for item in model.get("people") or []
            if isinstance(item, Mapping) and str(item.get("id") or "") == person_id
        ), None)
        if not person:
            return False
        expected_name = fields.get("name") if capability_id == "people.create_person" else fields.get("person_name")
        if expected_name and str(person.get("name") or "").casefold() != str(expected_name).casefold():
            return False
        for key in (
            "email", "phone", "address", "employment_type", "position_title", "start_date",
            "next_appraisal_date", "work_location", "cost_center", "status",
        ):
            if fields.get(key) not in (None, "") and str(person.get(key) or "") != str(fields[key]):
                return False
        costing_map = {
            "workforce_costing_basis": "basis",
            "workforce_costing_base_rate": "base_rate",
            "workforce_costing_employer_on_cost_percent": "employer_on_cost_percent",
            "workforce_costing_monthly_bonus": "monthly_bonus",
            "workforce_costing_commission_percent": "commission_percent",
            "workforce_costing_productive_hours_month": "productive_hours_month",
            "workforce_costing_hours_per_day": "hours_per_day",
        }
        costing = person.get("workforce_costing") or {}
        for source, target in costing_map.items():
            if fields.get(source) in (None, ""):
                continue
            if source == "workforce_costing_basis":
                if str(costing.get(target) or "") != str(fields[source]):
                    return False
            elif float(costing.get(target) or 0) != float(fields[source]):
                return False
        return True

    def _plan(self, workspace_id: str, instruction: str, *, document_context: str = "") -> dict[str, Any]:
        combined_instruction = f"{instruction}\n{document_context}" if document_context else instruction
        direct = self._fallback_plan(combined_instruction)
        runtime = self.repository.load_optional_dict(workspace_id, "operational_runtime_summary") or {}
        selection = self.models.resolve_model(runtime)
        if selection.get("status") == "selected":
            prompt = {
                "role": "People Pilot administration planner",
                "instruction": instruction,
                "local_document_extract": document_context,
                "registered_capabilities": PEOPLE_CAPABILITIES,
                "rules": [
                    "Interpret ordinary conversational language; users do not need to quote field labels or fixed commands.",
                    "Select only a registered capability when the user clearly asks to change People records.",
                    "Use capability_id none for questions, advice, unclear requests or unsupported actions.",
                    "Never invent a person, date, contact detail, manager, department or approval.",
                    "Return JSON only: capability_id, confidence, fields, missing_fields and user_summary.",
                    "Dates must be YYYY-MM-DD. A single day of leave uses the same start_date and end_date.",
                    "Classify paid holiday as Annual leave, unpaid time away as Unpaid leave and sickness as Sick leave.",
                ],
            }
            try:
                raw = self.models._invoke(selection, json.dumps(prompt, ensure_ascii=False, separators=(",", ":")))
                parsed = self._json_object(raw)
                parsed_capability = str(parsed.get("capability_id") or "")
                if parsed_capability not in {"none", *(item["id"] for item in PEOPLE_CAPABILITIES)}:
                    raise ValueError("unregistered_people_capability")
                parsed["planner"] = {
                    key: selection.get(key) for key in ("provider", "model", "source", "release_status")
                }
                parsed["planner"]["source"] = parsed["planner"].get("source") or "selected_vault_model"
                parsed["planner"]["semantic_interpreter"] = True
                # If the model declines an otherwise clear registered action,
                # retain safe local operation without turning model prose into a
                # success message.  The deterministic result still passes the
                # same schema, authority and read/write boundary below.
                if parsed_capability == "none" and str(direct.get("capability_id") or "") in {
                    item["id"] for item in PEOPLE_CAPABILITIES
                }:
                    direct["planner"] = {
                        "source": "bounded_people_language_fallback",
                        "model_required": True,
                        "semantic_model_declined": True,
                        **{key: selection.get(key) for key in ("provider", "model", "release_status")},
                    }
                    return direct
                return parsed
            except Exception as exc:
                fallback = direct
                fallback["planner_error"] = f"{type(exc).__name__}:{str(exc)[:160]}"
                fallback["planner"] = {
                    "source": "bounded_people_language_fallback",
                    "model_required": True,
                    **{key: selection.get(key) for key in ("provider", "model", "release_status")},
                }
                return fallback
        if str(direct.get("capability_id") or "") in {item["id"] for item in PEOPLE_CAPABILITIES}:
            direct["planner"] = {
                "source": "bounded_people_language_fallback",
                "model_required": True,
                "model_unavailable": True,
            }
        return direct

    def _resume_plan(
        self,
        workspace_id: str,
        pending_plan: Mapping[str, Any],
        instruction: str,
        *,
        document_context: str = "",
    ) -> dict[str, Any]:
        """Complete the immediately preceding bounded People request.

        A short answer such as ``Rebecca Newman`` has no independent intent, so
        it must be interpreted against the exact registered capability that
        asked the question.  The continuation never widens that capability.
        """
        capability_id = str(pending_plan.get("capability_id") or "")
        capability = next((item for item in PEOPLE_CAPABILITIES if item["id"] == capability_id), None)
        if not capability:
            return {"capability_id": "none", "fields": {}, "missing_fields": []}
        prior_fields = self._validated_fields(capability, pending_plan.get("fields"))
        runtime = self.repository.load_optional_dict(workspace_id, "operational_runtime_summary") or {}
        selection = self.models.resolve_model(runtime)
        if selection.get("status") == "selected":
            prompt = {
                "role": "People Pilot missing-information interpreter",
                "pending_capability": capability,
                "known_fields": prior_fields,
                "user_follow_up": instruction,
                "local_document_extract": document_context,
                "current_date_utc": datetime.now(UTC).date().isoformat(),
                "rules": [
                    "Interpret the follow-up conversationally against the pending request.",
                    "Do not select or widen to another capability.",
                    "Return the pending capability_id and only facts supplied by the user.",
                    "Use declared field names, ISO YYYY-MM-DD dates and decimal points.",
                    "Never invent missing information.",
                    "Return JSON only: capability_id, confidence, fields, missing_fields and user_summary.",
                ],
            }
            try:
                raw = self.models._invoke(
                    selection,
                    json.dumps(prompt, ensure_ascii=False, separators=(",", ":")),
                )
                continuation = self._json_object(raw)
                if str(continuation.get("capability_id") or "") != capability_id:
                    raise ValueError("pending_people_capability_changed")
                continued_fields = self._validated_fields(capability, continuation.get("fields"))
                return {
                    **continuation,
                    "capability_id": capability_id,
                    "fields": {**prior_fields, **continued_fields},
                    "planner": {
                        **{key: selection.get(key) for key in ("provider", "model", "source", "release_status")},
                        "context": "pending_people_request",
                    },
                    "continued_from_pending_action": True,
                }
            except Exception:
                pass
        if capability_id == "people.create_person":
            synthetic = f"Create a new employee named {instruction}"
        elif capability_id == "people.update_person":
            person_name = prior_fields.get("person_name", "")
            synthetic = f"Update employee {person_name}: {instruction}"
        else:
            person_name = prior_fields.get("person_name", "")
            synthetic = f"Record holiday for {person_name}: {instruction}"
        if document_context:
            synthetic = f"{synthetic}\n{document_context}"
        continuation = self._fallback_plan(synthetic)
        continued_fields = self._validated_fields(capability, continuation.get("fields"))
        fields = {**prior_fields, **continued_fields}
        return {
            "capability_id": capability_id,
            "confidence": continuation.get("confidence", 0.7),
            "fields": fields,
            "missing_fields": [],
            "planner": {"source": "bounded_pending_people_action"},
            "continued_from_pending_action": True,
        }

    def _continue_subject(
        self,
        workspace_id: str,
        subject_context: Mapping[str, Any],
        instruction: str,
        *,
        document_context: str = "",
    ) -> dict[str, Any]:
        person_name = _clean(subject_context.get("person_name"), 300)
        if not person_name:
            return {"capability_id": "none", "fields": {}, "missing_fields": []}

        runtime = self.repository.load_optional_dict(workspace_id, "operational_runtime_summary") or {}
        selection = self.models.resolve_model(runtime)
        if selection.get("status") == "selected":
            prompt = {
                "role": "People Pilot conversational administration interpreter",
                "active_person": person_name,
                "instruction": instruction,
                "local_document_extract": document_context,
                "registered_capabilities": PEOPLE_CAPABILITIES,
                "rules": [
                    "Interpret natural conversational wording, pronouns and elliptical follow-ups against active_person.",
                    "Users do not need to use field labels or a fixed command format.",
                    "A profile fact must use people.update_person and include active_person as person_name.",
                    "Time off, holiday, sickness or absence must use people.record_leave_request and include active_person as person_name unless the user clearly names somebody else.",
                    "Use only declared field names. Convert dates to YYYY-MM-DD and decimal commas to decimal points.",
                    "Use capability_id none for questions, advice or conversation that does not request a record change.",
                    "Never invent a value. Return JSON only: capability_id, confidence, fields, missing_fields and user_summary.",
                ],
            }
            try:
                raw = self.models._invoke(
                    selection,
                    json.dumps(prompt, ensure_ascii=False, separators=(",", ":")),
                )
                plan = self._json_object(raw)
                capability_id = str(plan.get("capability_id") or "")
                if capability_id not in {"none", "people.update_person", "people.record_leave_request"}:
                    raise ValueError("active_people_profile_capability_widened")
                if capability_id in {"people.update_person", "people.record_leave_request"}:
                    fields = dict(plan.get("fields") or {})
                    fields.setdefault("person_name", person_name)
                    plan["fields"] = fields
                plan["planner"] = {
                    **{key: selection.get(key) for key in ("provider", "model", "source", "release_status")},
                    "context": "active_people_profile",
                }
                plan["continued_active_profile"] = person_name
                return plan
            except Exception as exc:
                planner_error = f"{type(exc).__name__}:{str(exc)[:160]}"
        else:
            planner_error = "selected_vault_model_unavailable"

        # Deterministic recovery is deliberately secondary to model-led language
        # interpretation. It recognises common phrasing without granting any new
        # capability or bypassing field validation and authority checks.
        direct = self._fallback_plan(
            f"{instruction}\n{document_context}" if document_context else instruction
        )
        capability_id = str(direct.get("capability_id") or "")
        if capability_id == "people.record_leave_request":
            fields = dict(direct.get("fields") or {})
            fields.setdefault("person_name", person_name)
            direct["fields"] = fields
            direct["continued_active_profile"] = person_name
            direct["planner_error"] = planner_error
            return direct

        plan = self._fallback_plan(f"Update employee {person_name}, {instruction}")
        fields = dict(plan.get("fields") or {})
        changed_fields = {key for key, value in fields.items() if key != "person_name" and value not in (None, "")}
        if not changed_fields:
            return {
                "capability_id": "none",
                "fields": {},
                "missing_fields": [],
                "planner": {"source": "bounded_active_people_profile"},
                "planner_error": planner_error,
            }
        plan["planner"] = {"source": "bounded_active_people_profile"}
        plan["planner_error"] = planner_error
        plan["continued_active_profile"] = person_name
        return plan

    @staticmethod
    def _is_profile_continuation(instruction: str) -> bool:
        return bool(re.search(
            r"\b(?:e-?mail|mobile|phone|telephone|address|job\s+title|position|role|relationship|line\s+manager|manager|department|start\s+date|employment\s+type|work\s+location|cost\s+cent(?:re|er)|next\s+appraisal|software\s+accounts?|onboarding|contract\s+signed|right.to.work|health\s*(?:and|&)\s*safety|handbook|induction|payroll\s+details|equipment|hourly\s+rate|pay\s+rate|salary|on.cost|bonus|commission|productive\s+hours|hours\s+per\s+(?:working\s+)?day|expense\s+approval)\b",
            instruction,
            re.I,
        ))

    @staticmethod
    def _document_context(values: Any) -> tuple[str, list[str]]:
        paths = [Path(str(item)).expanduser() for item in list(values or [])[:3] if str(item).strip()]
        extracts: list[str] = []
        names: list[str] = []
        allowed = {".pdf", ".docx", ".txt", ".md", ".csv", ".json"}
        for path in paths:
            if not path.is_absolute() or path.suffix.casefold() not in allowed or not path.is_file():
                continue
            if path.stat().st_size > 10 * 1024 * 1024:
                continue
            try:
                suffix = path.suffix.casefold()
                if suffix == ".pdf":
                    from pypdf import PdfReader
                    text = "\n".join((page.extract_text() or "") for page in PdfReader(str(path)).pages[:20])
                elif suffix == ".docx":
                    with ZipFile(path) as archive:
                        root = ElementTree.fromstring(archive.read("word/document.xml"))
                    text = " ".join(node.text or "" for node in root.iter() if node.tag.endswith("}t"))
                else:
                    text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            clean = _clean(text, 12_000)
            if clean:
                names.append(path.name[:160])
                extracts.append(f"Document {path.name}: {clean}")
        return "\n".join(extracts)[:20_000], names

    @staticmethod
    def _json_object(raw: Any) -> dict[str, Any]:
        if isinstance(raw, Mapping):
            if isinstance(raw.get("content"), Mapping):
                return dict(raw["content"])
            if raw.get("capability_id") is not None:
                return dict(raw)
            raw = raw.get("content") or ""
        text = str(raw or "").strip()
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S | re.I)
        if fenced:
            text = fenced.group(1)
        elif not text.startswith("{"):
            match = re.search(r"\{.*\}", text, re.S)
            text = match.group(0) if match else ""
        value = json.loads(text)
        if not isinstance(value, dict):
            raise ValueError("people_action_plan_not_object")
        return value

    def _fallback_plan(self, instruction: str) -> dict[str, Any]:
        lower = instruction.casefold()
        fields: dict[str, Any] = {}
        capability_id = "none"
        if re.search(r"\b(?:create|add|onboard|register)\b.*\b(?:employee|person|contractor|worker|staff)\b", lower):
            capability_id = "people.create_person"
            fields["name"] = self._capture(instruction, r"\b(?:called|named)\s+(.+?)(?=\s*[,;]|\s+(?:whose|his|her|their|email|e-mail|mobile|phone|address|job|role|starts?)\b|$)")
            if not fields["name"]:
                fields["name"] = self._capture(instruction, r"\b(?:full\s+name|name)\s*:\s*(.+?)(?=\s+(?:email|e-mail|mobile|phone|address|job\s+title|role|start\s+date)\s*:|$)")
            if not fields["name"]:
                fields["name"] = self._capture(
                    instruction,
                    r"\b(?:employee|person|contractor|worker|staff(?:\s+member)?)\s+(?!called\b|named\b)(.+?)(?=\s*[,;]|\s+(?:whose|his|her|their|email|e-mail|mobile|phone|address|job|role|starts?)\b|$)",
                )
            if re.search(r"\bself[- ]employed(?:\s+(?:person|worker|contractor))?\b", lower):
                fields["employment_type"] = "self_employed"
            elif re.search(r"\b(?:contractor|subcontractor)\b", lower):
                fields["employment_type"] = "contractor"
            elif re.search(r"\bfreelancer\b", lower):
                fields["employment_type"] = "freelancer"
            else:
                fields["employment_type"] = "employee"
        elif re.search(r"\b(?:update|change|edit|correct|set)\b", lower) and (
            re.search(r"\b(?:employee|person|staff|record|details?)\b", lower)
            or self._is_profile_continuation(instruction)
        ):
            capability_id = "people.update_person"
            fields["person_name"] = self._capture(
                instruction,
                r"\b(?:hourly\s+(?:rate|pay)|pay\s+rate|base\s+rate|salary)\s+(?:of|for)\s+(.+?)(?=\s+(?:to|is|at|will\s+be)\b|\s*[,;]|$)",
            )
            if not fields["person_name"]:
                fields["person_name"] = self._capture(instruction, r"\b(?:for|employee|person|staff member)\s+(.+?)(?=\s*[,;]|\s+(?:whose|his|her|their|email|e-mail|mobile|phone|address|job|role|to|is)\b|$)")
            if not fields["person_name"]:
                fields["person_name"] = self._capture(
                    instruction,
                    r"\b(?:update|change|edit|correct)\s+(?:the\s+(?:employee|person|staff(?:\s+member)?)\s+)?(.+?)(?=\s+(?:whose|his|her|their|e-?mail|mobile|phone|telephone|address|job\s+title|position|role|relationship|line\s+manager|manager|department|start\s+date|employment\s+type|work\s+location|cost\s+cent(?:re|er)|next\s+appraisal|software\s+accounts?|onboarding|hourly\s+rate|pay\s+rate|salary|on.cost|bonus|commission|productive\s+hours|hours\s+per\s+(?:working\s+)?day|expense\s+approval)\b|\s*[,;]|$)",
                )
        elif re.search(r"\b(?:holiday|leave|time off|day off|absence|sick|sickness|unwell)\b", lower):
            capability_id = "people.record_leave_request"
            fields["person_name"] = self._capture(
                instruction,
                r"\b(?:for|employee|person|staff(?:\s+member)?)\s+(.+?)(?=\s*[,;]|\s+(?:down\s+as|as|needs?|is|will|has|on|from|for|to|taking|take)\b|$)",
            )
            if not fields["person_name"]:
                fields["person_name"] = self._capture(
                    instruction,
                    r"\b(?:mark|record|book)\s+(.+?)(?=\s+(?:down\s+as|as|on|for|off|sick|holiday|leave)\b|$)",
                )
            if not fields["person_name"]:
                fields["person_name"] = self._capture(
                    instruction,
                    r"^\s*(.+?)(?=\s+(?:is|will\s+be|was|has\s+been)\s+(?:off|on|taking|booked))",
                )
            date_texts = re.findall(r"\b\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+\d{4}\b|\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b", instruction, re.I)
            dates = [_normalise_date(value) for value in date_texts]
            dates = [value for value in dates if value]
            if dates:
                fields["start_date"] = dates[0]
                fields["end_date"] = dates[1] if len(dates) > 1 else dates[0]
            if re.search(r"\b(?:sick|sickness|ill|unwell)\b", lower):
                fields["leave_type"] = "Sick leave"
            elif re.search(r"\bunpaid\b", lower):
                fields["leave_type"] = "Unpaid leave"
            elif re.search(r"\b(?:paid\s+holiday|annual\s+leave|holiday)\b", lower):
                fields["leave_type"] = "Annual leave"
            else:
                fields["leave_type"] = "Other approved absence"
        if capability_id.startswith("people."):
            email = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", instruction, re.I)
            if email:
                fields["email"] = email.group(0).lower()
            phone = self._capture(instruction, r"\b(?:mobile|phone)(?:\s+number)?\s*(?:is|:)?\s*([+\d][\d ()-]{5,}\d)")
            address = self._capture(instruction, r"(?<!email )(?<!e-mail )\baddress\s*(?:is|:)?\s*(.+)$")
            if phone:
                fields["phone"] = phone
            if address:
                fields["address"] = address
            position = self._capture(instruction, r"\b(?:job\s+title|position|role)\s*(?:is|to|:)\s*(.+?)(?=\s*[,;]\s*(?:line\s+manager|manager|department|email|e-mail|mobile|phone|address|start\s+date)\b|\s+(?:email|e-mail|mobile|phone|address|start\s+date|line\s+manager|manager|department)\s*(?:is|to|:)|$)")
            if not position:
                position = self._capture(
                    instruction,
                    r"\b(?:he|she|they|the\s+person|the\s+employee|the\s+contractor)\s+(?:is|works?\s+as|will\s+be)\s+(?:an?\s+)?(.+?)(?=\s*[,;]|\s+and\s+(?:(?:will\s+)?reports?|works?|starts?|has|his|her|their)\b|$)",
                )
            if not position:
                subject = str(fields.get("name") or fields.get("person_name") or "").split()
                if subject:
                    position = self._capture(
                        instruction,
                        rf"\b{re.escape(subject[0])}\s+(?:is|works?\s+as|will\s+be)\s+(?:an?\s+)?(.+?)(?=\s*[,;]|\s+and\s+(?:(?:will\s+)?reports?|works?|starts?|has|his|her|their)\b|$)",
                    )
            if position:
                fields["position_title"] = position
            manager = self._capture(instruction, r"\b(?:line\s+manager|manager)\s*(?:is|to|:)\s*(.+?)(?=\s*[,;]|\s+(?:email|e-mail|mobile|phone|address|job|role|department|start\s+date)\b|$)")
            if not manager:
                manager = self._capture(
                    instruction,
                    r"\breports?\s+to\s+(.+?)(?=\s*[,;]|\s+and\s+(?:works?|starts?|has|his|her|their)\b|$)",
                )
            department = self._capture(instruction, r"\bdepartment\s*(?:is|to|:)\s*(.+?)(?=\s*[,;]|\s+(?:email|e-mail|mobile|phone|address|job|role|manager|start\s+date)\b|$)")
            if manager:
                fields["manager_name"] = manager
            if department:
                fields["department_name"] = department
            date_value = r"(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{4})"
            start_date = self._capture(
                instruction,
                rf"\b(?:start(?:ing)?(?:\s+date)?|first\s+day|begin(?:s|ning)?|commence(?:s|ment)?)\b(?:\s+(?:the\s+)?(?:job|work|employment))?\s*(?:is|will\s+be|will\s+be\s+on|on|to|:)?\s*(?:the\s+)?{date_value}",
            )
            if start_date:
                fields["start_date"] = start_date
            hourly_rate = self._capture(
                instruction,
                r"\b(?:hourly\s+(?:rate|pay)|pay\s+rate|rate|pay(?:\s+him|\s+her)?|earn(?:s|ing)?)\s*(?:is|will\s+be|to|at|of|:)?\s*(?:£|€|\$)?\s*(\d+(?:[.,]\d{1,2})?)\s*(?:(?:per|an|each|/)\s*(?:hour|hr)|hourly)?",
            )
            if not hourly_rate:
                hourly_rate = self._capture(
                    instruction,
                    r"\b(?:hourly\s+(?:rate|pay)|pay\s+rate|base\s+rate)\s+(?:of|for)\s+.+?\s+(?:is|to|at|will\s+be)\s*(?:£|€|\$)?\s*(\d+(?:[.,]\d{1,2})?)\s*(?:(?:per|an|each|/)\s*(?:hour|hr)|hourly)?\b",
                )
            if not hourly_rate:
                hourly_rate = self._capture(
                    instruction,
                    r"\bon\s*(?:£|€|\$)?\s*(\d+(?:[.,]\d{1,2})?)\s*(?:per|an|each|/)\s*(?:hour|hr)\b",
                )
            if hourly_rate:
                fields["workforce_costing_basis"] = "hourly"
                fields["workforce_costing_base_rate"] = hourly_rate
            relationship = self._capture(instruction, r"\b(?:relationship|employment\s+type)\s*(?:is|to|:)\s*(owner|employee|self[- ]employed(?:\s+person)?|contractor|freelancer|external\s+adviser)")
            if relationship:
                fields["employment_type"] = relationship.casefold().replace(" ", "_").replace("self-employed_person", "self_employed")
            work_location = self._capture(instruction, r"\bwork\s+location\s*(?:is|to|:)\s*(.+?)(?=\s*[,;]|$)")
            cost_center = self._capture(instruction, r"\bcost\s+cent(?:re|er)\s*(?:is|to|:)\s*(.+?)(?=\s*[,;]|$)")
            if work_location:
                fields["work_location"] = work_location
            if cost_center:
                fields["cost_center"] = cost_center
            next_appraisal = self._capture(
                instruction,
                r"\bnext\s+(?:appraisal|check[- ]?in)(?:\s+date)?\s*(?:is|will\s+be|to|:)?\s*(?:the\s+)?(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{4})",
            )
            if next_appraisal:
                fields["next_appraisal_date"] = next_appraisal
            software = self._capture(instruction, r"\bsoftware\s+accounts?\s*(?:are|is|include|:)?\s*(.+)$")
            if software:
                fields["software_accounts"] = software
            onboarding_terms = {
                "contract": r"\bcontract\s+signed\b",
                "identity": r"\b(?:identity|right.to.work)\b",
                "health_safety": r"\bhealth\s*(?:and|&)\s*safety\b",
                "handbook": r"\b(?:handbook|induction)\b",
                "payroll": r"\bpayroll\s+details?\b",
                "accounts": r"\bsoftware\s+accounts?\b",
                "equipment": r"\bequipment(?:\s+or\s+assets?)?\b",
            }
            completed = [key for key, pattern in onboarding_terms.items() if re.search(pattern, instruction, re.I) and re.search(r"\b(?:complete|completed|done|verified|signed|provided|issued|set up)\b", instruction, re.I)]
            if completed:
                fields["onboarding_completed"] = ",".join(completed)
            numeric_patterns = {
                "expense_approval_limit": r"\b(?:personal\s+)?expense\s+approval\s+limit\s*(?:is|to|:)?\s*(?:£|€|\$)?\s*(\d+(?:\.\d{1,2})?)",
                "workforce_costing_employer_on_cost_percent": r"\bemployer\s+on[- ]cost(?:\s+percent|\s*%)?\s*(?:is|to|:)?\s*(\d+(?:\.\d+)?)",
                "workforce_costing_monthly_bonus": r"\bmonthly\s+(?:bonus|allowance)\s*(?:is|to|:)?\s*(?:£|€|\$)?\s*(\d+(?:\.\d{1,2})?)",
                "workforce_costing_commission_percent": r"\bcommission(?:\s+percent|\s*%)?\s*(?:is|to|:)?\s*(\d+(?:\.\d+)?)",
                "workforce_costing_productive_hours_month": r"\bproductive\s+hours(?:\s+per\s+month|\/month)?\s*(?:is|are|to|:)?\s*(\d+(?:\.\d+)?)",
                "workforce_costing_hours_per_day": r"\bhours\s+per\s+(?:working\s+)?day\s*(?:is|are|to|:)?\s*(\d+(?:\.\d+)?)",
            }
            for key, pattern in numeric_patterns.items():
                value = self._capture(instruction, pattern)
                if value:
                    fields[key] = value
        return {"capability_id": capability_id, "confidence": 0.7 if capability_id != "none" else 0.0,
                "fields": fields, "missing_fields": [], "planner": {"source": "bounded_language_fallback"}}

    @staticmethod
    def _capture(text: str, pattern: str) -> str:
        match = re.search(pattern, text, re.I)
        return _clean(match.group(1), 300).strip(" ,.;") if match else ""

    @staticmethod
    def _validated_fields(capability: Mapping[str, Any], value: Any) -> dict[str, Any]:
        source = dict(value) if isinstance(value, Mapping) else {}
        aliases = {
            "full_name": "name",
            "employee_name": "person_name",
            "mobile": "phone",
            "mobile_number": "phone",
            "phone_number": "phone",
            "job_title": "position_title",
            "title": "position_title",
            "manager": "manager_name",
            "line_manager": "manager_name",
            "department": "department_name",
            "starting_date": "start_date",
            "first_day": "start_date",
            "appraisal_date": "next_appraisal_date",
            "cost_centre": "cost_center",
            "hourly_rate": "workforce_costing_base_rate",
            "base_rate": "workforce_costing_base_rate",
            "pay_basis": "workforce_costing_basis",
            "absence_type": "leave_type",
        }
        for alias, canonical in aliases.items():
            if alias in source and canonical not in source:
                source[canonical] = source[alias]
        if capability.get("id") == "people.create_person" and "person_name" in source and "name" not in source:
            source["name"] = source["person_name"]
        if capability.get("id") == "people.record_leave_request" and source.get("date"):
            source.setdefault("start_date", source["date"])
            source.setdefault("end_date", source["date"])
        allowed = set(capability["required"]) | set(capability["optional"])
        fields = {key: _clean(item, 600) for key, item in source.items() if key in allowed and item not in (None, "")}
        if "employment_type" in fields:
            relationship = fields["employment_type"].casefold().replace("-", "_").replace(" ", "_")
            relationship_aliases = {
                "owner_director": "owner",
                "self_employed_person": "self_employed",
                "self_employed_worker": "self_employed",
                "external_advisor": "external_adviser",
            }
            relationship = relationship_aliases.get(relationship, relationship)
            if relationship in _EMPLOYMENT_TYPES:
                fields["employment_type"] = relationship
            else:
                # Models occasionally classify an occupation (for example
                # "accountant" or "roofer") as the relationship.  Preserve
                # the useful fact as the job title, but never allow it to
                # corrupt the bounded relationship enum.
                fields.setdefault("position_title", fields["employment_type"])
                fields.pop("employment_type", None)
        for key in ("start_date", "end_date", "next_appraisal_date"):
            if key in fields:
                fields[key] = _normalise_date(fields[key])
        if "email" in fields:
            fields["email"] = fields["email"].casefold()
        numeric_fields = {
            "expense_approval_limit",
            "workforce_costing_base_rate",
            "workforce_costing_employer_on_cost_percent",
            "workforce_costing_monthly_bonus",
            "workforce_costing_commission_percent",
            "workforce_costing_productive_hours_month",
            "workforce_costing_hours_per_day",
        }
        for key in numeric_fields & fields.keys():
            fields[key] = re.sub(
                r"^\s*[£€$]\s*|\s*%\s*$",
                "",
                fields[key].replace(",", "."),
            )
            if not re.fullmatch(r"-?\d+(?:\.\d+)?", fields[key]):
                fields.pop(key, None)
        if "workforce_costing_base_rate" in fields and "workforce_costing_basis" not in fields:
            fields["workforce_costing_basis"] = "hourly"
        return fields

    def _authorised_actor(self, model: Mapping[str, Any], person_id: str, capability: str) -> dict[str, Any] | None:
        people = [dict(item) for item in model.get("people") or [] if isinstance(item, Mapping) and item.get("status") == "active"]
        direct = next((item for item in people if item.get("id") == person_id), None)
        if direct and self.authority.access_decision(model["workspace_id"], person_id=person_id, capability=capability).get("allowed"):
            return direct
        if person_id == "desktop_user":
            owners = [item for item in people if "role.owner_director" in set(item.get("role_ids") or [])]
            if len(owners) == 1:
                return owners[0]
        return None

    def _apply(self, capability_id: str, model: dict[str, Any], fields: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
        people = model.setdefault("people", [])
        if capability_id == "people.create_person":
            duplicate = self._match_person(people, fields["name"])
            if duplicate:
                return False, f"{duplicate['name']} already exists. Tell me which details you want changed instead.", {"status": "duplicate_person", "person_id": duplicate.get("id")}
            person = {
                "id": f"person.{re.sub(r'[^a-z0-9]+', '-', fields['name'].casefold()).strip('-')}.{uuid4().hex[:8]}",
                "name": fields["name"], "email": fields.get("email", ""), "phone": fields.get("phone", ""),
                "address": fields.get("address", ""), "employment_type": fields.get("employment_type", "employee"),
                "position_title": fields.get("position_title", ""), "status": "active", "manager_id": None,
                "department_ids": [], "role_ids": ["role.employee"], "start_date": fields.get("start_date", ""),
                "work_location": fields.get("work_location", ""), "cost_center": fields.get("cost_center", ""),
                "next_appraisal_date": fields.get("next_appraisal_date", ""),
                "software_accounts": [item.strip() for item in fields.get("software_accounts", "").split(",") if item.strip()],
                "expense_approval_limit": float(fields["expense_approval_limit"]) if fields.get("expense_approval_limit") else None,
                "onboarding": {"checks": {key: True for key in fields.get("onboarding_completed", "").split(",") if key}},
                "workforce_costing": {
                    "basis": fields.get("workforce_costing_basis", "hourly"),
                    "base_rate": float(fields.get("workforce_costing_base_rate") or 0),
                    "employer_on_cost_percent": float(fields.get("workforce_costing_employer_on_cost_percent") or 0),
                    "monthly_bonus": float(fields.get("workforce_costing_monthly_bonus") or 0),
                    "commission_percent": float(fields.get("workforce_costing_commission_percent") or 0),
                    "productive_hours_month": float(fields.get("workforce_costing_productive_hours_month") or 140),
                    "hours_per_day": float(fields.get("workforce_costing_hours_per_day") or 8),
                },
            }
            if person["employment_type"] in {"contractor", "self_employed", "freelancer"}:
                person["role_ids"] = ["role.self_employed_contractor"]
            self._resolve_relationships(model, person, fields)
            people.append(person)
            missing = [label for key, label in (("email", "work email"), ("position_title", "job title"), ("manager_id", "line manager"), ("department_ids", "department")) if not person.get(key)]
            suffix = (
                f" Still needed: {', '.join(missing)}. Send those details in your next messages and I will keep updating {person['name']}."
                if missing else ""
            )
            return True, f"I added {person['name']} to the People directory as an {person['employment_type'].replace('_', ' ')}.{suffix} No accounts or notifications were created.", {"status": "person_created", "person_id": person["id"], "missing_fields": missing}

        person = self._match_person(people, fields.get("person_name", ""))
        if not person:
            return False, f"I could not find one active person matching “{fields.get('person_name', '')}”. Tell me the exact name shown in the People directory.", {"status": "person_not_found"}

        if capability_id == "people.update_person":
            changed_fields = []
            for key in ("email", "phone", "address", "employment_type", "position_title", "start_date", "next_appraisal_date", "work_location", "cost_center", "status"):
                if fields.get(key) and person.get(key) != fields[key]:
                    person[key] = fields[key]
                    changed_fields.append(key)
            if fields.get("employment_type"):
                role_ids = (
                    ["role.self_employed_contractor"]
                    if fields["employment_type"] in {"contractor", "self_employed", "freelancer"}
                    else ["role.employee"]
                )
                if list(person.get("role_ids") or []) != role_ids:
                    person["role_ids"] = role_ids
                    changed_fields.append("role_ids")
            costing_field_map = {
                "workforce_costing_base_rate": "base_rate",
                "workforce_costing_employer_on_cost_percent": "employer_on_cost_percent",
                "workforce_costing_monthly_bonus": "monthly_bonus",
                "workforce_costing_commission_percent": "commission_percent",
                "workforce_costing_productive_hours_month": "productive_hours_month",
                "workforce_costing_hours_per_day": "hours_per_day",
            }
            if any(fields.get(key) for key in costing_field_map):
                costing = dict(person.get("workforce_costing") or {})
                basis = fields.get("workforce_costing_basis") or costing.get("basis") or "hourly"
                updates = {target: float(fields[source]) for source, target in costing_field_map.items() if fields.get(source)}
                if costing.get("basis") != basis or any(float(costing.get(key) or 0) != value for key, value in updates.items()):
                    costing.update({"basis": basis, **updates})
                    person["workforce_costing"] = costing
                    changed_fields.append("workforce_costing")
            if fields.get("expense_approval_limit"):
                limit = float(fields["expense_approval_limit"])
                if person.get("expense_approval_limit") != limit:
                    person["expense_approval_limit"] = limit
                    changed_fields.append("expense_approval_limit")
            if fields.get("software_accounts"):
                accounts = [item.strip() for item in re.split(r"[,;\n]", fields["software_accounts"]) if item.strip()]
                if accounts != list(person.get("software_accounts") or []):
                    person["software_accounts"] = accounts
                    changed_fields.append("software_accounts")
            if fields.get("onboarding_completed"):
                onboarding = dict(person.get("onboarding") or {})
                checks = dict(onboarding.get("checks") or {})
                completed = [item for item in fields["onboarding_completed"].split(",") if item]
                if any(not checks.get(item) for item in completed):
                    checks.update({item: True for item in completed})
                    onboarding.update({"checks": checks, "updated_at": datetime.now(UTC).replace(microsecond=0).isoformat()})
                    person["onboarding"] = onboarding
                    changed_fields.append("onboarding")
            self._resolve_relationships(model, person, fields, changed_fields)
            if not changed_fields:
                return False, f"I found {person['name']}, but the instruction did not contain a new value to save. Tell me exactly what should change.", {"status": "no_change_supplied", "person_id": person.get("id")}
            labels = ", ".join(item.replace("_", " ") for item in changed_fields)
            return True, f"I updated {labels} for {person['name']} in the People record. No external notification was sent.", {"status": "person_updated", "person_id": person["id"], "changed_fields": changed_fields}

        leave = {
            "id": f"leave.{uuid4().hex}", "person_id": person["id"],
            "leave_type": fields.get("leave_type") or "Annual leave",
            "start_date": fields["start_date"], "end_date": fields["end_date"],
            "cover_owner": fields.get("cover_owner", ""), "status": "requested",
            "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "updated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "source": "people_pilot_delegation",
        }
        operations = model.setdefault("people_operations", {})
        operations.setdefault("leave_requests", []).append(leave)
        return True, (
            f"I recorded a leave request for {person['name']} from {leave['start_date']} to {leave['end_date']}. "
            "It is waiting for an authorised human decision; I did not notify the line manager or alter an external calendar."
        ), {"status": "leave_request_recorded", "person_id": person["id"], "leave_request_id": leave["id"], "human_decision_required": True}

    @staticmethod
    def _match_person(people: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
        target = _clean(name).casefold()
        if not target:
            return None
        exact = [item for item in people if _clean(item.get("name")).casefold() == target and item.get("status", "active") == "active"]
        if len(exact) == 1:
            return exact[0]
        partial = [item for item in people if target in _clean(item.get("name")).casefold() and item.get("status", "active") == "active"]
        return partial[0] if len(partial) == 1 else None

    def _resolve_relationships(self, model: Mapping[str, Any], person: dict[str, Any], fields: Mapping[str, Any], changed: list[str] | None = None) -> None:
        if fields.get("manager_name"):
            manager = self._match_person(list(model.get("people") or []), str(fields["manager_name"]))
            if manager and manager.get("id") != person.get("id"):
                person["manager_id"] = manager["id"]
                if changed is not None:
                    changed.append("manager_id")
        if fields.get("department_name"):
            target = _clean(fields["department_name"]).casefold()
            department = next((item for item in model.get("departments") or [] if _clean(item.get("name")).casefold() == target), None)
            if department:
                person["department_ids"] = [department["id"]]
                if changed is not None:
                    changed.append("department_ids")

    @staticmethod
    def _missing_message(capability_id: str, missing: list[str]) -> str:
        labels = {"name": "the person’s full name", "person_name": "the exact name in the People directory",
                  "start_date": "the first day", "end_date": "the final day"}
        readable = [labels.get(item, item.replace("_", " ")) for item in missing]
        return f"I can do that, but I still need {', '.join(readable)}. I have not changed the People records yet."
