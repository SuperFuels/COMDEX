"""Deterministic expense categorisation and ambiguity routing."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any


CATEGORY_LABELS = {
    "materials": "Materials and direct costs", "tools_equipment": "Tools and equipment",
    "office": "Office supplies", "software": "Software and subscriptions",
    "telecoms": "Telephone and internet", "fuel": "Fuel", "vehicle": "Vehicle costs",
    "travel": "Business travel", "accommodation": "Accommodation", "meal": "Meals",
    "business_hospitality": "Business hospitality", "professional_fees": "Professional fees",
    "personal": "Personal / non-business", "mixed": "Mixed business and personal", "other": "Other",
}


def default_expense_policy() -> dict[str, Any]:
    return {
        "receipt_reader_provider": "auto",
        "currency": "EUR",
        "meal_daily_allowance": None,
        "meal_receipt_limit": None,
        "mileage_rate": None,
        "fuel_requires_vehicle": True,
        "meal_requires_business_purpose": True,
        "hospitality_requires_attendees": True,
        "alcohol_always_review": True,
        "mixed_purchase_always_review": True,
        "personal_purchase_always_review": True,
        "policy_note": "Business policy limits are optional. Statutory tax treatment is never inferred from these settings.",
    }


def _merchant_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def assess_expense(
    facts: dict[str, Any], *, learned_mappings: list[dict[str, Any]], policy: dict[str, Any],
) -> dict[str, Any]:
    signals = list(dict.fromkeys(str(item) for item in facts.get("category_signals", []) if item))
    supplier_key = _merchant_key(facts.get("supplier"))
    learned = next((item for item in reversed(learned_mappings) if item.get("supplier_key") == supplier_key), None)
    questions: list[dict[str, str]] = []
    flags: list[str] = []

    if "meal" in signals or "business_hospitality" in signals:
        questions.append({"id": "business_purpose", "label": "What was the business purpose of this meal?"})
        questions.append({"id": "attendees", "label": "Who attended? Include employees, customers or suppliers."})
        flags.append("meal_business_context_not_visible_on_receipt")
    if "alcohol" in signals:
        questions.append({"id": "alcohol_treatment", "label": "Why is the alcohol a valid business cost, or what amount should be excluded?"})
        flags.append("alcohol_requires_review")
    if "fuel" in signals:
        questions.append({"id": "vehicle_and_journey", "label": "Which vehicle and business journey does this fuel relate to?"})
        questions.append({"id": "reclaim_basis", "label": "Is this claimed as actual fuel cost or through the business mileage policy?"})
        flags.append("fuel_business_use_not_visible_on_receipt")
    if "mixed" in signals:
        questions.append({"id": "business_split", "label": "Which line items are business purchases, and what amount should be excluded?"})
        flags.append("mixed_purchase_requires_split")
    if "personal" in signals:
        questions.append({"id": "personal_treatment", "label": "Confirm the personal amount to exclude, or explain the business purpose."})
        flags.append("possible_personal_purchase")

    total = facts.get("total")
    meal_limit = policy.get("meal_receipt_limit")
    if meal_limit not in (None, "") and any(item in signals for item in ("meal", "business_hospitality")):
        try:
            if total is not None and float(total) > float(meal_limit):
                flags.append("meal_exceeds_business_policy_limit")
        except (TypeError, ValueError):
            flags.append("business_policy_limit_invalid")

    suggestion: dict[str, Any] = {"category": None, "category_label": None, "account_code": None, "account_name": None, "tax_code": None, "source": "none", "confidence": 0.0}
    if learned:
        suggestion.update({
            "category": learned.get("category"), "category_label": learned.get("category_label"),
            "account_code": learned.get("account_code"), "account_name": learned.get("account_name"),
            "tax_code": learned.get("tax_code"), "source": "confirmed_supplier_mapping", "confidence": 1.0,
        })
    else:
        usable = [item for item in signals if item not in {"alcohol", "personal", "mixed", "business_hospitality"}]
        primary = facts.get("primary_category")
        primary_confidence = float(facts.get("primary_category_confidence") or 0)
        category = primary if primary in CATEGORY_LABELS and primary not in {"personal", "mixed"} and primary_confidence >= 0.70 else (usable[0] if len(set(usable)) == 1 else None)
        if category:
            confidence = primary_confidence if category == primary else 0.72
            suggestion.update({"category": category, "category_label": CATEGORY_LABELS.get(category, category.replace("_", " ").title()), "source": "visible_document_signal", "confidence": confidence})

    key_confidence = facts.get("field_confidence", {})
    low_fields = [key for key in ("supplier", "document_date", "total") if float(key_confidence.get(key, 0) or 0) < 0.80]
    if low_fields:
        flags.append("low_confidence_key_fields:" + ",".join(low_fields))
    return {
        "suggestion": suggestion,
        "signals": signals,
        "questions": questions,
        "review_flags": list(dict.fromkeys(flags)),
        "straight_through_candidate": bool(not flags and not questions and suggestion.get("category") and not low_fields),
        "policy_snapshot": deepcopy(policy),
        "human_confirmation_required": True,
        "tax_treatment_inferred": False,
    }


def learned_mapping(supplier: Any, allocation: dict[str, Any]) -> dict[str, Any] | None:
    key = _merchant_key(supplier)
    if not key or not any(allocation.get(item) for item in ("category", "account_code", "account_name", "tax_code")):
        return None
    category = allocation.get("category")
    return {
        "supplier_key": key, "supplier": str(supplier).strip(), "category": category,
        "category_label": CATEGORY_LABELS.get(category, allocation.get("category_label")) if category else allocation.get("category_label"),
        "account_code": allocation.get("account_code"), "account_name": allocation.get("account_name"),
        "tax_code": allocation.get("tax_code"), "source": "human_confirmed_review",
    }
