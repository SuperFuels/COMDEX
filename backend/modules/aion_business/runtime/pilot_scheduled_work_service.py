from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import re
from threading import RLock
from typing import Any, Callable
from uuid import uuid4

from backend.modules.aion_business.contracts.department_pilot import canonical_contract_hash
from backend.modules.aion_business.runtime.business_knowledge_service import BusinessKnowledgeService
from backend.modules.aion_business.runtime.organization_authority_service import OrganizationAuthorityService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.sales_completion_service import SalesCompletionService
from backend.modules.aion_business.runtime.sales_revenue_service import SalesRevenueService


_LOCK = RLock()
SUPPORTED_JOB_TYPES = {"sales_inbox_monitor", "morning_business_briefing", "custom_prompt"}
SUPPORTED_POLICIES = {"prepare_only", "approval_required"}


def _now_dt() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _now() -> str:
    return _now_dt().isoformat()


def _parse_time(value: str | None) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return datetime.min.replace(tzinfo=UTC)


def _safe(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or "")).strip("-")


class PilotScheduledWorkService:
    """Durable, local Pilot jobs with an exact approval boundary.

    A scheduled job may read evidence and prepare work. It cannot silently send
    a message, move money, or invoke an unregistered computer-control adapter.
    """

    def __init__(
        self,
        *,
        base_dir: str | Path | None = None,
        authority: OrganizationAuthorityService | None = None,
        revenue: SalesRevenueService | None = None,
        completion: SalesCompletionService | None = None,
        knowledge: BusinessKnowledgeService | None = None,
        gmail_fetcher: Callable[[str, int], list[dict[str, Any]]] | None = None,
    ) -> None:
        self.base_dir = Path(base_dir) if base_dir else AIONBusinessPaths.BUSINESS_CONTAINERS
        self.authority = authority or OrganizationAuthorityService()
        self.revenue = revenue or SalesRevenueService()
        self.completion = completion or SalesCompletionService()
        self.knowledge = knowledge or BusinessKnowledgeService(self.base_dir)
        self.gmail_fetcher = gmail_fetcher

    def _root(self, workspace_id: str) -> Path:
        root = self.base_dir / workspace_id / "pilot" / "scheduled_work"
        (root / "runs").mkdir(parents=True, exist_ok=True)
        (root / "artifacts").mkdir(parents=True, exist_ok=True)
        return root

    def _index_path(self, workspace_id: str) -> Path:
        return self._root(workspace_id) / "schedules.json"

    def _load(self, workspace_id: str) -> dict[str, Any]:
        path = self._index_path(workspace_id)
        if not path.exists():
            return {"schema_version": "aion.pilot.scheduled_work.v1", "workspace_id": workspace_id,
                    "revision": 0, "schedules": [], "updated_at": None}
        payload = json.loads(path.read_text(encoding="utf-8"))
        expected = payload.get("index_hash")
        stable = dict(payload); stable.pop("index_hash", None)
        if not expected or canonical_contract_hash(stable) != expected:
            raise ValueError("pilot_schedule_index_hash_mismatch")
        return payload

    def _save(self, workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        payload["revision"] = int(payload.get("revision") or 0) + 1
        payload["updated_at"] = _now()
        stable = dict(payload); stable.pop("index_hash", None)
        payload["index_hash"] = canonical_contract_hash(stable)
        path = self._index_path(workspace_id)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(path)
        return payload

    def _require_manage(self, workspace_id: str, person_id: str) -> dict[str, Any]:
        for capability in ("department.manage_all", "sales.manage"):
            decision = self.authority.access_decision(workspace_id, person_id=person_id, capability=capability)
            if decision.get("allowed"):
                return decision
        raise PermissionError("pilot_scheduled_work_not_authorised")

    def list(self, workspace_id: str) -> dict[str, Any]:
        payload = self._load(workspace_id)
        schedules = payload.get("schedules") or []
        return {**payload, "summary": {"total": len(schedules),
                "enabled": sum(item.get("enabled") is True for item in schedules),
                "awaiting_approval": sum(int(item.get("awaiting_approval_count") or 0) for item in schedules)}}

    def create(
        self,
        workspace_id: str,
        *,
        title: str,
        job_type: str,
        cadence_minutes: int,
        created_by_person_id: str,
        prompt: str = "",
        query: str | None = None,
        max_results: int = 10,
        enabled: bool = False,
        action_policy: str = "approval_required",
    ) -> dict[str, Any]:
        authority = self._require_manage(workspace_id, created_by_person_id)
        job_type = str(job_type or "").strip()
        if job_type not in SUPPORTED_JOB_TYPES:
            raise ValueError("unsupported_pilot_schedule_job_type")
        if action_policy not in SUPPORTED_POLICIES:
            raise ValueError("unsupported_pilot_schedule_action_policy")
        cadence = int(cadence_minutes)
        if cadence < 5 or cadence > 43_200:
            raise ValueError("pilot_schedule_cadence_must_be_between_5_minutes_and_30_days")
        created = _now_dt()
        schedule = {
            "schema_version": "aion.pilot.schedule.v1",
            "schedule_id": f"pilot_schedule_{uuid4().hex[:16]}",
            "workspace_id": workspace_id,
            "title": str(title or job_type.replace("_", " ").title()).strip()[:160],
            "job_type": job_type,
            "prompt": str(prompt or "").strip()[:4000],
            "query": str(query or "in:inbox (subject:enquiry OR subject:quote OR subject:booking OR subject:estimate)")[:500],
            "max_results": max(1, min(int(max_results), 25)),
            "cadence_minutes": cadence,
            "enabled": bool(enabled),
            "action_policy": action_policy,
            "next_run_at": (created + timedelta(minutes=cadence)).isoformat() if enabled else None,
            "last_run_at": None,
            "last_run_id": None,
            "run_count": 0,
            "failure_count": 0,
            "awaiting_approval_count": 0,
            "created_at": created.isoformat(),
            "created_by_person_id": created_by_person_id,
            "authority_decision": authority,
            "external_side_effects": "forbidden_during_schedule_run",
        }
        schedule["schedule_hash"] = canonical_contract_hash(schedule)
        with _LOCK:
            payload = self._load(workspace_id)
            payload["schedules"].append(schedule)
            self._save(workspace_id, payload)
        return schedule

    def set_enabled(self, workspace_id: str, schedule_id: str, *, enabled: bool,
                    changed_by_person_id: str) -> dict[str, Any]:
        authority = self._require_manage(workspace_id, changed_by_person_id)
        with _LOCK:
            payload = self._load(workspace_id)
            schedule = next((item for item in payload["schedules"] if item.get("schedule_id") == schedule_id), None)
            if not schedule:
                raise FileNotFoundError(schedule_id)
            schedule.update({"enabled": bool(enabled), "next_run_at": (
                _now_dt() + timedelta(minutes=int(schedule["cadence_minutes"]))).isoformat() if enabled else None,
                "changed_at": _now(), "changed_by_person_id": changed_by_person_id,
                "change_authority": authority})
            schedule.pop("schedule_hash", None); schedule["schedule_hash"] = canonical_contract_hash(schedule)
            self._save(workspace_id, payload)
            return schedule

    def run_due(self, workspace_id: str, *, now: datetime | None = None) -> list[dict[str, Any]]:
        instant = (now or _now_dt()).astimezone(UTC)
        payload = self._load(workspace_id)
        due_ids = [item["schedule_id"] for item in payload.get("schedules") or []
                   if item.get("enabled") and _parse_time(item.get("next_run_at")) <= instant]
        return [self.run(workspace_id, schedule_id, due_at=instant) for schedule_id in due_ids]

    def run(self, workspace_id: str, schedule_id: str, *, due_at: datetime | None = None) -> dict[str, Any]:
        with _LOCK:
            payload = self._load(workspace_id)
            schedule = next((item for item in payload["schedules"] if item.get("schedule_id") == schedule_id), None)
            if not schedule:
                raise FileNotFoundError(schedule_id)
            schedule_snapshot = dict(schedule)
        started = (due_at or _now_dt()).astimezone(UTC)
        run = {"schema_version": "aion.pilot.scheduled_run.v1", "run_id": f"pilot_run_{uuid4().hex[:16]}",
               "workspace_id": workspace_id, "schedule_id": schedule_id, "job_type": schedule["job_type"],
               "started_at": started.isoformat(), "status": "running", "external_side_effects": []}
        try:
            if schedule["job_type"] == "sales_inbox_monitor":
                result = self._run_sales_inbox(workspace_id, schedule_snapshot, run["run_id"])
            else:
                result = {"status": "prepared_for_pilot", "prompt": schedule.get("prompt"),
                          "human_review_required": True, "external_side_effects": []}
            run.update({"status": "completed", "result": result,
                        "awaiting_approval_count": int(result.get("awaiting_approval_count") or 0)})
        except Exception as exc:
            run.update({"status": "failed", "error": f"{type(exc).__name__}:{exc}", "result": {}})
        run["completed_at"] = _now()
        run["run_hash"] = canonical_contract_hash(run)
        (self._root(workspace_id) / "runs" / f"{_safe(run['run_id'])}.json").write_text(
            json.dumps(run, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with _LOCK:
            payload = self._load(workspace_id)
            current = next(item for item in payload["schedules"] if item.get("schedule_id") == schedule_id)
            current["last_run_at"] = run["completed_at"]
            current["last_run_id"] = run["run_id"]
            current["run_count"] = int(current.get("run_count") or 0) + 1
            current["failure_count"] = int(current.get("failure_count") or 0) + (run["status"] == "failed")
            current["awaiting_approval_count"] = int(run.get("awaiting_approval_count") or 0)
            current["next_run_at"] = (started + timedelta(minutes=int(current["cadence_minutes"]))).isoformat() if current.get("enabled") else None
            current.pop("schedule_hash", None); current["schedule_hash"] = canonical_contract_hash(current)
            self._save(workspace_id, payload)
        return run

    def _fetch_gmail(self, query: str, max_results: int) -> list[dict[str, Any]]:
        if self.gmail_fetcher:
            return self.gmail_fetcher(query, max_results)
        from backend.api.local_node_router import get_runtime
        result = get_runtime().fetch_gmail_messages_readonly(query=query, max_results=max_results)
        if isinstance(result, dict):
            return list(result.get("messages") or result.get("items") or [])
        return list(result or [])

    def _run_sales_inbox(self, workspace_id: str, schedule: dict[str, Any], run_id: str) -> dict[str, Any]:
        actor = str(schedule.get("created_by_person_id") or "")
        messages = self._fetch_gmail(str(schedule.get("query") or ""), int(schedule.get("max_results") or 10))
        imported = self.revenue.import_gmail_messages(workspace_id, messages=messages,
                                                       imported_by_person_id=actor)
        prepared: list[dict[str, Any]] = []
        for opportunity in imported.get("opportunities") or []:
            enquiry = str(opportunity.get("enquiry") or opportunity.get("title") or "customer enquiry")
            recalled = self.knowledge.search(workspace_id, enquiry, actor_scope="sales", limit=5)
            facts = recalled.get("matches") or []
            body = self._sales_reply_body(opportunity, facts)
            message = self.completion.prepare_message(
                workspace_id, opportunity["opportunity_id"], channel="email",
                purpose="inbound_sales_enquiry_response", subject=f"Re: {opportunity.get('title') or 'Your enquiry'}",
                body=body, prepared_by_person_id=actor)
            artifact = self._write_client_artifact(workspace_id, run_id, opportunity, facts, message)
            prepared.append({"opportunity_id": opportunity["opportunity_id"], "message_id": message["message_id"],
                             "message_hash": message["message_hash"], "status": message["status"],
                             "knowledge_receipt": recalled.get("receipt"), "artifact": artifact})
        return {"status": "approval_required" if prepared else "no_new_enquiries",
                "messages_read": len(messages), "imported": imported.get("imported", 0),
                "deduplicated": imported.get("deduplicated", 0), "prepared": prepared,
                "awaiting_approval_count": len(prepared), "external_messages_sent": 0,
                "gmail_mutated": False, "human_review_required": bool(prepared),
                "next_step": "approve exact message payload, then create a Gmail draft" if prepared else None}

    @staticmethod
    def _sales_reply_body(opportunity: dict[str, Any], facts: list[dict[str, Any]]) -> str:
        name = str((opportunity.get("contact") or {}).get("name") or "there").split(" ", 1)[0]
        lines = [f"Hello {name},", "", "Thank you for getting in touch. We have received your enquiry and are reviewing it."]
        if facts:
            lines.extend(["", "The following verified business information may help:"])
            lines.extend(f"- {str(item.get('text') or '').strip()}" for item in facts[:3])
        lines.extend(["", "To make sure we give you the right answer, please reply with any missing scope, location, timing or quantity details.",
                      "", "A person will review the details before any price, availability, booking or commitment is confirmed.",
                      "", "Kind regards"])
        return "\n".join(lines)

    def _write_client_artifact(self, workspace_id: str, run_id: str, opportunity: dict[str, Any],
                               facts: list[dict[str, Any]], message: dict[str, Any]) -> dict[str, Any]:
        payload = {"schema_version": "aion.pilot.sales_enquiry_artifact.v1", "workspace_id": workspace_id,
                   "run_id": run_id, "opportunity_id": opportunity.get("opportunity_id"),
                   "customer": opportunity.get("contact"), "enquiry": opportunity.get("enquiry"),
                   "approved_business_facts": [{"claim_id": item.get("claim_id"), "source_hash": item.get("source_hash"),
                                                "text": item.get("text")} for item in facts],
                   "draft_message_id": message.get("message_id"), "draft_payload_hash": message.get("payload_hash"),
                   "status": "human_review_required", "created_at": _now()}
        payload["artifact_hash"] = canonical_contract_hash(payload)
        path = self._root(workspace_id) / "artifacts" / f"{_safe(payload['opportunity_id'])}-{_safe(run_id)}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {"local_path": str(path), "artifact_hash": payload["artifact_hash"], "status": payload["status"]}
