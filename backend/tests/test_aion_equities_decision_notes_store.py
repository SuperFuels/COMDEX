# backend/tests/test_aion_equities_decision_notes_store.py
from __future__ import annotations

from backend.modules.aion_equities.decision_notes_store import DecisionNotesStore


def test_decision_notes_store_can_save_and_load(tmp_path):
    store = DecisionNotesStore(tmp_path)

    payload = store.save_decision_notes(
        review_id="review/1",
        company_ref="company/ULVR.L",
        proposal_id="proposal/ULVR.L/2026-Q4",
        thesis_ref="thesis/ULVR.L/long/medium_term",
        decision_notes={
            "summary": "Approve with tranche plan.",
            "risks": ["fx", "guidance"],
            "invalidation": ["material margin collapse"],
        },
        generated_by="pytest",
    )

    assert payload["review_id"] == "review/1"
    assert payload["company_ref"] == "company/ULVR.L"
    assert payload["proposal_id"] == "proposal/ULVR.L/2026-Q4"
    assert payload["decision_notes"]["summary"] == "Approve with tranche plan."

    loaded = store.load_decision_notes(payload["decision_notes_id"])
    assert loaded["decision_notes_id"] == payload["decision_notes_id"]
    assert loaded["decision_notes"]["summary"] == "Approve with tranche plan."


def test_decision_notes_store_lists_ids(tmp_path):
    store = DecisionNotesStore(tmp_path)

    a = store.save_decision_notes(
        review_id="review/a",
        company_ref="company/A",
        proposal_id="proposal/A",
        decision_notes={"summary": "A"},
        generated_by="pytest",
    )
    b = store.save_decision_notes(
        review_id="review/b",
        company_ref="company/B",
        proposal_id="proposal/B",
        decision_notes={"summary": "B"},
        generated_by="pytest",
    )

    ids = store.list_decision_notes_ids()
    assert a["decision_notes_id"] in ids
    assert b["decision_notes_id"] in ids