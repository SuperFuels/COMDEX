# backend/tests/test_aion_equities_execution_instruction_store.py
from __future__ import annotations

from backend.modules.aion_equities.execution_instruction_store import ExecutionInstructionStore


def test_execution_instruction_store_can_save_and_load(tmp_path):
    store = ExecutionInstructionStore(tmp_path)

    payload = store.save_execution_instruction(
        review_id="review/1",
        company_ref="company/ULVR.L",
        proposal_id="proposal/ULVR.L/2026-Q4",
        thesis_ref="thesis/ULVR.L/long/medium_term",
        execution_instruction={
            "approve_trade": True,
            "trade_type": "fundamental_long",
            "size_percent": 20,
            "max_capital_allowed": 20000,
            "entry_method": "tranche_plan",
            "required_human_approval": True,
            "stop_style": "thesis_based",
            "expires_at": "2099-01-01T00:00:00Z",
        },
        generated_by="pytest",
    )

    assert payload["approval_state"] == "pending_human_approval"
    assert payload["instruction_status"] == "pending_guardrail_review"
    assert payload["execution_instruction"]["approve_trade"] is True

    loaded = store.load_execution_instruction(payload["execution_instruction_id"])
    assert loaded["execution_instruction_id"] == payload["execution_instruction_id"]
    assert loaded["execution_instruction"]["trade_type"] == "fundamental_long"


def test_execution_instruction_store_lists_ids(tmp_path):
    store = ExecutionInstructionStore(tmp_path)

    a = store.save_execution_instruction(
        review_id="review/a",
        company_ref="company/A",
        proposal_id="proposal/A",
        execution_instruction={"approve_trade": False, "size_percent": 1, "required_human_approval": True},
        generated_by="pytest",
    )
    b = store.save_execution_instruction(
        review_id="review/b",
        company_ref="company/B",
        proposal_id="proposal/B",
        execution_instruction={"approve_trade": True, "size_percent": 2, "required_human_approval": True},
        generated_by="pytest",
    )

    ids = store.list_execution_instruction_ids()
    assert a["execution_instruction_id"] in ids
    assert b["execution_instruction_id"] in ids