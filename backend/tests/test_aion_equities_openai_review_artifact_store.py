from __future__ import annotations

from backend.modules.aion_equities.openai_review_artifact_store import OpenAIReviewArtifactStore


def test_openai_review_artifact_store_can_save_and_load(tmp_path):
    store = OpenAIReviewArtifactStore(tmp_path)

    payload = store.save_review_artifact(
        review_id="review/ULVR.L/2026-Q4",
        company_ref="company/ULVR.L",
        proposal_id="proposal/ULVR.L/2026-Q4",
        thesis_ref="thesis/ULVR.L/long/medium_term",
        context_packet={"proposal_id": "proposal/ULVR.L/2026-Q4"},
        raw_response={"decision_notes": {"summary": "Approve"}},
        decision_notes_payload={"decision_notes": {"summary": "Approve"}},
        execution_instruction_payload={
            "execution_instruction": {
                "approve_trade": True,
                "trade_type": "fundamental_long",
            }
        },
        generated_by="pytest",
    )

    assert payload["review_id"] == "review/ULVR.L/2026-Q4"
    assert payload["company_ref"] == "company/ULVR.L"
    assert payload["proposal_id"] == "proposal/ULVR.L/2026-Q4"
    assert payload["decision_notes_payload"]["decision_notes"]["summary"] == "Approve"

    loaded = store.load_review_artifact(payload["review_artifact_id"])
    assert loaded["review_artifact_id"] == payload["review_artifact_id"]
    assert loaded["execution_instruction_payload"]["execution_instruction"]["trade_type"] == "fundamental_long"


def test_openai_review_artifact_store_lists_ids(tmp_path):
    store = OpenAIReviewArtifactStore(tmp_path)

    a = store.save_review_artifact(
        review_id="review/a",
        company_ref="company/A",
        proposal_id="proposal/A",
        context_packet={},
        raw_response={},
        decision_notes_payload={"decision_notes": {"summary": "A"}},
        execution_instruction_payload={"execution_instruction": {"approve_trade": False}},
        generated_by="pytest",
    )
    b = store.save_review_artifact(
        review_id="review/b",
        company_ref="company/B",
        proposal_id="proposal/B",
        context_packet={},
        raw_response={},
        decision_notes_payload={"decision_notes": {"summary": "B"}},
        execution_instruction_payload={"execution_instruction": {"approve_trade": True}},
        generated_by="pytest",
    )

    ids = store.list_review_artifact_ids()
    assert a["review_artifact_id"] in ids
    assert b["review_artifact_id"] in ids