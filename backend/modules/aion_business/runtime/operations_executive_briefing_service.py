"""Evidence-gated COO and Department Pilot executive conversations.

This service owns the durable Operations Command Centre streams.  The model is
replaceable and proposal-only: AION chooses the evidence, role, authority and
record format, while the selected Vault model supplies departmental judgement.
"""

from __future__ import annotations

from datetime import datetime
import json
import re
from threading import RLock
from typing import Any, Mapping
from uuid import uuid4
from zoneinfo import ZoneInfo

from backend.modules.aion_fabric.canonical import canonical_hash, utc_now_iso


_LOCK = RLock()
CORE_CHANNELS = ("sales", "marketing", "finance", "support", "people")
EXECUTIVE_CHANNEL_STORE_KEY = "executive_channel_conversations"
EXECUTIVE_MESSAGE_TYPES = frozenset({
    "morning_minutes", "executive_briefing_summary", "coo_instruction",
    "department_update", "delegated_people_action", "delegated_people_response",
})
_ROLE_CARDS: dict[str, dict[str, str]] = {
    "sales": {
        "title": "Sales Director",
        "mandate": "Protect revenue quality, progress qualified pipeline, remove conversion blockers and state the next accountable commercial action.",
    },
    "marketing": {
        "title": "Marketing Director",
        "mandate": "Protect efficient demand generation, distinguish measured attribution from assumptions and coordinate campaigns with Sales capacity.",
    },
    "finance": {
        "title": "Finance Director",
        "mandate": "Protect cash, margin and financial control; distinguish ledger evidence from forecasts and surface overdue or unreconciled exposure.",
    },
    "support": {
        "title": "Customer Support Director",
        "mandate": "Protect customer outcomes, service levels and closure quality; surface complaints, overdue replies and cross-department blockers.",
    },
    "people": {
        "title": "People Director",
        "mandate": "Protect team capacity, accountability and safe access; use only authorised people records and exclude unnecessary sensitive detail.",
    },
}


def _clean_text(value: Any, limit: int = 4_000) -> str:
    return " ".join(str(value or "").split())[:limit]


def _bounded(value: Any, *, depth: int = 0) -> Any:
    if depth > 5:
        return "[bounded]"
    if isinstance(value, Mapping):
        blocked = ("password", "secret", "token", "credential", "private_key", "api_key")
        return {
            str(key)[:80]: _bounded(item, depth=depth + 1)
            for key, item in list(value.items())[:35]
            if not any(marker in str(key).casefold() for marker in blocked)
        }
    if isinstance(value, (list, tuple)):
        return [_bounded(item, depth=depth + 1) for item in list(value)[:30]]
    if isinstance(value, str):
        return value[:1_200]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:300]


class OperationsExecutiveBriefingService:
    """Run and retain role-separated executive briefings without live actions."""

    def __init__(self, provider: Any) -> None:
        self.provider = provider
        self.repository = provider.containers
        self.models = provider.coo_missions

    def _channel_roles(self, workspace_id: str) -> dict[str, dict[str, str]]:
        roles = {key: dict(value) for key, value in _ROLE_CARDS.items()}
        core_names = {"sales": "Sales", "marketing": "Marketing", "finance": "Finance", "support": "Support", "people": "People"}
        for key, name in core_names.items():
            roles[key]["name"] = name
        loader = getattr(self.provider, "custom_departments", None)
        custom = loader(workspace_id) if callable(loader) else []
        for item in custom:
            if not isinstance(item, Mapping):
                continue
            key = re.sub(r"[^a-z0-9_]+", "", str(item.get("id") or "").casefold())[:40]
            name = _clean_text(item.get("name"), 80)
            if not key or not name or key in roles or key == "operations":
                continue
            title = _clean_text(item.get("pilot_title"), 100) or f"{name} Director"
            mandate = _clean_text(item.get("mandate"), 2_000) or f"Represent the authorised {name} department evidence and accountable work."
            roles[key] = {"title": title, "mandate": mandate, "name": name}
        return roles

    def canonical_channel(self, workspace_id: str, value: str) -> str:
        channel = re.sub(r"[^a-z0-9_]+", "", str(value or "").casefold())[:40]
        if channel not in self._channel_roles(workspace_id):
            raise ValueError("unsupported_operations_department_channel")
        return channel

    def status(self, workspace_id: str) -> dict[str, Any]:
        runtime = self._runtime(workspace_id)
        config = self._config(runtime)
        meetings = [dict(item) for item in runtime.get("executive_briefings") or [] if isinstance(item, Mapping)]
        local_now = self._local_now(config)
        today = local_now.date().isoformat()
        scheduled_time = str(config.get("local_time") or "08:00")
        due_by_clock = local_now.strftime("%H:%M") >= scheduled_time
        latest = meetings[-1] if meetings else None
        return {
            "ok": True,
            "workspace_id": workspace_id,
            "schedule": config,
            "today": today,
            "briefing_due": bool(config.get("enabled", True) and due_by_clock and not any(item.get("local_date") == today for item in meetings)),
            "latest_briefing": latest,
            "channels": [
                self._channel_summary(runtime, channel, role)
                for channel, role in self._channel_roles(workspace_id).items()
            ],
        }

    def channel_history(self, workspace_id: str, channel: str, *, limit: int = 75) -> dict[str, Any]:
        department = self.canonical_channel(workspace_id, channel)
        role = self._channel_roles(workspace_id)[department]
        runtime = self._runtime(workspace_id)
        turns = [dict(item) for item in self._turns(runtime) if item.get("department_id") == department]
        turns.sort(key=lambda item: (int(item.get("sequence") or 0), str(item.get("created_at") or "")))
        size = max(10, min(int(limit or 75), 100))
        return {
            "ok": True,
            "workspace_id": workspace_id,
            "department_id": department,
            "role": role,
            "turns": turns[-size:],
            "has_more": len(turns) > size,
            "summary": self._channel_summary(runtime, department, role),
        }

    def channel_turn(self, workspace_id: str, channel: str, text: str, *, person_id: str) -> dict[str, Any]:
        department = self.canonical_channel(workspace_id, channel)
        role = self._channel_roles(workspace_id)[department]
        question = _clean_text(text, 2_000)
        if not question:
            raise ValueError("department_channel_message_required")
        with _LOCK:
            runtime = self._runtime(workspace_id)
            context = [
                {"sender": item.get("sender"), "content": item.get("content")}
                for item in self._turns(runtime)
                if item.get("department_id") == department
            ][-8:]
            coo_record = self._append(
                runtime, department=department, role="user", sender="Operations Pilot",
                content=question, message_type="coo_instruction", metadata={"person_id": person_id},
            )
            position = self._department_position(
                workspace_id, department, question=question, context=context,
                meeting_context=self._board_context(workspace_id, person_id), runtime=runtime, role=role,
            )
            response = self._append(
                runtime, department=department, role="assistant",
                sender=f"{role['title']} Pilot",
                content=position["summary"], message_type="department_update",
                evidence=position.get("source_ids") or [], metadata=position,
            )
            self.repository.save_dict(workspace_id, "operational_runtime_summary", runtime)
        return {"ok": True, "request": coo_record, "response": response,
                "history": self.channel_history(workspace_id, department)}

    def delegate_people_action(
        self, workspace_id: str, text: str, *, person_id: str,
        attachments: Any = None,
    ) -> dict[str, Any]:
        """Delegate a bounded People action without depending on model availability.

        The COO instruction and People Pilot response live only in the executive
        channel.  The People capability service owns validation and the canonical
        internal record mutation; it never performs an external notification.
        """
        from backend.modules.aion_business.runtime.people_pilot_action_service import (
            PeoplePilotActionService,
        )

        question = _clean_text(text, 2_000)
        if not question:
            raise ValueError("department_channel_message_required")
        with _LOCK:
            runtime = self._runtime(workspace_id)
            turns = [item for item in self._turns(runtime) if item.get("department_id") == "people"]
            pending_plan = self._pending_people_plan(turns)
            subject_context = self._recent_people_subject(turns)
            request = self._append(
                runtime, department="people", role="user", sender="Operations Pilot",
                content=question, message_type="delegated_people_action",
                metadata={"person_id": person_id, "delegated_by": "operations"},
            )
            action = PeoplePilotActionService(self.provider).handle(
                workspace_id, question, person_id=person_id, attachments=attachments,
                pending_plan=pending_plan, subject_context=subject_context,
            )
            if action.get("handled"):
                metadata = {
                    "people_action": {
                        "status": action.get("status"),
                        "capability_id": (action.get("plan") or {}).get("capability_id"),
                        "plan": {
                            "capability_id": (action.get("plan") or {}).get("capability_id"),
                            "fields": dict((action.get("plan") or {}).get("fields") or {}),
                            "missing_fields": list((action.get("plan") or {}).get("missing_fields") or []),
                        },
                        "receipt": dict(action.get("action_receipt") or {}),
                        "organization_revision": (action.get("organization") or {}).get("revision"),
                    }
                }
                content = str(action.get("content") or "The People Pilot could not complete that request.")
                status = str(action.get("status") or "unknown")
            else:
                position = self._department_position(
                    workspace_id, "people", question=question,
                    context=[{"sender": item.get("sender"), "content": item.get("content")} for item in turns[-8:]],
                    meeting_context=self._board_context(workspace_id, person_id),
                    runtime=runtime, role=self._channel_roles(workspace_id)["people"],
                )
                content = str(position.get("summary") or "The People Pilot could not prepare a response.")
                metadata = {"department_position": position}
                status = "advisory"
            response = self._append(
                runtime, department="people", role="assistant", sender="People Director Pilot",
                content=content, message_type="delegated_people_response", metadata=metadata,
            )
            self.repository.save_dict(workspace_id, "operational_runtime_summary", runtime)
        return {
            "ok": True, "status": status, "handled": bool(action.get("handled")),
            "request": request, "response": response,
            "people_action": metadata.get("people_action"),
            "history": self.channel_history(workspace_id, "people"),
        }

    @staticmethod
    def _pending_people_plan(turns: list[Mapping[str, Any]]) -> dict[str, Any] | None:
        if not turns:
            return None
        latest = turns[-1]
        metadata = latest.get("metadata") if isinstance(latest.get("metadata"), Mapping) else {}
        action = metadata.get("people_action") if isinstance(metadata.get("people_action"), Mapping) else {}
        plan = action.get("plan") if isinstance(action.get("plan"), Mapping) else None
        return dict(plan) if latest.get("role") == "assistant" and action.get("status") == "needs_information" and plan else None

    @staticmethod
    def _recent_people_subject(turns: list[Mapping[str, Any]]) -> dict[str, Any] | None:
        for item in reversed(turns[-24:]):
            metadata = item.get("metadata") if isinstance(item.get("metadata"), Mapping) else {}
            action = metadata.get("people_action") if isinstance(metadata.get("people_action"), Mapping) else {}
            plan = action.get("plan") if isinstance(action.get("plan"), Mapping) else {}
            if action.get("status") == "context_cleared":
                return None
            if action.get("status") != "completed" or plan.get("capability_id") not in {"people.create_person", "people.update_person"}:
                continue
            fields = plan.get("fields") if isinstance(plan.get("fields"), Mapping) else {}
            name = _clean_text(fields.get("name") or fields.get("person_name"), 200)
            if name:
                return {"person_name": name, "capability_id": plan.get("capability_id")}
        return None

    def direct_department_turn(
        self, workspace_id: str, channel: str, text: str, *, person_id: str,
    ) -> dict[str, Any]:
        """Answer a founder-to-Department-Pilot turn using the governed model path.

        Direct department chat and COO executive channels are different records, but
        they must use the same role card, authorised evidence pack and Vault-selected
        model.  Persistence remains with the workspace conversation gateway so desktop
        and mobile clients receive one shared, ordered conversation history.
        """
        department = self.canonical_channel(workspace_id, channel)
        role = self._channel_roles(workspace_id)[department]
        question = _clean_text(text, 2_000)
        if not question:
            raise ValueError("department_pilot_message_required")
        runtime = self._runtime(workspace_id)
        direct_loader = getattr(self.provider, "_conversation_store", None)
        direct_store = direct_loader(workspace_id) if callable(direct_loader) else {"turns": []}
        context = [
            {"sender": item.get("sender"), "content": item.get("content")}
            for item in direct_store.get("turns") or []
            if isinstance(item, Mapping) and item.get("department_id") == department
        ][-8:]
        position = self._department_position(
            workspace_id, department, question=question, context=context,
            meeting_context=self._board_context(workspace_id, person_id),
            runtime=runtime, role=role,
        )
        return {
            "ok": True,
            "department_id": department,
            "role": role,
            "position": position,
            "external_writes_performed": False,
            "approval_gated": True,
        }

    def run_morning_briefing(
        self, workspace_id: str, *, person_id: str, force: bool = False,
    ) -> dict[str, Any]:
        with _LOCK:
            runtime = self._runtime(workspace_id)
            config = self._config(runtime)
            local_now = self._local_now(config)
            local_date = local_now.date().isoformat()
            existing = next((dict(item) for item in runtime.get("executive_briefings") or []
                             if isinstance(item, Mapping) and item.get("local_date") == local_date), None)
            if existing and not force:
                return {"ok": True, "deduplicated": True, "briefing": existing,
                        "status": self.status(workspace_id)}

            board_context = self._board_context(workspace_id, person_id)
            meeting_id = f"executive-briefing-{local_date}-{uuid4().hex[:10]}"
            positions: dict[str, dict[str, Any]] = {}
            roles = self._channel_roles(workspace_id)
            for department, role in roles.items():
                goal = (
                    "Give the executive morning update: yesterday's evidenced results, today's plan, "
                    "outstanding tasks, issues, target variance, dependencies and decisions needed from the COO."
                )
                positions[department] = self._department_position(
                    workspace_id, department, question=goal, context=[],
                    meeting_context=board_context, runtime=runtime, role=role,
                )

            critic = self._critic_review(runtime, board_context, positions)
            created_at = utc_now_iso()
            for department, role in roles.items():
                position = positions[department]
                challenge = dict((critic.get("departments") or {}).get(department) or {})
                content = self._minutes_text(local_now, role, position, challenge)
                self._append(
                    runtime, department=department, role="assistant",
                    sender=f"{role['title']} Pilot",
                    content=content, message_type="morning_minutes",
                    evidence=position.get("source_ids") or [],
                    metadata={**position, "meeting_id": meeting_id, "local_date": local_date,
                              "critic_challenge": challenge, "board_context": board_context},
                )

            executive_actions = []
            board_feedback = []
            for department, position in positions.items():
                for index, action in enumerate(position.get("actions") or []):
                    executive_actions.append({
                        "action_id": f"{meeting_id}-{department}-{index + 1}",
                        "meeting_id": meeting_id, "department_id": department,
                        "title": _clean_text(action, 500), "status": "open",
                        "created_at": created_at, "external_execution_allowed": False,
                    })
                variance = _clean_text(position.get("target_variance"), 1_000)
                risks = [_clean_text(item, 500) for item in position.get("risks") or []]
                if (variance and variance.casefold() not in {"unknown", "on evidence supplied"}) or risks:
                    board_feedback.append({
                        "meeting_id": meeting_id, "department_id": department,
                        "target_variance": variance or "Unknown", "risks": risks,
                        "status": "staged_for_coo_ceo_board", "created_at": created_at,
                    })

            summary = (
                f"Executive morning briefing {local_now.strftime('%d/%m/%Y')} completed across {len(roles)} departments. "
                f"{len(executive_actions)} evidenced action(s) are open and {len(board_feedback)} variance or risk item(s) "
                "are staged for COO, CEO and Board visibility. Open a department channel for its minutes. "
                "No external action was executed."
            )
            self._append(
                runtime, department="operations", role="assistant", sender="Operations Pilot",
                content=summary, message_type="executive_briefing_summary",
                metadata={"meeting_id": meeting_id, "local_date": local_date,
                          "action_count": len(executive_actions), "board_feedback": board_feedback},
            )

            briefing = {
                "schema_version": "aion.operations.executive_briefing.v1",
                "meeting_id": meeting_id, "local_date": local_date, "created_at": created_at,
                "status": "minutes_published", "departments": positions,
                "board_context": board_context, "critic_review": critic,
                "executive_actions": executive_actions, "board_feedback": board_feedback,
                "reasoning_mode": critic.get("reasoning_mode") or "single_model_role_separated",
                "external_writes_performed": False,
                "approval_required_for_live_actions": True,
            }
            briefing["briefing_hash"] = canonical_hash(briefing)
            meetings = [dict(item) for item in runtime.get("executive_briefings") or [] if isinstance(item, Mapping)]
            if force:
                meetings = [item for item in meetings if item.get("local_date") != local_date]
            meetings.append(briefing)
            runtime["executive_briefings"] = meetings[-120:]
            action_register = [dict(item) for item in runtime.get("executive_action_register") or [] if isinstance(item, Mapping)]
            runtime["executive_action_register"] = (action_register + executive_actions)[-1_000:]
            feedback_register = [dict(item) for item in runtime.get("executive_board_feedback") or [] if isinstance(item, Mapping)]
            runtime["executive_board_feedback"] = (feedback_register + board_feedback)[-500:]
            self.repository.save_dict(workspace_id, "operational_runtime_summary", runtime)
        return {"ok": True, "deduplicated": False, "briefing": briefing,
                "status": self.status(workspace_id)}

    def _department_position(
        self, workspace_id: str, department: str, *, question: str,
        context: list[dict[str, Any]], meeting_context: dict[str, Any], runtime: dict[str, Any],
        role: Mapping[str, str],
    ) -> dict[str, Any]:
        try:
            fact = self.provider._coo_department_fact(workspace_id, department, persona_id="desktop_user")
        except (OSError, ValueError, PermissionError, KeyError) as exc:
            fact = {"retrieval_state": "unavailable", "source_ids": [], "data": {}, "reason": type(exc).__name__}
        source_ids = [str(item)[:160] for item in fact.get("source_ids") or []]
        selection = self.models.resolve_model(runtime)
        if selection.get("status") != "selected":
            return self._evidence_fallback(department, role, fact, selection)
        prompt = {
            "role": role,
            "instruction": question,
            "authoritative_department_evidence": _bounded(fact),
            "board_mandates_and_targets": _bounded(meeting_context),
            "recent_channel_context": _bounded(context),
            "rules": [
                "Use only supplied evidence; mark missing evidence explicitly.",
                "Do not claim an action, message, payment, booking or external change occurred.",
                "Do not change Board targets. Escalate material variance to COO and Board.",
                "Return JSON only with summary, yesterday_results, today_plan, outstanding, risks, target_variance, decisions_needed and actions.",
            ],
        }
        try:
            raw = self.models._invoke(selection, json.dumps(prompt, ensure_ascii=False, separators=(",", ":")))
            parsed = self._parse_position(raw)
            parsed.update({"department": department, "role_title": role["title"],
                           "source_ids": source_ids, "retrieval_state": fact.get("retrieval_state"),
                           "model_selection": self._public_selection(selection), "model_status": "answered"})
            return parsed
        except Exception as exc:
            fallback = self._evidence_fallback(department, role, fact, selection)
            fallback["model_error"] = f"{type(exc).__name__}:{str(exc)[:180]}"
            return fallback

    def _critic_review(
        self, runtime: dict[str, Any], board_context: dict[str, Any], positions: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        configured = dict((self._config(runtime).get("critic_model_selection") or {}))
        if not configured:
            return {"reasoning_mode": "single_model_role_separated", "departments": {},
                    "disclosure": "No separately accepted critic model is configured."}
        selection = self.models.resolve_model({"coo_model_selection": configured})
        primary = self.models.resolve_model(runtime)
        if selection.get("status") != "selected" or (
            selection.get("provider"), selection.get("model")
        ) == (primary.get("provider"), primary.get("model")):
            return {"reasoning_mode": "single_model_role_separated", "departments": {},
                    "disclosure": "The configured critic is unavailable or is the same model as the primary.",
                    "critic_model_selection": self._public_selection(selection)}
        prompt = {
            "role": "Independent executive meeting challenger",
            "board_context": _bounded(board_context), "department_positions": _bounded(positions),
            "rules": ["Challenge unsupported claims and cross-department conflicts only.",
                      "Never invent business data or claim work was executed."],
            "output": "JSON only: {departments:{sales:{challenge,decision_needed},...},executive_risks:[]}",
        }
        try:
            raw = self.models._invoke(selection, json.dumps(prompt, ensure_ascii=False, separators=(",", ":")))
            value = self._parse_json(raw)
            departments = value.get("departments") if isinstance(value.get("departments"), Mapping) else {}
            return {"reasoning_mode": "two_model_challenge", "departments": _bounded(departments),
                    "executive_risks": [_clean_text(item, 300) for item in list(value.get("executive_risks") or [])[:12]],
                    "critic_model_selection": self._public_selection(selection),
                    "disclosure": "A separately accepted model challenged the departmental positions."}
        except Exception as exc:
            return {"reasoning_mode": "single_model_role_separated", "departments": {},
                    "disclosure": "The critic model did not return a valid review.",
                    "critic_error": f"{type(exc).__name__}:{str(exc)[:180]}",
                    "critic_model_selection": self._public_selection(selection)}

    @classmethod
    def _parse_json(cls, raw: Mapping[str, Any] | str) -> dict[str, Any]:
        value: Any = raw.get("content") if isinstance(raw, Mapping) and "content" in raw else raw
        if isinstance(value, str):
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", value.strip(), flags=re.IGNORECASE)
            start = cleaned.find("{")
            if start < 0:
                raise ValueError("executive_model_response_missing_json")
            value, _ = json.JSONDecoder().raw_decode(cleaned[start:])
        if not isinstance(value, Mapping):
            raise ValueError("executive_model_response_must_be_object")
        return dict(value)

    @classmethod
    def _parse_position(cls, raw: Mapping[str, Any] | str) -> dict[str, Any]:
        value = cls._parse_json(raw)
        summary = _clean_text(value.get("summary"), 3_000)
        if not summary:
            raise ValueError("department_position_missing_summary")
        result: dict[str, Any] = {"summary": summary}
        for key in ("yesterday_results", "today_plan", "outstanding", "risks", "decisions_needed", "actions"):
            result[key] = [_clean_text(item, 500) for item in list(value.get(key) or [])[:12] if _clean_text(item, 500)]
        result["target_variance"] = _clean_text(value.get("target_variance"), 1_000)
        return result

    def _evidence_fallback(
        self, department: str, role: Mapping[str, str], fact: Mapping[str, Any], selection: Mapping[str, Any],
    ) -> dict[str, Any]:
        data = fact.get("data") if isinstance(fact.get("data"), Mapping) else {}
        available = bool(data)
        source_ids = [str(item)[:160] for item in fact.get("source_ids") or []]
        summary = (
            f"{role['title']} evidence is available from {', '.join(source_ids)}; "
            "the selected Vault model was unavailable, so no executive judgement or invented plan was added."
            if available else
            f"No authorised {role['title']} evidence is currently published. The briefing records this as unknown."
        )
        return {"department": department, "role_title": role["title"],
                "summary": summary, "yesterday_results": [], "today_plan": [], "outstanding": [],
                "risks": ["Department evidence or model judgement is incomplete."], "target_variance": "Unknown",
                "decisions_needed": [], "actions": [], "source_ids": source_ids,
                "retrieval_state": fact.get("retrieval_state") or "not_published",
                "model_selection": self._public_selection(selection), "model_status": "unavailable"}

    def _board_context(self, workspace_id: str, person_id: str) -> dict[str, Any]:
        try:
            data = dict(self.provider.read_surface(workspace_id, "briefings", persona_id=person_id).get("data") or {})
        except (OSError, ValueError, PermissionError, KeyError):
            data = {}
        return {
            "latest_board_meetings": [dict(item) for item in data.get("meeting_history") or [] if isinstance(item, Mapping)][:5],
            "board_actions": [dict(item) for item in data.get("department_actions") or [] if isinstance(item, Mapping)][:30],
            "business_pulse": _bounded(data.get("pulse") or {}),
            "source_state": "published" if data else "not_published",
        }

    @staticmethod
    def _minutes_text(
        local_now: datetime, role: Mapping[str, str], position: Mapping[str, Any], challenge: Mapping[str, Any],
    ) -> str:
        lines = [f"Morning minutes {local_now.strftime('%d/%m/%Y')} — {role['title']}", _clean_text(position.get("summary"), 3_000)]
        sections = (("Yesterday", "yesterday_results"), ("Today", "today_plan"),
                    ("Outstanding", "outstanding"), ("Risks", "risks"),
                    ("Actions", "actions"), ("COO decisions", "decisions_needed"))
        for label, key in sections:
            values = [_clean_text(item, 500) for item in list(position.get(key) or []) if _clean_text(item, 500)]
            if values:
                lines.append(f"{label}: " + "; ".join(values))
        variance = _clean_text(position.get("target_variance"), 1_000)
        if variance:
            lines.append(f"Target position: {variance}")
        if challenge:
            text = _clean_text(challenge.get("challenge"), 800)
            decision = _clean_text(challenge.get("decision_needed"), 500)
            if text:
                lines.append(f"Independent challenge: {text}")
            if decision:
                lines.append(f"Challenge decision: {decision}")
        return "\n\n".join(lines)[:8_000]

    def _append(
        self, runtime: dict[str, Any], *, department: str, role: str, sender: str,
        content: str, message_type: str, evidence: list[str] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        turns = self._turns(runtime)
        previous_hash = str(turns[-1].get("record_hash") or "") if turns else ""
        record = {
            "id": f"exec-msg-{uuid4().hex}", "sequence": len(turns), "department_id": department,
            "role": role, "sender": _clean_text(sender, 100), "content": str(content or "")[:8_000],
            "message_type": message_type, "created_at": utc_now_iso(),
            "evidence_source_ids": [str(item)[:160] for item in list(evidence or [])[:24]],
            "metadata": _bounded(dict(metadata or {})), "approval_gated": True,
            "external_writes_performed": False, "previous_record_hash": previous_hash or None,
        }
        record["record_hash"] = canonical_hash(record)
        turns.append(record)
        runtime[EXECUTIVE_CHANNEL_STORE_KEY] = {
            "schema_version": "operations_executive_channel_v1", "turns": turns[-1_200:],
            "updated_at": record["created_at"],
        }
        return record

    @staticmethod
    def _turns(runtime: Mapping[str, Any]) -> list[dict[str, Any]]:
        store = runtime.get(EXECUTIVE_CHANNEL_STORE_KEY) if isinstance(runtime.get(EXECUTIVE_CHANNEL_STORE_KEY), Mapping) else {}
        turns = [dict(item) for item in store.get("turns") or [] if isinstance(item, Mapping)]
        if turns:
            return turns
        # Read legacy executive records once, without admitting direct founder ↔
        # Department Pilot turns into the executive channel.
        legacy = runtime.get("shared_conversations") if isinstance(runtime.get("shared_conversations"), Mapping) else {}
        return [
            dict(item) for item in legacy.get("turns") or []
            if isinstance(item, Mapping) and str(item.get("message_type") or "") in EXECUTIVE_MESSAGE_TYPES
        ]

    def _runtime(self, workspace_id: str) -> dict[str, Any]:
        return self.repository.load_optional_dict(workspace_id, "operational_runtime_summary") or {
            "workspace_id": workspace_id, "kind": "operational_runtime_summary"
        }

    @staticmethod
    def _config(runtime: Mapping[str, Any]) -> dict[str, Any]:
        saved = runtime.get("executive_briefing_config") if isinstance(runtime.get("executive_briefing_config"), Mapping) else {}
        return {"enabled": saved.get("enabled", True), "local_time": str(saved.get("local_time") or "08:00")[:5],
                "timezone": str(saved.get("timezone") or "Europe/Madrid")[:80],
                "critic_model_selection": dict(saved.get("critic_model_selection") or {})}

    @staticmethod
    def _local_now(config: Mapping[str, Any]) -> datetime:
        try:
            zone = ZoneInfo(str(config.get("timezone") or "Europe/Madrid"))
        except Exception:
            zone = ZoneInfo("UTC")
        return datetime.now(zone)

    @staticmethod
    def _public_selection(selection: Mapping[str, Any]) -> dict[str, Any]:
        return {key: selection.get(key) for key in ("status", "provider", "model", "source", "release_status", "reason")}

    def _channel_summary(
        self, runtime: Mapping[str, Any], department: str, role: Mapping[str, str],
    ) -> dict[str, Any]:
        turns = [item for item in self._turns(runtime) if item.get("department_id") == department]
        latest = turns[-1] if turns else {}
        return {"department_id": department, "display_name": role.get("name") or role["title"],
                "message_count": len(turns), "latest_at": latest.get("created_at"),
                "latest_type": latest.get("message_type"),
                "open_action_count": sum(len((item.get("metadata") or {}).get("actions") or []) for item in turns[-20:])}
