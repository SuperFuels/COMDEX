from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.modules.aion_fabric.private_saves import PrivateProgrammeSaves
from backend.modules.aion_fabric.voice import parse_voice_intent


def _prepare(service: PrivateProgrammeSaves, category: str = "product"):
    return service.prepare(
        category=category,
        request=f"Pilot save this {category}",
        live_context={
            "context_hash": "a" * 64,
            "recent_transcripts": ["This extendable ladder is designed for uneven ground"],
        },
        screen_understanding={
            "products": {
                "detected": True,
                "candidate_text": "Professional extendable ladder",
                "prices": ["€149.00"],
                "confidence": 0.91,
            }
        },
        provider_metadata={"provider": "browser", "title": "Ladder demonstration"},
    )


def test_shared_tv_prepares_but_does_not_choose_private_identity(tmp_path):
    item = _prepare(PrivateProgrammeSaves(tmp_path))

    assert item["status"] == "awaiting_private_claim"
    assert item["persona_id"] is None
    assert item["title"] == "Professional extendable ladder"
    assert item["privacy"]["shared_tv_selected_persona"] is False
    assert item["privacy"]["purchase_executed"] is False
    assert item["evidence_hash"]


def test_private_phone_claim_binds_only_the_explicit_persona(tmp_path):
    service = PrivateProgrammeSaves(tmp_path)
    prepared = _prepare(service)
    saved = service.claim(prepared["save_id"], persona_id="persona_a")

    assert saved["status"] == "saved"
    assert saved["persona_id"] == "persona_a"
    assert service.snapshot(persona_id="persona_a")["saved_count"] == 1
    assert service.snapshot(persona_id="persona_b")["saved_count"] == 0
    assert service.snapshot(persona_id="persona_b")["pending"] is None


def test_other_persona_cannot_delete_private_save(tmp_path):
    service = PrivateProgrammeSaves(tmp_path)
    saved = service.claim(_prepare(service)["save_id"], persona_id="persona_a")

    with pytest.raises(PermissionError):
        service.delete(saved["save_id"], persona_id="persona_b")

    assert service.delete(saved["save_id"], persona_id="persona_a")["status"] == "deleted"


def test_expired_shared_save_cannot_be_claimed(tmp_path):
    service = PrivateProgrammeSaves(tmp_path)
    item = _prepare(service)
    item["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    service._write(service.pending_path, item)

    with pytest.raises(PermissionError):
        service.claim(item["save_id"], persona_id="persona_a")


def test_private_save_voice_intents_are_distinct_from_moments():
    product = parse_voice_intent("Pilot save this product")
    place = parse_voice_intent("Pilot remember this place for later")
    idea = parse_voice_intent("Pilot add this idea to my phone")

    assert product and product.action == "private_save_prepare" and product.arguments["category"] == "product"
    assert place and place.action == "private_save_prepare" and place.arguments["category"] == "destination"
    assert idea and idea.action == "private_save_prepare" and idea.arguments["category"] == "idea"
