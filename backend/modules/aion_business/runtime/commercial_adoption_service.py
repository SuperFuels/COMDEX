"""Governed department trials, verified-action metering and private customer value evidence."""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict

from backend.modules.aion_fabric.canonical import canonical_hash, utc_now_iso


DEPARTMENTS = {"sales", "marketing", "customer_support", "finance_monitoring", "operations", "website_lead_response"}
FUNDING_CLASSES = {"local_customer_owned", "customer_provider", "tessaris_managed"}
NON_BILLABLE_CLASSES = {"internal_reasoning", "retry", "deterministic_check", "local_token", "customer_provider_token"}
EVIDENCE_LEVELS = {"verified", "estimated", "inferred"}


class CommercialAdoptionService:
    _lock = threading.RLock()

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.trials_path = self.root / "department_trials.json"
        self.actions_path = self.root / "verified_action_meter.json"
        self.values_path = self.root / "private_value_ledger.json"
        self.controls_path = self.root / "department_controls.json"

    def start_trial(self, *, trial_id: str, tenant_id: str, department: str, actor_id: str,
                    starts_at: str, ends_at: str, action_limit: int, managed_cost_limit: float,
                    currency: str, offer_version: str, consent_ref: str,
                    auto_renew: bool = False, renewal_plan: str = "", renewal_price: float | None = None) -> Dict[str, Any]:
        self._required(trial_id, tenant_id, actor_id, offer_version, consent_ref, currency)
        if department not in DEPARTMENTS:
            raise ValueError("trial_department_invalid")
        start, end = self._datetime(starts_at), self._datetime(ends_at)
        if end <= start:
            raise ValueError("trial_period_invalid")
        if not 1 <= int(action_limit) <= 1_000_000 or not 0 <= float(managed_cost_limit) <= 1_000_000:
            raise ValueError("trial_limit_invalid")
        if auto_renew and (not renewal_plan or renewal_price is None or float(renewal_price) < 0):
            raise ValueError("auto_renew_terms_required")
        with self._lock:
            records = self._records(self.trials_path)
            if any(item["trial_id"] == trial_id for item in records):
                raise ValueError("trial_id_reused")
            if any(item["tenant_id"] == tenant_id and item["department"] == department and item["state"] in {"active", "paid_active"} for item in records):
                raise ValueError("department_trial_already_active")
            record = {
                "schema_version": "aion.department_trial.v1", "trial_id": trial_id,
                "tenant_id": tenant_id, "department": department, "state": "active",
                "starts_at": start.isoformat(), "ends_at": end.isoformat(),
                "action_limit": int(action_limit), "managed_cost_limit": float(managed_cost_limit),
                "currency": currency.upper(), "offer_version": offer_version,
                "consent_receipt_hash": canonical_hash(consent_ref), "activated_by": actor_id,
                "auto_renew": bool(auto_renew), "renewal_plan": renewal_plan if auto_renew else None,
                "renewal_price": float(renewal_price) if auto_renew else None,
                "customer_content_stored": False, "created_at": utc_now_iso(), "updated_at": utc_now_iso(),
            }
            records.append(record)
            self._write(self.trials_path, records)
            return self.trial_status(trial_id=trial_id, as_of=start.isoformat())

    def record_action(self, *, action_id: str, trial_id: str, tenant_id: str, department: str,
                      action_type: str, accounting_class: str, funding_class: str,
                      verified: bool, receipt_ref: str, cost: float = 0,
                      currency: str = "EUR", provider: str = "local") -> Dict[str, Any]:
        self._required(action_id, trial_id, tenant_id, department, action_type, accounting_class, funding_class, receipt_ref)
        if department not in DEPARTMENTS or funding_class not in FUNDING_CLASSES:
            raise ValueError("action_classification_invalid")
        if float(cost) < 0:
            raise ValueError("action_cost_invalid")
        billable_action = accounting_class == "verified_business_action" and bool(verified)
        if accounting_class not in NON_BILLABLE_CLASSES | {"verified_business_action"}:
            raise ValueError("action_accounting_class_invalid")
        with self._lock:
            records = self._records(self.actions_path)
            if any(item["action_id"] == action_id for item in records):
                raise ValueError("action_id_reused")
            record = {
                "schema_version": "aion.verified_action_meter.v1", "action_id": action_id,
                "trial_id": trial_id, "tenant_id": tenant_id, "department": department,
                "action_type": action_type, "accounting_class": accounting_class,
                "funding_class": funding_class, "provider": provider,
                "verified": bool(verified), "counts_as_verified_action": billable_action,
                "managed_cost": float(cost) if funding_class == "tessaris_managed" else 0.0,
                "customer_funded_cost": float(cost) if funding_class == "customer_provider" else 0.0,
                "local_cost_not_metered": funding_class == "local_customer_owned",
                "currency": currency.upper(), "receipt_hash": canonical_hash(receipt_ref),
                "customer_content_stored": False, "recorded_at": utc_now_iso(),
            }
            records.append(record)
            self._write(self.actions_path, records)
            return record

    def trial_status(self, *, trial_id: str, as_of: str | None = None) -> Dict[str, Any]:
        trial = self._find(self.trials_path, "trial_id", trial_id)
        actions = [item for item in self._records(self.actions_path) if item["trial_id"] == trial_id]
        verified_actions = sum(1 for item in actions if item["counts_as_verified_action"])
        managed_cost = sum(float(item["managed_cost"]) for item in actions if item["currency"] == trial["currency"])
        current = self._datetime(as_of or utc_now_iso())
        reasons = []
        if current >= self._datetime(trial["ends_at"]):
            reasons.append("time_limit_reached")
        if verified_actions >= trial["action_limit"]:
            reasons.append("verified_action_limit_reached")
        if managed_cost >= trial["managed_cost_limit"] and trial["managed_cost_limit"] > 0:
            reasons.append("managed_cost_limit_reached")
        stored_state = trial["state"]
        state = "review_only" if reasons and stored_state == "active" else stored_state
        return {
            **trial, "state": state, "verified_actions": verified_actions,
            "managed_cost": managed_cost, "limit_reasons": reasons,
            "fallback": self._fallback(state), "cross_currency_total_suppressed": True,
        }

    def cancel(self, *, trial_id: str, actor_id: str, cancellation_ref: str) -> Dict[str, Any]:
        return self._transition(trial_id=trial_id, state="cancelled", actor_id=actor_id,
                                receipt_field="cancellation_receipt_hash", receipt_ref=cancellation_ref)

    def activate_paid(self, *, trial_id: str, actor_id: str, entitlement_ref: str,
                      billing_receipt_ref: str) -> Dict[str, Any]:
        self._required(entitlement_ref, billing_receipt_ref)
        result = self._transition(trial_id=trial_id, state="paid_active", actor_id=actor_id,
                                  receipt_field="billing_receipt_hash", receipt_ref=billing_receipt_ref)
        self._set_fields(trial_id, {"entitlement_hash": canonical_hash(entitlement_ref)})
        return {**result, "entitlement_hash": canonical_hash(entitlement_ref)}

    def set_capacity_control(self, *, tenant_id: str, department: str, actor_id: str,
                             monthly_action_limit: int, overage_allowed: bool,
                             overage_approval_ref: str = "") -> Dict[str, Any]:
        self._required(tenant_id, actor_id)
        if department not in DEPARTMENTS or int(monthly_action_limit) < 0:
            raise ValueError("capacity_control_invalid")
        if overage_allowed and not overage_approval_ref:
            raise ValueError("overage_approval_required")
        record = {
            "schema_version": "aion.department_capacity_control.v1", "tenant_id": tenant_id,
            "department": department, "monthly_action_limit": int(monthly_action_limit),
            "overage_allowed": bool(overage_allowed),
            "overage_approval_hash": canonical_hash(overage_approval_ref) if overage_allowed else None,
            "changed_by": actor_id, "changed_at": utc_now_iso(), "customer_content_stored": False,
        }
        with self._lock:
            records = [item for item in self._records(self.controls_path)
                       if not (item["tenant_id"] == tenant_id and item["department"] == department)]
            records.append(record)
            self._write(self.controls_path, records)
        return record

    def record_value(self, *, value_id: str, tenant_id: str, department: str, metric: str,
                     lower: float, upper: float, unit: str, evidence_level: str,
                     evidence_ref: str) -> Dict[str, Any]:
        self._required(value_id, tenant_id, metric, unit, evidence_level, evidence_ref)
        if department not in DEPARTMENTS or evidence_level not in EVIDENCE_LEVELS:
            raise ValueError("value_classification_invalid")
        if metric == "revenue_generated":
            raise ValueError("revenue_generated_requires_separate_causal_authority")
        if float(lower) < 0 or float(upper) < float(lower):
            raise ValueError("value_range_invalid")
        record = {
            "schema_version": "aion.private_value_evidence.v1", "value_id": value_id,
            "tenant_id": tenant_id, "department": department, "metric": metric,
            "lower": float(lower), "upper": float(upper), "unit": unit,
            "evidence_level": evidence_level, "evidence_hash": canonical_hash(evidence_ref),
            "customer_content_stored": False, "recorded_at": utc_now_iso(),
        }
        with self._lock:
            records = self._records(self.values_path)
            if any(item["value_id"] == value_id for item in records):
                raise ValueError("value_id_reused")
            records.append(record)
            self._write(self.values_path, records)
        return record

    def value_summary(self, *, tenant_id: str) -> Dict[str, Any]:
        values = [item for item in self._records(self.values_path) if item["tenant_id"] == tenant_id]
        actions = [item for item in self._records(self.actions_path) if item["tenant_id"] == tenant_id]
        aggregates: Dict[str, Dict[str, Any]] = {}
        for item in values:
            key = f"{item['metric']}::{item['unit']}"
            row = aggregates.setdefault(key, {"metric": item["metric"], "unit": item["unit"], "lower": 0.0,
                                               "upper": 0.0, "evidence_levels": set()})
            row["lower"] += item["lower"]
            row["upper"] += item["upper"]
            row["evidence_levels"].add(item["evidence_level"])
        normalized = [{**row, "evidence_levels": sorted(row["evidence_levels"])} for row in aggregates.values()]
        return {
            "schema_version": "aion.private_value_summary.v1", "tenant_id": tenant_id,
            "verified_actions": sum(1 for item in actions if item["counts_as_verified_action"]),
            "managed_costs_by_currency": self._costs(actions, "managed_cost"),
            "customer_provider_costs_by_currency": self._costs(actions, "customer_funded_cost"),
            "local_inference_charged_by_tessaris": False, "values": sorted(normalized, key=lambda row: (row["metric"], row["unit"])),
            "private_content_included": False,
        }

    def customer_dashboard(self, *, tenant_id: str, as_of: str | None = None) -> Dict[str, Any]:
        """Return a private, content-free customer view of trials, cost, value and controls."""
        trials = [self.trial_status(trial_id=item["trial_id"], as_of=as_of)
                  for item in self._records(self.trials_path) if item["tenant_id"] == tenant_id]
        controls = [item for item in self._records(self.controls_path) if item["tenant_id"] == tenant_id]
        for row in trials:
            row.pop("consent_receipt_hash", None)
            row.pop("billing_receipt_hash", None)
            row.pop("cancellation_receipt_hash", None)
            row.pop("entitlement_hash", None)
        return {
            "schema_version": "aion.commercial_adoption_dashboard.v1",
            "tenant_id": tenant_id,
            "trials": sorted(trials, key=lambda row: (row["department"], row["created_at"])),
            "value": self.value_summary(tenant_id=tenant_id),
            "controls": sorted(controls, key=lambda row: row["department"]),
            "ownership_message": "Your brain, memory, local models, backup and export remain yours.",
            "private_content_included": False,
        }

    @staticmethod
    def _costs(actions: list[Dict[str, Any]], field: str) -> Dict[str, float]:
        result: Dict[str, float] = {}
        for item in actions:
            amount = float(item[field])
            if amount:
                result[item["currency"]] = result.get(item["currency"], 0.0) + amount
        return result

    @staticmethod
    def _fallback(state: str) -> Dict[str, bool]:
        restricted = state in {"review_only", "cancelled"}
        return {"receive_enquiries": True, "deterministic_routing": True, "agent_to_agent": True,
                "prepare_for_review": True, "managed_model": not restricted,
                "autonomous_external_actions": not restricted}

    def _transition(self, *, trial_id: str, state: str, actor_id: str,
                    receipt_field: str, receipt_ref: str) -> Dict[str, Any]:
        self._required(actor_id, receipt_ref)
        with self._lock:
            records = self._records(self.trials_path)
            trial = next((item for item in records if item["trial_id"] == trial_id), None)
            if not trial:
                raise KeyError("trial_not_found")
            if trial["state"] in {"cancelled"}:
                raise ValueError("trial_transition_invalid")
            trial.update({"state": state, "changed_by": actor_id, receipt_field: canonical_hash(receipt_ref),
                          "updated_at": utc_now_iso()})
            self._write(self.trials_path, records)
            return self.trial_status(trial_id=trial_id)

    def _set_fields(self, trial_id: str, fields: Dict[str, Any]) -> None:
        with self._lock:
            records = self._records(self.trials_path)
            trial = next((item for item in records if item["trial_id"] == trial_id), None)
            if not trial:
                raise KeyError("trial_not_found")
            trial.update(fields)
            self._write(self.trials_path, records)

    @staticmethod
    def _datetime(value: str) -> datetime:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return result if result.tzinfo else result.replace(tzinfo=UTC)

    @staticmethod
    def _required(*values: str) -> None:
        if any(not str(value or "").strip() for value in values):
            raise ValueError("required_value_missing")

    def _find(self, path: Path, key: str, value: str) -> Dict[str, Any]:
        result = next((item for item in self._records(path) if item.get(key) == value), None)
        if not result:
            raise KeyError(f"{key}_not_found")
        return dict(result)

    @staticmethod
    def _records(path: Path) -> list[Dict[str, Any]]:
        if not path.exists():
            return []
        return list(json.loads(path.read_text(encoding="utf-8")).get("records") or [])

    @staticmethod
    def _write(path: Path, records: list[Dict[str, Any]]) -> None:
        temporary = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
        temporary.write_text(json.dumps({"records": records}, indent=2, sort_keys=True), encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
