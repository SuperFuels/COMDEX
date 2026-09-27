"""Evidence-grounded, read-only conversation runtime for the Finance Pilot."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.modules.aion_business.contracts.department_pilot import canonical_contract_hash
from backend.modules.aion_business.providers.router import ProviderRouter
from backend.modules.aion_business.runtime.business_container_repository import (
    BusinessContainerRepository,
)
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _number(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("value", value.get("amount"))
    try:
        return None if value is None or str(value).strip() == "" else float(value)
    except (TypeError, ValueError):
        return None


def _metric(metrics: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = _number(metrics.get(key))
        if value is not None:
            return value
    return None


def _bounded_rows(value: Any, limit: int = 25) -> dict[str, Any]:
    rows = list(value or []) if isinstance(value, list) else []
    return {
        "count": len(rows),
        "items": rows[:limit],
        "truncated": len(rows) > limit,
    }


class FinancePilotConversationRepository:
    """Atomic persistence for the permanent Finance terminal conversation."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir) if base_dir else AIONBusinessPaths.DEPARTMENT_PILOT_RUNTIME

    def path(self, workspace_id: str) -> Path:
        path = self.base_dir / workspace_id / "finance" / "conversations"
        path.mkdir(parents=True, exist_ok=True)
        return path / "finance_terminal.json"

    def load(self, workspace_id: str) -> dict[str, Any]:
        path = self.path(workspace_id)
        if not path.exists():
            payload = {
                "schema_version": "aion.finance_pilot.conversation_session.v1",
                "workspace_id": workspace_id,
                "department_id": "finance",
                "session_id": f"finance-terminal-{workspace_id}",
                "turns": [],
                "created_at": _now(),
                "updated_at": _now(),
            }
            payload["session_hash"] = canonical_contract_hash(payload)
            return payload
        return json.loads(path.read_text(encoding="utf-8"))

    def save(self, workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        value = dict(payload)
        value["updated_at"] = str(value.get("updated_at") or _now())
        value.pop("session_hash", None)
        value["session_hash"] = canonical_contract_hash(value)
        path = self.path(workspace_id)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
        return value


class FinancePilotConversationService:
    """Answer Finance questions from canonical context without mutating business truth."""

    def __init__(
        self,
        *,
        container_repository: BusinessContainerRepository | None = None,
        conversation_repository: FinancePilotConversationRepository | None = None,
        provider_router: ProviderRouter | None = None,
    ) -> None:
        self.containers = container_repository or BusinessContainerRepository()
        self.conversations = conversation_repository or FinancePilotConversationRepository()
        self.provider_router = provider_router or ProviderRouter()

    def get_session(self, workspace_id: str) -> dict[str, Any]:
        return self.conversations.load(workspace_id)

    def answer(
        self,
        workspace_id: str,
        user_text: str,
        *,
        preferred_provider: str | None = None,
        preferred_model: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        question = str(user_text or "").strip()
        if not question:
            raise ValueError("finance_question_required")
        timestamp = created_at or _now()
        context, sources, reliability = self._assemble_context(workspace_id, question)
        session = self.conversations.load(workspace_id)
        recent = list(session.get("turns") or [])[-8:]
        content, provider = self._generate(
            workspace_id,
            question,
            context,
            recent,
            preferred_provider,
            preferred_model,
        )
        user_turn = self._turn(
            session,
            role="user",
            content=question,
            created_at=timestamp,
            sources=[],
            reliability="not_applicable",
            provider={"provider": "user", "model": None},
        )
        session.setdefault("turns", []).append(user_turn)
        assistant_turn = self._turn(
            session,
            role="assistant",
            content=content,
            created_at=timestamp,
            sources=sources,
            reliability=reliability,
            provider=provider,
        )
        session["turns"].append(assistant_turn)
        session["turns"] = session["turns"][-200:]
        session["updated_at"] = timestamp
        saved = self.conversations.save(workspace_id, session)
        return {
            "ok": True,
            "workspace_id": workspace_id,
            "department_id": "finance",
            "turn": assistant_turn,
            "session_hash": saved["session_hash"],
            "external_writes_performed": False,
            "approval_gated": True,
        }

    def _assemble_context(
        self, workspace_id: str, question: str
    ) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
        records: dict[str, dict[str, Any]] = {}
        for kind in (
            "business_identity",
            "business_financial_model",
            "business_operating_model",
            "department_intelligence",
        ):
            value = self.containers.load_optional_dict(workspace_id, kind)  # type: ignore[arg-type]
            if value:
                records[kind] = value
        if "business_financial_model" not in records:
            raise FileNotFoundError("finance_model_missing")

        financial = records["business_financial_model"]
        intelligence = records.get("department_intelligence") or {}
        operating = records.get("business_operating_model") or {}
        identity = records.get("business_identity") or {}
        lowered = question.lower()
        needs_operating = any(
            word in lowered
            for word in (
                "price", "product", "service", "stock", "inventory", "margin",
                "labour", "labor", "capacity", "procurement", "volume", "offering",
            )
        )
        needs_intelligence = any(
            word in lowered
            for word in (
                "board", "action", "task", "decision", "previous", "latest", "update",
            )
        )
        context: dict[str, Any] = {
            "business": {
                "name": identity.get("trading_name") or identity.get("name"),
                "currency": financial.get("currency") or identity.get("currency") or "EUR",
            },
            "financial_model": {
                "revision": financial.get("revision"),
                "reporting_period": financial.get("reporting_period") or financial.get("period"),
                "metrics": financial.get("metrics") or {},
                "revenue_model": financial.get("revenue_model") or {},
                "direct_cost_model": financial.get("direct_cost_model") or {},
                "overhead_model": financial.get("overhead_model") or {},
                "cashflow_model": financial.get("cashflow_model") or {},
                "missing_information": financial.get("missing_information") or [],
                "assumptions": financial.get("assumptions") or [],
                "conflicts": financial.get("conflicts") or [],
                "integration_evidence": financial.get("integration_evidence") or {},
            },
        }
        selected_kinds = {"business_identity", "business_financial_model"}
        if needs_operating and operating:
            context["operating_model"] = {
                "revision": operating.get("revision"),
                "offerings": _bounded_rows(operating.get("offerings")),
                "unit_economics": _bounded_rows(operating.get("unit_economics")),
                "inventory_metrics": operating.get("inventory_metrics") or {},
                "financial_targets": _bounded_rows(operating.get("financial_targets")),
            }
            selected_kinds.add("business_operating_model")
        if needs_intelligence and intelligence:
            finance_intelligence = (intelligence.get("departments") or {}).get("finance") or {}
            context["finance_intelligence"] = {
                "status": finance_intelligence.get("status"),
                "boardroom_summary": finance_intelligence.get("boardroom_summary"),
                "latest_pilot_result": finance_intelligence.get("latest_pilot_result"),
                "missing_information": finance_intelligence.get("missing_information") or [],
            }
            selected_kinds.add("department_intelligence")
        evidence_refs = list(financial.get("evidence_refs") or [])
        xero = (financial.get("integration_evidence") or {}).get("xero") or {}
        sources: list[dict[str, Any]] = []
        verification_states: list[str] = []
        for kind, record in records.items():
            if kind not in selected_kinds:
                continue
            state = "founder_supplied"
            if kind == "business_financial_model" and (evidence_refs or xero):
                state = "source_backed"
            if record.get("conflicts"):
                state = "conflicted"
            sources.append(
                {
                    "source_id": f"{workspace_id}:{kind}:r{record.get('revision') or 1}",
                    "label": kind.replace("_", " ").title(),
                    "container_kind": kind,
                    "revision": record.get("revision"),
                    "content_hash": canonical_contract_hash(record),
                    "verification_state": state,
                }
            )
            verification_states.append(state)
        if "conflicted" in verification_states:
            reliability = "conflicted"
        elif "source_backed" in verification_states:
            reliability = "source_backed"
        else:
            reliability = "founder_supplied_unverified"
        return context, sources, reliability

    def _generate(
        self,
        workspace_id: str,
        question: str,
        context: dict[str, Any],
        recent: list[dict[str, Any]],
        preferred_provider: str | None,
        preferred_model: str | None,
    ) -> tuple[str, dict[str, Any]]:
        direct = self._direct_factual_answer(question, context)
        if direct is not None:
            return direct, {
                "provider": "deterministic_finance_fact",
                "model": None,
                "fallback_used": False,
            }
        labels = ["[Financial Model]"]
        if "operating_model" in context:
            labels.append("[Operating Model]")
        if "finance_intelligence" in context:
            labels.append("[Finance Intelligence]")
        source_labels = ", ".join(labels)
        system = (
            "You are the Finance Pilot for one business. Answer only from the supplied canonical "
            "context. Never invent a number. State when information is missing, stale, assumed or "
            "conflicted. Cite supporting sections using these labels: " + source_labels + ". "
            "Be concise and practical. You may analyse and recommend, but you cannot perform an "
            "external write or imply that an action has been executed. Use the currency symbol "
            "for amounts (for example, € for EUR), never spell the currency name."
        )
        # Keep phone conversations responsive: canonical records can contain detailed
        # models and historic results that are useful for storage but unnecessary for
        # a single Finance reply. The bounded extract below preserves the evidence
        # boundary without turning every mobile question into a long-context run.
        compact_context = self._conversation_context(context)
        prompt = json.dumps(
            {
                "question": question,
                "recent_conversation": [
                    {
                        "role": item.get("role"),
                        "content": str(item.get("content") or "")[:600],
                    }
                    for item in recent[-2:]
                ],
                "canonical_context": compact_context,
            },
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
        result = self.provider_router.generate(
            prompt=prompt,
            system_prompt=system,
            preferred_provider=preferred_provider,
            preferred_model=preferred_model,
            # The evidence boundary is enforced here, while the local model uses the
            # conversational drafting route to answer naturally in the Finance chat.
            capability="drafting",
            role_type="FINANCE",
            metadata={
                "workspace_id": workspace_id,
                "department_id": "finance",
                "read_only": True,
            },
            max_tokens=900,
        )
        if result.ok and str(result.content or "").strip():
            return str(result.content).strip(), {
                "provider": result.provider,
                "model": result.model,
                "latency_ms": result.latency_ms,
                "fallback_used": result.fallback_used,
            }
        return self._grounded_fallback(question, context), {
            "provider": "deterministic_finance_fallback",
            "model": None,
            "error_code": result.error_code,
        }

    @staticmethod
    def _direct_factual_answer(question: str, context: dict[str, Any]) -> str | None:
        """Answer single recorded headline facts without asking a language model.

        These are exact retrieval questions, not drafting tasks. Keeping them on
        the canonical path also means a model outage cannot turn a one-number
        question into an unrelated general briefing.
        """
        lowered = question.casefold()
        if not any(term in lowered for term in ("turnover", "revenue")):
            return None
        if any(term in lowered for term in (
            "compare", "growth", "forecast", "why", "trend", "summary", "overview", "update",
            "gross profit", "operating profit", "cash", "margin", "expense", "cost",
        )):
            return None
        financial = context.get("financial_model") or {}
        revenue = _metric(financial.get("metrics") or {}, "revenue", "net_sales", "annualised_revenue")
        if revenue is None:
            return "The Financial Model does not contain a recorded turnover figure. [Financial Model]"
        currency = str((context.get("business") or {}).get("currency") or "EUR").strip().upper()
        symbol = {"EUR": "€", "EURO": "€", "EUROS": "€", "GBP": "£", "USD": "$"}.get(currency, currency + " ")
        period = financial.get("reporting_period")
        if isinstance(period, dict):
            period_label = str(period.get("label") or period.get("basis") or "").strip()
        else:
            period_label = str(period or "").strip()
        qualifier = f" for {period_label}" if period_label else " in the recorded financial model (reporting period not specified)"
        return f"Turnover{qualifier} is {symbol}{revenue:,.2f}. [Financial Model] This was a read-only lookup; no external action was taken."

    @staticmethod
    def _conversation_context(context: dict[str, Any]) -> dict[str, Any]:
        """Return only the recorded facts relevant to a concise chat response."""
        financial = context.get("financial_model") if isinstance(context.get("financial_model"), dict) else {}
        compact: dict[str, Any] = {
            "business": context.get("business") or {},
            "financial_model": {
                "revision": financial.get("revision"),
                "metrics": financial.get("metrics") or {},
                "missing_information": list(financial.get("missing_information") or [])[:8],
                "conflicts": list(financial.get("conflicts") or [])[:6],
            },
        }
        intelligence = context.get("finance_intelligence")
        if isinstance(intelligence, dict):
            compact["finance_intelligence"] = {
                "status": intelligence.get("status"),
                "boardroom_summary": str(intelligence.get("boardroom_summary") or "")[:1_200],
                "latest_pilot_result": str(intelligence.get("latest_pilot_result") or "")[:1_200],
                "missing_information": list(intelligence.get("missing_information") or [])[:6],
            }
        operating = context.get("operating_model")
        if isinstance(operating, dict):
            compact["operating_model"] = {
                "revision": operating.get("revision"),
                "inventory_metrics": operating.get("inventory_metrics") or {},
                "financial_targets": operating.get("financial_targets") or {},
            }
        return compact

    @staticmethod
    def _grounded_fallback(question: str, context: dict[str, Any]) -> str:
        financial = context["financial_model"]
        metrics = financial.get("metrics") or {}
        currency = context["business"].get("currency") or "EUR"
        normalized_currency = str(currency).strip().upper()
        symbol = {"EUR": "€", "EURO": "€", "EUROS": "€", "GBP": "£", "USD": "$"}.get(normalized_currency, str(currency) + " ")
        values = {
            "revenue": _metric(metrics, "revenue", "net_sales", "annualised_revenue", "average_monthly_revenue"),
            "gross profit": _metric(metrics, "gross_profit", "monthly_gross_profit"),
            "operating profit": _metric(metrics, "operating_profit", "ebitda_profit", "monthly_operating_surplus"),
            "cash": _metric(metrics, "ending_cash", "cash", "cash_balance"),
            "gross margin": _metric(metrics, "gross_margin_percent"),
            "operating margin": _metric(metrics, "operating_margin_percent"),
        }
        lowered = question.lower()
        daily_terms = ("yesterday", "today", "daily", "this morning")
        if any(term in lowered for term in daily_terms) and any(
            term in lowered for term in ("sale", "revenue", "income", "turnover")
        ):
            return (
                "I do not have a recorded daily sales ledger for that date, so I cannot state "
                "yesterday's sales reliably. The Financial Model records longer-period revenue, "
                "but it must not be presented as a daily result. This was read-only analysis; "
                "no external action was taken."
            )
        selected = [key for key in values if key in lowered]
        if "turnover" in lowered and "revenue" not in selected:
            selected.append("revenue")
        if not selected or any(word in lowered for word in ("update", "overview", "summary")):
            selected = list(values)
        parts = []
        for key in selected:
            value = values[key]
            if value is None:
                continue
            rendered = f"{value:,.2f}%" if "margin" in key else f"{symbol}{value:,.2f}"
            parts.append(f"{key.title()}: {rendered}")
        missing = [str(item) for item in financial.get("missing_information") or []]
        if not parts:
            answer = "I do not have enough recorded Finance evidence to answer that reliably."
        else:
            answer = "Finance update — " + "; ".join(parts) + ". [Financial Model]"
        if missing:
            answer += " Missing information: " + ", ".join(missing[:8]) + "."
        answer += " This was read-only analysis; no external action was taken."
        return answer

    @staticmethod
    def _turn(
        session: dict[str, Any],
        *,
        role: str,
        content: str,
        created_at: str,
        sources: list[dict[str, Any]],
        reliability: str,
        provider: dict[str, Any],
    ) -> dict[str, Any]:
        previous = (session.get("turns") or [])[-1].get("turn_hash") if session.get("turns") else None
        turn = {
            "schema_version": "aion.finance_pilot.conversation_turn.v1",
            "turn_id": f"finance-turn-{uuid4().hex}",
            "workspace_id": session["workspace_id"],
            "department_id": "finance",
            "role": role,
            "content": content,
            "created_at": created_at,
            "sources": sources,
            "reliability": reliability,
            "provider": provider,
            "previous_turn_hash": previous,
            "external_writes_performed": False,
        }
        turn["turn_hash"] = canonical_contract_hash(turn)
        return turn
