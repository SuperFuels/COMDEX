"""Model-led conversation and safe tool orchestration for every Department Pilot.

The language model decides what the user is asking for from a department-scoped
tool catalogue. Tessaris, not the model, validates and executes the selected
tool. Safe internal work may run immediately; publishing, spend, customer
contact and external writes are only ever returned as approval-gated proposals.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
import re
from typing import Any, Mapping
from uuid import uuid4

from backend.modules.aion_business.providers.router import ProviderRouter
from backend.modules.aion_business.runtime.business_container_repository import (
    BusinessContainerRepository,
)
from backend.modules.aion_business.runtime.marketing_creative_engine import (
    MarketingCreativeEngine,
)


DEPARTMENT_CONVERSATION_PROFILES: dict[str, dict[str, Any]] = {
    "marketing": {
        "label": "Marketing",
        "remit": "campaigns, audiences, brand, content, channels and attributable results",
        "tools": [
            {
                "name": "marketing.create_content_plan",
                "description": "Create reviewable campaign or content drafts for one or more channels.",
                "authority": "safe_internal",
                "arguments": {
                    "brief": "string", "content_count": "integer 1-12",
                    "platforms": "array of instagram_feed, facebook_feed, linkedin_feed, tiktok, youtube_shorts, google_business",
                    "formats": "array of image, carousel, video or clip",
                    "audience": "string", "objective": "string", "offer": "string",
                    "tone": "string", "call_to_action": "string",
                },
            },
            {"name": "marketing.read_campaign_results", "description": "Read recorded campaign performance and evidence.", "authority": "read_only"},
            {"name": "marketing.prepare_publication", "description": "Prepare a post, schedule or paid campaign for explicit approval.", "authority": "approval_required"},
        ],
    },
    "sales": {
        "label": "Sales", "remit": "leads, pipeline, qualification, quotes, follow-up and revenue",
        "tools": [
            {"name": "sales.read_pipeline", "description": "Read current pipeline, contacts and recorded outcomes.", "authority": "read_only"},
            {"name": "sales.prepare_follow_up", "description": "Draft a customer follow-up without sending it.", "authority": "safe_internal"},
            {"name": "sales.contact_customer", "description": "Send or schedule customer contact.", "authority": "approval_required"},
        ],
    },
    "support": {
        "label": "Support", "remit": "cases, customer history, policy, replies, complaints and escalation",
        "tools": [
            {"name": "support.read_cases", "description": "Read recorded support cases and customer timelines.", "authority": "read_only"},
            {"name": "support.draft_response", "description": "Draft a policy-grounded response without sending it.", "authority": "safe_internal"},
            {"name": "support.send_response", "description": "Send a customer response or make an external change.", "authority": "approval_required"},
        ],
    },
    "operations": {
        "label": "Operations", "remit": "delivery, schedules, capacity, suppliers, workflow and operating risk",
        "tools": [
            {"name": "operations.read_status", "description": "Read schedules, capacity, operational work and risks.", "authority": "read_only"},
            {"name": "operations.prepare_work", "description": "Prepare internal work or a cross-department request.", "authority": "safe_internal"},
            {"name": "operations.external_change", "description": "Change a supplier, booking or external system.", "authority": "approval_required"},
        ],
    },
    "people": {
        "label": "People", "remit": "people records, roles, capacity, policies, hiring and training",
        "tools": [
            {"name": "people.read_directory", "description": "Read authorised People and organisation records.", "authority": "read_only"},
            {"name": "people.prepare_record_change", "description": "Prepare an internal People-record change for validation.", "authority": "safe_internal"},
            {"name": "people.external_or_sensitive_action", "description": "Perform a sensitive or external People action.", "authority": "approval_required"},
        ],
    },
    "products_services": {
        "label": "Products & Services", "remit": "offers, pricing, specifications, delivery models and product decisions",
        "tools": [
            {"name": "products.read_catalogue", "description": "Read recorded products, services, prices and evidence.", "authority": "read_only"},
            {"name": "products.prepare_update", "description": "Prepare a catalogue, offer or pricing update.", "authority": "safe_internal"},
            {"name": "products.publish_update", "description": "Publish a price or offer externally.", "authority": "approval_required"},
        ],
    },
}


class DepartmentPilotConversationService:
    """Convert a normal conversation into governed Department Pilot work."""

    def __init__(
        self,
        *,
        container_repository: BusinessContainerRepository | None = None,
        provider_router: ProviderRouter | None = None,
        marketing_engine: MarketingCreativeEngine | None = None,
    ) -> None:
        self.containers = container_repository or BusinessContainerRepository()
        self.providers = provider_router or ProviderRouter()
        self.marketing = marketing_engine or MarketingCreativeEngine()

    def answer(
        self,
        workspace_id: str,
        department_id: str,
        user_text: str,
        *,
        recent: list[Mapping[str, Any]] | None = None,
        preferred_provider: str | None = None,
        preferred_model: str | None = None,
    ) -> dict[str, Any]:
        department = self._normalise_department(department_id)
        question = " ".join(str(user_text or "").split())[:4_000]
        if not question:
            raise ValueError("department_pilot_question_required")
        profile = DEPARTMENT_CONVERSATION_PROFILES[department]
        context, evidence = self._context(workspace_id, department)
        result = self.providers.generate(
            prompt=json.dumps({
                "user_request": question,
                "recent_conversation": [
                    {"role": item.get("role"), "content": str(item.get("content") or "")[:800]}
                    for item in (recent or [])[-6:]
                ],
                "department_context": context,
                "available_tools": profile["tools"],
            }, ensure_ascii=False, default=str),
            system_prompt=self._system_prompt(profile),
            preferred_provider=preferred_provider,
            preferred_model=preferred_model,
            capability="drafting",
            metadata={"workspace_id": workspace_id, "department_id": department, "tool_selection": True},
            max_tokens=1_400,
        )
        envelope = self._parse_envelope(result.content if result.ok else "")
        tool_results, approvals = self._execute_tools(workspace_id, department, envelope.get("tool_calls"))
        message = str(envelope.get("message") or "").strip()
        if not message:
            message = (
                f"I do not have enough recorded {profile['label']} evidence to answer that reliably. No action was taken."
                if not evidence
                else self._failure_message(profile, result.error_code)
            )
        if tool_results:
            message = self._describe_completed_work(message, tool_results)
        if approvals:
            message += "\n\nI prepared the requested external action for review. Nothing has been published, sent or spent."
        return {
            "conversation_id": f"department-pilot-{department}-{workspace_id}",
            "department_id": department,
            "turn": {
                "turn_id": f"department-turn-{uuid4().hex}", "role": "assistant",
                "content": message, "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
            },
            "provider": {
                "provider": result.provider, "model": result.model,
                "fallback_used": result.fallback_used, "error_code": result.error_code,
            },
            "intent": envelope.get("intent") or "conversation",
            "evidence": evidence,
            "reliability": "model_with_workspace_context" if evidence else "insufficient_evidence",
            "tool_results": tool_results,
            "approval_requests": approvals,
            "external_writes_performed": False,
            "approval_gated": True,
        }

    @staticmethod
    def _normalise_department(value: str) -> str:
        aliases = {"hr": "people", "product": "products_services", "products": "products_services"}
        key = aliases.get(str(value or "").strip().casefold(), str(value or "").strip().casefold())
        if key not in DEPARTMENT_CONVERSATION_PROFILES:
            raise ValueError(f"unsupported_department_pilot:{key}")
        return key

    @staticmethod
    def _system_prompt(profile: Mapping[str, Any]) -> str:
        return (
            f"You are the {profile['label']} Pilot. Your remit is {profile['remit']}. "
            "Understand the user's natural language; do not match canned phrases. Use only supplied business context. "
            "Choose tools only from available_tools. Never claim a tool ran unless Tessaris returns a result. "
            "External publishing, sending, spending, deletion and third-party writes must remain approval_required. "
            "If facts are missing, ask one useful question. Return JSON only with this shape: "
            '{"message":"natural reply","intent":"answer|analyse|create|update|schedule",'
            '"tool_calls":[{"name":"registered tool name","arguments":{}}]}. '
            "The message should explain what you understood and what will be produced, not expose internal implementation details."
        )

    def _context(self, workspace_id: str, department: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        kinds = [
            "business_identity",
            "business_map",
            "department_intelligence",
            "business_operating_model",
            "operational_runtime_summary",
            "boardroom_snapshot",
        ]
        if department in {"marketing", "sales", "products_services"}:
            kinds.append("brand_foundation")
        if department in {"sales", "operations"}:
            kinds.append("business_financial_model")
        if department == "people":
            kinds.append("organization_authority")
        context: dict[str, Any] = {}
        evidence: list[dict[str, Any]] = []
        for kind in kinds:
            record = self.containers.load_optional_dict(workspace_id, kind)  # type: ignore[arg-type]
            if not record:
                continue
            context[kind] = self._bound(record)
            evidence.append({"source": kind, "revision": record.get("revision"), "verification_state": "workspace_record"})
        return context, evidence

    @classmethod
    def _bound(cls, value: Any, *, depth: int = 0) -> Any:
        if depth > 4:
            return "[bounded]"
        if isinstance(value, Mapping):
            return {str(key): cls._bound(item, depth=depth + 1) for key, item in list(value.items())[:40]}
        if isinstance(value, list):
            return [cls._bound(item, depth=depth + 1) for item in value[:20]]
        if isinstance(value, str):
            return value[:1_500]
        return value

    @staticmethod
    def _parse_envelope(raw: str) -> dict[str, Any]:
        text = str(raw or "").strip()
        candidates = [text]
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
        if fenced:
            candidates.insert(0, fenced.group(1))
        first, last = text.find("{"), text.rfind("}")
        if first >= 0 and last > first:
            candidates.append(text[first:last + 1])
        for candidate in candidates:
            try:
                value = json.loads(candidate)
                if isinstance(value, dict):
                    value["tool_calls"] = value.get("tool_calls") if isinstance(value.get("tool_calls"), list) else []
                    return value
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        return {"message": text, "intent": "conversation", "tool_calls": []}

    def _execute_tools(self, workspace_id: str, department: str, calls: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        catalog = {item["name"]: item for item in DEPARTMENT_CONVERSATION_PROFILES[department]["tools"]}
        completed: list[dict[str, Any]] = []
        approvals: list[dict[str, Any]] = []
        for call in list(calls or [])[:8]:
            if not isinstance(call, Mapping):
                continue
            name = str(call.get("name") or "")
            tool = catalog.get(name)
            if not tool:
                continue
            arguments = dict(call.get("arguments") or {}) if isinstance(call.get("arguments"), Mapping) else {}
            if tool["authority"] == "approval_required":
                approvals.append({"tool": name, "arguments": arguments, "status": "awaiting_approval"})
                continue
            if name == "marketing.create_content_plan":
                completed.append(self._create_marketing_plan(workspace_id, arguments))
            else:
                completed.append({"tool": name, "status": "context_ready", "arguments": arguments})
        return completed, approvals

    def _create_marketing_plan(self, workspace_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
        count = max(1, min(int(arguments.get("content_count") or 3), 12))
        platforms = [str(item) for item in arguments.get("platforms") or ["instagram_feed", "facebook_feed", "linkedin_feed"]]
        formats = [str(item) for item in arguments.get("formats") or ["image"]]
        plan = self.marketing.build_plan({
            "brief": arguments.get("brief") or "Create useful content from the approved business and brand context.",
            "objective": arguments.get("objective") or "Generate qualified interest",
            "audience": arguments.get("audience") or "Priority customer",
            "offer": arguments.get("offer") or "Approved business offer",
            "tone": arguments.get("tone") or "Clear, credible and human",
            "call_to_action": arguments.get("call_to_action") or "Take the next approved step",
            "platforms": platforms, "formats": formats, "variant_count": min(4, max(2, count)),
        })
        plan["campaign_schedule"] = list(plan.get("campaign_schedule") or [])[:count]
        plan["requested_content_count"] = count
        runtime = self.containers.load_optional_dict(workspace_id, "operational_runtime_summary") or {}
        artifacts = list(runtime.get("department_pilot_artifacts") or [])
        artifact = {
            "id": plan["id"], "department_id": "marketing", "type": "content_plan",
            "title": f"{count}-piece content plan", "status": "ready_for_review",
            "created_at": plan["created_at"], "payload": plan,
        }
        artifacts.append(artifact)
        runtime["department_pilot_artifacts"] = artifacts[-100:]
        self.containers.save_dict(workspace_id, "operational_runtime_summary", runtime)
        return {"tool": "marketing.create_content_plan", "status": "completed", "artifact": artifact}

    @staticmethod
    def _describe_completed_work(message: str, results: list[dict[str, Any]]) -> str:
        marketing = next((item for item in results if item.get("tool") == "marketing.create_content_plan"), None)
        if marketing:
            artifact = marketing.get("artifact") or {}
            count = (artifact.get("payload") or {}).get("requested_content_count") or 0
            return f"{message}\n\nI created {count} content item{'s' if count != 1 else ''} as a reviewable Marketing plan. It is saved as internal work; nothing has been published or scheduled."
        return message

    @staticmethod
    def _failure_message(profile: Mapping[str, Any], error_code: str | None) -> str:
        detail = f" ({error_code})" if error_code else ""
        return (
            f"I understood this as a {profile['label']} request, but the selected model could not prepare a reliable response{detail}. "
            "No action was taken. Check the selected model connection and try again."
        )
