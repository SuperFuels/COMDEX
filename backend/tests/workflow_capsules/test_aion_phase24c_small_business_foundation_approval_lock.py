from __future__ import annotations

import json

from backend.services.aion_mission_mode.small_business_foundation_approval import (
    approve_and_persist_foundation,
    compute_foundation_hash,
    departments_can_start_from_foundation,
    foundation_is_approvable,
    get_missing_required_foundation_fields,
)


FOUNDATION = {
    "business_name": "Home Fixed",
    "industry": "Property maintenance",
    "business_type": "services",
    "service_area": "Almería and Murcia",
    "primary_goal": "get_more_leads",
    "website": "https://homefixed.es",
}


def test_phase24c_foundation_hash_is_deterministic():
    first = compute_foundation_hash(FOUNDATION)
    second = compute_foundation_hash(dict(reversed(list(FOUNDATION.items()))))
    assert first == second
    assert len(first) == 64


def test_phase24c_foundation_requires_core_fields():
    incomplete = dict(FOUNDATION)
    incomplete["business_name"] = ""

    assert foundation_is_approvable(FOUNDATION) is True
    assert foundation_is_approvable(incomplete) is False
    assert get_missing_required_foundation_fields(incomplete) == ["business_name"]


def test_phase24c_approved_foundation_persists_inside_business_container(tmp_path):
    result = approve_and_persist_foundation(
        root=tmp_path,
        business_id="Home Fixed",
        foundation=FOUNDATION,
        approved_by="Kevin Robinson",
    )

    assert result["ok"] is True
    assert result["approved"] is True
    assert "aion_businesses/home-fixed/foundation/approved_foundation.json" in result["foundation_path"]
    assert "aion_businesses/home-fixed/foundation/foundation_receipt.json" in result["receipt_path"]

    payload = json.loads((tmp_path / "aion_businesses/home-fixed/foundation/approved_foundation.json").read_text())
    assert payload["foundation"]["business_name"] == "Home Fixed"
    assert payload["receipt"]["approved"] is True
    assert payload["receipt"]["foundation_hash"] == result["foundation_hash"]


def test_phase24c_rejects_persistence_when_required_fields_missing(tmp_path):
    incomplete = dict(FOUNDATION)
    incomplete["primary_goal"] = ""

    result = approve_and_persist_foundation(
        root=tmp_path,
        business_id="Home Fixed",
        foundation=incomplete,
    )

    assert result["ok"] is False
    assert result["approved"] is False
    assert result["missing_required_fields"] == ["primary_goal"]
    assert not (tmp_path / "aion_businesses/home-fixed/foundation/approved_foundation.json").exists()


def test_phase24c_departments_cannot_start_without_approved_matching_receipt():
    foundation_hash = compute_foundation_hash(FOUNDATION)

    assert departments_can_start_from_foundation({}) is False
    assert departments_can_start_from_foundation({"foundation": FOUNDATION}) is False
    assert departments_can_start_from_foundation({
        "foundation": FOUNDATION,
        "receipt": {"approved": True, "foundation_hash": "bad"},
    }) is False
    assert departments_can_start_from_foundation({
        "foundation": FOUNDATION,
        "receipt": {"approved": True, "foundation_hash": foundation_hash},
    }) is True
