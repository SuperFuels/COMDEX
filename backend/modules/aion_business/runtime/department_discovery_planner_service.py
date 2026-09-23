"""Provider-generated, canonical-context discovery questions for Department Pilots."""

from __future__ import annotations

import json
import re
from typing import Any

from backend.modules.aion_business.contracts.department_pilot import canonical_contract_hash
from backend.modules.aion_business.providers.router import ProviderRouter
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository


_DEPARTMENTS = {"marketing", "sales", "finance", "operations", "support", "hr"}
_TARGETS = _DEPARTMENTS | {"products_services", "boardroom"}
_ANSWER_TYPES = {"text", "money", "money_rate", "percent", "date", "choice"}


def _rows(value: Any, limit: int = 30) -> list[dict[str, Any]]:
    return [dict(item) for item in list(value or [])[:limit] if isinstance(item, dict)]


def _strings(value: Any) -> list[str]:
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                result.append(item.strip())
            elif isinstance(item, dict):
                text = item.get("question") or item.get("description") or item.get("field") or item.get("reason")
                if text:
                    result.append(str(text).strip())
        return result
    return []


def _parse_json(content: str) -> dict[str, Any] | None:
    raw = str(content or "").strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
    if fenced:
        raw = fenced.group(1).strip()
    try:
        value = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


class DepartmentDiscoveryPlannerService:
    """Ask a real Department Pilot for one missing fact; never use a fixed questionnaire."""

    def __init__(
        self,
        *,
        container_repository: BusinessContainerRepository | None = None,
        provider_router: ProviderRouter | None = None,
    ) -> None:
        self.containers = container_repository or BusinessContainerRepository()
        self.provider_router = provider_router or ProviderRouter()

    def next_question(
        self,
        workspace_id: str,
        department_id: str,
        *,
        resolved_field_keys: list[str] | None = None,
        skipped_field_keys: list[str] | None = None,
        recent_questions: list[str] | None = None,
        preferred_provider: str | None = None,
        preferred_model: str | None = None,
    ) -> dict[str, Any]:
        department = str(department_id or "").strip().lower()
        if department not in _DEPARTMENTS:
            raise ValueError("unsupported_discovery_department")
        context, gaps = self._context(workspace_id, department)
        resolved = [str(item) for item in (resolved_field_keys or []) if str(item).strip()]
        skipped = [str(item) for item in (skipped_field_keys or []) if str(item).strip()]
        recent = [str(item)[:500] for item in (recent_questions or [])[-12:] if str(item).strip()]

        system = (
            f"You are the {department.title()} Pilot for one real business. Generate exactly one discovery "
            "question only when material information is genuinely missing or ambiguous in the supplied canonical records. "
            "The business may be in any industry. Never use a generic fixed questionnaire, never invent a number, never "
            "ask for a fact already present, and never confuse customer selling prices with internal costs. Prefer explicit "
            "Boardroom or departmental gaps. Avoid recently asked or skipped fields unless they are an essential blocker. "
            "Return JSON only with: status ('question' or 'complete'), question, field_key, target_workspace, target_section, "
            "target_label, answer_type, rationale, evidence_checked. If no worthwhile gap remains, return status='complete' "
            "and an empty question. Ask one concise, business-specific question, not a compound checklist."
        )
        prompt = json.dumps(
            {
                "department": department,
                "canonical_business_context": context,
                "recorded_missing_information": gaps,
                "resolved_field_keys": resolved,
                "skipped_field_keys": skipped,
                "recent_questions": recent,
            },
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
        result = self.provider_router.generate(
            prompt=prompt,
            system_prompt=system,
            preferred_provider=preferred_provider,
            preferred_model=preferred_model,
            capability="reasoning",
            role_type=department.upper(),
            metadata={
                "workspace_id": workspace_id,
                "department_id": department,
                "operation": "discovery_question_planning",
                "read_only": True,
            },
            max_tokens=600,
        )
        parsed = _parse_json(result.content) if result.ok else None
        plan = self._validated_plan(parsed, department, context)
        if result.ok and parsed and plan is None:
            repair_prompt = json.dumps(
                {
                    "rejected_proposal": parsed,
                    "rejection_reason": "The proposed question overlaps a fact already present in canonical_business_context.",
                    "instruction": "Generate a different single question for a genuinely absent or ambiguous material fact. Return the same JSON schema only.",
                    "canonical_business_context": context,
                    "recorded_missing_information": gaps,
                    "resolved_field_keys": resolved,
                    "skipped_field_keys": skipped,
                    "recent_questions": recent,
                },
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
            repaired = self.provider_router.generate(
                prompt=repair_prompt,
                system_prompt=system,
                preferred_provider=preferred_provider,
                preferred_model=preferred_model,
                capability="reasoning",
                role_type=department.upper(),
                metadata={
                    "workspace_id": workspace_id,
                    "department_id": department,
                    "operation": "discovery_question_repair",
                    "read_only": True,
                },
                max_tokens=600,
            )
            repaired_parsed = _parse_json(repaired.content) if repaired.ok else None
            repaired_plan = self._validated_plan(repaired_parsed, department, context)
            if repaired_plan is not None:
                result = repaired
                plan = repaired_plan
        if plan is None:
            plan = self._recorded_gap_fallback(gaps, department, skipped)
            source = "recorded_gap_fallback"
        else:
            source = "department_pilot_provider"

        payload = {
            "schema_version": "aion.department_discovery_question.v1",
            "workspace_id": workspace_id,
            "department_id": department,
            **plan,
            "source": source,
            "provider": result.provider if result.ok else None,
            "model": result.model if result.ok else None,
            "provider_error": None if result.ok else result.error_code,
            "canonical_context_hash": canonical_contract_hash(context),
            "external_writes_performed": False,
            "approval_gated": True,
        }
        payload["question_hash"] = canonical_contract_hash(payload)
        return payload

    def _context(self, workspace_id: str, department: str) -> tuple[dict[str, Any], list[str]]:
        records = {
            kind: self.containers.load_optional_dict(workspace_id, kind) or {}
            for kind in (
                "business_identity", "business_structure", "business_map",
                "business_financial_model", "business_operating_model", "department_intelligence",
            )
        }
        operating = records["business_operating_model"]
        financial = records["business_financial_model"]
        business_map = records["business_map"]
        intelligence = records["department_intelligence"]
        department_record = (intelligence.get("departments") or {}).get(department) or {}
        context = {
            "business_identity": records["business_identity"],
            "business_structure": records["business_structure"],
            "business_map": business_map,
            "financial_model": {
                "currency": financial.get("currency"),
                "metrics": financial.get("metrics") or {},
                "revenue_model": financial.get("revenue_model") or {},
                "direct_cost_model": financial.get("direct_cost_model") or {},
                "overhead_model": financial.get("overhead_model") or {},
                "cashflow_model": financial.get("cashflow_model") or {},
                "missing_information": financial.get("missing_information") or [],
                "assumptions": financial.get("assumptions") or [],
                "conflicts": financial.get("conflicts") or [],
            },
            "operating_model": {
                "currency": operating.get("currency"),
                "offerings": _rows(operating.get("offerings")),
                "labour_resources": _rows(operating.get("labour_resources")),
                "jobs": _rows(operating.get("jobs")),
                "job_economics": _rows(operating.get("job_economics")),
                "job_cost_items": _rows(operating.get("job_cost_items")),
                "bills_of_materials": _rows(operating.get("bills_of_materials")),
                "inventory_items": _rows(operating.get("inventory_items")),
                "payment_terms": _rows(operating.get("payment_terms")),
                "overheads": _rows(operating.get("overheads")),
                "financial_targets": _rows(operating.get("financial_targets")),
                "unit_economics": _rows(operating.get("unit_economics")),
                "provenance": operating.get("provenance") or {},
            },
            "department_intelligence": department_record,
        }
        gaps: list[str] = []
        if department == "finance":
            gaps.extend(_strings(financial.get("missing_information")))
        for value in (
            business_map.get("unknowns"), business_map.get("unanswered_fields"),
            business_map.get("department_discovery_gaps"), department_record.get("missing_information"),
            department_record.get("discovery_gaps"), department_record.get("unanswered_questions"),
        ):
            gaps.extend(_strings(value))
        unique = list(dict.fromkeys(item for item in gaps if item))
        return context, unique[:40]

    @staticmethod
    def _known_fact_descriptors(context: dict[str, Any]) -> list[str]:
        operating = context.get("operating_model") or {}
        descriptors: list[str] = []
        for row in operating.get("labour_resources") or []:
            if row.get("cost_rate") not in (None, ""):
                descriptors.append(
                    f"{row.get('person_name') or 'workforce'} {row.get('cost_basis') or ''} labour cost rate {row.get('cost_rate')}"
                )
        for row in operating.get("offerings") or []:
            if row.get("price") not in (None, ""):
                descriptors.append(f"offering {row.get('name') or ''} customer selling price {row.get('price')}")
            if row.get("direct_cost_per_unit") not in (None, ""):
                descriptors.append(f"offering {row.get('name') or ''} direct delivery cost {row.get('direct_cost_per_unit')}")
        metrics = (context.get("financial_model") or {}).get("metrics") or {}
        descriptors.extend(f"financial metric {key} {value}" for key, value in metrics.items() if value not in (None, ""))
        return descriptors

    @classmethod
    def _overlaps_known_fact(cls, value: dict[str, Any], context: dict[str, Any]) -> bool:
        stop = {
            "the", "a", "an", "is", "are", "for", "used", "internal", "effective",
            "confirm", "confirmed", "recorded", "current", "business", "planning", "owner",
        }
        subject = f"{value.get('field_key') or ''} {value.get('question') or ''}".lower()
        subject_tokens = {
            token for token in re.findall(r"[a-z0-9]+", subject)
            if len(token) > 2 and token not in stop
        }
        for descriptor in cls._known_fact_descriptors(context):
            descriptor_tokens = {
                token for token in re.findall(r"[a-z0-9]+", descriptor.lower())
                if len(token) > 2 and token not in stop
            }
            meaningful_overlap = subject_tokens & descriptor_tokens
            if len(meaningful_overlap) >= 3:
                return True
        return False

    @classmethod
    def _validated_plan(cls, value: dict[str, Any] | None, department: str, context: dict[str, Any]) -> dict[str, Any] | None:
        if not value:
            return None
        status = str(value.get("status") or "").lower()
        if status == "complete":
            return {"status": "complete", "question": "", "rationale": str(value.get("rationale") or "No material discovery gap remains.")}
        question = " ".join(str(value.get("question") or "").split())
        if status != "question" or len(question) < 8 or len(question) > 600:
            return None
        if cls._overlaps_known_fact(value, context):
            return None
        if not question.endswith("?"):
            question += "?"
        field = re.sub(r"[^a-z0-9_]+", "_", str(value.get("field_key") or "generated_discovery_gap").lower()).strip("_")
        target = str(value.get("target_workspace") or department).lower()
        if target not in _TARGETS:
            target = department
        answer_type = str(value.get("answer_type") or "text").lower()
        if answer_type not in _ANSWER_TYPES:
            answer_type = "text"
        return {
            "status": "question",
            "question": question,
            "field_key": field or "generated_discovery_gap",
            "target_workspace": target,
            "target_section": re.sub(r"[^a-z0-9_]+", "_", str(value.get("target_section") or "discovery").lower()).strip("_") or "discovery",
            "target_label": str(value.get("target_label") or f"{target.replace('_', ' ').title()} · Discovery")[:160],
            "answer_type": answer_type,
            "rationale": str(value.get("rationale") or "Material information is missing from canonical records.")[:500],
            "evidence_checked": list(value.get("evidence_checked") or [])[:20],
        }

    @staticmethod
    def _recorded_gap_fallback(gaps: list[str], department: str, skipped: list[str]) -> dict[str, Any]:
        skipped_lower = {item.lower() for item in skipped}
        gap = next((item for item in gaps if item.lower() not in skipped_lower), "")
        if not gap:
            return {"status": "complete", "question": "", "rationale": "No recorded missing-information item remains; provider generation was unavailable."}
        question = gap if gap.rstrip().endswith("?") else f"Please provide the missing information recorded as “{gap}”?"
        return {
            "status": "question",
            "question": question,
            "field_key": re.sub(r"[^a-z0-9_]+", "_", gap.lower()).strip("_")[:80] or "recorded_gap",
            "target_workspace": department,
            "target_section": "discovery",
            "target_label": f"{department.title()} · Discovery",
            "answer_type": "text",
            "rationale": "This question comes from a recorded canonical missing-information item.",
            "evidence_checked": ["recorded_missing_information"],
        }
