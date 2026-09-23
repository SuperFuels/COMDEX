from __future__ import annotations

import pytest

from backend.modules.aion_fabric.household import HouseholdIdentityRegistry
from backend.modules.aion_fabric.saved_followthrough import SavedItemFollowThrough
from backend.modules.aion_fabric.services import ServiceExecutionHub


class _Researcher:
    def search(self, query, *, mode):
        assert mode == "general"
        assert "Extendable ladder" in query
        return {
            "answer": "Compare platform stability and manufacturer load ratings.",
            "provider": "aion_native_public_evidence",
            "display_label": "AION + live public evidence",
            "items": [
                {"title": "Safety guide", "reason": "Primary guidance", "detail": "Check EN 131", "url": "https://example.org/safety"},
                {"title": "Unsafe", "reason": "Rejected URL", "detail": "", "url": "http://example.org/not-https"},
            ],
        }


def _item(persona_id: str, category: str = "product"):
    return {
        "save_id": "save_123",
        "persona_id": persona_id,
        "status": "saved",
        "category": category,
        "title": "Extendable ladder" if category == "product" else "Granada",
        "detail": "Seen on television",
        "item_hash": "a" * 64,
    }


def _services(tmp_path):
    household = HouseholdIdentityRegistry(tmp_path)
    persona = household.ensure_local_persona(mother_id="mother_a")
    return persona, ServiceExecutionHub(tmp_path, household=household)


def test_saved_item_research_is_private_and_has_no_external_effect(tmp_path):
    persona, _hub = _services(tmp_path)
    service = SavedItemFollowThrough(tmp_path)
    result = service.research(item=_item(persona["persona_id"]), persona_id=persona["persona_id"], researcher=_Researcher())

    assert result["status"] == "research_complete"
    assert result["external_effect"] is False
    assert result["private_approval_created"] is False
    assert result["items"][0]["url"].startswith("https://")
    assert result["items"][1]["url"] == ""


def test_other_persona_cannot_continue_saved_item(tmp_path):
    persona, hub = _services(tmp_path)
    with pytest.raises(PermissionError):
        SavedItemFollowThrough(tmp_path).prepare_action(
            item=_item(persona["persona_id"]),
            persona_id="persona_other",
            action="shopping",
            service_hub=hub,
        )


def test_shopping_conversion_creates_new_approval_without_purchase(tmp_path):
    persona, hub = _services(tmp_path)
    result = SavedItemFollowThrough(tmp_path).prepare_action(
        item=_item(persona["persona_id"]),
        persona_id=persona["persona_id"],
        action="shopping",
        service_hub=hub,
    )

    proposal = result["service_proposal"]
    assert proposal["status"] == "awaiting_private_approval"
    assert proposal["external_effect"] is False
    assert proposal["parameters"]["purchase"] is False
    assert result["private_approval_created"] is True


def test_local_task_and_learning_drafts_need_no_external_service(tmp_path):
    persona, hub = _services(tmp_path)
    service = SavedItemFollowThrough(tmp_path)
    for action in ("task", "learning", "shortlist"):
        result = service.prepare_action(
            item=_item(persona["persona_id"]),
            persona_id=persona["persona_id"],
            action=action,
            service_hub=hub,
        )
        assert result["status"] == "local_draft_ready"
        assert result["service_proposal"] is None
        assert result["external_effect"] is False


def test_trip_requires_private_date_then_separate_approval(tmp_path):
    persona, hub = _services(tmp_path)
    service = SavedItemFollowThrough(tmp_path)
    result = service.prepare_action(
        item=_item(persona["persona_id"], category="destination"),
        persona_id=persona["persona_id"],
        action="trip",
        service_hub=hub,
    )
    proposal = result["service_proposal"]
    assert proposal["status"] == "needs_details"
    assert proposal["missing_fields"] == ["date"]

    proposal = hub.update_details(
        proposal["proposal_id"], persona_id=persona["persona_id"], details={"date": "2026-10-02T09:00"}
    )
    refreshed = service.refresh_proposal(proposal, persona_id=persona["persona_id"])
    assert refreshed["service_proposal"]["status"] == "awaiting_private_approval"

    proposal = hub.decide(proposal["proposal_id"], persona_id=persona["persona_id"], approved=True)
    refreshed = service.refresh_proposal(proposal, persona_id=persona["persona_id"])
    assert refreshed["service_proposal"]["status"] == "approved_pending_adapter"
    assert refreshed["service_proposal"]["external_effect"] is False


def test_snapshot_is_filtered_to_private_persona(tmp_path):
    persona, hub = _services(tmp_path)
    service = SavedItemFollowThrough(tmp_path)
    service.prepare_action(item=_item(persona["persona_id"]), persona_id=persona["persona_id"], action="task", service_hub=hub)

    assert service.snapshot(persona_id=persona["persona_id"])["count"] == 1
    assert service.snapshot(persona_id="persona_other")["count"] == 0
