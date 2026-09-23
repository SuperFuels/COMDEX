"""Human-confirmed counterparty memory with bounded LLM classification.

The model may suggest an account; it cannot confirm canonical truth or post to Xero.
Only an authorised review creates a reusable mapping.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any

from backend.modules.aion_business.contracts.department_pilot import canonical_contract_hash
from backend.modules.aion_business.providers.router import ProviderRouter
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _normalise(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _redact_reference(value: Any) -> str:
    text = str(value or "")[:160]
    text = re.sub(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b", "[REDACTED_IBAN]", text, flags=re.I)
    text = re.sub(r"\b\d{8,}\b", "[REDACTED_NUMBER]", text)
    return text


class FinanceCounterpartyIntelligenceService:
    DECISIONS = {"accept_mapping", "reject_mapping", "needs_clarification"}

    def __init__(self, provider_router: ProviderRouter | None = None) -> None:
        self.provider_router = provider_router or ProviderRouter()

    def classify(self, workspace_id: str, transaction: dict[str, Any], accounts: list[dict[str, Any]], *,
                 preferred_provider: str | None = None, preferred_model: str | None = None) -> dict[str, Any]:
        counterparty = str((transaction.get("contact") or {}).get("display_name") or "").strip()
        key = _normalise(counterparty)
        known = self._known(workspace_id, key)
        if known:
            return self._suggestion(transaction, source="confirmed_mapping", account=known,
                                    confidence=1.0, rationale="Reused a mapping previously confirmed by an authorised reviewer.",
                                    model=None, status="known_mapping_review")

        line_codes = [str(item.get("account_code")) for item in (transaction.get("line_items") or []) if item.get("account_code")]
        if line_codes:
            account = next((item for item in accounts if str(item.get("code")) == line_codes[0]), None)
            if account:
                return self._suggestion(transaction, source="xero_existing_account", account=account,
                                        confidence=1.0, rationale="Xero already records an account code on this transaction.",
                                        model=None, status="provider_mapping_review")

        candidates = [
            {"account_id": item.get("account_id"), "code": item.get("code"), "name": item.get("name"), "type": item.get("type")}
            for item in accounts if item.get("status") in (None, "ACTIVE") and item.get("code")
        ][:150]
        minimum_context = {
            "counterparty_label": counterparty[:120],
            "transaction_type": transaction.get("transaction_type"),
            "amount": transaction.get("total"),
            "reference": _redact_reference(transaction.get("reference")),
            "description_lines": [str(item.get("description") or "")[:120] for item in (transaction.get("line_items") or [])[:10]],
            "allowed_accounts": candidates,
        }
        result = self.provider_router.generate(
            prompt=json.dumps(minimum_context, sort_keys=True, ensure_ascii=False),
            system_prompt=(
                "You classify one bookkeeping transaction using only the supplied chart of accounts. "
                "Return JSON only with account_code, category, confidence from 0 to 1, rationale, and "
                "question_for_human. Never invent an account code. Use null account_code and ask a concise "
                "question when evidence is insufficient. A human will review every new mapping."
            ),
            preferred_provider=preferred_provider, preferred_model=preferred_model,
            capability="classification", role_type="FINANCE", max_tokens=400,
            metadata={"workspace_id": workspace_id, "department_id": "finance", "read_only": True,
                      "personal_data_minimised": True, "external_write_allowed": False},
        )
        parsed = self._parse(result.content) if result.ok else {}
        code = str(parsed.get("account_code") or "").strip()
        account = next((item for item in candidates if str(item.get("code")) == code), None)
        confidence = self._confidence(parsed.get("confidence")) if account else 0.0
        if not account:
            parsed["rationale"] = parsed.get("rationale") or "No supported account could be established from the available evidence."
            parsed["question_for_human"] = parsed.get("question_for_human") or f"What type of cost or income is {counterparty or 'this transaction'}?"
        suggestion = self._suggestion(
            transaction, source="llm_suggestion" if account else "human_input_required", account=account,
            confidence=confidence, rationale=str(parsed.get("rationale") or "")[:600],
            model={"provider": result.provider, "model": result.model, "error_code": result.error_code,
                   "minimum_context_hash": canonical_contract_hash(minimum_context)},
            status="human_confirmation_required" if account and confidence >= 0.75 else "needs_human_input",
        )
        suggestion["category"] = parsed.get("category")
        suggestion["question_for_human"] = parsed.get("question_for_human") or "Confirm or select the correct account."
        return suggestion

    def confirm(self, workspace_id: str, suggestion: dict[str, Any], *, decision: str,
                reviewed_by: str, selected_account: dict[str, Any] | None = None,
                notes: str | None = None, reviewed_at: str | None = None) -> dict[str, Any]:
        if decision not in self.DECISIONS:
            raise ValueError("invalid_counterparty_mapping_decision")
        account = selected_account or suggestion.get("suggested_account")
        if decision == "accept_mapping" and not account:
            raise ValueError("accepted_counterparty_mapping_requires_account")
        review = {"decision": decision, "reviewed_by": reviewed_by, "reviewed_at": reviewed_at or _now(), "notes": notes}
        if decision == "accept_mapping":
            self._store_mapping(workspace_id, suggestion, account, review)
        return review

    def _known(self, workspace_id: str, key: str) -> dict[str, Any] | None:
        if not key:
            return None
        payload = self._load(workspace_id)
        item = next((row for row in payload.get("mappings") or [] if row.get("normalised_counterparty") == key and row.get("status") == "confirmed"), None)
        return (item or {}).get("account")

    def _store_mapping(self, workspace_id: str, suggestion: dict[str, Any], account: dict[str, Any], review: dict[str, Any]) -> None:
        payload = self._load(workspace_id)
        key = _normalise(suggestion.get("counterparty"))
        mapping = {"mapping_id": f"counterparty-{canonical_contract_hash({'workspace': workspace_id, 'key': key})[-16:]}",
                   "normalised_counterparty": key, "counterparty_label": suggestion.get("counterparty"),
                   "account": {k: account.get(k) for k in ("account_id", "code", "name", "type")},
                   "status": "confirmed", "confirmed_by": review["reviewed_by"], "confirmed_at": review["reviewed_at"],
                   "source_suggestion_hash": suggestion.get("suggestion_hash")}
        mapping["mapping_hash"] = canonical_contract_hash(mapping)
        payload["mappings"] = [row for row in payload.get("mappings") or [] if row.get("normalised_counterparty") != key] + [mapping]
        payload["updated_at"] = review["reviewed_at"]
        self._save(workspace_id, payload)

    @staticmethod
    def _suggestion(transaction: dict[str, Any], *, source: str, account: dict[str, Any] | None,
                    confidence: float, rationale: str, model: dict[str, Any] | None, status: str) -> dict[str, Any]:
        value = {"schema_version": "aion.finance.counterparty_suggestion.v1",
                 "suggestion_id": f"classification-{transaction.get('bank_transaction_id')}",
                 "bank_transaction_id": transaction.get("bank_transaction_id"),
                 "counterparty": (transaction.get("contact") or {}).get("display_name"),
                 "amount": transaction.get("total"), "date": transaction.get("date"),
                 "source": source, "confidence": confidence, "status": status,
                 "suggested_account": account, "rationale": rationale, "model": model,
                 "review": None, "external_write_performed": False}
        value["suggestion_hash"] = canonical_contract_hash(value)
        return value

    @staticmethod
    def _parse(content: Any) -> dict[str, Any]:
        text = str(content or "").strip()
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
        try:
            value = json.loads(text)
            return value if isinstance(value, dict) else {}
        except (TypeError, ValueError):
            return {}

    @staticmethod
    def _confidence(value: Any) -> float:
        try:
            return max(0.0, min(float(value or 0), 1.0))
        except (TypeError, ValueError):
            return 0.0

    def _path(self, workspace_id: str) -> Path:
        path = AIONBusinessPaths.business_container_dir(workspace_id) / "finance/counterparty_intelligence/mappings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _load(self, workspace_id: str) -> dict[str, Any]:
        path = self._path(workspace_id)
        if not path.exists():
            return {"schema_version": "aion.finance.counterparty_mappings.v1", "workspace_id": workspace_id, "mappings": [], "updated_at": None}
        value = json.loads(path.read_text(encoding="utf-8")); expected = value.pop("mappings_hash", None)
        if not expected or canonical_contract_hash(value) != expected:
            raise ValueError("counterparty_mapping_hash_mismatch")
        return value

    def _save(self, workspace_id: str, payload: dict[str, Any]) -> None:
        value = dict(payload); value.pop("mappings_hash", None); value["mappings_hash"] = canonical_contract_hash(value)
        self._path(workspace_id).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
