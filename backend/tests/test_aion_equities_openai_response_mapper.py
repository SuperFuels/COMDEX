from __future__ import annotations

import pytest

from backend.modules.aion_equities.openai_response_mapper import (
    map_openai_trade_review_response,
)


def test_openai_response_mapper_splits_structured_response():
    response = {
        "decision_notes": {
            "summary": "Approve with staggered entry.",
            "risks": ["fx volatility", "weak guidance"],
            "what_to_watch_next": ["consensus revision", "margin trend"],
        },
        "execution_instruction": {
            "approve_trade": True,
            "trade_type": "fundamental_long",
            "entry_method": "tranche_plan",
            "size_percent": 18,
            "required_human_approval": True,
            "expires_at": "2099-01-01T00:00:00Z",
        },
    }

    out = map_openai_trade_review_response(
        response,
        company_ref="company/ULVR.L",
        proposal_id="proposal/ULVR.L/2026-Q4",
        review_id="review/ULVR.L/2026-Q4",
        thesis_ref="thesis/ULVR.L/long/medium_term",
        generated_by="pytest",
    )

    notes_payload = out["decision_notes_payload"]
    instruction_payload = out["execution_instruction_payload"]

    assert notes_payload["review_id"] == "review/ULVR.L/2026-Q4"
    assert notes_payload["company_ref"] == "company/ULVR.L"
    assert notes_payload["proposal_id"] == "proposal/ULVR.L/2026-Q4"
    assert notes_payload["decision_notes"]["summary"] == "Approve with staggered entry."
    assert notes_payload["thesis_ref"] == "thesis/ULVR.L/long/medium_term"

    assert instruction_payload["review_id"] == "review/ULVR.L/2026-Q4"
    assert instruction_payload["company_ref"] == "company/ULVR.L"
    assert instruction_payload["proposal_id"] == "proposal/ULVR.L/2026-Q4"
    assert instruction_payload["execution_instruction"]["approve_trade"] is True
    assert instruction_payload["payload_patch"]["approval_state"] == "pending_human_approval"
    assert instruction_payload["payload_patch"]["instruction_status"] == "pending_guardrail_review"
    assert instruction_payload["payload_patch"]["thesis_ref"] == "thesis/ULVR.L/long/medium_term"


def test_openai_response_mapper_defaults_review_id_when_missing():
    response = {
        "decision_notes": {"summary": "Reject for now."},
        "execution_instruction": {
            "approve_trade": False,
            "trade_type": "catalyst_sprint",
            "required_human_approval": False,
        },
    }

    out = map_openai_trade_review_response(
        response,
        company_ref="company/PAGE.L",
        proposal_id="proposal/PAGE.L/2026-Q4",
        generated_by="pytest",
    )

    assert out["decision_notes_payload"]["review_id"] == "review/proposal/PAGE.L/2026-Q4"
    assert out["execution_instruction_payload"]["review_id"] == "review/proposal/PAGE.L/2026-Q4"
    assert (
        out["execution_instruction_payload"]["payload_patch"]["approval_state"]
        == "approved_no_human_required"
    )


def test_openai_response_mapper_rejects_missing_sections():
    with pytest.raises(ValueError, match="missing decision_notes"):
        map_openai_trade_review_response(
            {"execution_instruction": {"approve_trade": True}},
            company_ref="company/X",
            proposal_id="proposal/X",
        )

    with pytest.raises(ValueError, match="missing execution_instruction"):
        map_openai_trade_review_response(
            {"decision_notes": {"summary": "x"}},
            company_ref="company/X",
            proposal_id="proposal/X",
        )