from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
from typing import Any, Mapping, Protocol, Sequence
from uuid import uuid4

from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash, utc_now_iso
from backend.modules.aion_fabric.identity import DeviceIdentity
from backend.modules.aion_business.runtime.organization_authority_service import OrganizationAuthorityService
from backend.modules.aion_business.runtime.finance_sales_service import FinanceSalesService
from backend.modules.aion_business.runtime.sales_revenue_service import SalesRevenueService
from backend.modules.aion_business.runtime.support_case_service import SupportCaseService
from backend.modules.aion_business.runtime.work_schedule_service import WorkScheduleService
from backend.services.aion_mission_mode.coo_mission import CooMissionService

from .compatibility import adapt_workspace
from .contracts import Invitation, InvitationState, Membership, SpaceRef, SurfaceManifest
from .pairing import MobilePairingAuthority


class AionBoardroomWorkspaceProvider:
    """Read-only mobile projection over the existing AION Business repositories."""

    provider_id = "aion-boardroom"
    CORE_DEPARTMENTS = frozenset({"sales", "marketing", "finance", "operations", "support", "people"})
    CUSTOM_TEMPLATES = {
        "innovation": "Innovation Director",
        "legal": "Legal & Compliance Director",
        "compliance": "Compliance Director",
        "it": "Technology Director",
        "technical": "Technical Director",
        "product": "Product Director",
        "research": "Research Director",
        "partnerships": "Partnerships Director",
    }

    def __init__(
        self,
        workspace_repository: Any,
        container_repository: Any,
        department_repository: Any,
        finance_conversation_service: Any | None = None,
        file_repository: Any | None = None,
        boardroom_ledger_root: Path | None = None,
        support_case_service: Any | None = None,
        organization_authority_service: Any | None = None,
        sales_revenue_service: Any | None = None,
        finance_sales_service: Any | None = None,
        coo_mission_service: Any | None = None,
        calendar_snapshot_loader: Any | None = None,
    ) -> None:
        self.workspaces = workspace_repository
        self.containers = container_repository
        self.departments = department_repository
        self.finance_conversations = finance_conversation_service
        self.files = file_repository
        self.boardroom_ledger_root = boardroom_ledger_root or Path(".runtime/local_node/boardroom_meetings")
        self.support_cases = support_case_service or SupportCaseService(container_repository)
        self.organization_authority = organization_authority_service or OrganizationAuthorityService(container_repository)
        self.sales_revenue = sales_revenue_service or SalesRevenueService(container_repository)
        self.finance_sales = finance_sales_service or FinanceSalesService(container_repository)
        self.coo_missions = coo_mission_service or CooMissionService()
        self.calendar_snapshot_loader = calendar_snapshot_loader

    def list_workspaces(self) -> Sequence[Mapping[str, Any]]:
        return [self.workspaces.load(item).model_dump(mode="json") for item in self.workspaces.list_ids()]

    def describe_workspace(self, workspace_ref: str) -> Mapping[str, Any]:
        workspace = self.workspaces.load(workspace_ref)
        boardroom = self.containers.load_optional_dict(workspace_ref, "boardroom_snapshot") or {}
        payload = dict(boardroom.get("boardroom") or {})
        departments = [
            {"id": str(item.get("id") or item.get("department_id") or ""), "label": str(item.get("name") or item.get("label") or item.get("id") or "")}
            for item in payload.get("departments", []) if isinstance(item, Mapping)
        ]
        departments.extend({"id": item["id"], "label": item["name"]} for item in self.custom_departments(workspace_ref))
        return {
            "id": workspace_ref,
            "departments": [item for item in departments if item["id"] and item["label"]][:100],
            "agents": [], "dashboards": [{"id": "boardroom", "label": "Boardroom overview"}],
            "files": self._file_catalog(workspace_ref), "packages": [], "decisions": [],
            "permitted_actions": ["workspace.read", "workspace.briefings.read", "workspace.dashboards.read", "workspace.departments.read"],
        }

    def read_surface(self, workspace_ref: str, surface: str, *, persona_id: str) -> Mapping[str, Any]:
        runtime = self.containers.load_optional_dict(workspace_ref, "operational_runtime_summary") or {}
        boardroom = self.containers.load_optional_dict(workspace_ref, "boardroom_snapshot") or {}
        runtime_summary = dict(runtime.get("runtime_summary") or {})
        dashboard = dict(runtime.get("dashboard_summary") or {})
        boardroom_summary = dict(runtime_summary.get("boardroom_summary") or {})
        boardroom_payload = dict(boardroom.get("boardroom") or {})
        if surface in {"overview", "briefings"}:
            source = self._boardroom_mobile_briefing(
                boardroom_summary=boardroom_summary,
                boardroom_payload=boardroom_payload,
                legacy_meeting_history=self._legacy_boardroom_history(workspace_ref),
            )
        elif surface == "dashboards":
            source = dashboard
        elif surface == "departments":
            department_rows = [*boardroom_payload.get("departments", []), *self.custom_departments(workspace_ref)]
            source = {
                "departments": department_rows,
                "executive_members": self._executive_members(department_rows),
                "work": [self._work_summary(item) for item in self.departments.list_for_workspace(workspace_ref)[:50]],
            }
        elif surface == "support":
            source = self._mobile_support_cases(workspace_ref)
        elif surface == "people":
            source = self._mobile_people_directory(workspace_ref)
        elif surface == "sales":
            source = self._mobile_sales_briefing(
                workspace_ref,
                boardroom_summary=boardroom_summary,
                boardroom_payload=boardroom_payload,
            )
        elif surface == "finance":
            source = self._mobile_finance_briefing(workspace_ref)
        elif surface == "work_schedule":
            source = self.work_schedule_snapshot(workspace_ref)
        elif surface == "files":
            source = {"files": self._file_catalog(workspace_ref)}
        else:
            source = {}
        return {
            "revision": int((runtime.get("meta") or {}).get("revision") or 1),
            "data": self._mobile_summary(source),
        }

    def _work_schedule_path(self, workspace_ref: str) -> Path:
        path = Path(self.containers.base_dir) / workspace_ref / "work_schedule.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def work_schedule_snapshot(self, workspace_ref: str) -> dict[str, Any]:
        """Canonical jobs and appointments shared by desktop and paired phones."""
        return WorkScheduleService(self.containers).get(workspace_ref)

    def work_schedule_action(
        self, workspace_ref: str, operation: str, fields: Mapping[str, Any], *, actor_id: str
    ) -> dict[str, Any]:
        if str(operation or "").strip().casefold() == "upload_evidence":
            encoded = str(fields.get("data_base64") or "")
            if len(encoded) > 28_000_000:
                raise ValueError("work evidence exceeds the 20 MB limit")
            result = WorkScheduleService(self.containers).upload(
                workspace_ref, str(fields.get("id") or ""),
                filename=str(fields.get("filename") or "evidence"),
                content_type=str(fields.get("content_type") or "application/octet-stream"),
                data_base64=encoded, actor_id=actor_id,
            )
            return dict(result["schedule"])
        safe_fields = {
            str(key): value for key, value in dict(fields or {}).items()
            if str(key) in {
                "id", "title", "customer", "customer_id", "location", "starts_at", "ends_at",
                "date", "time", "duration", "type", "assignee", "assignee_ids", "resource_ids",
                "skills_required", "status", "notes", "evidence_count", "recurrence", "dependencies",
                "checklist_id", "label", "done", "material_id", "name", "quantity", "unit",
                "unit_cost", "used", "minutes", "note", "movement_type", "kind", "channel", "message",
            }
        }
        if len(str(safe_fields).encode("utf-8")) > 64_000:
            raise ValueError("work schedule update exceeds the size limit")
        # Older phone builds used evidence_count as a button. Preserve that
        # interaction without manufacturing a file that does not exist.
        safe_fields.pop("evidence_count", None)
        return WorkScheduleService(self.containers).action(
            workspace_ref, operation, safe_fields, actor_id=actor_id,
        )

    def _mobile_support_cases(self, workspace_ref: str) -> dict[str, Any]:
        """Bounded Support projection from the canonical case ledger.

        This is deliberately read-only. A phone can see the same status, risk and
        evidence timeline as the desktop Support workspace, but it cannot send a
        response, resolve a case, or create a refund from this surface.
        """
        try:
            workspace = self.support_cases.workspace(workspace_ref)
        except (OSError, ValueError, PermissionError):
            return {"summary": {"status": "unavailable"}, "support_cases": []}
        cases: list[dict[str, Any]] = []
        for raw in workspace.get("cases") or []:
            if not isinstance(raw, Mapping):
                continue
            events = []
            for event in list(raw.get("conversation") or [])[-12:]:
                if not isinstance(event, Mapping):
                    continue
                events.append({
                    "direction": str(event.get("direction") or "update")[:40],
                    "channel": str(event.get("channel") or "")[:40],
                    "recorded_at": str(event.get("recorded_at") or "")[:80],
                    "content": " ".join(str(event.get("content") or "").split())[:800],
                })
            flags = [str(item)[:80] for item in raw.get("risk_flags") or [] if str(item).strip()][:12]
            escalation = raw.get("escalation") if isinstance(raw.get("escalation"), Mapping) else {}
            needs_human = str(raw.get("status") or "") == "human_intervention_required" or bool(escalation.get("required"))
            cases.append({
                "id": str(raw.get("case_id") or "")[:120],
                "number": str(raw.get("case_number") or "")[:40],
                "subject": " ".join(str(raw.get("subject") or "Customer support request").split())[:300],
                "customer": " ".join(str((raw.get("customer") or {}).get("name") or "Customer").split())[:160],
                "category": str(raw.get("category") or "unknown")[:80],
                "priority": str(raw.get("priority") or "normal")[:40],
                "status": str(raw.get("status") or "open")[:80],
                "updated_at": str(raw.get("updated_at") or raw.get("created_at") or "")[:80],
                "risk_flags": flags,
                "needs_human": needs_human,
                "human_request": "A customer or policy risk needs your direction before Support can continue." if needs_human else "",
                "timeline": events,
            })
        return {"summary": dict(workspace.get("summary") or {}), "support_cases": cases[:50]}

    def _mobile_sales_briefing(
        self, workspace_ref: str, *, boardroom_summary: Mapping[str, Any], boardroom_payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        """A bounded, evidence-led Sales opening brief for a founder's phone.

        Pipeline activity is read from the canonical Sales revenue spine. Board
        actions are read from the signed Boardroom projection. Missing connectors
        stay explicitly unavailable rather than being inferred as cash, quotes or
        Executive decisions.
        """
        today = datetime.now(timezone.utc).date().isoformat()
        try:
            opportunities = [item for item in self.sales_revenue.list_opportunities(workspace_ref) if isinstance(item, Mapping)]
        except (OSError, ValueError, PermissionError):
            opportunities = []

        def occurred_today(row: Mapping[str, Any]) -> bool:
            return any(str(row.get(field) or "").startswith(today) for field in ("created_at", "updated_at"))

        today_rows = [row for row in opportunities if occurred_today(row)]
        open_rows = [row for row in opportunities if str(row.get("status") or "") == "open"]
        closed = [row for row in opportunities if str(row.get("stage") or "") in {"won", "lost"}]
        won = [row for row in opportunities if str(row.get("stage") or "") == "won"]
        quote_events = [
            event for row in opportunities for event in (row.get("activities") or [])
            if isinstance(event, Mapping) and str(event.get("kind") or "") in {"quote_draft", "quote_approved", "quote_sent"}
            and str(event.get("created_at") or "").startswith(today)
        ]
        deposit_events = [
            event for row in opportunities for event in (row.get("activities") or [])
            if isinstance(event, Mapping) and str(event.get("kind") or "") == "payment_recorded"
            and str(event.get("created_at") or "").startswith(today)
        ]
        follow_ups = [
            row for row in open_rows
            if str((row.get("relationship") or {}).get("next_action") or "").strip()
        ]
        briefing = self._boardroom_mobile_briefing(
            boardroom_summary=boardroom_summary,
            boardroom_payload=boardroom_payload,
            legacy_meeting_history=self._legacy_boardroom_history(workspace_ref),
        )
        sales_actions = [action for action in briefing["department_actions"] if str(action.get("department") or "").casefold() == "sales"]
        conversion = round((len(won) / len(closed)) * 100) if closed else None
        return {
            "sales_briefing": {
                "date": today,
                "headline": "Today’s Sales briefing",
                "message": "This card refreshes from the Sales ledger during the day. It shows recorded activity only.",
                "metrics": {
                    "leads_today": sum(str(row.get("stage") or "") == "new" for row in today_rows),
                    "activity_today": len(today_rows),
                    "quotes_today": len(quote_events),
                    "follow_ups_open": len(follow_ups),
                    "deposits_today": len(deposit_events),
                    "won_total": len(won),
                    "conversion_closed_percent": conversion,
                    "sales_generated_today": None,
                },
                "availability": {
                    "sales_generated_today": "No settled-sales or invoice connector is published to the Sales ledger yet.",
                    "cash_flow": "No Finance cash-position update is published to this Sales briefing yet.",
                    "executive_meeting": "No Executive meeting record has been published to the mobile ledger for today.",
                },
                "board_actions": sales_actions,
                "today_queue": [
                    {"title": str(row.get("title") or "Sales opportunity")[:200], "stage": str(row.get("stage") or "")[:80],
                     "next_action": str((row.get("relationship") or {}).get("next_action") or "Review opportunity")[:240]}
                    for row in open_rows[:8]
                ],
                "governance": "A Board objective is not changed in Sales chat. Give Sales Pilot the feedback and it will be prepared for the COO or Executive meeting to review with Finance and Marketing.",
            }
        }

    def _coo_sales_today_answer(self, workspace_ref: str) -> tuple[str, list[dict[str, Any]], str]:
        """Answer a COO daily-sales question from the canonical ledger only.

        A completed sale cannot be inferred from leads, quotes, or activity.  The
        response therefore separates recorded commercial activity from settled
        sales until an invoice or payment connector publishes that evidence.
        """
        boardroom = self.containers.load_optional_dict(workspace_ref, "boardroom_snapshot") or {}
        runtime = self.containers.load_optional_dict(workspace_ref, "operational_runtime_summary") or {}
        briefing = self._mobile_sales_briefing(
            workspace_ref,
            boardroom_summary=dict(runtime.get("runtime_summary") or {}).get("boardroom_summary") or {},
            boardroom_payload=dict(boardroom.get("boardroom") or {}),
        ).get("sales_briefing") or {}
        metrics = dict(briefing.get("metrics") or {})
        availability = dict(briefing.get("availability") or {})
        today = str(briefing.get("date") or datetime.now(timezone.utc).date().isoformat())
        sales_value = metrics.get("sales_generated_today")
        evidence = [{"source": "sales_revenue_spine", "date": today, "metrics": {
            key: metrics.get(key) for key in ("leads_today", "activity_today", "quotes_today", "deposits_today", "sales_generated_today")
        }}]
        if isinstance(sales_value, (int, float)) and not isinstance(sales_value, bool):
            return (f"Sales briefing for {today}: recorded settled sales are €{float(sales_value):,.2f}. "
                    f"The Sales ledger also shows {metrics.get('activity_today', 0)} activity record(s), "
                    f"{metrics.get('quotes_today', 0)} quote event(s), and {metrics.get('deposits_today', 0)} payment record(s) today.", evidence, "sales_ledger_backed")
        return (f"I checked the Sales ledger for {today}. It records {metrics.get('activity_today', 0)} activity record(s), "
                f"{metrics.get('quotes_today', 0)} quote event(s), and {metrics.get('deposits_today', 0)} payment record(s) today. "
                f"I cannot state a settled-sales value yet because {availability.get('sales_generated_today') or 'no settled-sales evidence is published.'}", evidence, "sales_ledger_incomplete")

    @staticmethod
    def _is_outstanding_invoice_question(lowered: str) -> bool:
        return "invoice" in lowered and any(term in lowered for term in ("outstanding", "unpaid", "overdue", "due"))

    @staticmethod
    def _is_calendar_question(lowered: str) -> bool:
        # A request about what was discussed or decided belongs to the Boardroom
        # minutes ledger, even when it says "today's meeting". Personal calendar
        # routing is only for diary/attendance questions.
        if any(term in lowered for term in (
            "discussed", "decided", "minutes", "notes", "overview", "brief", "recap", "plan", "action",
        )):
            return False
        personal_calendar = any(term in lowered for term in ("appointment", "calendar"))
        timed_schedule = any(term in lowered for term in ("meeting", "schedule")) and any(
            term in lowered for term in ("tomorrow", "today", "next", "booked", "upcoming")
        )
        return personal_calendar or timed_schedule

    def _coo_outstanding_invoice_answer(self, workspace_ref: str) -> tuple[str, list[dict[str, Any]], str]:
        invoices = [dict(item) for item in self.finance_sales.list_invoices(workspace_ref) if isinstance(item, Mapping)]
        outstanding = [item for item in invoices if float(item.get("amount_due") or 0) > 0 and str(item.get("status") or "").casefold() != "voided"]
        total = round(sum(float(item.get("amount_due") or 0) for item in outstanding), 2)
        today = datetime.now(timezone.utc).date()
        overdue = []
        for item in outstanding:
            try:
                if datetime.fromisoformat(str(item.get("due_date") or "")[:10]).date() < today:
                    overdue.append(item)
            except ValueError:
                continue
        currencies = {str(item.get("currency") or "EUR").upper() for item in outstanding}
        currency = currencies.pop() if len(currencies) == 1 else "EUR"
        symbol = {"EUR": "€", "EURO": "€", "EUROS": "€", "GBP": "£", "USD": "$"}.get(currency, currency + " ")
        evidence = [{
            "source": "finance_sales_invoice_ledger", "invoice_count": len(invoices),
            "outstanding_count": len(outstanding), "outstanding_amount": total,
            "overdue_count": len(overdue), "read_only": True,
        }]
        if not outstanding:
            return ("The invoice ledger has no outstanding invoices. This was a read-only lookup; no external action was taken.", evidence, "invoice_ledger_backed")
        overdue_total = round(sum(float(item.get("amount_due") or 0) for item in overdue), 2)
        suffix = f" {len(overdue)} of them are overdue, totalling {symbol}{overdue_total:,.2f}." if overdue else " None are overdue."
        return (f"Yes. The invoice ledger has {len(outstanding)} outstanding invoice(s), totalling {symbol}{total:,.2f}.{suffix} "
                "This was a read-only lookup; no external action was taken.", evidence, "invoice_ledger_backed")

    def _coo_calendar_answer(self, persona_id: str, lowered: str) -> tuple[str, list[dict[str, Any]], str]:
        if not callable(self.calendar_snapshot_loader):
            return ("I can’t check your appointments because no private calendar is connected to this Operations session. "
                    "No external action was taken.", [], "calendar_unavailable")
        try:
            snapshot = dict(self.calendar_snapshot_loader(persona_id) or {})
        except (OSError, ValueError, PermissionError, RuntimeError, KeyError):
            return ("I can’t check your appointments because the private calendar is not available to this Operations session. "
                    "No external action was taken.", [], "calendar_unavailable")
        if snapshot.get("connected") is not True:
            return ("I can’t check your appointments because no private calendar is connected to this Operations session. "
                    "No external action was taken.", [], "calendar_not_connected")
        try:
            from zoneinfo import ZoneInfo
            local_zone = ZoneInfo(str(snapshot.get("time_zone") or "Europe/Madrid"))
        except Exception:
            local_zone = timezone.utc
        now = datetime.now(local_zone)
        target = now.date() + timedelta(days=1) if "tomorrow" in lowered else now.date()
        events = []
        for raw in snapshot.get("events") or []:
            if not isinstance(raw, Mapping) or str(raw.get("status") or "confirmed") == "cancelled":
                continue
            try:
                start = datetime.fromisoformat(str(raw.get("start") or "").replace("Z", "+00:00")).astimezone(local_zone)
            except ValueError:
                continue
            if start.date() == target:
                events.append((start, dict(raw)))
        events.sort(key=lambda item: item[0])
        evidence = [{"source": "normalized_private_calendar", "date": target.isoformat(), "event_count": len(events), "read_only": True}]
        if not events:
            return (f"Your connected calendar has no appointments recorded for {target.strftime('%A, %d %B')}. "
                    "This was a read-only lookup; no external action was taken.", evidence, "private_calendar_backed")
        rendered = []
        for start, event in events[:8]:
            title = " ".join(str(event.get("title") or "Busy").split())[:120]
            rendered.append(f"{start.strftime('%H:%M')} — {title}")
        return (f"You have {len(events)} appointment(s) on {target.strftime('%A, %d %B')}: " + "; ".join(rendered) +
                ". This was a read-only lookup; no external action was taken.", evidence, "private_calendar_backed")

    @staticmethod
    def _coo_direct_response(
        workspace_ref: str, answer: str, evidence: list[dict[str, Any]], reliability: str, provider: str,
    ) -> dict[str, Any]:
        return {
            "conversation_id": f"coo-mission-{workspace_ref}", "department_id": "operations",
            "turn": {"turn_id": f"coo-turn-{uuid4().hex}", "role": "assistant", "content": answer, "created_at": utc_now_iso()},
            "provider": {"provider": provider, "model": None}, "evidence": evidence,
            "reliability": reliability, "external_writes_performed": False, "approval_gated": True,
        }

    def _coo_department_fact(self, workspace_ref: str, department: str, *, persona_id: str) -> dict[str, Any]:
        """Load one bounded authoritative projection for the COO fact pack."""
        sources = {
            "finance": ["business_financial_model", "finance_sales_ledger"],
            "sales": ["sales_revenue_spine", "boardroom_snapshot"],
            "marketing": ["department_intelligence.marketing", "boardroom_snapshot"],
            "operations": ["department_work_queue", "operational_runtime_summary"],
            "support": ["support_case_ledger"],
            "people": ["organization_authority"],
            "products_services": ["business_operating_model.offerings", "business_operating_model.unit_economics"],
        }
        if department in {"finance", "sales", "support", "people"}:
            surface = self.read_surface(workspace_ref, department, persona_id=persona_id)
            data = dict(surface.get("data") or {})
        elif department == "operations":
            surface = self.read_surface(workspace_ref, "departments", persona_id=persona_id)
            raw = dict(surface.get("data") or {})
            briefing = dict(self.read_surface(workspace_ref, "briefings", persona_id=persona_id).get("data") or {})
            data = {
                "work": [
                    item for item in raw.get("work") or []
                    if isinstance(item, Mapping) and str(item.get("department_id") or "").casefold() == "operations"
                ][:20],
                "meeting_history": [dict(item) for item in briefing.get("meeting_history") or [] if isinstance(item, Mapping)][:12],
                "department_actions": [dict(item) for item in briefing.get("department_actions") or [] if isinstance(item, Mapping)][:30],
            }
        elif department == "marketing":
            intelligence = self.containers.load_optional_dict(workspace_ref, "department_intelligence") or {}
            marketing = dict((intelligence.get("departments") or {}).get("marketing") or {})
            briefing = dict(self.read_surface(workspace_ref, "briefings", persona_id=persona_id).get("data") or {})
            data = {
                "intelligence": self._bounded_value(marketing, depth=0),
                "department_actions": [dict(item) for item in briefing.get("department_actions") or []
                                       if isinstance(item, Mapping) and str(item.get("department") or "").casefold() == "marketing"][:30],
            }
        elif department == "products_services":
            operating = self.containers.load_optional_dict(workspace_ref, "business_operating_model") or {}
            data = {
                "currency": operating.get("currency") or "EUR",
                "offerings": [dict(item) for item in operating.get("offerings") or [] if isinstance(item, Mapping)][:100],
                "unit_economics": [dict(item) for item in operating.get("unit_economics") or [] if isinstance(item, Mapping)][:100],
                "inventory_metrics": dict(operating.get("inventory_metrics") or {}),
            }
        else:
            custom = next(
                (item for item in self.custom_departments(workspace_ref) if item["id"] == department), None,
            )
            if custom is None:
                raise ValueError("unsupported_coo_department")
            surface = self.read_surface(workspace_ref, "departments", persona_id=persona_id)
            raw = dict(surface.get("data") or {})
            briefing = dict(self.read_surface(workspace_ref, "briefings", persona_id=persona_id).get("data") or {})
            data = {
                "department": self._bounded_value(custom, depth=0),
                "work": [
                    dict(item) for item in raw.get("work") or []
                    if isinstance(item, Mapping)
                    and str(item.get("department_id") or "").casefold() == department
                ][:30],
                "department_actions": [
                    dict(item) for item in briefing.get("department_actions") or []
                    if isinstance(item, Mapping)
                    and re.sub(r"[^a-z0-9_]+", "_", str(item.get("department") or "").casefold()).strip("_") == department
                ][:30],
            }
            sources[department] = [
                f"department_intelligence.custom_departments.{department}",
                f"department_work_queue.{department}",
                "boardroom_snapshot.department_actions",
            ]
        return {
            "retrieval_state": "retrieved" if data else "not_published",
            "source_ids": sources[department], "retrieved_at": utc_now_iso(), "data": data,
        }

    def _mobile_finance_briefing(self, workspace_ref: str) -> dict[str, Any]:
        """Founder/FD finance summary from recorded models and invoice ledger only."""
        financial = self.containers.load_optional_dict(workspace_ref, "business_financial_model") or {}
        director = financial.get("finance_director") if isinstance(financial.get("finance_director"), Mapping) else {}
        pnl = director.get("profit_and_loss") if isinstance(director.get("profit_and_loss"), Mapping) else {}
        cashflow = director.get("cash_flow") if isinstance(director.get("cash_flow"), Mapping) else {}
        balance = director.get("balance_sheet") if isinstance(director.get("balance_sheet"), Mapping) else {}
        working = director.get("working_capital") if isinstance(director.get("working_capital"), Mapping) else {}
        metrics = financial.get("metrics") if isinstance(financial.get("metrics"), Mapping) else {}
        try:
            invoices = self.finance_sales.summary(workspace_ref)
        except (OSError, ValueError, PermissionError):
            invoices = {}

        def value(*names: str) -> Any:
            for source in (cashflow, pnl, balance, metrics):
                for name in names:
                    raw = source.get(name) if isinstance(source, Mapping) else None
                    if isinstance(raw, Mapping): raw = raw.get("value", raw.get("amount", raw.get("actual")))
                    if isinstance(raw, (int, float)) and not isinstance(raw, bool): return round(float(raw), 2)
            return None

        signals = director.get("proactive_signals") if isinstance(director.get("proactive_signals"), Sequence) else []
        actions = [
            {"title": str(item.get("title") or "Finance review")[:180], "recommendation": str(item.get("recommendation") or "Review with Finance Pilot.")[:360], "severity": str(item.get("severity") or "normal")[:40]}
            for item in signals if isinstance(item, Mapping)
        ][:6]
        # Opening an authorised mobile workspace must be bounded by the phone's request
        # timeout. The detailed, locally generated briefing is therefore produced through
        # the Finance conversation endpoint after the workspace has opened, not inline here.
        briefing_provider: dict[str, Any] = {"provider": "recorded_finance_snapshot", "model": None}
        priorities: list[str] = []
        overdue = invoices.get("overdue")
        drafts = invoices.get("draft_count")
        if isinstance(overdue, (int, float)) and overdue > 0:
            priorities.append("Review the recorded overdue invoices and prepare chases for approval.")
        if isinstance(drafts, (int, float)) and drafts > 0:
            priorities.append("Review the recorded invoice drafts before they are issued.")
        if not priorities:
            priorities.append("Review new completed work and prepare any invoice, payment or cash-collection requests that the evidence supports.")
        daily_update = "Finance Pilot is ready. " + " ".join(priorities) + " Ask for today's briefing to receive a grounded analysis. No payment, customer message or accounting-provider update has been performed."
        has_director = bool(director)
        return {"finance_briefing": {
            "headline": "Today’s Finance briefing",
            "currency": str(director.get("currency") or financial.get("currency") or "EUR")[:8],
            "generated_at": str(director.get("created_at") or financial.get("updated_at") or ""),
            "verification_state": str(director.get("verification_state") or "finance_model_not_published"),
            "metrics": {
                "cash_in_bank": value("ending_cash", "opening_or_latest_cash", "cash_balance", "cash"),
                "revenue": value("revenue", "net_sales", "sales"),
                "gross_profit": value("gross_profit"),
                "operating_profit": value("operating_profit", "net_profit"),
                "trade_debtors": value("debtors", "accounts_receivable"),
                "trade_creditors": value("creditors", "accounts_payable"),
                "outstanding_invoices": invoices.get("outstanding"),
                "overdue_invoices": invoices.get("overdue"),
                "invoice_count": invoices.get("invoice_count"),
                "invoice_drafts": invoices.get("draft_count"),
                "cash_collections": value("cash_collections"),
                "cash_payments": value("cash_payments"),
                "net_cash_change": value("net_cash_change"),
                "runway_months": value("estimated_runway_months"),
                "overdue_receivables": working.get("overdue_receivables"),
            },
            "actions": actions,
            "today_plan": daily_update,
            "briefing_provider": briefing_provider,
            "availability": [] if has_director else ["No Finance Director model is published yet, so the mobile briefing cannot state a cash position, P&L or balance-sheet figure reliably."],
            "receipt_policy": "Anyone with expense-submission permission can add a receipt. Tessaris will extract and classify it, check the person’s limit and route exceptions to the named manager. Xero reconciliation remains a separately approved provider step.",
        }}

    def _mobile_people_directory(self, workspace_ref: str) -> dict[str, Any]:
        """Useful mobile People records without private HR, payroll or contact data."""
        model = self.organization_authority.get(workspace_ref)
        departments = {
            str(item.get("id") or ""): " ".join(str(item.get("name") or "").split())[:120]
            for item in model.get("departments") or [] if isinstance(item, Mapping)
        }
        roles = {
            str(item.get("id") or ""): item
            for item in model.get("roles") or [] if isinstance(item, Mapping)
        }
        all_people = [item for item in model.get("people") or [] if isinstance(item, Mapping)]
        direct_report_counts: dict[str, int] = {}
        for person in all_people:
            manager = str(person.get("manager_id") or "")
            if manager:
                direct_report_counts[manager] = direct_report_counts.get(manager, 0) + 1
        asset_counts: dict[str, int] = {}
        for asset in model.get("assets") or []:
            if not isinstance(asset, Mapping):
                continue
            owner = str(asset.get("assigned_person_id") or "")
            if owner:
                asset_counts[owner] = asset_counts.get(owner, 0) + 1

        people: list[dict[str, Any]] = []
        for row in all_people:
            person_id = str(row.get("id") or "")[:120]
            role_rows = [roles[role_id] for role_id in row.get("role_ids") or [] if role_id in roles]
            capability_groups: list[str] = []
            capability_set = {str(capability) for role in role_rows for capability in role.get("capabilities") or []}
            for label, prefixes in (
                ("People & permissions", ("people.", "permissions.")),
                ("Boardroom", ("boardroom.",)),
                ("Finance oversight", ("finance.", "expenses.")),
                ("Commercial", ("sales.", "marketing.")),
                ("Operations", ("operations.", "support.")),
            ):
                if any(capability.startswith(prefix) for capability in capability_set for prefix in prefixes):
                    capability_groups.append(label)
            department_names = [departments.get(str(item), str(item).replace("department.", "").replace("_", " ").title()) for item in row.get("department_ids") or []]
            business_wide = any(str(role.get("scope") or "") == "business" for role in role_rows)
            people.append({
                "id": person_id,
                "name": " ".join(str(row.get("name") or "Team member").split())[:160],
                "title": " ".join(str(row.get("position_title") or row.get("job_title") or "").split())[:160],
                "status": str(row.get("status") or "active")[:40],
                "employment_type": str(row.get("employment_type") or "employee")[:40],
                "role_names": [" ".join(str(role.get("name") or "").split())[:100] for role in role_rows if role.get("name")][:6],
                "department_names": department_names[:8],
                "authority_scope": "Business-wide" if business_wide else ("Department-scoped" if department_names else "Assigned work"),
                "access_areas": capability_groups[:5],
                "direct_reports": direct_report_counts.get(person_id, 0),
                "project_count": len([item for item in row.get("project_ids") or [] if item]),
                "assigned_asset_count": asset_counts.get(person_id, 0),
                "has_manager": bool(row.get("manager_id")),
            })
        person_names = {str(item.get("id") or ""): " ".join(str(item.get("name") or "Team member").split())[:160] for item in all_people}
        operations = model.get("people_operations") if isinstance(model.get("people_operations"), Mapping) else {}
        today = datetime.now(timezone.utc).date()
        leave: list[dict[str, Any]] = []
        for raw in operations.get("leave_requests") or []:
            if not isinstance(raw, Mapping):
                continue
            try:
                begins = datetime.fromisoformat(str(raw.get("start_date") or "")[:10]).date()
                ends = datetime.fromisoformat(str(raw.get("end_date") or "")[:10]).date()
            except ValueError:
                continue
            status = str(raw.get("status") or "requested").casefold()
            leave.append({
                "id": str(raw.get("id") or "")[:120],
                "person_id": str(raw.get("person_id") or "")[:120],
                "person_name": person_names.get(str(raw.get("person_id") or ""), "Team member"),
                "start_date": begins.isoformat(), "end_date": ends.isoformat(), "status": status[:40],
                "off_today": status in {"approved", "confirmed", "active"} and begins <= today <= ends,
                "cover_assigned": bool(raw.get("cover_owner")),
            })
        return {
            "people_access": {"allowed": True, "record_scope": "authorised_people_directory", "sensitive_detail_excluded": True},
            "people": people[:200],
            "people_availability": {
                "date": today.isoformat(),
                "off_today_count": sum(bool(item.get("off_today")) for item in leave),
                "off_today": [item for item in leave if item.get("off_today")][:50],
                "leave_records": leave[:100],
                "source": "organization_authority.people_operations.leave_requests",
            },
        }

    def custom_departments(self, workspace_ref: str) -> list[dict[str, Any]]:
        intelligence = self.containers.load_optional_dict(workspace_ref, "department_intelligence") or {}
        raw = intelligence.get("custom_departments") or []
        return [self._validated_custom_department(item) for item in raw if isinstance(item, Mapping) and self._is_valid_custom_department(item)]

    def create_custom_department(self, workspace_ref: str, department: Mapping[str, Any], *, actor_persona_id: str) -> dict[str, Any]:
        name = " ".join(str(department.get("name") or "").split())[:80]
        template = " ".join(str(department.get("template") or "").split()).casefold()[:40]
        mandate = " ".join(str(department.get("mandate") or "").split())[:2_000]
        key = re.sub(r"[^a-z0-9]+", "_", name.casefold()).strip("_")[:40]
        if not name or not key:
            raise ValueError("custom department name is required")
        if key in self.CORE_DEPARTMENTS:
            raise PermissionError("core departments cannot be replaced")
        if template not in self.CUSTOM_TEMPLATES:
            raise ValueError("select a supported custom department template")
        if not mandate:
            raise ValueError("a Pilot mandate is required")
        intelligence = self.containers.load_optional_dict(workspace_ref, "department_intelligence") or {"workspace_id": workspace_ref, "kind": "department_intelligence", "departments": {}, "revision": 1}
        existing = self.custom_departments(workspace_ref)
        parent_department_id = re.sub(
            r"[^a-z0-9_]+", "", str(department.get("parent_department_id") or "").casefold()
        )[:40] or None
        if len(existing) >= 20:
            raise ValueError("custom department limit reached")
        if any(item["id"] == key for item in existing):
            raise ValueError("a department with that name already exists")
        if parent_department_id and not any(item["id"] == parent_department_id for item in existing):
            raise ValueError("parent custom department was not found")
        created = {
            "id": key, "name": name, "template": template,
            "pilot_title": self.CUSTOM_TEMPLATES[template], "mandate": mandate,
            "core": False, "parent_department_id": parent_department_id,
            "created_by": actor_persona_id, "created_at": utc_now_iso(),
        }
        intelligence["custom_departments"] = [*existing, created]
        intelligence["revision"] = int(intelligence.get("revision") or 1) + 1
        audit = list(intelligence.get("custom_department_audit") or [])[-99:]
        audit.append({"operation": "created", "department_id": key, "actor_persona_id": actor_persona_id, "recorded_at": utc_now_iso()})
        intelligence["custom_department_audit"] = audit
        self.containers.save_dict(workspace_ref, "department_intelligence", intelligence)
        return created

    def delete_custom_department(self, workspace_ref: str, department_id: str, *, actor_persona_id: str) -> dict[str, Any]:
        key = re.sub(r"[^a-z0-9_]+", "", str(department_id).casefold())[:40]
        if key in self.CORE_DEPARTMENTS:
            raise PermissionError("core departments cannot be deleted")
        intelligence = self.containers.load_optional_dict(workspace_ref, "department_intelligence") or {}
        existing = self.custom_departments(workspace_ref)
        removed = next((item for item in existing if item["id"] == key), None)
        if removed is None:
            raise LookupError("custom department was not found")
        intelligence["custom_departments"] = [item for item in existing if item["id"] != key]
        intelligence["revision"] = int(intelligence.get("revision") or 1) + 1
        audit = list(intelligence.get("custom_department_audit") or [])[-99:]
        audit.append({"operation": "deleted", "department_id": key, "actor_persona_id": actor_persona_id, "recorded_at": utc_now_iso()})
        intelligence["custom_department_audit"] = audit
        self.containers.save_dict(workspace_ref, "department_intelligence", intelligence)
        return {"id": key, "deleted": True, "name": removed["name"]}

    @classmethod
    def _boardroom_mobile_briefing(
        cls, *, boardroom_summary: Mapping[str, Any], boardroom_payload: Mapping[str, Any],
        legacy_meeting_history: Sequence[Mapping[str, Any]] = (),
    ) -> dict[str, Any]:
        """Build the compact, read-only Boardroom feed used by a signed phone.

        The first Board meeting stays on desktop because it creates the business
        foundation.  This projection intentionally contains only the established
        roster, published meeting records and delegated department actions.  It
        never creates a meeting, infers a decision, or exposes raw context.
        """
        summary_boardroom = dict(boardroom_summary.get("boardroom") or {})
        summary_runtime = dict(boardroom_summary.get("runtime") or {})
        payload_runtime = dict(boardroom_payload.get("runtime") or {})
        runtime = {**payload_runtime, **summary_runtime, **dict(summary_boardroom.get("runtime") or {})}

        raw_members = cls._first_mapping_list(
            summary_boardroom.get("board_members"),
            boardroom_payload.get("board_members"),
            runtime.get("board_members"),
            runtime.get("council_members"),
        )
        # The desktop Board currently has these three standing intelligence seats.
        # A published Board roster always takes precedence when it exists.
        if not raw_members:
            raw_members = [
                {"id": "aion", "name": "AION", "role": "Board intelligence"},
                {"id": "openai", "name": "OpenAI", "role": "Board intelligence"},
                {"id": "gemini", "name": "Gemini", "role": "Board intelligence"},
            ]
        members = cls._mobile_board_members(raw_members)

        history = cls._mobile_meeting_history(cls._first_mapping_list(
            summary_boardroom.get("meeting_history"), summary_boardroom.get("meetings"),
            boardroom_payload.get("meeting_history"), boardroom_payload.get("meetings"),
            runtime.get("meeting_history"), runtime.get("boardroom_sessions"), runtime.get("sessions"),
        ))
        # Older desktop Boardroom analysis was persisted as a per-business ledger
        # before formal meeting sign-off existed. It remains visible to the same
        # business as clearly marked working analysis; it is never passed off as
        # approved minutes.
        if not history:
            history = cls._mobile_meeting_history(legacy_meeting_history)
        actions = cls._mobile_department_actions(cls._first_mapping_list(
            summary_boardroom.get("department_actions"), summary_boardroom.get("delegated_actions"),
            boardroom_payload.get("department_actions"), boardroom_payload.get("delegated_actions"),
            runtime.get("department_actions"), runtime.get("delegated_actions"),
            runtime.get("proposed_pilot_actions"),
        ))

        return {
            "headline": str(boardroom_summary.get("headline") or "Boardroom"),
            "generated_at": boardroom_summary.get("generated_at") or boardroom_payload.get("generated_at"),
            "pulse": boardroom_summary.get("pulse") or summary_boardroom.get("pulse") or boardroom_payload.get("pulse") or {},
            "center": boardroom_summary.get("center") or summary_boardroom.get("center") or boardroom_payload.get("center") or {},
            "departments": summary_boardroom.get("departments") or boardroom_payload.get("departments") or [],
            "board_members": members,
            "meeting_history": history,
            "department_actions": actions,
            "mobile_meeting_policy": {
                "first_meeting": "desktop_required",
                "subsequent_meetings": "mobile_review_and_response",
            },
        }

    @staticmethod
    def _executive_members(raw_departments: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
        defaults = [
            ("sales", "Sales Pilot", "Revenue and pipeline"),
            ("marketing", "Marketing Pilot", "Campaigns and demand"),
            ("finance", "Finance Pilot", "Cash and invoices"),
            ("operations", "Operations Pilot", "Delivery and risks"),
            ("support", "Support Pilot", "Customer issues"),
            ("people", "People Pilot", "Team records"),
        ]
        known = {str(item.get("key") or item.get("id") or "").casefold() for item in raw_departments if isinstance(item, Mapping)}
        return [
            {"id": key, "name": name, "role": role}
            for key, name, role in defaults if not known or key in known or f"dept_{key}" in known
        ]

    def _legacy_boardroom_history(self, workspace_ref: str) -> list[Mapping[str, Any]]:
        safe_workspace = re.sub(r"[^a-z0-9_-]+", "", str(workspace_ref).casefold())
        if not safe_workspace:
            return []
        path = self.boardroom_ledger_root / f"{safe_workspace}.json"
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return []
        entries = raw.get("history") if isinstance(raw, Mapping) else []
        if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)):
            return []
        records: list[Mapping[str, Any]] = []
        for index, entry in enumerate(entries):
            if not isinstance(entry, Mapping):
                continue
            responses = entry.get("responses")
            successful = next((item for item in responses or [] if isinstance(item, Mapping) and item.get("status") == "succeeded" and isinstance(item.get("structured"), Mapping)), None)
            structured = dict(successful.get("structured") or {}) if successful else {}
            position = " ".join(str(structured.get("position") or "").split())
            plan = structured.get("plan_changes") or []
            plan_text = " ".join(str(item) for item in plan[:2]) if isinstance(plan, Sequence) and not isinstance(plan, (str, bytes)) else ""
            summary = " ".join(f"{position} {plan_text}".split())[:500]
            if not summary:
                continue
            persisted_at = str(entry.get("persisted_at") or "")
            records.append({
                "id": f"legacy-{safe_workspace}-{index}",
                "title": "Board analysis", "occurred_at": persisted_at,
                "summary": summary, "status": "analysis_pending_signoff",
            })
        return list(reversed(records[-12:]))

    @staticmethod
    def _first_mapping_list(*candidates: Any) -> list[Mapping[str, Any]]:
        for candidate in candidates:
            if isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes)):
                values = [item for item in candidate if isinstance(item, Mapping)]
                if values:
                    return values
        return []

    @staticmethod
    def _mobile_board_members(raw_members: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
        members: list[dict[str, str]] = []
        seen: set[str] = set()
        for index, item in enumerate(raw_members):
            name = " ".join(str(item.get("name") or item.get("label") or item.get("display_name") or item.get("id") or "").split())[:80]
            if not name or name.casefold() in seen:
                continue
            seen.add(name.casefold())
            member_id = "".join(str(item.get("id") or name.casefold()).split())[:80]
            members.append({"id": member_id or f"board-{index}", "name": name, "role": " ".join(str(item.get("role") or item.get("title") or "Board intelligence").split())[:120]})
        return members[:12]

    @staticmethod
    def _mobile_meeting_history(raw_meetings: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
        meetings: list[dict[str, str]] = []
        for item in raw_meetings:
            status = str(item.get("status") or item.get("state") or item.get("approval_status") or "").casefold()
            if status and status not in {"approved", "published", "signed_off", "complete", "completed", "analysis_pending_signoff"}:
                continue
            title = " ".join(str(item.get("title") or item.get("name") or item.get("session_type") or "Board meeting").replace("_", " ").split())[:160]
            occurred_at = str(item.get("approved_at") or item.get("published_at") or item.get("occurred_at") or item.get("generated_at") or item.get("date") or "")[:80]
            summary = " ".join(str(item.get("summary") or item.get("minutes_summary") or item.get("consensus") or "Approved Board record").split())[:500]
            meeting_id = str(item.get("id") or item.get("session_id") or item.get("meeting_id") or f"meeting-{len(meetings)}")[:100]
            meetings.append({"id": meeting_id, "title": title, "occurred_at": occurred_at, "summary": summary, "status": status or "published"})
        return meetings[:12]

    @staticmethod
    def _mobile_department_actions(raw_actions: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
        actions: list[dict[str, str]] = []
        for item in raw_actions:
            title = " ".join(str(item.get("title") or item.get("action") or item.get("objective") or "").split())[:180]
            department = " ".join(str(item.get("department") or item.get("department_id") or item.get("department_key") or "").replace("_", " ").split())[:80]
            if not title or not department:
                continue
            action_id = str(item.get("id") or item.get("action_id") or item.get("task_id") or f"action-{len(actions)}")[:100]
            actions.append({"id": action_id, "title": title, "department": department, "status": str(item.get("status") or "delegated")[:80], "due_at": str(item.get("due_at") or item.get("dueAt") or "")[:80]})
        return actions[:30]

    @classmethod
    def _is_valid_custom_department(cls, item: Mapping[str, Any]) -> bool:
        return bool(str(item.get("id") or "") and str(item.get("name") or "") and str(item.get("template") or "") in cls.CUSTOM_TEMPLATES)

    @classmethod
    def _validated_custom_department(cls, item: Mapping[str, Any]) -> dict[str, Any]:
        return {key: item.get(key) for key in (
            "id", "name", "template", "pilot_title", "mandate", "core",
            "parent_department_id", "created_at",
        )}

    def conversation_turn(
        self,
        workspace_ref: str,
        department_id: str,
        user_text: str,
        *,
        persona_id: str,
        attachments: Sequence[str] | None = None,
    ) -> Mapping[str, Any]:
        """Adapt existing read-only departmental conversation authorities.

        Finance has a permanent evidence-grounded conversation service. Other
        departments currently expose governed work queues, so their mobile turn is
        deliberately a deterministic briefing rather than an invented model answer.
        """
        question = " ".join(str(user_text or "").split())[:2_000]
        department = " ".join(str(department_id or "boardroom").split()).casefold()[:80]
        if not question:
            raise ValueError("workspace conversation text is required")
        if department == "finance" and self.finance_conversations is not None:
            result = dict(self.finance_conversations.answer(workspace_ref, question))
            turn = dict(result.get("turn") or {})
            response = {
                "conversation_id": f"finance-terminal-{workspace_ref}",
                "department_id": "finance",
                "turn": turn,
                "provider": turn.get("provider", {}),
                "evidence": turn.get("sources", []),
                "reliability": turn.get("reliability", "unknown"),
                "external_writes_performed": False,
                "approval_gated": True,
            }
            return self._record_conversation_exchange(workspace_ref, department, question, response)

        # Pilot is the guarded central assistant. It may summarise the shared
        # workspace and prepare a route, but it never executes an external action
        # or silently changes a departmental objective.
        if department in {"pilot", "operations"}:
            runtime = self.containers.load_optional_dict(workspace_ref, "operational_runtime_summary") or {}
            lowered = question.casefold()
            request_kind = CooMissionService().classify(question)
            delegated_department = self._explicit_department_delegation(workspace_ref, lowered)
            if department == "operations" and delegated_department:
                from backend.modules.aion_business.runtime.operations_executive_briefing_service import (
                    OperationsExecutiveBriefingService,
                )
                executive = OperationsExecutiveBriefingService(self)
                if delegated_department == "people":
                    delegated = executive.delegate_people_action(
                        workspace_ref, question, person_id=persona_id, attachments=attachments,
                    )
                    department_reply = str((delegated.get("response") or {}).get("content") or "The People Pilot did not return a response.")
                    answer = f"I delegated this to the People Pilot. {department_reply}"
                    reliability = "governed_internal_action" if delegated.get("handled") else "workspace_record_backed"
                else:
                    delegated = executive.channel_turn(
                        workspace_ref, delegated_department, question, person_id=persona_id,
                    )
                    role = executive._channel_roles(workspace_ref)[delegated_department]
                    department_reply = str((delegated.get("response") or {}).get("content") or "No department response was returned.")
                    answer = f"I delegated this to the {role['title']} Pilot. {department_reply}"
                    reliability = "workspace_record_backed"
                response = {
                    "conversation_id": f"coo-mission-{workspace_ref}", "department_id": "operations",
                    "turn": {"turn_id": f"coo-turn-{uuid4().hex}", "role": "assistant", "content": answer, "created_at": utc_now_iso()},
                    "provider": {"provider": "aion_capability_router", "model": None},
                    "evidence": [{"source": f"executive_channel.{delegated_department}"}],
                    "reliability": reliability, "external_writes_performed": False,
                    "approval_gated": True,
                    "delegation_receipt": {
                        "department_id": delegated_department, "status": delegated.get("status") or "recorded",
                        "request_id": (delegated.get("request") or {}).get("id"),
                        "response_id": (delegated.get("response") or {}).get("id"),
                    },
                }
                return self._record_conversation_exchange(workspace_ref, department, question, response)
            if department == "operations" and request_kind == "business_fact_lookup" and self._is_outstanding_invoice_question(lowered):
                answer, evidence, reliability = self._coo_outstanding_invoice_answer(workspace_ref)
                response = self._coo_direct_response(workspace_ref, answer, evidence, reliability, "coo_invoice_ledger")
                return self._record_conversation_exchange(workspace_ref, department, question, response)
            if department == "operations" and request_kind == "business_fact_lookup" and self._is_calendar_question(lowered):
                answer, evidence, reliability = self._coo_calendar_answer(persona_id, lowered)
                response = self._coo_direct_response(workspace_ref, answer, evidence, reliability, "coo_private_calendar")
                return self._record_conversation_exchange(workspace_ref, department, question, response)
            if department == "operations" and self._is_people_record_lookup(lowered):
                answer, evidence, reliability = self._coo_people_record_answer(workspace_ref, lowered)
                response = self._coo_direct_response(workspace_ref, answer, evidence, reliability, "coo_people_directory")
                return self._record_conversation_exchange(workspace_ref, department, question, response)
            coo_result = self.coo_missions.run(
                workspace_id=workspace_ref, question=question, workspace_state=runtime,
                fact_loader=lambda name: self._coo_department_fact(workspace_ref, name, persona_id=persona_id),
            )
            surface = self.read_surface(workspace_ref, "departments", persona_id=persona_id)
            data = dict(surface.get("data") or {})
            work = [item for item in data.get("work", []) if isinstance(item, Mapping)][:8]
            routes = {
                "finance": ("Finance", ("cash", "invoice", "payment", "expense", "profit", "margin", "tax", "budget", "turnover", "revenue")),
                "sales": ("Sales", ("sale", "lead", "quote", "pipeline", "customer")),
                "marketing": ("Marketing", ("marketing", "advert", "ads", "campaign", "traffic", "roi")),
                "support": ("Support", ("case", "complaint", "support", "refund")),
                "people": ("People", ("employee", "staff", "team", "people", "hr")),
                "products_services": ("Products & Services", ("product", "service", "offering", "price", "unit cost")),
                "operations": ("Operations", ("delivery", "risk", "supplier", "schedule", "operations")),
            }
            route = next((label for label, terms in routes.values() if any(term in lowered for term in terms)), None)
            if department == "operations" and request_kind == "business_fact_lookup" and route == "Finance" and self.finance_conversations is not None:
                finance_result = dict(self.finance_conversations.answer(workspace_ref, question))
                finance_turn = dict(finance_result.get("turn") or {})
                response = {
                    "conversation_id": f"coo-mission-{workspace_ref}", "department_id": "operations",
                    "turn": {"turn_id": f"coo-turn-{uuid4().hex}", "role": "assistant", "content": "Finance briefing for the COO: " + str(finance_turn.get("content") or "No readable Finance briefing was returned."), "created_at": utc_now_iso()},
                    "provider": {"provider": "coo_finance_consultation", "model": finance_turn.get("provider")},
                    "evidence": list(finance_turn.get("sources") or []), "reliability": finance_turn.get("reliability", "unknown"),
                    "external_writes_performed": False, "approval_gated": True,
                    "mission_receipt": coo_result,
                }
                return self._record_conversation_exchange(workspace_ref, department, question, response)
            if department == "operations" and request_kind == "business_fact_lookup" and route == "Sales" and any(term in lowered for term in ("today", "made", "sales", "sold", "revenue")):
                answer, evidence, reliability = self._coo_sales_today_answer(workspace_ref)
                response = {
                    "conversation_id": f"coo-mission-{workspace_ref}", "department_id": "operations",
                    "turn": {"turn_id": f"coo-turn-{uuid4().hex}", "role": "assistant", "content": answer, "created_at": utc_now_iso()},
                    "provider": {"provider": "coo_sales_consultation", "model": None},
                    "evidence": evidence, "reliability": reliability,
                    "external_writes_performed": False, "approval_gated": True,
                    "mission_receipt": coo_result,
                }
                return self._record_conversation_exchange(workspace_ref, department, question, response)
            work_line = "; ".join(
                f"{str(item.get('title') or 'Untitled work')[:100]} ({str(item.get('status') or 'unknown')})"
                for item in work[:4]
            )
            proposal = dict(coo_result.get("proposal") or {})
            if coo_result.get("status") == "proposal_ready" and proposal.get("answer"):
                answer = str(proposal["answer"])
            elif route:
                answer = (
                    f"I identified {route} as the authority for this question. The COO fact pack was prepared, but the selected Vault model is unavailable ({coo_result.get('reason') or 'no released model'}), so I will not invent an answer or treat it as an external action. "
                    f"{('Current recorded work: ' + work_line + '. ') if work_line else ''}"
                    "I can prepare a reviewable request for that department once the selected Vault model is released to this workspace."
                )
            else:
                answer = (
                    f"The COO fact pack was prepared, but the selected Vault model is unavailable ({coo_result.get('reason') or 'no released model'}). I will not substitute canned business advice. "
                    f"{('Current recorded work: ' + work_line + '. ') if work_line else ''}"
                    "No external action was taken."
                )
            response = {
                "conversation_id": f"{'coo-mission' if department == 'operations' else 'pilot-central'}-{workspace_ref}",
                "department_id": department,
                "turn": {"turn_id": f"pilot-turn-{uuid4().hex}", "role": "assistant", "content": answer, "created_at": utc_now_iso()},
                "provider": dict(coo_result.get("model_selection") or {"provider": "guarded_workspace_router", "model": None}),
                "evidence": [{"source": item} for item in proposal.get("sources") or []] or work,
                "reliability": "model_proposal_with_bounded_facts" if proposal else ("workspace_record_backed" if work else "model_unavailable"),
                "external_writes_performed": False,
                "approval_gated": True,
                "mission_receipt": coo_result,
                "proposal": proposal or None,
                "research_job": coo_result.get("research_job"),
                "required_approval": coo_result.get("required_approval"),
                "delegation_queue": coo_result.get("delegation_queue"),
            }
            return self._record_conversation_exchange(workspace_ref, department, question, response)

        if department == "people":
            # People administration is capability-driven.  The selected Vault model
            # may choose and populate a registered action, but only AION validates
            # authority and changes the canonical People record.  Questions and
            # unsupported requests continue through the evidence-gated adviser path.
            from backend.modules.aion_business.runtime.people_pilot_action_service import (
                PeoplePilotActionService,
            )
            from backend.modules.aion_business.runtime.operations_executive_briefing_service import (
                OperationsExecutiveBriefingService,
            )

            pending_people_plan = self._pending_people_action_plan(workspace_ref)
            people_subject_context = self._recent_people_subject_context(workspace_ref)
            action = PeoplePilotActionService(self).handle(
                workspace_ref,
                question,
                person_id=persona_id,
                attachments=attachments,
                pending_plan=pending_people_plan,
                subject_context=people_subject_context,
            )
            if action.get("handled"):
                receipt = dict(action.get("action_receipt") or {})
                response = {
                    "conversation_id": f"department-pilot-{department}-{workspace_ref}",
                    "department_id": department,
                    "turn": {
                        "turn_id": f"department-turn-{uuid4().hex}",
                        "role": "assistant",
                        "content": str(action.get("content") or "The People Pilot could not complete that request."),
                        "created_at": utc_now_iso(),
                    },
                    "provider": dict((action.get("plan") or {}).get("planner") or {}),
                    "evidence": [{"source": "organization_authority"}],
                    "reliability": "governed_internal_action" if action.get("status") == "completed" else "needs_information",
                    "external_writes_performed": False,
                    "approval_gated": True,
                    "people_action": {
                        "status": action.get("status"),
                        "capability_id": (action.get("plan") or {}).get("capability_id"),
                        "plan": {
                            "capability_id": (action.get("plan") or {}).get("capability_id"),
                            "fields": dict((action.get("plan") or {}).get("fields") or {}),
                            "missing_fields": list((action.get("plan") or {}).get("missing_fields") or []),
                        },
                        "receipt": receipt,
                        "organization_revision": (action.get("organization") or {}).get("revision"),
                    },
                }
                return self._record_conversation_exchange(workspace_ref, department, question, response)

            result = OperationsExecutiveBriefingService(self).direct_department_turn(
                workspace_ref, department, question, person_id=persona_id,
            )
            position = dict(result.get("position") or {})
            model_status = str(position.get("model_status") or "unavailable")
            source_ids = [str(item)[:160] for item in position.get("source_ids") or []]
            response = {
                "conversation_id": f"department-pilot-{department}-{workspace_ref}",
                "department_id": department,
                "turn": {
                    "turn_id": f"department-turn-{uuid4().hex}",
                    "role": "assistant",
                    "content": str(position.get("summary") or "The People Pilot could not prepare a response."),
                    "created_at": utc_now_iso(),
                },
                "provider": dict(position.get("model_selection") or {}),
                "evidence": [{"source": item} for item in source_ids],
                "reliability": (
                    "model_proposal_with_bounded_facts"
                    if model_status == "answered"
                    else ("workspace_record_backed" if source_ids else "insufficient_evidence")
                ),
                "external_writes_performed": False,
                "approval_gated": True,
                "department_position": position,
            }
            return self._record_conversation_exchange(workspace_ref, department, question, response)

        surface = self.read_surface(workspace_ref, "departments", persona_id=persona_id)
        data = dict(surface.get("data") or {})
        relevant = [
            item for item in data.get("work", [])
            if isinstance(item, Mapping) and (
                department in {"boardroom", "executive"} or str(item.get("department_id") or "").casefold() == department
            )
        ][:12]
        if relevant:
            lines = "; ".join(
                f"{str(item.get('title') or 'Untitled work')[:120]} ({str(item.get('status') or 'unknown')})"
                for item in relevant
            )
            answer = f"Current {department.title()} work: {lines}. No external action was taken."
            reliability = "workspace_record_backed"
        else:
            answer = (
                f"I do not have enough recorded {department.title()} work evidence to answer that "
                "reliably. No external action was taken."
            )
            reliability = "insufficient_evidence"
        response = {
            "conversation_id": f"mobile-{department}-{workspace_ref}",
            "department_id": department,
            "turn": {
                "turn_id": f"mobile-turn-{uuid4().hex}",
                "role": "assistant",
                "content": answer,
                "created_at": utc_now_iso(),
            },
            "provider": {"provider": "deterministic_workspace_projection", "model": None},
            "evidence": relevant,
            "reliability": reliability,
            "external_writes_performed": False,
            "approval_gated": True,
        }
        return self._record_conversation_exchange(workspace_ref, department, question, response)

    # Workspace conversations are shared business records, not screen-local UI
    # state.  The latest turns stay light enough to open quickly; the complete
    # record is retained locally and is returned in pages when either client
    # scrolls upwards.
    def conversation_history(
        self, workspace_ref: str, department_id: str, *, before: str = "", limit: int = 50
    ) -> Mapping[str, Any]:
        department = " ".join(str(department_id or "pilot").split()).casefold()[:80]
        bounded_limit = max(10, min(int(limit or 50), 75))
        store = self._conversation_store(workspace_ref)
        turns = [item for item in store.get("turns") or [] if isinstance(item, Mapping) and item.get("department_id") == department]
        turns.sort(key=lambda item: (int(item.get("sequence") or 0), str(item.get("created_at") or ""), str(item.get("id") or "")))
        if before:
            index = next((i for i, item in enumerate(turns) if str(item.get("id") or "") == before), len(turns))
            turns = turns[:index]
        page = turns[-bounded_limit:]
        has_more = len(turns) > len(page)
        return {
            "conversation_id": f"workspace-{department}-{workspace_ref}",
            "department_id": department,
            "turns": page,
            "has_more": has_more,
            "next_before": str(page[0].get("id") or "") if has_more and page else "",
            "retention": {"recent_window": 75, "page_size": bounded_limit, "archive_searchable": True},
        }

    def executive_channel_status(self, workspace_ref: str) -> Mapping[str, Any]:
        """Return the shared desktop/mobile executive-channel status."""
        from backend.modules.aion_business.runtime.operations_executive_briefing_service import (
            OperationsExecutiveBriefingService,
        )
        return OperationsExecutiveBriefingService(self).status(workspace_ref)

    def executive_channel_history(
        self, workspace_ref: str, department_id: str, *, limit: int = 75,
    ) -> Mapping[str, Any]:
        """Read the COO-to-Department-Pilot stream used by Operations desktop."""
        from backend.modules.aion_business.runtime.operations_executive_briefing_service import (
            OperationsExecutiveBriefingService,
        )
        return OperationsExecutiveBriefingService(self).channel_history(
            workspace_ref, department_id, limit=limit,
        )

    def executive_channel_turn(
        self, workspace_ref: str, department_id: str, user_text: str, *, persona_id: str,
    ) -> Mapping[str, Any]:
        """Send a signed mobile COO instruction through the same desktop engine."""
        from backend.modules.aion_business.runtime.operations_executive_briefing_service import (
            OperationsExecutiveBriefingService,
        )
        return OperationsExecutiveBriefingService(self).channel_turn(
            workspace_ref, department_id, user_text, person_id=persona_id,
        )

    def _conversation_store(self, workspace_ref: str) -> dict[str, Any]:
        from backend.modules.aion_business.runtime.operations_executive_briefing_service import (
            EXECUTIVE_MESSAGE_TYPES,
        )
        runtime = self.containers.load_optional_dict(workspace_ref, "operational_runtime_summary") or {}
        raw = runtime.get("shared_conversations")
        if not isinstance(raw, Mapping):
            raw = {"schema_version": "workspace_conversation_v1", "turns": []}
        turns = [
            dict(item) for item in raw.get("turns") or []
            if isinstance(item, Mapping) and str(item.get("message_type") or "") not in EXECUTIVE_MESSAGE_TYPES
        ][-1200:]
        return {"schema_version": "workspace_conversation_v1", "turns": turns}

    def _explicit_department_delegation(self, workspace_ref: str, text: str) -> str | None:
        """Recognise an explicit COO instruction without asking a model to route it."""
        if not re.search(r"\b(?:speak|talk|ask|tell|instruct|delegate|send|pass|hand|have|notify|request)\b", text):
            return None
        aliases = {
            "people": ("people", "hr", "human resources", "people pilot"),
            "sales": ("sales", "sales pilot"),
            "marketing": ("marketing", "marketing pilot"),
            "finance": ("finance", "finance pilot"),
            "support": ("support", "customer support", "support pilot"),
        }
        for item in self.custom_departments(workspace_ref):
            key = re.sub(r"[^a-z0-9_]+", "", str(item.get("id") or "").casefold())[:40]
            name = " ".join(str(item.get("name") or "").casefold().split())
            if key and name:
                aliases[key] = (name, f"{name} pilot")
        return next((department for department, names in aliases.items() if any(re.search(rf"\b{re.escape(name)}\b", text) for name in names)), None)

    @staticmethod
    def _is_people_record_lookup(text: str) -> bool:
        return bool(
            re.search(r"\b(?:check|verify|confirm|find|show|was|is|does)\b", text)
            and re.search(r"\b(?:employee|self[- ]employed|contractor|person|staff|people\s+directory|added|recorded|profile)\b", text)
        )

    def _coo_people_record_answer(
        self, workspace_ref: str, question: str,
    ) -> tuple[str, list[dict[str, Any]], str]:
        """Verify one named person from the canonical People directory."""
        try:
            model = self.organization_authority.get(workspace_ref)
        except (OSError, ValueError, PermissionError, KeyError):
            return (
                "I could not open the authorised People directory, so I cannot verify that record.",
                [], "people_directory_unavailable",
            )
        people = [dict(item) for item in model.get("people") or [] if isinstance(item, Mapping)]
        matches = [
            item for item in people
            if str(item.get("name") or "").strip()
            and re.search(rf"\b{re.escape(str(item.get('name')).strip().casefold())}\b", question)
        ]
        if not matches:
            return (
                "I could not find a named People record matching that question. Give me the person’s name exactly as it appears in the directory.",
                [{"source": "organization_authority", "match_count": 0}],
                "workspace_record_backed",
            )
        person = max(matches, key=lambda item: len(str(item.get("name") or "")))
        people_by_id = {str(item.get("id") or ""): item for item in people}
        departments = {
            str(item.get("id") or ""): str(item.get("name") or "")
            for item in model.get("departments") or [] if isinstance(item, Mapping)
        }
        employment = str(person.get("employment_type") or "employee").replace("_", " ")
        details = [
            f"status: {str(person.get('status') or 'active').replace('_', ' ')}",
            f"relationship: {employment}",
        ]
        if person.get("position_title"):
            details.append(f"job title: {person['position_title']}")
        manager = people_by_id.get(str(person.get("manager_id") or ""))
        if manager and manager.get("name"):
            details.append(f"reports to: {manager['name']}")
        department_names = [departments.get(str(item), "") for item in person.get("department_ids") or []]
        department_names = [item for item in department_names if item]
        if department_names:
            details.append("department: " + ", ".join(department_names))
        answer = f"I checked the authorised People directory. {person.get('name')} is recorded ({'; '.join(details)})."
        return (
            answer,
            [{"source": "organization_authority", "person_id": str(person.get("id") or ""),
              "organization_revision": model.get("revision")}],
            "workspace_record_backed",
        )

    def _pending_people_action_plan(self, workspace_ref: str) -> dict[str, Any] | None:
        """Return only the immediately preceding unanswered People action."""
        turns = [
            item for item in self._conversation_store(workspace_ref).get("turns", [])
            if str(item.get("department_id") or "").casefold() == "people"
        ]
        if not turns:
            return None
        latest = turns[-1]
        action = latest.get("people_action") if isinstance(latest, Mapping) else None
        if latest.get("role") != "assistant" or not isinstance(action, Mapping):
            return None
        if str(action.get("status") or "") != "needs_information":
            return None
        plan = action.get("plan")
        return dict(plan) if isinstance(plan, Mapping) else None

    def _recent_people_subject_context(self, workspace_ref: str) -> dict[str, Any] | None:
        """Keep a recently changed person as the subject of short profile updates."""
        turns = [
            item for item in self._conversation_store(workspace_ref).get("turns", [])[-24:]
            if str(item.get("department_id") or "").casefold() == "people"
        ]
        for item in reversed(turns):
            action = item.get("people_action") if isinstance(item, Mapping) else None
            if not isinstance(action, Mapping):
                continue
            if str(action.get("status") or "") == "context_cleared":
                return None
            if str(action.get("status") or "") != "completed":
                continue
            plan = action.get("plan") if isinstance(action.get("plan"), Mapping) else {}
            capability_id = str(plan.get("capability_id") or action.get("capability_id") or "")
            if capability_id not in {"people.create_person", "people.update_person"}:
                continue
            fields = plan.get("fields") if isinstance(plan.get("fields"), Mapping) else {}
            person_name = str(fields.get("name") or fields.get("person_name") or "").strip()
            if person_name:
                return {"person_name": person_name, "capability_id": capability_id}
        return None

    def _record_conversation_exchange(
        self, workspace_ref: str, department: str, question: str, response: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        from backend.modules.aion_business.runtime.operations_executive_briefing_service import (
            EXECUTIVE_CHANNEL_STORE_KEY,
            EXECUTIVE_MESSAGE_TYPES,
        )
        runtime = self.containers.load_optional_dict(workspace_ref, "operational_runtime_summary") or {}
        if not isinstance(runtime.get(EXECUTIVE_CHANNEL_STORE_KEY), Mapping):
            raw_shared = runtime.get("shared_conversations") if isinstance(runtime.get("shared_conversations"), Mapping) else {}
            legacy_executive = [
                dict(item) for item in raw_shared.get("turns") or []
                if isinstance(item, Mapping) and str(item.get("message_type") or "") in EXECUTIVE_MESSAGE_TYPES
            ]
            if legacy_executive:
                runtime[EXECUTIVE_CHANNEL_STORE_KEY] = {
                    "schema_version": "operations_executive_channel_v1",
                    "turns": legacy_executive[-1200:], "updated_at": utc_now_iso(),
                }
        store = self._conversation_store(workspace_ref)
        now = utc_now_iso()
        assistant = dict(response.get("turn") or {})
        turns = list(store["turns"])
        assistant_record = {
            "id": str(assistant.get("turn_id") or f"msg-{uuid4().hex}"), "sequence": len(turns) + 1,
            "department_id": department, "role": "assistant", "sender": f"{department.title()} Pilot",
            "content": str(assistant.get("content") or ""), "created_at": str(assistant.get("created_at") or now),
            "evidence": list(response.get("evidence") or [])[:12], "approval_gated": True,
        }
        for key in ("mission_receipt", "proposal", "research_job", "required_approval", "delegation_queue", "delegation_receipt", "people_action"):
            if response.get(key) is not None:
                assistant_record[key] = response.get(key)
        turns.extend((
            {"id": f"msg-{uuid4().hex}", "sequence": len(turns), "department_id": department, "role": "user", "sender": "You", "content": question, "created_at": now},
            assistant_record,
        ))
        # Keep the newest 1,200 turns in the encrypted local workspace record.
        # Clients initially receive only the latest 50 and page backwards.
        runtime["shared_conversations"] = {"schema_version": "workspace_conversation_v1", "turns": turns[-1200:], "updated_at": now}
        receipt = response.get("mission_receipt")
        if isinstance(receipt, Mapping):
            receipts = [dict(item) for item in runtime.get("coo_mission_receipts") or [] if isinstance(item, Mapping)]
            receipts.append(dict(receipt))
            runtime["coo_mission_receipts"] = receipts[-200:]
        research_job = response.get("research_job")
        if isinstance(research_job, Mapping):
            jobs = [dict(item) for item in runtime.get("coo_research_jobs") or [] if isinstance(item, Mapping)]
            jobs.append(dict(research_job))
            runtime["coo_research_jobs"] = jobs[-100:]
        delegation_queue = response.get("delegation_queue")
        if isinstance(delegation_queue, Mapping):
            queues = [dict(item) for item in runtime.get("coo_delegation_queues") or [] if isinstance(item, Mapping)]
            queues.append(dict(delegation_queue))
            runtime["coo_delegation_queues"] = queues[-100:]
        result = dict(response)
        # Some read-only provider adapters intentionally expose only load access.
        # They can still return the model result, but cannot retain a chat page.
        save_runtime = getattr(self.containers, "save_dict", None)
        if not callable(save_runtime):
            return result
        save_runtime(workspace_ref, "operational_runtime_summary", runtime)
        result["history"] = self.conversation_history(workspace_ref, department, limit=50)
        return result

    @staticmethod
    def _work_summary(envelope: Any) -> dict[str, Any]:
        task = envelope.task
        return {"task_id": task.task_id, "department_id": task.department_id, "status": task.status, "title": task.title}

    def _file_catalog(self, workspace_ref: str) -> list[dict[str, Any]]:
        if self.files is None:
            return []
        tree = self.files.load(workspace_ref)
        nodes = tree.get("folders") or (tree.get("root") or {}).get("children") or []
        catalog: list[dict[str, Any]] = []
        for node in self.files._walk(nodes):
            if not isinstance(node, Mapping) or str(node.get("type") or "") == "folder":
                continue
            reference = str(node.get("id") or "").strip()
            label = str(node.get("name") or node.get("title") or "Untitled file").strip()
            if not reference:
                continue
            protection = self.files.protection(dict(node))
            catalog.append({
                "id": reference[:200], "label": label[:160],
                "document_type": str(node.get("document_type") or node.get("type") or "file")[:80],
                "status": str(node.get("status") or "available")[:80],
                "protected": bool(protection.get("protected")),
            })
            if len(catalog) >= 100:
                break
        return catalog

    @classmethod
    def _mobile_summary(cls, source: Mapping[str, Any]) -> dict[str, Any]:
        allowed = {"headline", "summary", "generated_at", "health", "queue", "approvals", "alerts", "pulse", "center", "departments", "work", "files", "executive_members", "board_members", "meeting_history", "department_actions", "mobile_meeting_policy", "support_cases", "people_access", "people", "people_availability", "sales_briefing", "finance_briefing"}
        projected = {key: source[key] for key in allowed if key in source}
        return cls._bounded_value(projected, depth=0)

    @classmethod
    def _bounded_value(cls, value: Any, *, depth: int) -> Any:
        if depth > 5:
            return "[summary depth limited]"
        if isinstance(value, Mapping):
            blocked = ("password", "secret", "token", "credential", "private_key", "api_key", "email", "phone")
            return {
                str(key)[:80]: cls._bounded_value(item, depth=depth + 1)
                for key, item in list(value.items())[:40]
                if not any(marker in str(key).casefold() for marker in blocked)
            }
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            return [cls._bounded_value(item, depth=depth + 1) for item in list(value)[:50]]
        if isinstance(value, str):
            return value[:500]
        if isinstance(value, (int, float, bool)) or value is None:
            return value
        return str(value)[:200]


class WorkspaceProvider(Protocol):
    """Minimal provider boundary; provider data remains in its authoritative store."""

    provider_id: str

    def list_workspaces(self) -> Sequence[Mapping[str, Any]]: ...

    def describe_workspace(self, workspace_ref: str) -> Mapping[str, Any]: ...

    def read_surface(
        self, workspace_ref: str, surface: str, *, persona_id: str
    ) -> Mapping[str, Any]: ...

    def conversation_turn(
        self, workspace_ref: str, department_id: str, user_text: str, *, persona_id: str
    ) -> Mapping[str, Any]: ...


@dataclass(frozen=True, slots=True)
class WorkspaceBinding:
    provider_id: str
    provider_workspace_ref: str
    space: SpaceRef


class ProviderIndependentWorkspaceGateway:
    """Authority-first bridge between mobile Pilot and replaceable workspace providers.

    The gateway stores no Boardroom records. It binds a canonical SpaceRef to a provider
    reference, validates a separately issued membership, and requests only the named
    surface from the owning provider.
    """

    MAX_PROVIDERS = 16
    MAX_MEMBERSHIPS = 512
    MAX_SCOPES = 64
    ALLOWED_SURFACES = frozenset(
        {"overview", "briefings", "departments", "agents", "dashboards", "files", "packages", "decisions", "support", "people", "sales", "finance", "work_schedule"}
    )

    MANIFEST_COLLECTIONS = (
        "departments", "agents", "dashboards", "files", "packages", "decisions"
    )

    def __init__(
        self,
        *,
        issuer_id: str = "",
        issuer_identity: DeviceIdentity | None = None,
        pairing_authority: MobilePairingAuthority | None = None,
        commercial_service: Any | None = None,
    ) -> None:
        self._providers: dict[str, WorkspaceProvider] = {}
        self._bindings: dict[str, WorkspaceBinding] = {}
        self._memberships: dict[str, Membership] = {}
        self._invitations: dict[str, dict[str, Any]] = {}
        self._invitation_replays: dict[str, str] = {}
        self._card_states: dict[str, dict[str, Any]] = {}
        self._card_replays: dict[str, dict[str, Any]] = {}
        self._signoff_packages: dict[str, dict[str, Any]] = {}
        self._signoff_replays: dict[str, dict[str, Any]] = {}
        self._cross_space_file_refs: dict[str, dict[str, Any]] = {}
        self._desktop_handoffs: dict[str, dict[str, Any]] = {}
        self._issuer_id = issuer_id
        self._issuer_identity = issuer_identity
        self._pairing = pairing_authority
        self._commercial = commercial_service

    def register_provider(self, provider: WorkspaceProvider) -> None:
        provider_id = str(getattr(provider, "provider_id", "")).strip()
        if not provider_id or len(provider_id) > 80:
            raise ValueError("provider_id is required and must be bounded")
        if provider_id not in self._providers and len(self._providers) >= self.MAX_PROVIDERS:
            raise ValueError("workspace provider limit reached")
        self._providers[provider_id] = provider

    def discover(self, provider_id: str) -> tuple[WorkspaceBinding, ...]:
        provider = self._provider(provider_id)
        records = provider.list_workspaces()
        if len(records) > 256:
            raise ValueError("provider returned too many workspaces")
        bindings: list[WorkspaceBinding] = []
        for record in records:
            provider_ref = str(record.get("id") or "").strip()
            if not provider_ref:
                continue
            space = adapt_workspace(record)
            binding = WorkspaceBinding(provider_id, provider_ref, space)
            self._bindings[space.space_id] = binding
            bindings.append(binding)
        return tuple(bindings)

    def grant_membership(self, membership: Membership) -> None:
        if membership.space_id not in self._bindings:
            raise ValueError("workspace is not bound to a registered provider")
        if len(membership.scopes) > self.MAX_SCOPES:
            raise ValueError("membership contains too many scopes")
        if membership.membership_id not in self._memberships and len(self._memberships) >= self.MAX_MEMBERSHIPS:
            raise ValueError("workspace membership limit reached")
        self._memberships[membership.membership_id] = membership

    def spaces_for(self, persona_id: str) -> tuple[dict[str, Any], ...]:
        visible: list[dict[str, Any]] = []
        for membership in self._memberships.values():
            if membership.persona_id != persona_id or not membership.is_active():
                continue
            binding = self._bindings.get(membership.space_id)
            if binding is None:
                continue
            visible.append(
                {
                    "space": binding.space.to_dict(),
                    "membership": membership.to_dict(),
                    "provider_id": binding.provider_id,
                }
            )
        return tuple(sorted(visible, key=lambda item: item["space"]["display_name"].casefold()))

    def mobile_spaces_snapshot(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        """Return only the workspaces the signed phone already has authority to see.

        This deliberately does not create a membership, infer an owner role, or
        expose a provider catalogue.  A founder must be enrolled through the
        normal workspace membership route before a Boardroom appears on mobile.
        """
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.read",
        )
        requested_persona = str(request.get("persona_id") or persona_id)
        if requested_persona != persona_id:
            raise PermissionError("workspace snapshot targets another person")
        return {
            "ok": True,
            "persona_id": persona_id,
            "spaces": list(self.spaces_for(persona_id)),
            "source_of_truth": "workspace_membership",
            "private_phone_only": True,
        }

    def mobile_open_surface(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        """Open the caller's active workspace surface with one possession proof.

        The active membership is derived only from the signed certificate.  The
        requested surface is validated here before dispatch: protected Finance
        and People data require their explicit membership grants.
        """
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.read",
        )
        if str(request.get("persona_id") or persona_id) != persona_id:
            raise PermissionError("workspace surface targets another person")
        surface = str(request.get("surface") or "overview")
        if surface not in self.ALLOWED_SURFACES:
            raise ValueError("workspace surface is not supported")
        spaces = self.spaces_for(persona_id)
        if not spaces:
            raise PermissionError("no authorised workspace is connected to this phone")
        membership_id = str(dict(spaces[0].get("membership") or {}).get("membership_id") or "")
        membership = self._active_membership(persona_id, membership_id)
        required_scope = f"workspace.{surface}.read"
        if surface in {"finance", "people"} and required_scope not in membership.scopes:
            raise PermissionError(f"membership does not permit {required_scope}")
        if surface not in {"finance", "people"} and required_scope not in membership.scopes and "workspace.read" not in membership.scopes:
            raise PermissionError(f"membership does not permit {required_scope}")
        return self.read(persona_id=persona_id, membership_id=membership_id, surface=surface)

    def surface_manifests_for(
        self, *, persona_id: str, device_id: str, surface_id: str, lease_id: str,
        ttl_seconds: int = 300,
    ) -> tuple[dict[str, Any], ...]:
        """Publish only active memberships and provider-declared read capabilities."""
        manifests: list[dict[str, Any]] = []
        for visible in self.spaces_for(persona_id):
            membership = dict(visible["membership"])
            binding = self._bindings.get(str(membership.get("space_id") or ""))
            if binding is None:
                continue
            descriptor = dict(self._provider(binding.provider_id).describe_workspace(binding.provider_workspace_ref))
            declared = {str(item) for item in descriptor.get("permitted_actions", ()) if str(item)}
            capabilities = [str(item) for item in membership.get("scopes", ()) if str(item) in declared]
            if not capabilities:
                continue
            manifests.append(self.publish_signed_manifest(
                persona_id=persona_id, membership_id=str(membership["membership_id"]),
                device_id=device_id, lease_id=lease_id, surface_id=surface_id,
                requested_capabilities=capabilities, ttl_seconds=ttl_seconds,
            ))
        return tuple(manifests[:24])

    def manage_membership(
        self,
        *,
        actor_persona_id: str,
        actor_membership_id: str,
        target_membership_id: str,
        operation: str,
        role_id: str = "",
        scopes: Sequence[str] = (),
        expires_at: str = "",
        reason: str = "",
    ) -> dict[str, Any]:
        actor = self._active_membership(actor_persona_id, actor_membership_id)
        if "workspace.members.manage" not in actor.scopes:
            raise PermissionError("membership does not permit member administration")
        target = self._memberships.get(target_membership_id)
        if target is None or target.space_id != actor.space_id:
            raise PermissionError("target membership is unavailable in this workspace")
        if operation not in {"change_role", "suspend", "restore", "revoke", "set_expiry"}:
            raise ValueError("unsupported membership operation")
        new_role = target.role_id
        new_scopes = target.scopes
        new_status = target.status
        new_expiry = target.expires_at
        if operation == "change_role":
            offered = tuple(dict.fromkeys(str(item) for item in scopes if str(item)))
            if not role_id or not offered:
                raise ValueError("role and exact scopes are required")
            grantable = set(actor.scopes).difference({"workspace.members.manage"})
            if set(offered).difference(grantable):
                raise PermissionError("administrator cannot grant scopes they do not hold")
            new_role, new_scopes = role_id, offered
        elif operation == "suspend":
            new_status = "suspended"
        elif operation == "restore":
            if target.status != "suspended":
                raise ValueError("only a suspended membership can be restored")
            new_status = "active"
        elif operation == "revoke":
            new_status = "revoked"
        elif operation == "set_expiry":
            parsed = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if parsed <= datetime.now(timezone.utc):
                raise ValueError("membership expiry must be in the future")
            new_expiry = parsed.isoformat()
        changed = Membership(
            membership_id=target.membership_id,
            persona_id=target.persona_id,
            space_id=target.space_id,
            role_id=new_role,
            scopes=new_scopes,
            status=new_status,
            issued_at=target.issued_at,
            expires_at=new_expiry,
            revision=target.revision + 1,
        )
        self._memberships[target_membership_id] = changed
        return {
            "membership": changed.to_dict(),
            "receipt": {
                "operation": operation,
                "actor_persona_id": actor_persona_id,
                "reason": " ".join(reason.split())[:240],
                "recorded_at": utc_now_iso(),
                "membership_hash": changed.contract_hash(),
                "immediately_enforced": True,
            },
        }

    def read(
        self,
        *,
        persona_id: str,
        membership_id: str,
        surface: str,
    ) -> dict[str, Any]:
        if surface not in self.ALLOWED_SURFACES:
            raise ValueError("workspace surface is not supported")
        membership = self._active_membership(persona_id, membership_id)
        required_scope = f"workspace.{surface}.read"
        # Employee records are a protected directory. They must have an explicit
        # grant, even where a membership can read normal workspace summaries.
        sensitive_surface = surface in {"people", "finance"}
        if required_scope not in membership.scopes and (sensitive_surface or "workspace.read" not in membership.scopes):
            raise PermissionError(f"membership does not permit {required_scope}")
        binding = self._bindings[membership.space_id]
        provider = self._provider(binding.provider_id)
        result = dict(
            provider.read_surface(binding.provider_workspace_ref, surface, persona_id=persona_id)
        )
        self._validate_provider_result(result)
        self._assert_no_personal_payload(result.get("data", {}))
        return {
            "ok": True,
            "space": binding.space.to_dict(),
            "membership_id": membership.membership_id,
            "surface": surface,
            "provider_id": binding.provider_id,
            "provider_revision": result.get("revision"),
            "data": result.get("data", {}),
            "retrieved_at": utc_now_iso(),
            "projection_hash": canonical_hash(result.get("data", {})),
            "authority": "active_membership",
            "source_of_truth": "workspace_provider",
        }

    def conversation_turn(
        self,
        *,
        persona_id: str,
        membership_id: str,
        department_id: str,
        user_text: str,
    ) -> dict[str, Any]:
        membership = self._active_membership(persona_id, membership_id)
        department = " ".join(str(department_id or "boardroom").split()).casefold()[:80]
        required_scope = f"workspace.department.{department}.conversation"
        if "workspace.conversation" not in membership.scopes and required_scope not in membership.scopes:
            raise PermissionError("membership does not permit this workspace conversation")
        question = " ".join(str(user_text or "").split())[:2_000]
        if not question:
            raise ValueError("workspace conversation text is required")
        binding = self._bindings[membership.space_id]
        provider = self._provider(binding.provider_id)
        handler = getattr(provider, "conversation_turn", None)
        if not callable(handler):
            raise NotImplementedError("workspace provider does not support governed conversation")
        result = dict(handler(
            binding.provider_workspace_ref, department, question, persona_id=persona_id
        ))
        if bool(result.get("external_writes_performed")):
            raise ValueError("workspace conversation provider attempted an external write")
        turn = result.get("turn")
        if not isinstance(turn, Mapping) or not str(turn.get("content") or "").strip():
            raise ValueError("workspace conversation provider returned an invalid turn")
        if len(str(result).encode("utf-8")) > 256_000:
            raise ValueError("workspace conversation response exceeds the mobile limit")
        return {
            "ok": True,
            "space": binding.space.to_dict(),
            "membership_id": membership.membership_id,
            "department_id": department,
            "provider_id": binding.provider_id,
            "conversation": result,
            "question_hash": canonical_hash({"question": question}),
            "retrieved_at": utc_now_iso(),
            "authority": "active_membership",
            "source_of_truth": "workspace_provider",
            "external_writes_performed": False,
        }

    def conversation_history(
        self, *, persona_id: str, membership_id: str, department_id: str, before: str = "", limit: int = 50
    ) -> dict[str, Any]:
        membership = self._active_membership(persona_id, membership_id)
        department = " ".join(str(department_id or "pilot").split()).casefold()[:80]
        required_scope = f"workspace.department.{department}.conversation"
        if "workspace.conversation" not in membership.scopes and required_scope not in membership.scopes:
            raise PermissionError("membership does not permit this workspace conversation")
        binding = self._bindings[membership.space_id]
        provider = self._provider(binding.provider_id)
        handler = getattr(provider, "conversation_history", None)
        if not callable(handler):
            raise NotImplementedError("workspace provider does not support conversation history")
        history = dict(handler(binding.provider_workspace_ref, department, before=str(before or ""), limit=limit))
        return {
            "ok": True, "membership_id": membership.membership_id, "department_id": department,
            "provider_id": binding.provider_id, "history": history,
            "retrieved_at": utc_now_iso(), "authority": "active_membership",
            "source_of_truth": "workspace_provider",
        }

    def executive_channels_status(self, *, persona_id: str, membership_id: str) -> dict[str, Any]:
        membership = self._active_membership(persona_id, membership_id)
        if "workspace.conversation" not in membership.scopes:
            raise PermissionError("membership does not permit executive channels")
        binding = self._bindings[membership.space_id]
        provider = self._provider(binding.provider_id)
        handler = getattr(provider, "executive_channel_status", None)
        if not callable(handler):
            raise NotImplementedError("workspace provider does not support executive channels")
        result = dict(handler(binding.provider_workspace_ref))
        return {"ok": True, "membership_id": membership.membership_id,
                "provider_id": binding.provider_id, "executive": result,
                "retrieved_at": utc_now_iso(), "authority": "active_membership",
                "source_of_truth": "workspace_provider", "external_writes_performed": False}

    def executive_channel_history(
        self, *, persona_id: str, membership_id: str, department_id: str, limit: int = 75,
    ) -> dict[str, Any]:
        membership = self._active_membership(persona_id, membership_id)
        department = " ".join(str(department_id or "").split()).casefold()[:80]
        required_scope = f"workspace.department.{department}.conversation"
        if "workspace.conversation" not in membership.scopes and required_scope not in membership.scopes:
            raise PermissionError("membership does not permit this executive channel")
        binding = self._bindings[membership.space_id]
        provider = self._provider(binding.provider_id)
        handler = getattr(provider, "executive_channel_history", None)
        if not callable(handler):
            raise NotImplementedError("workspace provider does not support executive channels")
        history = dict(handler(binding.provider_workspace_ref, department, limit=max(10, min(int(limit), 100))))
        return {"ok": True, "membership_id": membership.membership_id,
                "department_id": history.get("department_id") or department,
                "provider_id": binding.provider_id, "history": history,
                "retrieved_at": utc_now_iso(), "authority": "active_membership",
                "source_of_truth": "workspace_provider", "external_writes_performed": False}

    def executive_channel_turn(
        self, *, persona_id: str, membership_id: str, department_id: str, user_text: str,
    ) -> dict[str, Any]:
        membership = self._active_membership(persona_id, membership_id)
        department = " ".join(str(department_id or "").split()).casefold()[:80]
        required_scope = f"workspace.department.{department}.conversation"
        if "workspace.conversation" not in membership.scopes and required_scope not in membership.scopes:
            raise PermissionError("membership does not permit this executive channel")
        text = " ".join(str(user_text or "").split())[:2_000]
        if not text:
            raise ValueError("executive channel message is required")
        binding = self._bindings[membership.space_id]
        provider = self._provider(binding.provider_id)
        handler = getattr(provider, "executive_channel_turn", None)
        if not callable(handler):
            raise NotImplementedError("workspace provider does not support executive channels")
        result = dict(handler(
            binding.provider_workspace_ref, department, text, persona_id=persona_id,
        ))
        if bool(result.get("external_writes_performed")):
            raise ValueError("executive channel provider attempted an external write")
        return {"ok": True, "membership_id": membership.membership_id,
                "department_id": department, "provider_id": binding.provider_id,
                "executive": result, "retrieved_at": utc_now_iso(),
                "authority": "active_membership", "source_of_truth": "workspace_provider",
                "external_writes_performed": False}

    def review_cards(self, *, persona_id: str, membership_id: str) -> dict[str, Any]:
        membership = self._active_membership(persona_id, membership_id)
        if "workspace.cards.read" not in membership.scopes and "workspace.read" not in membership.scopes:
            raise PermissionError("membership does not permit workspace review cards")
        binding = self._bindings[membership.space_id]
        provider = self._provider(binding.provider_id)
        result = dict(provider.read_surface(binding.provider_workspace_ref, "departments", persona_id=persona_id))
        self._validate_provider_result(result)
        work = result.get("data", {}).get("work", []) if isinstance(result.get("data"), Mapping) else []
        cards: list[dict[str, Any]] = []
        for item in work[:100] if isinstance(work, list) else []:
            if not isinstance(item, Mapping):
                continue
            source_ref = str(item.get("task_id") or "").strip()
            if not source_ref:
                continue
            key = f"{membership.space_id}:{source_ref}"
            base = {
                "card_id": f"card/{canonical_hash({'space_id': membership.space_id, 'source_ref': source_ref})[:24]}",
                "space_id": membership.space_id,
                "source_ref": source_ref,
                "department_id": str(item.get("department_id") or "")[:80],
                "title": str(item.get("title") or "Untitled work")[:200],
                "source_status": str(item.get("status") or "unknown")[:80],
                "state": "ready_for_review",
                "revision": 1,
            }
            current = self._card_states.get(key)
            if current:
                base.update(current)
            base["scope_hash"] = canonical_hash({k: v for k, v in base.items() if k != "scope_hash"})
            cards.append(base)
        return {
            "ok": True, "space": binding.space.to_dict(), "membership_id": membership_id,
            "cards": cards, "provider_revision": result.get("revision"), "private_phone_only": True,
            "external_writes_performed": False,
        }

    def act_on_review_card(
        self,
        *,
        persona_id: str,
        membership_id: str,
        card_id: str,
        operation: str,
        expected_scope_hash: str,
        correction: str = "",
        recipient_ref: str = "",
        idempotency_key: str,
    ) -> dict[str, Any]:
        membership = self._active_membership(persona_id, membership_id)
        required = "workspace.approve" if operation == "approve" else "workspace.cards.act"
        if required not in membership.scopes:
            raise PermissionError(f"membership does not permit {required}")
        if operation not in {"review", "correct", "delegate", "approve"}:
            raise ValueError("unsupported workspace review-card operation")
        clean_correction = " ".join(correction.split())[:2_000]
        clean_recipient = " ".join(recipient_ref.split())[:200]
        if operation == "correct" and not clean_correction:
            raise ValueError("correction text is required")
        if operation == "delegate" and not clean_recipient:
            raise ValueError("an exact delegation recipient is required")
        request_hash = canonical_hash({
            "persona_id": persona_id, "membership_id": membership_id, "card_id": card_id,
            "operation": operation, "scope_hash": expected_scope_hash,
            "correction": clean_correction, "recipient_ref": clean_recipient,
        })
        replay = self._card_replays.get(idempotency_key)
        if replay:
            if replay["request_hash"] != request_hash:
                raise ValueError("idempotency key was reused for a different card action")
            return dict(replay["result"])
        snapshot = self.review_cards(persona_id=persona_id, membership_id=membership_id)
        card = next((dict(item) for item in snapshot["cards"] if item["card_id"] == card_id), None)
        if card is None:
            raise LookupError("workspace review card was not found")
        if card["scope_hash"] != expected_scope_hash:
            raise PermissionError("workspace review card changed before action")
        state = {
            "review": "reviewed", "correct": "correction_requested",
            "delegate": "delegation_prepared", "approve": "approved",
        }[operation]
        stored = {
            "state": state, "revision": int(card["revision"]) + 1,
            "last_operation": operation, "acted_by": persona_id, "acted_at": utc_now_iso(),
        }
        if clean_correction:
            stored["correction"] = clean_correction
        if clean_recipient:
            stored["recipient_ref"] = clean_recipient
        key = f"{membership.space_id}:{card['source_ref']}"
        self._card_states[key] = stored
        receipt = {
            "operation": operation, "card_id": card_id, "previous_scope_hash": expected_scope_hash,
            "actor_persona_id": persona_id, "membership_id": membership_id,
            "recorded_at": stored["acted_at"], "external_write_performed": False,
        }
        receipt["receipt_hash"] = canonical_hash(receipt)
        result = {"ok": True, "state": state, "receipt": receipt, "approval_is_execution": False}
        self._card_replays[idempotency_key] = {"request_hash": request_hash, "result": result}
        return result

    def prepare_signoff_package(
        self,
        *,
        persona_id: str,
        membership_id: str,
        card_id: str,
        expected_scope_hash: str,
        signatory_role: str,
        statement: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        membership = self._active_membership(persona_id, membership_id)
        if "workspace.signoff.prepare" not in membership.scopes:
            raise PermissionError("membership does not permit sign-off package preparation")
        role = str(signatory_role or "").casefold().strip()
        if role not in {"accountant", "auditor", "adviser", "director"}:
            raise ValueError("unsupported professional signatory role")
        declaration = " ".join(str(statement or "").split())[:2_000]
        if not declaration:
            raise ValueError("sign-off statement is required")
        snapshot = self.review_cards(persona_id=persona_id, membership_id=membership_id)
        card = next((dict(item) for item in snapshot["cards"] if item["card_id"] == card_id), None)
        if card is None:
            raise LookupError("workspace review card was not found")
        if card["scope_hash"] != expected_scope_hash:
            raise PermissionError("workspace review card changed before sign-off preparation")
        request_hash = canonical_hash({
            "persona_id": persona_id, "membership_id": membership_id, "card_id": card_id,
            "scope_hash": expected_scope_hash, "role": role, "statement": declaration,
        })
        replay = self._signoff_replays.get(idempotency_key)
        if replay:
            if replay["request_hash"] != request_hash:
                raise ValueError("idempotency key was reused for a different sign-off package")
            return dict(replay["result"])
        package_id = f"signoff/{canonical_hash({'request_hash': request_hash, 'idempotency_key': idempotency_key})[:24]}"
        package = {
            "schema_version": "pilot.workspace-signoff-package.v1",
            "package_id": package_id,
            "space_id": membership.space_id,
            "source_card_id": card_id,
            "source_scope_hash": expected_scope_hash,
            "source_ref": card["source_ref"],
            "title": card["title"],
            "signatory_role": role,
            "statement": declaration,
            "prepared_by": persona_id,
            "prepared_at": utc_now_iso(),
            "status": "awaiting_signoff",
            "revision": 1,
        }
        package["package_hash"] = canonical_hash(package)
        self._signoff_packages[package_id] = package
        result = {"ok": True, "package": dict(package), "external_write_performed": False}
        self._signoff_replays[idempotency_key] = {"request_hash": request_hash, "result": result}
        return result

    def signoff_packages(self, *, persona_id: str, membership_id: str) -> dict[str, Any]:
        membership = self._active_membership(persona_id, membership_id)
        if "workspace.signoff.read" not in membership.scopes and "workspace.read" not in membership.scopes:
            raise PermissionError("membership does not permit sign-off package review")
        packages = [dict(item) for item in self._signoff_packages.values() if item["space_id"] == membership.space_id]
        return {
            "ok": True, "space_id": membership.space_id, "membership_id": membership_id,
            "packages": sorted(packages, key=lambda item: item["prepared_at"], reverse=True)[:100],
            "private_phone_only": True,
        }

    def decide_signoff_package(
        self,
        *,
        persona_id: str,
        membership_id: str,
        package_id: str,
        expected_package_hash: str,
        decision: str,
        professional_reference: str,
        phone_device_id: str,
        phone_signature: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        membership = self._active_membership(persona_id, membership_id)
        package = self._signoff_packages.get(package_id)
        if package is None or package["space_id"] != membership.space_id:
            raise LookupError("sign-off package was not found in this workspace")
        exact_scope = f"workspace.signoff.{package['signatory_role']}"
        if "workspace.signoff" not in membership.scopes and exact_scope not in membership.scopes:
            raise PermissionError("membership does not permit this professional sign-off role")
        if decision not in {"signed", "rejected"}:
            raise ValueError("sign-off decision must be signed or rejected")
        reference = " ".join(str(professional_reference or "").split())[:240]
        if decision == "signed" and not reference:
            raise ValueError("professional reference or capacity declaration is required")
        request_hash = canonical_hash({
            "persona_id": persona_id, "membership_id": membership_id, "package_id": package_id,
            "expected_package_hash": expected_package_hash, "decision": decision,
            "professional_reference": reference,
        })
        replay = self._signoff_replays.get(idempotency_key)
        if replay:
            if replay["request_hash"] != request_hash:
                raise ValueError("idempotency key was reused for a different sign-off decision")
            return dict(replay["result"])
        if package["status"] != "awaiting_signoff" or package["package_hash"] != expected_package_hash:
            raise PermissionError("sign-off package changed or is no longer awaiting sign-off")
        receipt = {
            "schema_version": "pilot.workspace-signoff-receipt.v1",
            "package_id": package_id, "package_hash": expected_package_hash,
            "decision": decision, "signatory_role": package["signatory_role"],
            "signer_persona_id": persona_id, "signer_membership_id": membership_id,
            "phone_device_id": phone_device_id, "phone_signature_hash": canonical_hash({"signature": phone_signature}),
            "professional_reference": reference, "signed_at": utc_now_iso(),
            "external_write_performed": False,
        }
        receipt["receipt_hash"] = canonical_hash(receipt)
        package.update({"status": decision, "revision": int(package["revision"]) + 1, "signoff_receipt": receipt})
        result = {"ok": True, "package": dict(package), "receipt": receipt, "independently_verifiable": True}
        self._signoff_replays[idempotency_key] = {"request_hash": request_hash, "result": result}
        return result

    def create_cross_space_file_reference(
        self,
        *,
        persona_id: str,
        source_membership_id: str,
        target_membership_id: str,
        file_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        source = self._active_membership(persona_id, source_membership_id)
        target = self._active_membership(persona_id, target_membership_id)
        if source.space_id == target.space_id:
            raise ValueError("cross-space reference requires two different workspaces")
        if "workspace.files.read" not in source.scopes and "workspace.read" not in source.scopes:
            raise PermissionError("source membership does not permit file references")
        if "workspace.files.reference" not in target.scopes:
            raise PermissionError("target membership does not permit cross-space file references")
        source_binding = self._bindings[source.space_id]
        provider = self._provider(source_binding.provider_id)
        result = dict(provider.read_surface(source_binding.provider_workspace_ref, "files", persona_id=persona_id))
        self._validate_provider_result(result)
        files = result.get("data", {}).get("files", []) if isinstance(result.get("data"), Mapping) else []
        item = next((dict(row) for row in files if isinstance(row, Mapping) and str(row.get("id") or "") == file_id), None)
        if item is None:
            raise LookupError("organization file was not found")
        request_hash = canonical_hash({
            "persona_id": persona_id, "source_membership_id": source_membership_id,
            "target_membership_id": target_membership_id, "file_id": file_id,
        })
        existing = self._cross_space_file_refs.get(idempotency_key)
        if existing:
            if existing["request_hash"] != request_hash:
                raise ValueError("idempotency key was reused for another file reference")
            return dict(existing["result"])
        reference = {
            "schema_version": "pilot.workspace-file-reference.v1",
            "reference_id": f"workspace-file-ref/{canonical_hash({'request_hash': request_hash, 'key': idempotency_key})[:24]}",
            "source_space_id": source.space_id,
            "target_space_id": target.space_id,
            "organization_file_id": file_id,
            "label": str(item.get("label") or "Organization file")[:160],
            "document_type": str(item.get("document_type") or "file")[:80],
            "protected": bool(item.get("protected")),
            "access_mode": "reference_only_reauthorize_at_source",
            "content_included": False,
            "storage_path_included": False,
            "created_by": persona_id,
            "created_at": utc_now_iso(),
        }
        reference["reference_hash"] = canonical_hash(reference)
        result_value = {"ok": True, "reference": reference, "bytes_copied": 0, "source_ownership_preserved": True}
        self._cross_space_file_refs[idempotency_key] = {"request_hash": request_hash, "result": result_value}
        return result_value

    def cross_space_file_references(self, *, persona_id: str, membership_id: str) -> dict[str, Any]:
        membership = self._active_membership(persona_id, membership_id)
        if "workspace.files.reference" not in membership.scopes:
            raise PermissionError("membership does not permit cross-space file references")
        references = [
            dict(record["result"]["reference"]) for record in self._cross_space_file_refs.values()
            if record["result"]["reference"]["target_space_id"] == membership.space_id
        ]
        return {"ok": True, "space_id": membership.space_id, "references": references, "content_included": False}

    def prepare_desktop_handoff(
        self,
        *,
        persona_id: str,
        membership_id: str,
        purpose: str,
        idempotency_key: str,
        ttl_seconds: int = 300,
    ) -> dict[str, Any]:
        membership = self._active_membership(persona_id, membership_id)
        if "workspace.desktop.handoff" not in membership.scopes:
            raise PermissionError("membership does not permit desktop handoff")
        if self._issuer_identity is None or not self._issuer_id:
            raise RuntimeError("desktop handoff signing identity is unavailable")
        intent = " ".join(str(purpose or "").split())[:240]
        if not intent:
            raise ValueError("desktop handoff purpose is required")
        if ttl_seconds < 60 or ttl_seconds > 900:
            raise ValueError("desktop handoff lifetime must be between one and fifteen minutes")
        request_hash = canonical_hash({
            "persona_id": persona_id, "membership_id": membership_id, "purpose": intent,
            "ttl_seconds": ttl_seconds,
        })
        existing = self._desktop_handoffs.get(idempotency_key)
        if existing:
            if existing["request_hash"] != request_hash:
                raise ValueError("idempotency key was reused for another desktop handoff")
            return dict(existing["result"])
        now = datetime.now(timezone.utc).replace(microsecond=0)
        binding = self._bindings[membership.space_id]
        token = canonical_hash({"request_hash": request_hash, "nonce": uuid4().hex, "issued_at": now.isoformat()})
        ticket = {
            "schema_version": "pilot.desktop-handoff.v1",
            "handoff_id": f"handoff/{token[:24]}", "token": token,
            "token_hash": canonical_hash({"token": token}),
            "issuer_id": self._issuer_id, "issuer_public_key": self._issuer_identity.public_key_b64,
            "persona_id": persona_id, "membership_id": membership_id,
            "space_id": membership.space_id, "provider_id": binding.provider_id,
            "provider_workspace_ref": binding.provider_workspace_ref,
            "purpose": intent, "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
            "authentication_required": True, "grants_workspace_access": False,
        }
        signed_payload = {key: value for key, value in ticket.items() if key != "token"}
        ticket["ticket_hash"] = canonical_hash(signed_payload)
        ticket["signature"] = self._issuer_identity.sign(canonical_bytes(signed_payload))
        result = {
            "ok": True, "ticket": ticket,
            "desktop_path": f"/aion-business?workspace_id={binding.provider_workspace_ref}&pilot_handoff={token}",
            "instruction": "Continue on desktop and authenticate there. This handoff does not grant access.",
        }
        self._desktop_handoffs[idempotency_key] = {"request_hash": request_hash, "result": result}
        return result

    def publish_signed_manifest(
        self,
        *,
        persona_id: str,
        membership_id: str,
        device_id: str,
        lease_id: str,
        surface_id: str,
        requested_capabilities: Sequence[str],
        redactions: Sequence[str] = (),
        ttl_seconds: int = 600,
    ) -> dict[str, Any]:
        if self._issuer_identity is None or not self._issuer_id:
            raise RuntimeError("workspace manifest signing identity is unavailable")
        if ttl_seconds < 30 or ttl_seconds > 900:
            raise ValueError("workspace manifest lifetime must be between 30 and 900 seconds")
        membership = self._active_membership(persona_id, membership_id)
        capabilities = tuple(dict.fromkeys(str(item) for item in requested_capabilities if str(item)))
        if not capabilities or len(capabilities) > self.MAX_SCOPES:
            raise ValueError("workspace manifest capabilities are empty or excessive")
        unauthorized = set(capabilities).difference(membership.scopes)
        if unauthorized:
            raise PermissionError("workspace manifest requested capabilities outside the membership")
        binding = self._bindings[membership.space_id]
        descriptor = dict(
            self._provider(binding.provider_id).describe_workspace(binding.provider_workspace_ref)
        )
        catalog = self._bounded_catalog(descriptor)
        declared_actions = {
            str(item) for item in descriptor.get("permitted_actions", ()) if str(item)
        }
        permitted_actions = tuple(item for item in capabilities if item in declared_actions)
        now = datetime.now(timezone.utc).replace(microsecond=0)
        expires = now + timedelta(seconds=ttl_seconds)
        seed = {
            "surface_id": surface_id,
            "persona_id": persona_id,
            "space_id": membership.space_id,
            "lease_id": lease_id,
            "issued_at": now.isoformat(),
        }
        manifest = SurfaceManifest(
            manifest_id=f"manifest/{canonical_hash(seed)[:24]}",
            surface_id=surface_id,
            persona_id=persona_id,
            space_id=membership.space_id,
            lease_id=lease_id,
            capabilities=permitted_actions,
            redactions=tuple(dict.fromkeys(str(item) for item in redactions if str(item)))[:32],
            issued_at=now.isoformat(),
            expires_at=expires.isoformat(),
        )
        payload = {
            "schema_version": "pilot.workspace-manifest.v1",
            "issuer_id": self._issuer_id,
            "issuer_public_key": self._issuer_identity.public_key_b64,
            "provider_id": binding.provider_id,
            "membership_id": membership.membership_id,
            "space": binding.space.to_dict(),
            "membership_summary": {
                "membership_id": membership.membership_id, "role_id": membership.role_id,
                "revision": membership.revision,
            },
            "manifest": manifest.to_dict(),
            "catalog": catalog,
        }
        return {
            **payload,
            "payload_hash": canonical_hash(payload),
            "signature": self._issuer_identity.sign(canonical_bytes(payload)),
        }

    def create_invitation(
        self,
        *,
        inviter_persona_id: str,
        inviter_membership_id: str,
        recipient_ref: str,
        role_id: str,
        requested_scopes: Sequence[str],
        constraints: Mapping[str, Any] | None = None,
        expires_in_seconds: int = 86_400,
        idempotency_key: str,
    ) -> dict[str, Any]:
        inviter = self._active_membership(inviter_persona_id, inviter_membership_id)
        if "workspace.invite" not in inviter.scopes:
            raise PermissionError("membership does not permit workspace invitations")
        scopes = tuple(dict.fromkeys(str(item) for item in requested_scopes if str(item)))
        if not scopes or len(scopes) > self.MAX_SCOPES:
            raise ValueError("invitation scopes are empty or excessive")
        grantable = set(inviter.scopes).difference({"workspace.invite"})
        if set(scopes).difference(grantable):
            raise PermissionError("invitation cannot grant scopes the inviter does not hold")
        if expires_in_seconds < 300 or expires_in_seconds > 2_592_000:
            raise ValueError("invitation lifetime must be between five minutes and 30 days")
        safe_constraints = self._bounded_constraints(constraints or {})
        fingerprint = canonical_hash(
            {
                "inviter_persona_id": inviter_persona_id,
                "membership_id": inviter_membership_id,
                "recipient_ref": recipient_ref,
                "role_id": role_id,
                "scopes": scopes,
                "constraints": safe_constraints,
                "expires_in_seconds": expires_in_seconds,
            }
        )
        replay = self._invitation_replays.get(idempotency_key)
        if replay:
            existing = self._invitations[replay]
            if existing["request_hash"] != fingerprint:
                raise ValueError("idempotency key was already used for different invitation scope")
            return dict(existing)
        if len(self._invitations) >= 1_024:
            raise ValueError("workspace invitation limit reached")
        now = datetime.now(timezone.utc).replace(microsecond=0)
        seed = {"idempotency_key": idempotency_key, "request_hash": fingerprint, "created_at": now.isoformat()}
        invitation_id = f"invite/{canonical_hash(seed)[:24]}"
        invitation = Invitation(
            invitation_id=invitation_id,
            space_id=inviter.space_id,
            inviter_persona_id=inviter_persona_id,
            recipient_ref=recipient_ref,
            role_id=role_id,
            requested_scopes=scopes,
            state=InvitationState.PENDING,
            created_at=now.isoformat(),
            expires_at=(now + timedelta(seconds=expires_in_seconds)).isoformat(),
        )
        record = {
            "invitation": invitation.to_dict(),
            "organization": self._bindings[inviter.space_id].space.to_dict(),
            "constraints": safe_constraints,
            "revocation_route": f"/v1/workspaces/invitations/{invitation_id.split('/', 1)[1]}/revoke",
            "request_hash": fingerprint,
        }
        self._invitations[invitation_id] = record
        self._invitation_replays[idempotency_key] = invitation_id
        return dict(record)

    def revoke_invitation(
        self, *, invitation_id: str, actor_persona_id: str, actor_membership_id: str
    ) -> dict[str, Any]:
        actor = self._active_membership(actor_persona_id, actor_membership_id)
        record = self._invitations.get(invitation_id)
        if record is None:
            raise LookupError("workspace invitation was not found")
        invitation_data = dict(record["invitation"])
        invitation_data.pop("schema_version", None)
        invitation_data["state"] = InvitationState(invitation_data["state"])
        invitation_data["requested_scopes"] = tuple(invitation_data["requested_scopes"])
        current = Invitation(**invitation_data)
        if actor.space_id != current.space_id:
            raise PermissionError("invitation belongs to a different workspace")
        if actor_persona_id != current.inviter_persona_id and "workspace.invite.revoke" not in actor.scopes:
            raise PermissionError("membership cannot revoke this invitation")
        if current.state == InvitationState.REVOKED:
            return dict(record)
        if current.state != InvitationState.PENDING:
            raise ValueError("only a pending invitation can be revoked")
        revoked = Invitation(
            invitation_id=current.invitation_id,
            space_id=current.space_id,
            inviter_persona_id=current.inviter_persona_id,
            recipient_ref=current.recipient_ref,
            role_id=current.role_id,
            requested_scopes=current.requested_scopes,
            state=InvitationState.REVOKED,
            created_at=current.created_at,
            expires_at=current.expires_at,
            revoked_at=utc_now_iso(),
        )
        record["invitation"] = revoked.to_dict()
        return dict(record)

    def invitation_snapshot(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.invitations.read",
        )
        invitations = []
        for record in self._invitations.values():
            invitation = record["invitation"]
            if invitation["recipient_ref"] not in {persona_id, f"person/{persona_id}"}:
                continue
            invitations.append(self._invitation_view(record))
        return {"ok": True, "persona_id": persona_id, "invitations": invitations, "private_phone_only": True}

    def mobile_read_surface(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.read",
        )
        return self.read(
            persona_id=persona_id,
            membership_id=str(request.get("membership_id") or ""),
            surface=str(request.get("surface") or "overview"),
        )

    def mobile_conversation_turn(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.conversation",
        )
        return self.conversation_turn(
            persona_id=persona_id,
            membership_id=str(request.get("membership_id") or ""),
            department_id=str(request.get("department_id") or "boardroom"),
            user_text=str(request.get("user_text") or ""),
        )

    def mobile_conversation_history(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.conversation",
        )
        return self.conversation_history(
            persona_id=persona_id, membership_id=str(request.get("membership_id") or ""),
            department_id=str(request.get("department_id") or "pilot"),
            before=str(request.get("before") or ""), limit=int(request.get("limit") or 50),
        )

    def mobile_executive_channels_status(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.conversation",
        )
        return self.executive_channels_status(
            persona_id=persona_id, membership_id=str(request.get("membership_id") or ""),
        )

    def mobile_executive_channel_history(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.conversation",
        )
        return self.executive_channel_history(
            persona_id=persona_id, membership_id=str(request.get("membership_id") or ""),
            department_id=str(request.get("department_id") or "sales"),
            limit=int(request.get("limit") or 75),
        )

    def mobile_executive_channel_turn(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.conversation",
        )
        return self.executive_channel_turn(
            persona_id=persona_id, membership_id=str(request.get("membership_id") or ""),
            department_id=str(request.get("department_id") or "sales"),
            user_text=str(request.get("user_text") or ""),
        )

    def mobile_custom_department_create(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.custom_departments.manage",
        )
        membership = self._active_membership(persona_id, str(request.get("membership_id") or ""))
        if "workspace.custom_departments.manage" not in membership.scopes:
            raise PermissionError("membership does not permit custom department management")
        binding = self._bindings[membership.space_id]
        provider = self._provider(binding.provider_id)
        handler = getattr(provider, "create_custom_department", None)
        if not callable(handler):
            raise NotImplementedError("workspace provider does not support custom departments")
        result = dict(handler(binding.provider_workspace_ref, dict(request.get("department") or {}), actor_persona_id=persona_id))
        return {"ok": True, "membership_id": membership.membership_id, "department": result, "authority": "founder_custom_department_scope"}

    def mobile_custom_department_delete(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str,
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.custom_departments.manage",
        )
        membership = self._active_membership(persona_id, str(request.get("membership_id") or ""))
        if "workspace.custom_departments.manage" not in membership.scopes:
            raise PermissionError("membership does not permit custom department management")
        binding = self._bindings[membership.space_id]
        provider = self._provider(binding.provider_id)
        handler = getattr(provider, "delete_custom_department", None)
        if not callable(handler):
            raise NotImplementedError("workspace provider does not support custom departments")
        result = dict(handler(binding.provider_workspace_ref, str(request.get("department_id") or ""), actor_persona_id=persona_id))
        return {"ok": True, "membership_id": membership.membership_id, "department": result, "authority": "founder_custom_department_scope"}

    def mobile_review_cards(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.cards.read",
        )
        return self.review_cards(persona_id=persona_id, membership_id=str(request.get("membership_id") or ""))

    def mobile_review_card_action(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        operation = str(request.get("operation") or "")
        phone_scope = "workspace.approve" if operation == "approve" else "workspace.cards.act"
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope=phone_scope,
        )
        return self.act_on_review_card(
            persona_id=persona_id, membership_id=str(request.get("membership_id") or ""),
            card_id=str(request.get("card_id") or ""), operation=operation,
            expected_scope_hash=str(request.get("expected_scope_hash") or ""),
            correction=str(request.get("correction") or ""), recipient_ref=str(request.get("recipient_ref") or ""),
            idempotency_key=str(request.get("idempotency_key") or ""),
        )

    def mobile_prepare_signoff(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.signoff.prepare",
        )
        return self.prepare_signoff_package(
            persona_id=persona_id, membership_id=str(request.get("membership_id") or ""),
            card_id=str(request.get("card_id") or ""), expected_scope_hash=str(request.get("expected_scope_hash") or ""),
            signatory_role=str(request.get("signatory_role") or ""), statement=str(request.get("statement") or ""),
            idempotency_key=str(request.get("idempotency_key") or ""),
        )

    def mobile_signoff_snapshot(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.signoff.read",
        )
        return self.signoff_packages(persona_id=persona_id, membership_id=str(request.get("membership_id") or ""))

    def mobile_decide_signoff(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.signoff",
        )
        return self.decide_signoff_package(
            persona_id=persona_id, membership_id=str(request.get("membership_id") or ""),
            package_id=str(request.get("package_id") or ""), expected_package_hash=str(request.get("expected_package_hash") or ""),
            decision=str(request.get("decision") or ""), professional_reference=str(request.get("professional_reference") or ""),
            phone_device_id=str(certificate.get("device_id") or ""), phone_signature=phone_signature,
            idempotency_key=str(request.get("idempotency_key") or ""),
        )

    def mobile_create_file_reference(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.files.reference",
        )
        return self.create_cross_space_file_reference(
            persona_id=persona_id, source_membership_id=str(request.get("source_membership_id") or ""),
            target_membership_id=str(request.get("target_membership_id") or ""), file_id=str(request.get("file_id") or ""),
            idempotency_key=str(request.get("idempotency_key") or ""),
        )

    def mobile_file_references(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.files.reference",
        )
        return self.cross_space_file_references(
            persona_id=persona_id, membership_id=str(request.get("membership_id") or "")
        )

    def mobile_prepare_desktop_handoff(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.desktop.handoff",
        )
        return self.prepare_desktop_handoff(
            persona_id=persona_id, membership_id=str(request.get("membership_id") or ""),
            purpose=str(request.get("purpose") or "Continue workspace work"),
            idempotency_key=str(request.get("idempotency_key") or ""),
        )

    def mobile_commercial_snapshot(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.commercial.read",
        )
        membership = self._active_membership(persona_id, str(request.get("membership_id") or ""))
        if "workspace.commercial.read" not in membership.scopes:
            raise PermissionError("membership does not permit commercial status")
        if self._commercial is None:
            raise RuntimeError("commercial adoption service is unavailable")
        binding = self._bindings[membership.space_id]
        dashboard = dict(self._commercial.customer_dashboard(tenant_id=binding.provider_workspace_ref))
        if dashboard.get("private_content_included") is not False:
            raise ValueError("commercial dashboard crossed the private-content boundary")
        return {
            "ok": True, "membership_id": membership.membership_id,
            "space": binding.space.to_dict(), "dashboard": dashboard,
            "private_phone_only": True, "external_writes_performed": False,
        }

    def mobile_work_schedule_snapshot(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.read",
        )
        membership = self._active_membership(persona_id, str(request.get("membership_id") or ""))
        binding = self._bindings[membership.space_id]
        provider = self._provider(binding.provider_id)
        handler = getattr(provider, "work_schedule_snapshot", None)
        if not callable(handler):
            raise NotImplementedError("workspace provider does not support work schedules")
        return {"ok": True, "membership_id": membership.membership_id, "schedule": dict(handler(binding.provider_workspace_ref)), "private_phone_only": True}

    def mobile_work_schedule_action(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.read",
        )
        membership = self._active_membership(persona_id, str(request.get("membership_id") or ""))
        binding = self._bindings[membership.space_id]
        provider = self._provider(binding.provider_id)
        handler = getattr(provider, "work_schedule_action", None)
        if not callable(handler):
            raise NotImplementedError("workspace provider does not support work schedule updates")
        result = handler(
            binding.provider_workspace_ref, str(request.get("operation") or ""),
            dict(request.get("fields") or {}), actor_id=persona_id,
        )
        return {"ok": True, "membership_id": membership.membership_id, "schedule": dict(result), "external_writes_performed": False}

    def mobile_commercial_action(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.commercial.control",
        )
        membership = self._active_membership(persona_id, str(request.get("membership_id") or ""))
        if "workspace.commercial.control" not in membership.scopes:
            raise PermissionError("membership does not permit commercial control")
        if self._commercial is None:
            raise RuntimeError("commercial adoption service is unavailable")
        binding = self._bindings[membership.space_id]
        tenant_id = binding.provider_workspace_ref
        operation = str(request.get("operation") or "")
        if operation == "start_trial":
            now = datetime.now(timezone.utc)
            days = int(request.get("days") or 30)
            if not 1 <= days <= 90:
                raise ValueError("trial period must be between 1 and 90 days")
            result = self._commercial.start_trial(
                trial_id=f"trial.{uuid4().hex}", tenant_id=tenant_id,
                department=str(request.get("department") or ""), actor_id=persona_id,
                starts_at=now.isoformat(), ends_at=(now + timedelta(days=days)).isoformat(),
                action_limit=int(request.get("action_limit") or 0),
                managed_cost_limit=float(request.get("managed_cost_limit") or 0),
                currency=str(request.get("currency") or "EUR"),
                offer_version=str(request.get("offer_version") or ""),
                consent_ref=str(request.get("consent_ref") or ""), auto_renew=False,
            )
        elif operation == "cancel_trial":
            trial_id = str(request.get("trial_id") or "")
            current = self._commercial.trial_status(trial_id=trial_id)
            if current.get("tenant_id") != tenant_id:
                raise PermissionError("trial belongs to another workspace")
            result = self._commercial.cancel(
                trial_id=trial_id, actor_id=persona_id,
                cancellation_ref=str(request.get("cancellation_ref") or ""),
            )
        elif operation == "set_capacity":
            result = self._commercial.set_capacity_control(
                tenant_id=tenant_id, department=str(request.get("department") or ""),
                actor_id=persona_id, monthly_action_limit=int(request.get("monthly_action_limit") or 0),
                overage_allowed=bool(request.get("overage_allowed")),
                overage_approval_ref=str(request.get("overage_approval_ref") or ""),
            )
        else:
            raise ValueError("unsupported commercial operation")
        return {
            "ok": True, "operation": operation, "result": result,
            "dashboard": self._commercial.customer_dashboard(tenant_id=tenant_id),
            "membership_id": membership.membership_id, "private_phone_only": True,
        }

    def respond_to_invitation(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any], phone_signature: str
    ) -> dict[str, Any]:
        persona_id = self._authorize_phone(
            request, certificate=certificate, lease=lease, phone_signature=phone_signature,
            scope="workspace.invitations.respond",
        )
        invitation_id = str(request.get("invitation_id") or "")
        decision = str(request.get("decision") or "")
        if decision not in {"accepted", "declined"}:
            raise ValueError("invitation decision must be accepted or declined")
        record = self._invitations.get(invitation_id)
        if record is None:
            raise LookupError("workspace invitation was not found")
        data = dict(record["invitation"])
        if data["recipient_ref"] not in {persona_id, f"person/{persona_id}"}:
            raise PermissionError("workspace invitation belongs to another person")
        if data["state"] != "pending":
            if data["state"] == decision:
                return self._invitation_view(record)
            raise ValueError("workspace invitation is no longer pending")
        expires = datetime.fromisoformat(str(data["expires_at"]).replace("Z", "+00:00"))
        if expires <= datetime.now(timezone.utc):
            data["state"] = "expired"
            record["invitation"] = data
            raise PermissionError("workspace invitation has expired")
        data["state"] = decision
        if decision == "accepted":
            data["accepted_by_persona_id"] = persona_id
            membership = Membership(
                membership_id=f"membership/{canonical_hash({'invitation_id': invitation_id, 'persona_id': persona_id})[:24]}",
                persona_id=persona_id,
                space_id=str(data["space_id"]),
                role_id=str(data["role_id"]),
                scopes=tuple(data["requested_scopes"]),
                status="active",
                issued_at=utc_now_iso(),
                expires_at=str(data["expires_at"]),
            )
            self.grant_membership(membership)
            record["membership"] = membership.to_dict()
        record["invitation"] = data
        record["decision_receipt"] = {
            "decision": decision,
            "persona_id": persona_id,
            "device_id": certificate.get("device_id"),
            "scope_hash": canonical_hash({"invitation_id": invitation_id, "decision": decision}),
            "recorded_at": utc_now_iso(),
        }
        return self._invitation_view(record)

    @staticmethod
    def verify_signed_manifest(
        envelope: Mapping[str, Any], *, expected_persona_id: str = "", expected_device_id: str = ""
    ) -> bool:
        try:
            required = (
                "schema_version", "issuer_id", "issuer_public_key", "provider_id",
                "membership_id", "manifest", "catalog",
            )
            payload = {key: envelope[key] for key in required}
            for optional in ("space", "membership_summary"):
                if optional in envelope:
                    payload[optional] = envelope[optional]
            if payload["schema_version"] != "pilot.workspace-manifest.v1":
                return False
            if canonical_hash(payload) != envelope.get("payload_hash"):
                return False
            if not DeviceIdentity.verify(
                str(payload["issuer_public_key"]), canonical_bytes(payload), str(envelope.get("signature") or "")
            ):
                return False
            manifest = payload["manifest"]
            if expected_persona_id and manifest.get("persona_id") != expected_persona_id:
                return False
            if expected_device_id and manifest.get("surface_id") != expected_device_id:
                return False
            expiry = datetime.fromisoformat(str(manifest["expires_at"]).replace("Z", "+00:00"))
            return expiry > datetime.now(timezone.utc)
        except (KeyError, TypeError, ValueError):
            return False

    def _active_membership(self, persona_id: str, membership_id: str) -> Membership:
        membership = self._memberships.get(membership_id)
        if membership is None or membership.persona_id != persona_id:
            raise PermissionError("workspace membership is unavailable")
        if not membership.is_active(now=datetime.now(timezone.utc)):
            raise PermissionError("workspace membership is inactive or expired")
        if membership.space_id not in self._bindings:
            raise PermissionError("workspace provider binding is unavailable")
        return membership

    def _provider(self, provider_id: str) -> WorkspaceProvider:
        provider = self._providers.get(provider_id)
        if provider is None:
            raise LookupError("workspace provider is not registered")
        return provider

    def _authorize_phone(
        self, request: dict[str, Any], *, certificate: dict[str, Any], lease: dict[str, Any],
        phone_signature: str, scope: str,
    ) -> str:
        if self._pairing is None:
            raise RuntimeError("workspace phone authority is unavailable")
        authority = self._pairing.validate_signed_request(
            certificate=certificate, lease=lease, required_scope=scope,
            request=request, phone_signature=phone_signature,
        )
        return str(authority["persona_id"])

    @staticmethod
    def _invitation_view(record: Mapping[str, Any]) -> dict[str, Any]:
        return {
            key: value for key, value in record.items()
            if key in {"invitation", "organization", "constraints", "revocation_route", "membership", "decision_receipt"}
        }

    @staticmethod
    def _bounded_constraints(constraints: Mapping[str, Any]) -> dict[str, Any]:
        if len(constraints) > 16:
            raise ValueError("invitation has too many constraints")
        allowed = {"departments", "regions", "project_refs", "approval_limit", "working_hours", "notes"}
        if set(constraints).difference(allowed):
            raise ValueError("invitation contains an unsupported constraint")
        if len(str(constraints).encode("utf-8")) > 8_192:
            raise ValueError("invitation constraints exceed the size limit")
        return dict(constraints)

    @staticmethod
    def _validate_provider_result(result: Mapping[str, Any]) -> None:
        if not isinstance(result.get("data", {}), Mapping):
            raise ValueError("workspace provider data must be a mapping")
        encoded_size = len(str(result).encode("utf-8"))
        if encoded_size > 1_000_000:
            raise ValueError("workspace provider response exceeds the mobile projection limit")

    @classmethod
    def _assert_no_personal_payload(cls, value: Any, *, depth: int = 0) -> None:
        if depth > 8:
            return
        prohibited = {
            "personal_pilot", "personal_memory", "private_identity", "private_calendar",
            "personal_calendar", "personal_tasks", "guardian_controlled_children",
            "home_devices", "household_location", "payment_methods",
        }
        if isinstance(value, Mapping):
            for key, item in value.items():
                normalized = str(key).casefold().replace("-", "_").replace(" ", "_")
                if normalized in prohibited:
                    raise PermissionError("workspace provider attempted to expose Personal Pilot data")
                cls._assert_no_personal_payload(item, depth=depth + 1)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            for item in list(value)[:1_000]:
                cls._assert_no_personal_payload(item, depth=depth + 1)

    @classmethod
    def _bounded_catalog(cls, descriptor: Mapping[str, Any]) -> dict[str, list[dict[str, str]]]:
        catalog: dict[str, list[dict[str, str]]] = {}
        for collection in cls.MANIFEST_COLLECTIONS:
            items = descriptor.get(collection, ())
            if not isinstance(items, Sequence) or isinstance(items, (str, bytes)) or len(items) > 100:
                raise ValueError(f"workspace {collection} manifest is invalid or excessive")
            normalized: list[dict[str, str]] = []
            for item in items:
                if not isinstance(item, Mapping):
                    raise ValueError(f"workspace {collection} item must be a mapping")
                reference = str(item.get("id") or "").strip()
                label = str(item.get("label") or item.get("name") or "").strip()
                if not reference or len(reference) > 200 or not label or len(label) > 160:
                    raise ValueError(f"workspace {collection} item is not bounded")
                normalized.append({"id": reference, "label": label})
            catalog[collection] = normalized
        return catalog
