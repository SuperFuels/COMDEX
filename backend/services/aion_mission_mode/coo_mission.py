"""Bounded, proposal-only COO mission preparation and model routing."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Callable, Mapping
from uuid import uuid4

from backend.modules.aion_fabric.canonical import utc_now_iso
from backend.services.aion_mission_mode.department_capability_map import get_department_capabilities
from backend.services.aion_mission_mode.department_execution_queue import create_department_queue_item


DEPARTMENTS = ("finance", "sales", "marketing", "operations", "support", "people", "products_services")
FORBIDDEN_KEYS = {
    "execute_now", "send_now", "publish_now", "pay_now", "book_now",
    "api_key", "secret", "password", "access_token", "refresh_token",
    "chain_of_thought", "hidden_reasoning", "private_reasoning",
}


def _text(value: Any, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def _bounded(value: Any, depth: int = 0) -> Any:
    if depth > 5:
        return "[bounded]"
    if isinstance(value, Mapping):
        blocked = ("password", "secret", "token", "credential", "private_key", "api_key")
        return {
            str(key)[:80]: _bounded(item, depth + 1)
            for key, item in list(value.items())[:40]
            if not any(marker in str(key).casefold() for marker in blocked)
        }
    if isinstance(value, (list, tuple)):
        return [_bounded(item, depth + 1) for item in list(value)[:40]]
    if isinstance(value, str):
        return value[:1200]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:300]


def _model_bounded(value: Any, depth: int = 0) -> Any:
    """Small evidence projection for local models with a 2K context window."""
    if depth > 4:
        return "[bounded]"
    if isinstance(value, Mapping):
        blocked = ("password", "secret", "token", "credential", "private_key", "api_key")
        return {
            str(key)[:60]: _model_bounded(item, depth + 1)
            for key, item in list(value.items())[:12]
            if not any(marker in str(key).casefold() for marker in blocked)
        }
    if isinstance(value, (list, tuple)):
        return [_model_bounded(item, depth + 1) for item in list(value)[:4]]
    if isinstance(value, str):
        return value[:180]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:180]


class CooMissionService:
    """Ask only a released model for a non-executing, validated proposal."""

    def __init__(
        self, *,
        public_provider_loader: Callable[[], Mapping[str, Any]] | None = None,
        local_model_loader: Callable[[], Mapping[str, Any]] | None = None,
        model_invoker: Callable[[str, str], Mapping[str, Any] | str] | None = None,
    ) -> None:
        self.public_provider_loader = public_provider_loader
        self.local_model_loader = local_model_loader
        self.model_invoker = model_invoker

    def classify(self, text: str) -> str:
        value = _text(text, 2_000).casefold()
        if any(term in value for term in ("competitor", "research", "cost per click", "market rate", "find out")):
            return "research_job"
        if any(term in value for term in (
            "send ", "book ", "pay ", "publish ", "change ", "create ", "chase ", "follow up",
            "make sure", "increase ", "decrease ", "ask ", "tell ", "speak to", "delegate ",
        )):
            return "approval_gated_action"
        if any(term in value for term in ("draft", "write", "prepare", "plan")):
            return "draft"
        return "business_fact_lookup"

    def prepare(
        self, *, workspace_id: str, question: str,
        department_facts: Mapping[str, Any] | None = None,
        fact_loader: Callable[[str], Mapping[str, Any]] | None = None,
        model_selection: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a five-department fact pack with source and retrieval state."""
        supplied = dict(department_facts or {})
        facts: dict[str, Any] = {}
        relevant = self._relevant_departments(question)
        for department in DEPARTMENTS:
            if department not in relevant:
                facts[department] = {
                    "retrieval_state": "not_requested", "source_ids": [],
                    "retrieved_at": utc_now_iso(), "data": {},
                }
                continue
            raw: Any = supplied.get(department)
            if raw is None and fact_loader:
                try:
                    raw = fact_loader(department)
                except Exception as exc:
                    raw = {"retrieval_state": "unavailable", "reason": type(exc).__name__}
            record = dict(raw) if isinstance(raw, Mapping) else {"data": raw or {}}
            source_ids = record.get("source_ids")
            facts[department] = {
                "retrieval_state": _text(record.get("retrieval_state") or ("retrieved" if raw is not None else "not_published"), 80),
                "source_ids": [str(item)[:160] for item in source_ids[:12]] if isinstance(source_ids, list) else [],
                "retrieved_at": _text(record.get("retrieved_at") or utc_now_iso(), 80),
                "data": _bounded(record.get("data", record)),
            }
        selection = dict(model_selection or {})
        kind = self.classify(question)
        allowed_capabilities = {
            department: get_department_capabilities(department)
            for department in DEPARTMENTS if department in relevant
        }
        return {
            "schema_version": "aion.coo.mission.v1", "mission_id": f"coo-{uuid4().hex}",
            "created_at": utc_now_iso(), "workspace_id": _text(workspace_id, 160),
            "request_kind": kind, "user_goal": _text(question, 2_000),
            "verified_business_facts": facts,
            "model_selection": {key: selection.get(key) for key in (
                "provider", "model", "binding_ref", "release_status", "selection_status", "source"
            )},
            "allowed_model_capabilities": ["retrieve_business_facts", "classify_business_item", "prepare_business_draft"],
            "allowed_department_capabilities": allowed_capabilities,
            "research_policy": "source_required" if kind == "research_job" else "not_requested",
            "external_writes_allowed": False, "approval_required_for_external_change": True,
        }

    @staticmethod
    def _relevant_departments(question: str) -> set[str]:
        value = _text(question, 2_000).casefold()
        terms = {
            "finance": ("cash", "invoice", "payment", "expense", "profit", "margin", "tax", "budget", "turnover", "revenue"),
            "sales": ("sale", "lead", "quote", "pipeline", "customer", "competitor", "cost per click"),
            "marketing": ("marketing", "advert", " ad ", "ads", "campaign", "traffic", "cpc", "roas", "marketing spend"),
            "support": ("case", "ticket", "complaint", "support", "refund", "customer issue"),
            "people": ("employee", "staff", "team", "people", " hr ", "hiring", "holiday", "leave", "absence", "off today", "sick"),
            "operations": ("delivery", "risk", "supplier", "schedule", "operations", "research", "find out", "meeting", "minutes", "discussed", "decision", "today's plan"),
            "products_services": ("product", "service", "offering", "unit cost", "unit economics", "price", "gross margin"),
        }
        matched = {department for department, words in terms.items() if any(word in f" {value} " for word in words)}
        if not matched:
            return set(DEPARTMENTS)
        # Operations coordinates cross-functional work, while a Sales answer
        # involving revenue or payment also needs the Finance boundary visible.
        matched.add("operations")
        if "sales" in matched and any(term in value for term in ("revenue", "payment", "made", "sold")):
            matched.add("finance")
        return matched

    def resolve_model(self, workspace_state: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Prefer workspace selection; reject every non-selectable local card."""
        state = dict(workspace_state or {})
        explicit: dict[str, Any] = {}
        for key in ("coo_model_selection", "ai_model_selection", "model_selection"):
            if isinstance(state.get(key), Mapping):
                explicit = dict(state[key])
                break
        if not explicit and state.get("workspace_id"):
            from backend.modules.aion_inference.local_model_selection_store import load_local_model_selection

            explicit = load_local_model_selection(str(state["workspace_id"]))
        provider_id = _text(explicit.get("provider") or explicit.get("provider_id"), 80).casefold()
        model_id = _text(explicit.get("model") or explicit.get("model_id"), 200)
        local_card = explicit.get("source") == "local_model_vault" or provider_id in {"local_model", "local-package"}
        if local_card:
            snapshot = self._local_models()
            models = snapshot.get("models") if isinstance(snapshot, Mapping) else []
            match = next((dict(item) for item in models or [] if isinstance(item, Mapping)
                          and str(item.get("model_id") or item.get("id") or "") == model_id), None)
            installation = next((dict(item) for item in (match or {}).get("installations") or []
                                 if isinstance(item, Mapping) and item.get("selectable") is True), None)
            if not match or match.get("selection_status") != "selectable" or installation is None:
                return {"status": "unavailable", "provider": provider_id or "local_model", "model": model_id or None,
                        "selection_status": (match or {}).get("selection_status", "not_found"),
                        "release_status": (match or {}).get("release_status"),
                        "reason": (match or {}).get("reason") or "local_model_not_selectable", "source": "local_model_vault"}
            runtime = {
                **dict(match.get("runtime_profile") or {}),
                **dict(installation.get("runtime_profile") or {}),
            }
            return {"status": "selected", "provider": "local_model", "model": model_id,
                    "binding_ref": explicit.get("binding_ref"), "selection_status": "selectable",
                    "release_status": match.get("release_status"), "source": "local_model_vault",
                    "endpoint": runtime.get("endpoint"), "model_sha256": installation.get("model_sha256"),
                    "model_path": installation.get("model_path"),
                    "runtime_adapter": runtime.get("adapter"),
                    "chat_template_kwargs": runtime.get("chat_template_kwargs"),
                    "max_output_tokens": runtime.get("max_output_tokens"),
                    "context_size": runtime.get("context_size"),
                    "parallel_slots": runtime.get("parallel_slots"),
                    "finance_arithmetic": runtime.get("finance_arithmetic")}

        records = [dict(item) for item in self._public_providers().get("providers") or [] if isinstance(item, Mapping)]
        if provider_id:
            record = next((item for item in records if str(item.get("id") or "").casefold() == provider_id), None)
            if not record or record.get("connected") is not True:
                return {"status": "unavailable", "provider": provider_id, "model": model_id or (record or {}).get("model"),
                        "reason": (record or {}).get("reason") or "selected_provider_not_connected",
                        "source": "vault_public_records", "release_status": "unavailable"}
        else:
            record = next((item for item in records if item.get("connected") is True), None)
        if not record:
            return {"status": "unavailable", "provider": None, "model": None,
                    "reason": "no_connected_vault_model", "source": "vault_public_records", "release_status": "unavailable"}
        return {"status": "selected", "provider": str(record.get("id") or ""),
                "model": model_id or record.get("model"), "binding_ref": explicit.get("binding_ref"),
                "selection_status": "selectable", "release_status": "connected", "source": "vault_public_records"}

    def run(
        self, *, workspace_id: str, question: str, workspace_state: Mapping[str, Any] | None,
        fact_loader: Callable[[str], Mapping[str, Any]],
    ) -> dict[str, Any]:
        selection = self.resolve_model(workspace_state)
        mission = self.prepare(workspace_id=workspace_id, question=question, fact_loader=fact_loader,
                               model_selection=selection)
        if selection.get("status") != "selected":
            return self._receipt(mission, selection, "model_unavailable", str(selection.get("reason") or "model_unavailable"))
        try:
            proposal = self._validate_proposal(self._invoke(selection, self._prompt(mission)))
            if (mission["request_kind"] == "approval_gated_action" and
                    not proposal.get("department_tasks") and not proposal.get("action_proposal")):
                proposal = self._validate_proposal(self._invoke(selection, self._repair_prompt(mission)))
                if not proposal.get("department_tasks") and not proposal.get("action_proposal"):
                    raise ValueError("coo_action_requires_registered_department_task")
            proposal = self._bind_verified_sources(mission, proposal)
        except Exception as exc:
            return self._receipt(mission, selection, "model_unavailable", f"{type(exc).__name__}:{str(exc)[:240]}")
        result = self._receipt(mission, selection, "proposal_ready")
        result["proposal"] = proposal
        if proposal.get("department_tasks"):
            result["delegation_queue"] = self._delegation_queue(mission, proposal)
            proposal["answer"] = self._queue_status_answer(result["delegation_queue"])
        if mission["request_kind"] == "research_job":
            result["research_job"] = self._research_job(mission, proposal)
        if mission["request_kind"] == "approval_gated_action":
            result["required_approval"] = self._approval_request(
                mission, proposal, result.get("delegation_queue")
            )
        return result

    def _public_providers(self) -> Mapping[str, Any]:
        if self.public_provider_loader:
            return self.public_provider_loader()
        from backend.modules.vault.ai_provider_key_store import list_ai_provider_public_records
        return list_ai_provider_public_records()

    def _local_models(self) -> Mapping[str, Any]:
        if self.local_model_loader:
            return self.local_model_loader()
        from backend.modules.aion_inference.local_model_vault import LocalModelVault
        return LocalModelVault().snapshot()

    def _invoke(self, selection: Mapping[str, Any], prompt: str) -> Mapping[str, Any] | str:
        provider = str(selection.get("provider") or "")
        if self.model_invoker:
            return self.model_invoker(provider, prompt)
        if provider == "local_model":
            from backend.services.aion_mission_mode.pilot_local_model_runtime import (
                selected_local_runtime_profile, run_selected_local_chat,
            )
            runtime = selected_local_runtime_profile(
                model_id=str(selection.get("model") or ""),
                adapter=str(selection.get("runtime_adapter") or ""),
                endpoint=str(selection.get("endpoint") or ""),
                model_sha256=str(selection.get("model_sha256") or ""),
                model_path=str(selection.get("model_path") or ""),
                finance_arithmetic=str(selection.get("finance_arithmetic") or ""),
                chat_template_kwargs=selection.get("chat_template_kwargs"),
                max_output_tokens=selection.get("max_output_tokens"),
                context_size=selection.get("context_size"),
                parallel_slots=selection.get("parallel_slots"),
            )
            return run_selected_local_chat(prompt=prompt, runtime_profile=runtime)
        from backend.api.boardroom_provider_router import _call_connected_provider
        return _call_connected_provider(provider, prompt, str(selection.get("model") or "") or None)

    @staticmethod
    def _prompt(mission: Mapping[str, Any]) -> str:
        facts = {
            name: _model_bounded(record)
            for name, record in dict(mission.get("verified_business_facts") or {}).items()
            if isinstance(record, Mapping) and record.get("retrieval_state") != "not_requested"
        }
        model_mission = {
            "request_kind": mission.get("request_kind"), "user_goal": mission.get("user_goal"),
            "facts": facts,
            "allowed_department_capabilities": mission.get("allowed_department_capabilities") or {},
            "external_writes_allowed": False,
        }
        action_rule = ("This is an ACTION request: department_tasks MUST contain at least one registered task. "
                       if mission.get("request_kind") == "approval_gated_action" else "")
        return ("Act as a bounded COO. Answer only from facts. Never invent data or say an action ran. " + action_rule +
                "For requests to do work, select department_tasks only from the allowed capability "
                "list; use {department,capability,title,objective}. Live changes will be approval-gated by the "
                "system. Return compact JSON only: {answer,department_consultations:[{department,finding,source_ids}],"
                "sources:[],draft:null,action_proposal:null,department_tasks:[]}.\nMISSION:\n" +
                json.dumps(model_mission, ensure_ascii=False, separators=(",", ":")))

    @classmethod
    def _repair_prompt(cls, mission: Mapping[str, Any]) -> str:
        return (cls._prompt(mission) +
                "\nCORRECTION: The previous response omitted the required department task. Choose the best "
                "registered capability or capabilities for the goal. Do not claim anybody was contacted and do "
                "not claim work completed. Return the full compact JSON object again.")

    @classmethod
    def _validate_proposal(cls, raw: Mapping[str, Any] | str) -> dict[str, Any]:
        value: Any = raw.get("content") if isinstance(raw, Mapping) and "content" in raw else raw
        if isinstance(value, str):
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", value.strip(), flags=re.IGNORECASE)
            start = cleaned.find("{")
            if start < 0:
                raise ValueError("coo_proposal_missing_json_object")
            value, _ = json.JSONDecoder().raw_decode(cleaned[start:])
        if not isinstance(value, Mapping):
            raise ValueError("coo_proposal_must_be_object")

        def reject(item: Any) -> None:
            if isinstance(item, Mapping):
                for key, child in item.items():
                    if str(key).casefold() in FORBIDDEN_KEYS:
                        raise ValueError(f"forbidden_coo_proposal_key:{key}")
                    reject(child)
            elif isinstance(item, list):
                for child in item:
                    reject(child)
        reject(value)
        answer = _text(value.get("answer"), 8_000)
        if not answer:
            raise ValueError("coo_proposal_missing_answer")
        consultations = []
        for item in value.get("department_consultations") or []:
            if isinstance(item, Mapping):
                consultations.append({"department": _text(item.get("department"), 80),
                                      "finding": _text(item.get("finding"), 1_000),
                                      "source_ids": [str(source)[:160] for source in list(item.get("source_ids") or [])[:12]]})
        action = value.get("action_proposal") if isinstance(value.get("action_proposal"), Mapping) else None
        department_tasks = []
        for item in list(value.get("department_tasks") or [])[:12]:
            if not isinstance(item, Mapping):
                continue
            department = _text(item.get("department"), 80).casefold().replace("&", "and").replace(" ", "_")
            if department == "products_and_services":
                department = "products_services"
            capability = _text(item.get("capability"), 160)
            if department not in DEPARTMENTS or capability not in get_department_capabilities(department):
                raise ValueError(f"unsupported_department_task:{department}:{capability}")
            department_tasks.append({
                "department": department, "capability": capability,
                "title": _text(item.get("title") or capability, 240),
                "objective": _text(item.get("objective") or item.get("title") or capability, 2_000),
            })
        return {"schema_version": "aion.coo.proposal.v1", "answer": answer,
                "department_consultations": consultations[:12],
                "sources": [str(item)[:160] for item in list(value.get("sources") or [])[:24]],
                "draft": _bounded(value.get("draft")) if isinstance(value.get("draft"), Mapping) else None,
                "action_proposal": {"action_type": _text(action.get("action_type"), 120),
                                    "proposed_payload": _bounded(action.get("proposed_payload") or {})} if action else None,
                "department_tasks": department_tasks,
                "model_may_execute": False, "external_side_effect_executed": False}

    @staticmethod
    def _delegation_queue(mission: Mapping[str, Any], proposal: Mapping[str, Any]) -> dict[str, Any]:
        items = []
        for index, task in enumerate(proposal.get("department_tasks") or []):
            items.append(create_department_queue_item(
                business_id=str(mission.get("workspace_id") or ""),
                mission_id=str(mission.get("mission_id") or ""), mission_run_id="",
                department_id=str(task.get("department") or ""),
                capability=str(task.get("capability") or ""), title=str(task.get("title") or ""),
                objective=str(task.get("objective") or ""), task_type="coo_delegation", task_index=index,
            ))
        return {
            "schema_version": "aion.coo.delegation_queue.v1", "mission_id": mission.get("mission_id"),
            "status": "prepared", "items": items,
            "ready_count": sum(item["status"] in {"ready", "staged"} for item in items),
            "waiting_approval_count": sum(item["status"] == "waiting_approval" for item in items),
            "external_side_effect_executed": False,
        }

    @staticmethod
    def _bind_verified_sources(mission: Mapping[str, Any], proposal: Mapping[str, Any]) -> dict[str, Any]:
        result = dict(proposal)
        allowed = []
        for record in dict(mission.get("verified_business_facts") or {}).values():
            if not isinstance(record, Mapping) or record.get("retrieval_state") == "not_requested":
                continue
            for source in record.get("source_ids") or []:
                source_id = str(source)[:160]
                if source_id and source_id not in allowed:
                    allowed.append(source_id)
        supplied = [str(item)[:160] for item in result.get("sources") or []]
        result["sources"] = [item for item in supplied if item in allowed] or allowed[:24]
        consultations = []
        for item in result.get("department_consultations") or []:
            consultation = dict(item)
            consultation["source_ids"] = [
                str(source)[:160] for source in consultation.get("source_ids") or [] if str(source)[:160] in allowed
            ]
            consultations.append(consultation)
        result["department_consultations"] = consultations
        return result

    @staticmethod
    def _queue_status_answer(queue: Mapping[str, Any]) -> str:
        items = [dict(item) for item in queue.get("items") or [] if isinstance(item, Mapping)]
        departments = []
        for item in items:
            name = str(item.get("department_display_name") or item.get("department_id") or "Department")
            if name not in departments:
                departments.append(name)
        titles = "; ".join(str(item.get("title") or item.get("capability") or "Department task") for item in items[:5])
        ready = int(queue.get("ready_count") or 0)
        waiting = int(queue.get("waiting_approval_count") or 0)
        return (f"Prepared {len(items)} governed task(s) for {', '.join(departments)}: {titles}. "
                f"{ready} can proceed as internal department work; {waiting} live action(s) are waiting for exact approval. "
                "No live external action has run.")

    @staticmethod
    def _receipt(mission: Mapping[str, Any], selection: Mapping[str, Any], status: str, reason: str = "") -> dict[str, Any]:
        return {"schema_version": "aion.coo.mission_receipt.v1", "status": status, "mission": dict(mission),
                "model_selection": dict(selection), "reason": reason or None, "external_writes_performed": False,
                "approval_gated": True, "completed_at": utc_now_iso()}

    @staticmethod
    def _research_job(mission: Mapping[str, Any], proposal: Mapping[str, Any]) -> dict[str, Any]:
        return {"schema_version": "aion.coo.research_job.v1", "job_id": f"research-{uuid4().hex}",
                "mission_id": mission.get("mission_id"), "scope": mission.get("user_goal"),
                "budget": {"max_sources": 12, "max_elapsed_seconds": 300},
                "source_requirements": "independent_sources_required", "status": "prepared",
                "sources": list(proposal.get("sources") or []), "external_writes_performed": False,
                "created_at": utc_now_iso()}

    @staticmethod
    def _approval_request(
        mission: Mapping[str, Any], proposal: Mapping[str, Any],
        delegation_queue: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        action = dict(proposal.get("action_proposal") or {})
        payload = action.get("proposed_payload") if isinstance(action.get("proposed_payload"), Mapping) else {}
        waiting_items = [
            dict(item) for item in (delegation_queue or {}).get("items") or []
            if isinstance(item, Mapping) and item.get("status") == "waiting_approval"
        ]
        if not payload and waiting_items:
            payload = {"department_tasks": waiting_items}
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return {"schema_version": "aion.coo.exact_approval_request.v1", "approval_id": f"approval-{uuid4().hex}",
                "mission_id": mission.get("mission_id"), "action_type": action.get("action_type") or ("department_live_actions" if waiting_items else "external_change"),
                "proposed_payload": payload, "expected_payload_hash": "sha256:" + hashlib.sha256(encoded.encode()).hexdigest(),
                "approval_state": "waiting_exact_payload_approval" if payload else "no_live_payload_prepared",
                "execution_allowed": False,
                "external_side_effect_executed": False}
