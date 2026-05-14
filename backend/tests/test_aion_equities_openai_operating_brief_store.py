# backend/tests/test_aion_equities_openai_operating_brief_store.py
from __future__ import annotations

from backend.modules.aion_equities.openai_operating_brief_store import OpenAIOperatingBriefStore


def test_openai_operating_brief_store_can_save_and_load(tmp_path):
    store = OpenAIOperatingBriefStore(tmp_path)

    payload = store.save_operating_brief(
        brief_id="briefs/aion_equities_operating_brief_v2",
        version="v2",
        title="AION Equities Operating Brief",
        summary="Operating constraints + capital model + OpenAI role.",
        sections=[
            {"id": "scope", "title": "Scope", "body": "Document-in / document-out. No chat parsing."},
            {"id": "constraints", "title": "Constraints", "body": "No leverage. Human approval required."},
        ],
        generated_by="pytest",
        set_active=True,
    )

    assert payload["brief_id"] == "briefs/aion_equities_operating_brief_v2"
    assert payload["version"] == "v2"
    assert payload["status"] == "active"
    assert len(payload["sections"]) == 2

    loaded = store.load_operating_brief("briefs/aion_equities_operating_brief_v2")
    assert loaded["brief_id"] == payload["brief_id"]
    assert loaded["version"] == "v2"
    assert loaded["title"] == "AION Equities Operating Brief"

    active = store.load_active_brief()
    assert active["brief_id"] == payload["brief_id"]
    assert active["version"] == "v2"


def test_openai_operating_brief_store_can_switch_active_brief(tmp_path):
    store = OpenAIOperatingBriefStore(tmp_path)

    store.save_operating_brief(
        brief_id="briefs/brief_a",
        version="v1",
        title="Brief A",
        summary="A",
        sections=[{"id": "a", "title": "A", "body": "A"}],
        generated_by="pytest",
        set_active=True,
    )
    assert store.load_active_brief()["brief_id"] == "briefs/brief_a"

    store.save_operating_brief(
        brief_id="briefs/brief_b",
        version="v2",
        title="Brief B",
        summary="B",
        sections=[{"id": "b", "title": "B", "body": "B"}],
        generated_by="pytest",
        set_active=True,
    )
    assert store.load_active_brief()["brief_id"] == "briefs/brief_b"

    store.set_active_brief("briefs/brief_a")
    assert store.load_active_brief()["brief_id"] == "briefs/brief_a"


def test_openai_operating_brief_store_lists_ids(tmp_path):
    store = OpenAIOperatingBriefStore(tmp_path)

    store.save_operating_brief(
        brief_id="briefs/one",
        version="v1",
        title="One",
        summary="One",
        sections=[{"id": "one", "title": "One", "body": "One"}],
        generated_by="pytest",
        set_active=False,
    )
    store.save_operating_brief(
        brief_id="briefs/two",
        version="v1",
        title="Two",
        summary="Two",
        sections=[{"id": "two", "title": "Two", "body": "Two"}],
        generated_by="pytest",
        set_active=False,
    )

    ids = store.list_brief_ids()
    assert "briefs/one" in ids
    assert "briefs/two" in ids