# backend/tests/test_aion_equities_trade_execution_guardrails.py
from __future__ import annotations

from backend.modules.aion_equities.trade_execution_guardrails import TradeExecutionGuardrails


def test_trade_execution_guardrails_passes_valid_instruction():
    guard = TradeExecutionGuardrails(max_size_percent=35.0, allow_leverage=False, require_human_approval=True)

    execution_instruction_payload = {
        "execution_instruction_id": "execution_instruction/company/ULVR.L/proposal/ULVR.L/2026-Q4",
        "execution_instruction": {
            "approve_trade": True,
            "trade_type": "fundamental_long",
            "size_percent": 20,
            "max_capital_allowed": 20000,
            "required_human_approval": True,
            "stop_style": "thesis_based",
            "expires_at": "2099-01-01T00:00:00Z",
        },
    }

    out = guard.validate_instruction(
        execution_instruction_payload=execution_instruction_payload,
        business_status={"total_capital": 100000, "free_cash": 50000},
        as_of="2026-03-01T00:00:00Z",
    )
    assert out["status"] == "pass"
    assert out["failures"] == []


def test_trade_execution_guardrails_fails_on_leverage_and_size():
    guard = TradeExecutionGuardrails(max_size_percent=10.0, allow_leverage=False, require_human_approval=True)

    execution_instruction_payload = {
        "execution_instruction_id": "execution_instruction/company/X/proposal/X",
        "execution_instruction": {
            "approve_trade": True,
            "trade_type": "fundamental_long",
            "size_percent": 50,
            "use_leverage": True,
            "required_human_approval": True,
            "expires_at": "2099-01-01T00:00:00Z",
        },
    }

    out = guard.validate_instruction(
        execution_instruction_payload=execution_instruction_payload,
        business_status={"total_capital": 100000, "free_cash": 50000},
        as_of="2026-03-01T00:00:00Z",
    )

    assert out["status"] == "fail"
    assert "leverage_not_allowed" in out["failures"]
    assert "size_exceeds_guardrail_cap" in out["failures"]


def test_trade_execution_guardrails_fails_on_expiry():
    guard = TradeExecutionGuardrails(max_size_percent=35.0, allow_leverage=False, require_human_approval=True)

    execution_instruction_payload = {
        "execution_instruction_id": "execution_instruction/company/X/proposal/X",
        "execution_instruction": {
            "approve_trade": True,
            "trade_type": "catalyst_sprint",
            "size_percent": 5,
            "required_human_approval": True,
            "expires_at": "2026-02-01T00:00:00Z",
        },
    }

    out = guard.validate_instruction(
        execution_instruction_payload=execution_instruction_payload,
        business_status={},
        as_of="2026-03-01T00:00:00Z",
    )
    assert out["status"] == "fail"
    assert "instruction_expired" in out["failures"]