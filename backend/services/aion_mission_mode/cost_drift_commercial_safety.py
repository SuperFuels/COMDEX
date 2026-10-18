from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import json
from typing import Any


COMMERCIAL_WARNING_FIELDS = {
    "tax_amount",
    "fees_amount",
    "renewal_cost",
    "subscription_term",
    "trial_period",
    "auto_renew",
    "cancellation_window",
}

MATERIAL_FIELDS = {
    "provider",
    "action_type",
    "target",
    "currency",
    "plan_estimated_cost",
    "payload_actual_cost",
    "renewal_cost",
    "subscription_term",
    "auto_renew",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _money(value: Any) -> Decimal:
    return Decimal(str(value or "0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def create_commercial_plan_contract(
    *,
    mission_id: str,
    mission_run_id: str,
    step_id: str,
    provider: str,
    action_type: str,
    target: str,
    currency: str,
    plan_estimated_cost: Any,
    cost_variance_percent: Any = "5.00",
    cost_variance_fixed: Any = "5.00",
    renewal_cost: Any | None = None,
    subscription_term: str | None = None,
    auto_renew: bool | None = None,
) -> dict[str, Any]:
    contract = {
        "schema_version": "aion.commercial_plan_contract.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "step_id": step_id,
        "provider": provider,
        "action_type": action_type,
        "target": target,
        "currency": currency,
        "plan_estimated_cost": str(_money(plan_estimated_cost)),
        "cost_variance_percent": str(_money(cost_variance_percent)),
        "cost_variance_fixed": str(_money(cost_variance_fixed)),
        "renewal_cost": None if renewal_cost is None else str(_money(renewal_cost)),
        "subscription_term": subscription_term,
        "auto_renew": auto_renew,
        "commercial_plan_hash": "",
    }
    contract["commercial_plan_hash"] = _hash(
        {k: v for k, v in contract.items() if k != "commercial_plan_hash"}
    )
    return contract


def create_commercial_payload_snapshot(
    *,
    mission_id: str,
    mission_run_id: str,
    step_id: str,
    provider: str,
    action_type: str,
    target: str,
    currency: str,
    payload_actual_cost: Any,
    tax_amount: Any = "0.00",
    fees_amount: Any = "0.00",
    renewal_cost: Any | None = None,
    subscription_term: str | None = None,
    trial_period: str | None = None,
    auto_renew: bool | None = None,
    cancellation_window: str | None = None,
) -> dict[str, Any]:
    payload = {
        "schema_version": "aion.commercial_payload_snapshot.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "step_id": step_id,
        "provider": provider,
        "action_type": action_type,
        "target": target,
        "currency": currency,
        "payload_actual_cost": str(_money(payload_actual_cost)),
        "tax_amount": str(_money(tax_amount)),
        "fees_amount": str(_money(fees_amount)),
        "renewal_cost": None if renewal_cost is None else str(_money(renewal_cost)),
        "subscription_term": subscription_term,
        "trial_period": trial_period,
        "auto_renew": auto_renew,
        "cancellation_window": cancellation_window,
        "commercial_payload_hash": "",
    }
    payload["commercial_payload_hash"] = _hash(
        {k: v for k, v in payload.items() if k != "commercial_payload_hash"}
    )
    return payload


def evaluate_cost_drift(
    *,
    plan_contract: dict[str, Any],
    payload_snapshot: dict[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    warnings: list[str] = []

    for field in ["mission_id", "mission_run_id", "step_id", "provider", "action_type", "target", "currency"]:
        if plan_contract.get(field) != payload_snapshot.get(field):
            reasons.append(f"{field}_mismatch")

    estimated = _money(plan_contract.get("plan_estimated_cost"))
    actual = _money(payload_snapshot.get("payload_actual_cost"))
    absolute_delta = abs(actual - estimated).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    percent_delta = Decimal("0.00")
    if estimated > 0:
        percent_delta = ((absolute_delta / estimated) * Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    allowed_percent = _money(plan_contract.get("cost_variance_percent"))
    allowed_fixed = _money(plan_contract.get("cost_variance_fixed"))

    exceeds_percent = percent_delta > allowed_percent
    exceeds_fixed = absolute_delta > allowed_fixed

    if exceeds_percent and exceeds_fixed:
        reasons.append("cost_drift_exceeds_threshold")

    plan_renewal = plan_contract.get("renewal_cost")
    payload_renewal = payload_snapshot.get("renewal_cost")
    if plan_renewal != payload_renewal:
        reasons.append("renewal_cost_changed")

    if plan_contract.get("subscription_term") != payload_snapshot.get("subscription_term"):
        reasons.append("subscription_term_changed")

    if plan_contract.get("auto_renew") != payload_snapshot.get("auto_renew"):
        reasons.append("auto_renew_changed")

    for field in COMMERCIAL_WARNING_FIELDS:
        if payload_snapshot.get(field) not in (None, "", "0.00", False):
            warnings.append(f"{field}_present")

    allowed = len(reasons) == 0

    result = {
        "schema_version": "aion.cost_drift_evaluation.v0",
        "mission_id": plan_contract["mission_id"],
        "mission_run_id": plan_contract["mission_run_id"],
        "step_id": plan_contract["step_id"],
        "provider": plan_contract["provider"],
        "action_type": plan_contract["action_type"],
        "target": plan_contract["target"],
        "currency": plan_contract["currency"],
        "plan_estimated_cost": str(estimated),
        "payload_actual_cost": str(actual),
        "absolute_delta": str(absolute_delta),
        "percent_delta": str(percent_delta),
        "cost_variance_percent": str(allowed_percent),
        "cost_variance_fixed": str(allowed_fixed),
        "allowed": allowed,
        "commercial_state": "commercial_terms_clear" if allowed else "commercial_re_review_required",
        "requires_plan_re_review": not allowed,
        "warnings": sorted(set(warnings)),
        "reasons": reasons,
        "commercial_plan_hash": plan_contract["commercial_plan_hash"],
        "commercial_payload_hash": payload_snapshot["commercial_payload_hash"],
        "cost_drift_hash": "",
    }
    result["cost_drift_hash"] = _hash({k: v for k, v in result.items() if k != "cost_drift_hash"})
    return result


def bind_commercial_safety_to_external_approval(
    *,
    cost_drift_evaluation: dict[str, Any],
    external_approval: dict[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []

    if not cost_drift_evaluation.get("allowed"):
        reasons.append("commercial_terms_not_clear")

    if not external_approval.get("allowed", False):
        reasons.append("external_approval_not_allowed")

    if cost_drift_evaluation.get("mission_id") != external_approval.get("mission_id"):
        reasons.append("mission_mismatch")

    if cost_drift_evaluation.get("mission_run_id") != external_approval.get("mission_run_id"):
        reasons.append("mission_run_mismatch")

    if cost_drift_evaluation.get("step_id") != external_approval.get("step_id"):
        reasons.append("step_mismatch")

    approval_payload_hash = external_approval.get("approved_payload_hash")
    if approval_payload_hash != cost_drift_evaluation.get("commercial_payload_hash"):
        reasons.append("approval_payload_not_bound_to_commercial_snapshot")

    allowed = not reasons

    result = {
        "schema_version": "aion.commercial_external_approval_binding.v0",
        "mission_id": cost_drift_evaluation.get("mission_id"),
        "mission_run_id": cost_drift_evaluation.get("mission_run_id"),
        "step_id": cost_drift_evaluation.get("step_id"),
        "commercial_payload_hash": cost_drift_evaluation.get("commercial_payload_hash"),
        "external_approval_hash": external_approval.get("approval_hash"),
        "allowed": allowed,
        "binding_state": "commercial_approval_binding_clear" if allowed else "commercial_approval_binding_blocked",
        "reasons": reasons,
        "binding_hash": "",
    }
    result["binding_hash"] = _hash({k: v for k, v in result.items() if k != "binding_hash"})
    return result


def summarize_cost_drift_evaluations(
    *,
    mission_id: str,
    mission_run_id: str,
    evaluations: list[dict[str, Any]],
) -> dict[str, Any]:
    blocked = [item for item in evaluations if not item["allowed"]]
    allowed = [item for item in evaluations if item["allowed"]]

    result = {
        "schema_version": "aion.cost_drift_summary.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "allowed_count": len(allowed),
        "blocked_count": len(blocked),
        "blocked_reasons": sorted({reason for item in blocked for reason in item["reasons"]}),
        "evaluation_hashes": sorted(item["cost_drift_hash"] for item in evaluations),
        "runtime_state": "commercial_terms_clear" if not blocked else "commercial_re_review_required",
        "summary_hash": "",
    }
    result["summary_hash"] = _hash({k: v for k, v in result.items() if k != "summary_hash"})
    return result
