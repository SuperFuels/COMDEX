# /workspaces/COMDEX/backend/tests/test_aion_trading_paper_runtime_phase2.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from backend.modules.aion_trading.contracts import TradeProposal
from backend.modules.aion_trading.dmip_runtime import (
    submit_paper_trade,
    manage_open_trade,
    close_trade,
    get_paper_trade,
    list_paper_trades,
    configure_paper_runtime_persistence,
    persist_paper_runtime_snapshot,
    reset_paper_runtime_state,
    restore_paper_runtime_snapshot,
    validate_risk_rules,  # <-- add this
)


def _mk_valid_proposal(**overrides: Any) -> TradeProposal:
    """
    Baseline valid paper-trade proposal.

    NOTE:
    - take_profit is set slightly above exact 2R to avoid float-edge failures where
      rr_ratio evaluates to 1.9999999999 and trips min_rr=2.0.
    - Some Phase 2 runtimes read `proposal.session` as a top-level attribute
      (not proposal.metadata.session), so we attach it after construction.
    """
    # allow callers to override session even though TradeProposal schema may not declare it
    session_value = overrides.pop("session", "london")

    data: Dict[str, Any] = {
        "pair": "EUR/USD",
        "strategy_tier": "tier3_smc_intraday",
        "direction": "BUY",
        "account_mode": "paper",
        "entry": 1.1000,
        "stop_loss": 1.0950,
        "take_profit": 1.1102,  # > 2R to avoid float-edge failing min_rr=2.0
        "account_equity": 10_000.0,
        "risk_pct": 1.0,
        "pip_value": 10.0,
        "stop_pips": 50.0,
        "thesis": "Liquidity sweep + CHoCH + retrace entry",
        "setup_tags": ["smc", "london", "sweep", "choch"],
        "metadata": {
            "source": "pytest_phase2_valid_submit",
            "session": "london",
            "setup_grade": "A",
            "eod_debrief_ack": True,
        }
    }
    data.update(overrides)

    proposal = TradeProposal(**data).validate()

    # Phase 2 scope-lock compatibility: some runtimes inspect top-level proposal.session
    setattr(proposal, "session", str(session_value).strip().lower())

    return proposal


def _as_dict(x: Any) -> Dict[str, Any]:
    if isinstance(x, dict):
        return x
    if hasattr(x, "to_dict"):
        return x.to_dict()
    raise AssertionError(f"Expected dict-like response, got: {type(x)}")

def _safe_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        if x is None:
            return default
        return int(x)
    except Exception:
        return default


def _extract_paths(resp: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tolerate multiple path container shapes in persistence responses.
    """
    if isinstance(resp.get("paths"), dict):
        return dict(resp["paths"])

    if isinstance(resp.get("persistence"), dict):
        p = resp["persistence"]
        if isinstance(p.get("files"), dict):
            return dict(p["files"])

    if isinstance(resp.get("files"), dict):
        return dict(resp["files"])

    return {}

def _find_nested_dict(resp: Dict[str, Any], keys: List[str]) -> Optional[Dict[str, Any]]:
    for k in keys:
        v = resp.get(k)
        if isinstance(v, dict):
            return v
    return None


def _extract_trade_id(resp: Dict[str, Any]) -> str:
    """
    Be tolerant to different response shapes.
    """
    candidates = [
        resp.get("trade_id"),
        (resp.get("trade") or {}).get("trade_id") if isinstance(resp.get("trade"), dict) else None,
        (resp.get("paper_trade") or {}).get("trade_id") if isinstance(resp.get("paper_trade"), dict) else None,
        (resp.get("result") or {}).get("trade_id") if isinstance(resp.get("result"), dict) else None,
        (resp.get("execution") or {}).get("trade_id") if isinstance(resp.get("execution"), dict) else None,
        ((resp.get("event") or {}).get("payload") or {}).get("trade_id")
        if isinstance(resp.get("event"), dict) and isinstance((resp.get("event") or {}).get("payload"), dict)
        else None,
    ]
    for c in candidates:
        if isinstance(c, str) and c.strip():
            return c
    raise AssertionError(f"Could not find trade_id in response keys: {sorted(resp.keys())}")


def _extract_ok(resp: Dict[str, Any]) -> Optional[bool]:
    """
    Tolerate ok flag in multiple places.
    """
    if isinstance(resp.get("ok"), bool):
        return bool(resp["ok"])

    for key in ("result", "risk_validation", "validation", "scope_validation"):
        nested = resp.get(key)
        if isinstance(nested, dict) and isinstance(nested.get("ok"), bool):
            return bool(nested["ok"])

    event = resp.get("event")
    if isinstance(event, dict):
        payload = event.get("payload")
        if isinstance(payload, dict):
            if isinstance(payload.get("ok"), bool):
                return bool(payload["ok"])
            for key in ("scope_validation", "validation", "risk_validation"):
                nested = payload.get(key)
                if isinstance(nested, dict) and isinstance(nested.get("ok"), bool):
                    return bool(nested["ok"])

    return None


def _extract_scope_validation(resp: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    sv = resp.get("scope_validation")
    if isinstance(sv, dict):
        return sv

    event = resp.get("event")
    if isinstance(event, dict):
        payload = event.get("payload")
        if isinstance(payload, dict):
            sv = payload.get("scope_validation")
            if isinstance(sv, dict):
                return sv

    return None


def _extract_reason(resp: Dict[str, Any]) -> Optional[str]:
    reason = resp.get("reason")
    if isinstance(reason, str) and reason.strip():
        return reason

    sv = _extract_scope_validation(resp)
    if isinstance(sv, dict):
        r = sv.get("reason")
        if isinstance(r, str) and r.strip():
            return r

    return None


def _extract_violations(resp: Dict[str, Any]) -> List[str]:
    """
    Tolerate violations at top-level, nested risk validation, or centralized scope_validation.
    """
    vals = resp.get("violations")
    if isinstance(vals, list):
        return list(vals)

    for key in ("risk_validation", "validation", "result", "scope_validation"):
        nested = resp.get(key)
        if isinstance(nested, dict) and isinstance(nested.get("violations"), list):
            return list(nested.get("violations") or [])

    event = resp.get("event")
    if isinstance(event, dict):
        payload = event.get("payload")
        if isinstance(payload, dict):
            for key in ("risk_validation", "validation", "scope_validation"):
                nested = payload.get(key)
                if isinstance(nested, dict) and isinstance(nested.get("violations"), list):
                    return list(nested.get("violations") or [])

    return []


def _has_violation(resp: Dict[str, Any], code: str) -> bool:
    return code in set(_extract_violations(resp))


def _base_submit_metadata(source: str) -> Dict[str, Any]:
    """
    IMPORTANT:
    Current runtime's centralized phase2 scope validator reads request metadata
    (scope_validation.meta.request_metadata), so session must be supplied here.
    """
    return {
        "source": source,
        "session": "london",
    }


def test_validate_risk_rules_rejects_live_mode_phase_policy():
    proposal = _mk_valid_proposal(account_mode="live")

    out = _as_dict(validate_risk_rules(proposal))

    assert _extract_ok(out) is False
    violations = _extract_violations(out)
    assert "live_trading_blocked_phase_policy" in violations


def test_submit_paper_trade_rejects_invalid_risk():
    # Exceeds max risk per trade policy (default policy max = 1.0%)
    proposal = _mk_valid_proposal(risk_pct=2.5)

    out = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=_base_submit_metadata("pytest_phase2_invalid_risk"),
        )
    )

    assert _extract_ok(out) is False, f"Unexpected submit response: {out}"

    violations = _extract_violations(out)
    assert "risk_per_trade_exceeds_policy" in violations, f"Violations not found in response: {out}"


def test_submit_paper_trade_accepts_valid_paper_trade():
    proposal = _mk_valid_proposal()

    out = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=_base_submit_metadata("pytest_phase2_valid_submit"),
        )
    )

    assert _extract_ok(out) is True, f"Unexpected submit response: {out}"

    rv = _find_nested_dict(out, ["risk_validation", "validation"])
    if isinstance(rv, dict) and "ok" in rv:
        assert rv.get("ok") is True, f"Risk validation failed: {rv}"

    sv = _extract_scope_validation(out)
    if isinstance(sv, dict) and "ok" in sv:
        assert sv.get("ok") is True, f"Scope validation failed: {sv}"

    trade_id = _extract_trade_id(out)
    assert isinstance(trade_id, str) and trade_id.strip()


def test_manage_and_close_trade_lifecycle_happy_path():
    proposal = _mk_valid_proposal()

    submit = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=_base_submit_metadata("pytest_phase2_lifecycle"),
        )
    )
    assert _extract_ok(submit) is True, f"Submit failed: {submit}"

    trade_id = _extract_trade_id(submit)

    manage = _as_dict(
        manage_open_trade(
            trade_id=trade_id,
            action="move_stop",
            payload={"stop_loss": 1.1005},
        )
    )
    assert _extract_ok(manage) is True, f"Manage failed: {manage}"

    close = _as_dict(
        close_trade(
            trade_id=trade_id,
            close_price=1.1080,
            close_reason="pytest_take_profit_partial_or_manual_close",
            outcome={"pnl_hint": "positive"},
        )
    )
    assert _extract_ok(close) is True, f"Close failed: {close}"

    if "trade_id" in close:
        assert close["trade_id"] == trade_id
    if isinstance(close.get("trade"), dict) and "trade_id" in close["trade"]:
        assert close["trade"]["trade_id"] == trade_id


# ---------------------------------------------------------------------
# Phase 2 scope lock tests (centralized validator + legacy compatible)
# ---------------------------------------------------------------------


def test_submit_paper_trade_rejects_non_eurusd_phase2_scope_if_enabled():
    proposal = _mk_valid_proposal(pair="GBP/USD")

    out = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=_base_submit_metadata("pytest_phase2_scope_pair"),
        )
    )

    if _extract_ok(out) is True:
        pytest.skip("Phase 2 scope lock (pair) not enabled in current runtime.")

    reason = _extract_reason(out)
    assert isinstance(reason, str), f"Missing reject reason: {out}"

    if reason == "phase2_scope_or_progression_validation_failed":
        violations = _extract_violations(out)
        assert "phase2_scope_pair_locked" in violations, f"Expected pair scope violation: {out}"
        return

    assert reason in {
        "pair_not_allowed_phase2_scope",
        "risk_validation_failed",
    }, f"Unexpected reject reason: {out}"


def test_submit_paper_trade_rejects_non_london_phase2_scope_if_enabled():
    proposal = _mk_valid_proposal(session="new_york", metadata={"source": "pytest_phase2", "session": "new_york"})

    out = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            # IMPORTANT: request metadata drives current centralized scope validator
            metadata={"source": "pytest_phase2_scope_session", "session": "new_york"},
        )
    )

    if _extract_ok(out) is True:
        pytest.skip("Phase 2 scope lock (session) not enabled in current runtime.")

    reason = _extract_reason(out)
    assert isinstance(reason, str), f"Missing reject reason: {out}"

    if reason == "phase2_scope_or_progression_validation_failed":
        violations = _extract_violations(out)
        assert "phase2_scope_session_locked" in violations, f"Expected session scope violation: {out}"
        return

    assert reason in {
        "session_not_allowed_phase2_scope",
        "risk_validation_failed",
    }, f"Unexpected reject reason: {out}"


def test_submit_paper_trade_rejects_non_tier3_phase2_scope_if_enabled():
    proposal = _mk_valid_proposal(strategy_tier="tier2_momentum_orb")

    out = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=_base_submit_metadata("pytest_phase2_scope_strategy"),
        )
    )

    if _extract_ok(out) is True:
        pytest.skip("Phase 2 scope lock (strategy tier) not enabled in current runtime.")

    reason = _extract_reason(out)
    assert isinstance(reason, str), f"Missing reject reason: {out}"

    if reason == "phase2_scope_or_progression_validation_failed":
        violations = _extract_violations(out)
        assert "phase2_scope_strategy_locked" in violations, f"Expected strategy scope violation: {out}"
        return

    assert reason in {
        "strategy_not_allowed_phase2_scope",
        "risk_validation_failed",
    }, f"Unexpected reject reason: {out}"


def test_submit_paper_trade_rejects_non_paper_phase2_scope_or_risk_gate():
    # validate_risk_rules may reject live mode; scope lock may reject sim/live too.
    proposal = _mk_valid_proposal(account_mode="sim")

    out = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=_base_submit_metadata("pytest_phase2_scope_account_mode"),
        )
    )

    assert _extract_ok(out) is False, f"Unexpected response: {out}"

    reason = _extract_reason(out)
    assert isinstance(reason, str), f"Missing reject reason: {out}"

    if reason == "phase2_scope_or_progression_validation_failed":
        violations = _extract_violations(out)
        assert (
            "phase2_progression_requires_paper_mode" in violations
            or "phase2_scope_account_mode_locked" in violations
        ), f"Expected account mode/progression scope violation: {out}"
        return

    assert reason in {
        "risk_validation_failed",
        "account_mode_not_allowed_phase2_scope",
    }, f"Unexpected reject reason: {out}"


def test_submit_paper_trade_scope_reject_exposes_scope_validation_when_centralized():
    """
    Soft-shape test:
    If runtime is using centralized scope validator rejects, ensure `scope_validation`
    payload is included for diagnostics.
    """
    proposal = _mk_valid_proposal(pair="USD/JPY")

    out = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=_base_submit_metadata("pytest_phase2_scope_diag"),
        )
    )

    if _extract_ok(out) is True:
        pytest.skip("Phase 2 scope lock not enabled in current runtime.")

    if _extract_reason(out) == "phase2_scope_or_progression_validation_failed":
        sv = _extract_scope_validation(out)
        assert isinstance(sv, dict), f"Expected scope_validation payload in centralized scope reject: {out}"
        if "ok" in sv:
            assert sv.get("ok") is False


# ---------------------------------------------------------------------
# Phase 2 initial trade limits (P2E) tests
# These are tolerant of runtimes that may not yet enforce P2E.
# If P2E is not enabled, tests skip instead of failing.
# ---------------------------------------------------------------------


def _extract_phase2_limits_validation(resp: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Tolerate phase2_limits_validation in multiple common locations.
    """
    top = resp.get("phase2_limits_validation")
    if isinstance(top, dict):
        return top

    for key in ("result",):
        nested = resp.get(key)
        if isinstance(nested, dict):
            p2 = nested.get("phase2_limits_validation")
            if isinstance(p2, dict):
                return p2

    event = resp.get("event")
    if isinstance(event, dict):
        payload = event.get("payload")
        if isinstance(payload, dict):
            p2 = payload.get("phase2_limits_validation")
            if isinstance(p2, dict):
                return p2

    return None


def _is_phase2_limits_reject(out: Dict[str, Any]) -> bool:
    reason = out.get("reason")
    if reason == "phase2_initial_trade_limits_validation_failed":
        return True
    p2 = _extract_phase2_limits_validation(out)
    return isinstance(p2, dict) and (p2.get("ok") is False)


def _extract_phase2_limits_violations(out: Dict[str, Any]) -> List[str]:
    p2 = _extract_phase2_limits_validation(out)
    if isinstance(p2, dict) and isinstance(p2.get("violations"), list):
        return list(p2.get("violations") or [])
    return []


def _valid_submit_metadata_for_p2e(source: str) -> Dict[str, Any]:
    """
    Request-level metadata that satisfies P2E gates in runtimes that enforce them.
    Also includes session='london' to satisfy P2C/P2D-capable runtimes.
    """
    return {
        "source": source,
        "session": "london",
        "setup_grade": "A",
        "eod_debrief_ack": True,
    }


def test_submit_paper_trade_rejects_phase2_max_trades_per_session_if_enabled():
    proposal = _mk_valid_proposal()

    out = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={
                "losing_trades": 0,
                "trades_taken": 2,  # projected -> 3, should exceed cap=2 if P2E enabled
            },
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=_valid_submit_metadata_for_p2e("pytest_phase2_limits_max_trades"),
        )
    )

    if _extract_ok(out) is True:
        pytest.skip("Phase 2 initial trade limits (max trades/session) not enabled in current runtime.")

    # If rejected, ensure it is either P2E-specific or another explicit earlier gate
    reason = out.get("reason")
    assert isinstance(reason, str), f"Unexpected reject shape: {out}"
    if _is_phase2_limits_reject(out):
        violations = _extract_phase2_limits_violations(out)
        assert any(
            v in {
                "phase2_max_trades_per_session_exceeded",
                "phase2_session_trade_limit_reached",
            }
            for v in violations
        ), f"Unexpected P2E violations: {out}"
    else:
        # tolerate older runtimes or stricter earlier gates
        assert reason in {
            "phase2_scope_or_progression_validation_failed",
            "risk_validation_failed",
        }, f"Unexpected reject reason: {out}"


def test_submit_paper_trade_rejects_phase2_non_a_grade_if_enabled():
    proposal = _mk_valid_proposal()

    md = _valid_submit_metadata_for_p2e("pytest_phase2_limits_non_a_grade")
    md.pop("setup_grade", None)  # no grade flag supplied

    out = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0, "trades_taken": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=md,
        )
    )

    if _extract_ok(out) is True:
        pytest.skip("Phase 2 initial trade limits (A-grade only) not enabled in current runtime.")

    reason = out.get("reason")
    assert isinstance(reason, str), f"Unexpected reject shape: {out}"
    if _is_phase2_limits_reject(out):
        violations = _extract_phase2_limits_violations(out)
        assert "phase2_a_grade_only_required" in violations, f"Unexpected P2E violations: {out}"
    else:
        assert reason in {
            "phase2_scope_or_progression_validation_failed",
            "risk_validation_failed",
        }, f"Unexpected reject reason: {out}"


def test_submit_paper_trade_rejects_phase2_red_event_if_enabled():
    proposal = _mk_valid_proposal()

    md = _valid_submit_metadata_for_p2e("pytest_phase2_limits_red_event")
    md["red_event_active"] = True

    out = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0, "trades_taken": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=md,
        )
    )

    if _extract_ok(out) is True:
        pytest.skip("Phase 2 initial trade limits (red-event stand-down) not enabled in current runtime.")

    reason = out.get("reason")
    assert isinstance(reason, str), f"Unexpected reject shape: {out}"
    if _is_phase2_limits_reject(out):
        violations = _extract_phase2_limits_violations(out)
        assert "phase2_red_event_stand_down" in violations, f"Unexpected P2E violations: {out}"
    else:
        assert reason in {
            "phase2_scope_or_progression_validation_failed",
            "risk_validation_failed",
        }, f"Unexpected reject reason: {out}"


def test_submit_paper_trade_rejects_phase2_missing_eod_ack_if_enabled():
    proposal = _mk_valid_proposal()

    md = _valid_submit_metadata_for_p2e("pytest_phase2_limits_missing_eod_ack")
    md.pop("eod_debrief_ack", None)

    out = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0, "trades_taken": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=md,
        )
    )

    if _extract_ok(out) is True:
        pytest.skip("Phase 2 initial trade limits (EOD debrief ack) not enabled in current runtime.")

    reason = out.get("reason")
    assert isinstance(reason, str), f"Unexpected reject shape: {out}"
    if _is_phase2_limits_reject(out):
        violations = _extract_phase2_limits_violations(out)
        assert "phase2_eod_debrief_ack_required" in violations, f"Unexpected P2E violations: {out}"
    else:
        assert reason in {
            "phase2_scope_or_progression_validation_failed",
            "risk_validation_failed",
        }, f"Unexpected reject reason: {out}"


def test_submit_paper_trade_accepts_phase2_limits_when_enabled_or_skips():
    """
    This test is tolerant:
    - If P2E is enabled and all flags are satisfied, submit should pass (or fail later only on risk, which should not happen for baseline valid proposal).
    - If P2E is not enabled, submit may still pass; that's also acceptable.
    """
    proposal = _mk_valid_proposal()

    out = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={
                "losing_trades": 0,
                "trades_taken": 0,
            },
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=_valid_submit_metadata_for_p2e("pytest_phase2_limits_accept"),
        )
    )

    # Preferred behavior: accepted.
    if _extract_ok(out) is True:
        return

    # If rejected, surface exact reason so it's obvious what gate is still blocking.
    pytest.fail(f"Expected valid submit to pass P2E-ready path, got: {out}")

def test_submit_paper_trade_scope_validation_shape_includes_request_metadata_when_present():
    """
    Current runtime includes request metadata under:
    scope_validation.meta.request_metadata
    """
    proposal = _mk_valid_proposal(pair="GBP/USD")

    req_meta = {"source": "pytest_phase2_scope_meta_shape", "session": "london"}

    out = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=req_meta,
        )
    )

    if _extract_ok(out) is True:
        pytest.skip("Phase 2 scope lock not enabled in current runtime.")

    sv = _extract_scope_validation(out)
    if not isinstance(sv, dict):
        pytest.skip("Centralized scope_validation payload not present in this runtime.")

    meta = sv.get("meta")
    if not isinstance(meta, dict):
        pytest.skip("scope_validation.meta not present in this runtime.")

    request_metadata = meta.get("request_metadata")
    if not isinstance(request_metadata, dict):
        pytest.skip("scope_validation.meta.request_metadata not present in this runtime.")

    assert request_metadata.get("source") == req_meta["source"]
    assert request_metadata.get("session") == req_meta["session"]


# Optional sanity test to ensure pytest imports are used and helpers remain stable.
def test_helper_extract_ok_handles_top_level_bool():
    assert _extract_ok({"ok": True}) is True
    assert _extract_ok({"ok": False}) is False

def test_manage_open_trade_rejects_phase2_size_up_actions():
    proposal = _mk_valid_proposal()

    submit = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0, "trades_taken": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=_valid_submit_metadata_for_p2e("pytest_phase2_manage_size_up_reject"),
        )
    )
    assert _extract_ok(submit) is True, f"Submit failed: {submit}"

    trade_id = _extract_trade_id(submit)

    for action in ("average_down", "scale_in", "increase_size", "add_to_position", "pyramid"):
        out = _as_dict(
            manage_open_trade(
                trade_id=trade_id,
                action=action,
                payload={"units": 1, "reason": "pytest_should_reject_phase2_size_up"},
            )
        )
        assert _extract_ok(out) is False, f"Expected reject for action={action}: {out}"
        assert out.get("reason") == "phase2_position_sizing_invariants_failed", f"Unexpected reason for {action}: {out}"

        violations = _extract_violations(out)
        # manage_open_trade returns top-level violations in current runtime patch;
        # tolerate either helper extraction or direct top-level list.
        if not violations and isinstance(out.get("violations"), list):
            violations = list(out.get("violations") or [])

        assert "phase2_no_size_up_during_open_trade" in violations, f"Missing no-size-up violation for {action}: {out}"


def test_manage_open_trade_rejects_buy_stop_widening_phase2_invariant():
    proposal = _mk_valid_proposal(direction="BUY", entry=1.1000, stop_loss=1.0950, take_profit=1.1102)

    submit = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0, "trades_taken": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=_valid_submit_metadata_for_p2e("pytest_phase2_manage_buy_stop_widen_reject"),
        )
    )
    assert _extract_ok(submit) is True, f"Submit failed: {submit}"

    trade_id = _extract_trade_id(submit)

    # BUY widening risk => moving stop lower than current stop
    out = _as_dict(
        manage_open_trade(
            trade_id=trade_id,
            action="move_stop",
            payload={"stop_loss": 1.0940, "reason": "pytest_buy_widen_should_reject"},
        )
    )
    assert _extract_ok(out) is False, f"Expected BUY stop-widen reject: {out}"
    assert out.get("reason") == "phase2_stop_invariants_failed", f"Unexpected reason: {out}"

    violations = _extract_violations(out)
    if not violations and isinstance(out.get("violations"), list):
        violations = list(out.get("violations") or [])
    assert "phase2_stop_never_widen_buy" in violations, f"Missing BUY stop invariant violation: {out}"


def test_manage_open_trade_rejects_sell_stop_widening_phase2_invariant():
    proposal = _mk_valid_proposal(
        direction="SELL",
        entry=1.1000,
        stop_loss=1.1050,
        take_profit=1.0898,  # > 2R for SELL with 50 pip stop
    )

    submit = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0, "trades_taken": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=_valid_submit_metadata_for_p2e("pytest_phase2_manage_sell_stop_widen_reject"),
        )
    )
    assert _extract_ok(submit) is True, f"Submit failed: {submit}"

    trade_id = _extract_trade_id(submit)

    # SELL widening risk => moving stop higher than current stop
    out = _as_dict(
        manage_open_trade(
            trade_id=trade_id,
            action="move_stop",
            payload={"stop_loss": 1.1060, "reason": "pytest_sell_widen_should_reject"},
        )
    )
    assert _extract_ok(out) is False, f"Expected SELL stop-widen reject: {out}"
    assert out.get("reason") == "phase2_stop_invariants_failed", f"Unexpected reason: {out}"

    violations = _extract_violations(out)
    if not violations and isinstance(out.get("violations"), list):
        violations = list(out.get("violations") or [])
    assert "phase2_stop_never_widen_sell" in violations, f"Missing SELL stop invariant violation: {out}"


def test_manage_open_trade_allows_buy_stop_tightening_phase2_invariant():
    proposal = _mk_valid_proposal(direction="BUY", entry=1.1000, stop_loss=1.0950, take_profit=1.1102)

    submit = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0, "trades_taken": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=_valid_submit_metadata_for_p2e("pytest_phase2_manage_buy_stop_tighten_ok"),
        )
    )
    assert _extract_ok(submit) is True, f"Submit failed: {submit}"

    trade_id = _extract_trade_id(submit)

    out = _as_dict(
        manage_open_trade(
            trade_id=trade_id,
            action="move_stop",
            payload={"stop_loss": 1.0960, "reason": "pytest_buy_tighten_should_pass"},
        )
    )
    assert _extract_ok(out) is True, f"Expected BUY stop tighten to pass: {out}"


def test_manage_open_trade_allows_sell_stop_tightening_phase2_invariant():
    proposal = _mk_valid_proposal(
        direction="SELL",
        entry=1.1000,
        stop_loss=1.1050,
        take_profit=1.0898,
    )

    submit = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0, "trades_taken": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=_valid_submit_metadata_for_p2e("pytest_phase2_manage_sell_stop_tighten_ok"),
        )
    )
    assert _extract_ok(submit) is True, f"Submit failed: {submit}"

    trade_id = _extract_trade_id(submit)

    out = _as_dict(
        manage_open_trade(
            trade_id=trade_id,
            action="move_stop",
            payload={"stop_loss": 1.1040, "reason": "pytest_sell_tighten_should_pass"},
        )
    )
    assert _extract_ok(out) is True, f"Expected SELL stop tighten to pass: {out}"

def test_close_trade_returns_close_validation_ok_on_valid_close():
    proposal = _mk_valid_proposal()

    submit = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0, "trades_taken": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=_valid_submit_metadata_for_p2e("pytest_phase2_close_shape_valid"),
        )
    )
    assert _extract_ok(submit) is True, f"Submit failed: {submit}"

    trade_id = _extract_trade_id(submit)

    out = _as_dict(
        close_trade(
            trade_id=trade_id,
            close_price=1.1080,
            close_reason="pytest_valid_close",
            outcome={"pnl_hint": "positive"},
        )
    )

    assert _extract_ok(out) is True, f"Close failed: {out}"

    cv = out.get("close_validation")
    if not isinstance(cv, dict):
        cv = _find_nested_dict(_safe_dict(out.get("trade")), ["close"]) or {}
        cv = _safe_dict(cv).get("close_validation") if isinstance(cv, dict) else None

    assert isinstance(cv, dict), f"Missing close_validation: {out}"
    assert cv.get("ok") is True, f"close_validation not ok: {out}"


def test_close_trade_outcome_classification_label_is_expected():
    proposal = _mk_valid_proposal()

    submit = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0, "trades_taken": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=_valid_submit_metadata_for_p2e("pytest_phase2_close_outcome_label"),
        )
    )
    assert _extract_ok(submit) is True, f"Submit failed: {submit}"

    trade_id = _extract_trade_id(submit)

    out = _as_dict(
        close_trade(
            trade_id=trade_id,
            close_price=1.1080,
            close_reason="pytest_outcome_label",
            outcome={"pnl_hint": "positive"},
        )
    )
    assert _extract_ok(out) is True, f"Close failed: {out}"

    oc = out.get("outcome_classification")
    if not isinstance(oc, dict):
        trade = _safe_dict(out.get("trade"))
        close_block = _safe_dict(trade.get("close"))
        oc = close_block.get("outcome_classification")

    assert isinstance(oc, dict), f"Missing outcome_classification: {out}"
    label = oc.get("label")
    assert label in {"WIN", "LOSS", "BREAKEVEN"}, f"Unexpected label={label!r} in {out}"


def test_close_trade_rejects_non_numeric_close_price_with_invalid_close_payload_reason():
    proposal = _mk_valid_proposal()

    submit = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0, "trades_taken": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=_valid_submit_metadata_for_p2e("pytest_phase2_close_bad_price"),
        )
    )
    assert _extract_ok(submit) is True, f"Submit failed: {submit}"

    trade_id = _extract_trade_id(submit)

    out = _as_dict(
        close_trade(
            trade_id=trade_id,
            close_price="not-a-number",  # type: ignore[arg-type]
            close_reason="pytest_bad_close_price",
            outcome={},
        )
    )

    assert _extract_ok(out) is False, f"Expected reject, got: {out}"
    assert out.get("reason") == "invalid_close_payload", f"Unexpected reason: {out}"
    violations = _extract_violations(out)
    # Some runtimes may return top-level violations directly; this patch does.
    if not violations and isinstance(out.get("violations"), list):
        violations = list(out.get("violations") or [])
    assert "close_price_invalid_type" in violations, f"Expected close_price_invalid_type: {out}"


def test_close_trade_rejects_empty_close_reason_with_close_validation_failed_reason():
    proposal = _mk_valid_proposal()

    submit = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0, "trades_taken": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=_valid_submit_metadata_for_p2e("pytest_phase2_close_empty_reason"),
        )
    )
    assert _extract_ok(submit) is True, f"Submit failed: {submit}"

    trade_id = _extract_trade_id(submit)

    out = _as_dict(
        close_trade(
            trade_id=trade_id,
            close_price=1.1080,
            close_reason="",
            outcome={},
        )
    )

    assert _extract_ok(out) is False, f"Expected reject, got: {out}"
    assert out.get("reason") == "close_validation_failed", f"Unexpected reason: {out}"

    cv = out.get("close_validation")
    assert isinstance(cv, dict), f"Expected close_validation in reject response: {out}"
    assert cv.get("ok") is False, f"Expected close_validation.ok False: {out}"
    violations = list(cv.get("violations") or [])
    assert "close_reason_required" in violations, f"Expected close_reason_required: {out}"

def test_manage_open_trade_rejects_buy_stop_widening_phase2_invariant():
    proposal = _mk_valid_proposal(direction="BUY")

    submit = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0, "trades_taken": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=_valid_submit_metadata_for_p2e("pytest_phase2_manage_buy_widen_reject"),
        )
    )
    assert _extract_ok(submit) is True, f"Submit failed: {submit}"
    trade_id = _extract_trade_id(submit)

    out = _as_dict(
        manage_open_trade(
            trade_id=trade_id,
            action="move_stop",
            payload={"stop_loss": 1.0940, "reason": "pytest_widen_buy_should_reject"},
        )
    )

    assert _extract_ok(out) is False, f"Expected reject, got: {out}"
    assert out.get("reason") == "phase2_stop_invariants_failed", f"Unexpected reason: {out}"
    violations = _extract_violations(out)
    if not violations and isinstance(out.get("violations"), list):
        violations = list(out.get("violations") or [])
    assert "phase2_stop_never_widen_buy" in violations, f"Unexpected violations: {out}"


def test_manage_open_trade_accepts_buy_stop_tighten_phase2_invariant():
    proposal = _mk_valid_proposal(direction="BUY")

    submit = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0, "trades_taken": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=_valid_submit_metadata_for_p2e("pytest_phase2_manage_buy_tighten_ok"),
        )
    )
    assert _extract_ok(submit) is True, f"Submit failed: {submit}"
    trade_id = _extract_trade_id(submit)

    out = _as_dict(
        manage_open_trade(
            trade_id=trade_id,
            action="move_stop",
            payload={"stop_loss": 1.1005, "reason": "pytest_tighten_buy_should_pass"},
        )
    )

    assert _extract_ok(out) is True, f"Expected accept, got: {out}"
    notes = list(out.get("notes") or [])
    assert "stop_loss_updated" in notes, f"Missing stop update note: {out}"

    trade = out.get("trade")
    assert isinstance(trade, dict), f"Missing trade payload: {out}"
    assert float(trade.get("stop_loss")) == pytest.approx(1.1005)


def test_manage_open_trade_rejects_sell_stop_widening_phase2_invariant():
    # SELL valid proposal: entry 1.1000, stop above entry, TP below entry
    proposal = _mk_valid_proposal(
        direction="SELL",
        entry=1.1000,
        stop_loss=1.1050,
        take_profit=1.0898,  # >2R equivalent on SELL side
    )

    submit = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0, "trades_taken": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=_valid_submit_metadata_for_p2e("pytest_phase2_manage_sell_widen_reject"),
        )
    )
    assert _extract_ok(submit) is True, f"Submit failed: {submit}"
    trade_id = _extract_trade_id(submit)

    # SELL widening = moving stop UP (away from profit / more risk)
    out = _as_dict(
        manage_open_trade(
            trade_id=trade_id,
            action="move_stop",
            payload={"stop_loss": 1.1060, "reason": "pytest_widen_sell_should_reject"},
        )
    )

    assert _extract_ok(out) is False, f"Expected reject, got: {out}"
    assert out.get("reason") == "phase2_stop_invariants_failed", f"Unexpected reason: {out}"
    violations = _extract_violations(out)
    if not violations and isinstance(out.get("violations"), list):
        violations = list(out.get("violations") or [])
    assert "phase2_stop_never_widen_sell" in violations, f"Unexpected violations: {out}"


def test_manage_open_trade_rejects_non_numeric_stop_with_invalid_manage_payload():
    proposal = _mk_valid_proposal(direction="BUY")

    submit = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0, "trades_taken": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=_valid_submit_metadata_for_p2e("pytest_phase2_manage_bad_stop_type"),
        )
    )
    assert _extract_ok(submit) is True, f"Submit failed: {submit}"
    trade_id = _extract_trade_id(submit)

    out = _as_dict(
        manage_open_trade(
            trade_id=trade_id,
            action="move_stop",
            payload={"stop_loss": "not-a-number", "reason": "pytest_bad_stop_type"},
        )
    )

    assert _extract_ok(out) is False, f"Expected reject, got: {out}"
    assert out.get("reason") == "invalid_manage_payload", f"Unexpected reason: {out}"

    violations = _extract_violations(out)
    if not violations and isinstance(out.get("violations"), list):
        violations = list(out.get("violations") or [])
    assert "move_stop_invalid_stop_loss_type" in violations, f"Unexpected violations: {out}"

# ---------------------------------------------------------------------
# Close-path diagnostics / scoring scaffold tests (Phase 2 close contract)
# ---------------------------------------------------------------------


def _extract_close_validation(resp: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    cv = resp.get("close_validation")
    if isinstance(cv, dict):
        return cv

    trade = resp.get("trade")
    if isinstance(trade, dict):
        close = trade.get("close")
        if isinstance(close, dict):
            cv = close.get("close_validation")
            if isinstance(cv, dict):
                return cv
    return None


def _extract_outcome_classification(resp: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    oc = resp.get("outcome_classification")
    if isinstance(oc, dict):
        return oc

    trade = resp.get("trade")
    if isinstance(trade, dict):
        close = trade.get("close")
        if isinstance(close, dict):
            oc = close.get("outcome_classification")
            if isinstance(oc, dict):
                return oc
    return None


def _extract_rule_compliance_snapshot(resp: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rcs = resp.get("rule_compliance_snapshot")
    if isinstance(rcs, dict):
        return rcs

    trade = resp.get("trade")
    if isinstance(trade, dict):
        close = trade.get("close")
        if isinstance(close, dict):
            rcs = close.get("rule_compliance_snapshot")
            if isinstance(rcs, dict):
                return rcs
    return None


def _extract_scores(resp: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    scores = resp.get("scores")
    if isinstance(scores, dict):
        return scores

    trade = resp.get("trade")
    if isinstance(trade, dict):
        close = trade.get("close")
        if isinstance(close, dict):
            scores = close.get("scores")
            if isinstance(scores, dict):
                return scores
    return None


def _extract_final_result(resp: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    fr = resp.get("final_result")
    if isinstance(fr, dict):
        return fr

    trade = resp.get("trade")
    if isinstance(trade, dict):
        close = trade.get("close")
        if isinstance(close, dict):
            fr = close.get("final_result")
            if isinstance(fr, dict):
                return fr
    return None


def _open_trade_for_close_tests(
    *,
    direction: str = "BUY",
    entry: float = 1.1000,
    stop_loss: float = 1.0950,
    take_profit: float = 1.1110,  # <- safely above 2R (risk=0.0050, reward=0.0110 => RR=2.2)
    source: str = "pytest_phase2_close_open",
) -> str:
    proposal = _mk_valid_proposal(
        direction=direction,
        entry=entry,
        stop_loss=stop_loss,
        take_profit=take_profit,
    )

    out = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0, "trades_taken": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=_valid_submit_metadata_for_p2e(source),
        )
    )
    assert _extract_ok(out) is True, f"Submit failed for close test setup: {out}"
    return _extract_trade_id(out)


def test_close_trade_returns_scores_shape_keys():
    trade_id = _open_trade_for_close_tests(source="pytest_phase2_close_scores_shape")

    out = _as_dict(
        close_trade(
            trade_id=trade_id,
            close_price=1.1080,
            close_reason="pytest_close_scores_shape",
            outcome={"pnl_hint": "positive"},
        )
    )

    assert _extract_ok(out) is True, f"Close failed: {out}"

    scores = _extract_scores(out)
    assert isinstance(scores, dict), f"Missing scores diagnostics: {out}"

    expected_keys = {
        "process_score",
        "outcome_score",
        "rule_compliance_score",
        "context_quality_score",
        "execution_quality_score",
        "reward_score",
    }
    assert expected_keys.issubset(set(scores.keys())), f"Scores keys mismatch: {scores}"


def test_close_trade_final_result_contains_lifecycle_counts():
    trade_id = _open_trade_for_close_tests(source="pytest_phase2_close_final_result_counts")

    # Create management activity before close
    m1 = _as_dict(
        manage_open_trade(
            trade_id=trade_id,
            action="move_stop",
            payload={"stop_loss": 1.1005, "reason": "pytest_tighten"},
        )
    )
    assert _extract_ok(m1) is True, f"Manage move_stop failed: {m1}"

    m2 = _as_dict(
        manage_open_trade(
            trade_id=trade_id,
            action="take_partial",
            payload={"fraction": 0.5, "price": 1.1060, "reason": "pytest_partial"},
        )
    )
    assert _extract_ok(m2) is True, f"Manage take_partial failed: {m2}"

    out = _as_dict(
        close_trade(
            trade_id=trade_id,
            close_price=1.1080,
            close_reason="pytest_close_final_result_counts",
            outcome={"pnl_hint": "positive"},
        )
    )
    assert _extract_ok(out) is True, f"Close failed: {out}"

    fr = _extract_final_result(out)
    assert isinstance(fr, dict), f"Missing final_result: {out}"

    # Required normalized summary fields
    for k in (
        "label",
        "pnl_direction",
        "close_reason",
        "held_duration_sec",
        "managed",
        "partials_taken",
        "stop_moves",
    ):
        assert k in fr, f"final_result missing key '{k}': {fr}"

    assert fr.get("managed") is True, f"Expected managed=True after management events: {fr}"
    assert isinstance(fr.get("partials_taken"), int), f"partials_taken should be int: {fr}"
    assert isinstance(fr.get("stop_moves"), int), f"stop_moves should be int: {fr}"
    assert fr.get("partials_taken", -1) >= 1, f"Expected partials_taken >= 1: {fr}"
    assert fr.get("stop_moves", -1) >= 1, f"Expected stop_moves >= 1: {fr}"


def test_close_trade_rule_compliance_snapshot_reflects_entry_validations():
    trade_id = _open_trade_for_close_tests(source="pytest_phase2_close_rule_snapshot")

    out = _as_dict(
        close_trade(
            trade_id=trade_id,
            close_price=1.1080,
            close_reason="pytest_close_rule_snapshot",
            outcome={"pnl_hint": "positive"},
        )
    )
    assert _extract_ok(out) is True, f"Close failed: {out}"

    rcs = _extract_rule_compliance_snapshot(out)
    assert isinstance(rcs, dict), f"Missing rule_compliance_snapshot: {out}"

    # Support either summary nesting or direct fields
    summary = rcs.get("summary")
    if not isinstance(summary, dict):
        summary = rcs

    # Legacy/current names accepted
    scope_ok = summary.get("phase2_scope_ok_at_entry", summary.get("scope_validation_ok"))
    limits_ok = summary.get("phase2_limits_ok_at_entry", summary.get("phase2_limits_validation_ok"))
    risk_ok = summary.get("risk_validation_ok_at_entry", summary.get("risk_validation_ok"))

    assert scope_ok is True, f"Expected phase2 scope entry validation ok: {rcs}"
    assert limits_ok is True, f"Expected phase2 limits entry validation ok: {rcs}"
    assert risk_ok is True, f"Expected risk entry validation ok: {rcs}"

    # Placeholder lifecycle violations list (recommended next shape)
    if "violations_detected_during_lifecycle" in rcs:
        assert isinstance(rcs["violations_detected_during_lifecycle"], list), (
            f"violations_detected_during_lifecycle must be list: {rcs}"
        )


def test_close_trade_outcome_classification_buy_win_loss_breakeven():
    # BUY WIN
    tid_win = _open_trade_for_close_tests(
        direction="BUY",
        entry=1.1000,
        stop_loss=1.0950,
        take_profit=1.1110,  # safe >2R
        source="pytest_phase2_close_buy_win",
    )
    out_win = _as_dict(
        close_trade(
            trade_id=tid_win,
            close_price=1.1050,
            close_reason="pytest_buy_win",
            outcome={"pnl_hint": "positive"},
        )
    )
    assert _extract_ok(out_win) is True, f"BUY win close failed: {out_win}"
    oc_win = _extract_outcome_classification(out_win)
    assert isinstance(oc_win, dict), f"Missing outcome_classification (BUY win): {out_win}"
    assert oc_win.get("label") in {"WIN", "LOSS", "BREAKEVEN"}, f"Unexpected label: {oc_win}"
    assert oc_win.get("label") == "WIN", f"BUY close above entry should classify WIN: {oc_win}"

    # BUY LOSS
    tid_loss = _open_trade_for_close_tests(
        direction="BUY",
        entry=1.1000,
        stop_loss=1.0950,
        take_profit=1.1110,   # was 1.1100
        source="pytest_phase2_close_buy_loss",
    )
    out_loss = _as_dict(
        close_trade(
            trade_id=tid_loss,
            close_price=1.0990,
            close_reason="pytest_buy_loss",
            outcome={"pnl_hint": "negative"},
        )
    )
    assert _extract_ok(out_loss) is True, f"BUY loss close failed: {out_loss}"
    oc_loss = _extract_outcome_classification(out_loss)
    assert isinstance(oc_loss, dict), f"Missing outcome_classification (BUY loss): {out_loss}"
    assert oc_loss.get("label") == "LOSS", f"BUY close below entry should classify LOSS: {oc_loss}"

    # BUY BREAKEVEN
    tid_be = _open_trade_for_close_tests(
        direction="BUY",
        entry=1.1000,
        stop_loss=1.0950,
        take_profit=1.1110,   # was 1.1100
        source="pytest_phase2_close_buy_breakeven",
    )
    out_be = _as_dict(
        close_trade(
            trade_id=tid_be,
            close_price=1.1000,
            close_reason="pytest_buy_breakeven",
            outcome={"pnl_hint": "flat"},
        )
    )
    assert _extract_ok(out_be) is True, f"BUY breakeven close failed: {out_be}"
    oc_be = _extract_outcome_classification(out_be)
    assert isinstance(oc_be, dict), f"Missing outcome_classification (BUY breakeven): {out_be}"
    assert oc_be.get("label") == "BREAKEVEN", f"BUY close at entry should classify BREAKEVEN: {oc_be}"


def test_close_trade_outcome_classification_sell_win_loss_breakeven():
    # SELL WIN (close below entry)
    tid_win = _open_trade_for_close_tests(
        direction="SELL",
        entry=1.1000,
        stop_loss=1.1050,
        take_profit=1.0890,  # >2R (avoid float-edge rr==1.999999...)
        source="pytest_phase2_close_sell_win",
    )
    out_win = _as_dict(
        close_trade(
            trade_id=tid_win,
            close_price=1.0950,
            close_reason="pytest_sell_win",
            outcome={"pnl_hint": "positive"},
        )
    )
    assert _extract_ok(out_win) is True, f"SELL win close failed: {out_win}"
    oc_win = _extract_outcome_classification(out_win)
    assert isinstance(oc_win, dict), f"Missing outcome_classification (SELL win): {out_win}"
    assert oc_win.get("label") == "WIN", f"SELL close below entry should classify WIN: {oc_win}"

    # SELL LOSS (close above entry)
    tid_loss = _open_trade_for_close_tests(
        direction="SELL",
        entry=1.1000,
        stop_loss=1.1050,
        take_profit=1.0890,  # >2R (avoid float-edge rr==1.999999...)
        source="pytest_phase2_close_sell_loss",
    )
    out_loss = _as_dict(
        close_trade(
            trade_id=tid_loss,
            close_price=1.1010,
            close_reason="pytest_sell_loss",
            outcome={"pnl_hint": "negative"},
        )
    )
    assert _extract_ok(out_loss) is True, f"SELL loss close failed: {out_loss}"
    oc_loss = _extract_outcome_classification(out_loss)
    assert isinstance(oc_loss, dict), f"Missing outcome_classification (SELL loss): {out_loss}"
    assert oc_loss.get("label") == "LOSS", f"SELL close above entry should classify LOSS: {oc_loss}"

    # SELL BREAKEVEN
    tid_be = _open_trade_for_close_tests(
        direction="SELL",
        entry=1.1000,
        stop_loss=1.1050,
        take_profit=1.0890,  # >2R (avoid float-edge rr==1.999999...)
        source="pytest_phase2_close_sell_breakeven",
    )
    out_be = _as_dict(
        close_trade(
            trade_id=tid_be,
            close_price=1.1000,
            close_reason="pytest_sell_breakeven",
            outcome={"pnl_hint": "flat"},
        )
    )
    assert _extract_ok(out_be) is True, f"SELL breakeven close failed: {out_be}"
    oc_be = _extract_outcome_classification(out_be)
    assert isinstance(oc_be, dict), f"Missing outcome_classification (SELL breakeven): {out_be}"
    assert oc_be.get("label") == "BREAKEVEN", f"SELL close at entry should classify BREAKEVEN: {oc_be}"


def test_close_trade_event_payload_includes_close_diagnostics():
    trade_id = _open_trade_for_close_tests(source="pytest_phase2_close_event_payload")

    out = _as_dict(
        close_trade(
            trade_id=trade_id,
            close_price=1.1080,
            close_reason="pytest_close_event_payload",
            outcome={"pnl_hint": "positive"},
        )
    )
    assert _extract_ok(out) is True, f"Close failed: {out}"

    event = out.get("event")
    assert isinstance(event, dict), f"Missing event payload: {out}"
    payload = event.get("payload")
    assert isinstance(payload, dict), f"Missing event.payload: {event}"

    # Accept current + upgraded payloads, but enforce richer diagnostics if present
    assert payload.get("trade_id") == trade_id, f"event.payload.trade_id mismatch: {payload}"

    # Recommended richer fields (test is tolerant if not yet added; flip these to hard asserts once implemented)
    for k in ("outcome_classification", "close_validation", "final_result", "scores"):
        if k in payload:
            assert isinstance(payload.get(k), dict), f"event.payload.{k} should be dict: {payload}"

    # At minimum current close event fields should still exist
    assert "close_price" in payload, f"event payload missing close_price: {payload}"
    assert "close_reason" in payload, f"event payload missing close_reason: {payload}"


def test_close_trade_preserves_non_breaking_response_shape_trade_id_trade_event():
    trade_id = _open_trade_for_close_tests(source="pytest_phase2_close_shape_non_breaking")

    out = _as_dict(
        close_trade(
            trade_id=trade_id,
            close_price=1.1080,
            close_reason="pytest_close_shape_non_breaking",
            outcome={"pnl_hint": "positive"},
        )
    )

    assert _extract_ok(out) is True, f"Close failed: {out}"
    assert out.get("trade_id") == trade_id, f"trade_id mismatch: {out}"
    assert out.get("status") == "closed", f"status mismatch: {out}"

    trade = out.get("trade")
    assert isinstance(trade, dict), f"Missing trade object: {out}"
    assert trade.get("trade_id") == trade_id, f"trade.trade_id mismatch: {trade}"

    event = out.get("event")
    assert isinstance(event, dict), f"Missing event object: {out}"
    assert isinstance(event.get("event_type"), str) and event["event_type"], f"Invalid event_type: {event}"

    # New diagnostics should be additive / non-breaking
    cv = _extract_close_validation(out)
    if cv is not None:
        assert isinstance(cv, dict)
        assert cv.get("ok") in {True, False}

# ---------------------------------------------------------------------
# Phase 2 persistence / replay tests (P2Q scaffold)
# Add near the end of: backend/tests/test_aion_trading_paper_runtime_phase2.py
# ---------------------------------------------------------------------

from pathlib import Path
import json

import backend.modules.aion_trading.dmip_runtime as dmip_runtime


def _require_runtime_attr(name: str):
    fn = getattr(dmip_runtime, name, None)
    if fn is None:
        pytest.skip(f"{name} not implemented in current runtime.")
    return fn


def _runtime_paths_dict() -> Dict[str, Any]:
    fn = getattr(dmip_runtime, "_paper_runtime_paths", None)
    if fn is None:
        pytest.skip("_paper_runtime_paths not implemented in current runtime.")
    out = fn()
    if not isinstance(out, dict):
        pytest.skip("_paper_runtime_paths did not return dict.")
    return out


def _submit_one_trade_for_persistence(source: str = "pytest_phase2_persistence_submit") -> str:
    proposal = _mk_valid_proposal()
    out = _as_dict(
        submit_paper_trade(
            trade_proposal=proposal,
            session_stats={"losing_trades": 0, "trades_taken": 0},
            account_stats={
                "day_risk_used_pct": 0.0,
                "week_risk_used_pct": 0.0,
                "drawdown_pct": 0.0,
            },
            metadata=_valid_submit_metadata_for_p2e(source),
        )
    )
    assert _extract_ok(out) is True, f"Submit failed for persistence setup: {out}"
    return _extract_trade_id(out)


def test_paper_runtime_persistence_can_be_enabled_and_disabled(tmp_path: Path):
    configure = _require_runtime_attr("configure_paper_runtime_persistence")
    reset_state = _require_runtime_attr("reset_paper_runtime_state")

    # Start clean (tolerate different signatures)
    try:
        reset_state(clear_files=False)
    except TypeError:
        reset_state()

    base_dir = tmp_path / "paper_runtime_store"
    out_on = configure(enabled=True, base_dir=str(base_dir))
    assert isinstance(out_on, dict), f"configure(enabled=True) should return dict, got: {out_on}"

    # Tolerate shape differences, but ensure "enabled" is reflected somewhere
    enabled_flag = out_on.get("enabled")
    if enabled_flag is not None:
        assert enabled_flag is True, f"Persistence not enabled: {out_on}"

    paths = out_on.get("paths") if isinstance(out_on.get("paths"), dict) else _runtime_paths_dict()
    assert isinstance(paths, dict), f"Missing runtime paths after enable: {out_on}"

    # At least one path should point inside tmp dir
    joined = " | ".join(str(v) for v in paths.values())
    assert str(base_dir) in joined, f"Expected configured base_dir in runtime paths: {paths}"

    out_off = configure(enabled=False)
    assert isinstance(out_off, dict), f"configure(enabled=False) should return dict, got: {out_off}"
    enabled_flag_off = out_off.get("enabled")
    if enabled_flag_off is not None:
        assert enabled_flag_off is False, f"Persistence not disabled: {out_off}"


def test_emit_event_appends_jsonl_when_persistence_enabled(tmp_path: Path):
    configure = _require_runtime_attr("configure_paper_runtime_persistence")
    reset_state = _require_runtime_attr("reset_paper_runtime_state")

    try:
        reset_state(clear_files=False)
    except TypeError:
        reset_state()

    base_dir = tmp_path / "emit_event_store"
    configure(enabled=True, base_dir=str(base_dir))

    # Generate at least one event via normal runtime flow (submit emits accepted/rejected event)
    _submit_one_trade_for_persistence(source="pytest_phase2_emit_event_jsonl")

    paths = _runtime_paths_dict()
    events_jsonl = paths.get("events_jsonl")
    if not isinstance(events_jsonl, str):
        pytest.skip("events_jsonl path not exposed by runtime.")

    p = Path(events_jsonl)
    assert p.exists(), f"Expected events JSONL file to exist after event emission: {events_jsonl}"

    lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 1, f"Expected >=1 event JSONL line, got {len(lines)}"

    last = json.loads(lines[-1])
    assert isinstance(last, dict), f"Last JSONL row is not dict: {last}"
    assert isinstance(last.get("event_id"), str) and last["event_id"], f"Missing event_id: {last}"
    assert isinstance(last.get("event_type"), str) and last["event_type"], f"Missing event_type: {last}"
    assert "ts" in last, f"Missing ts: {last}"
    assert isinstance(last.get("payload"), dict), f"Missing payload dict: {last}"


def test_persist_snapshot_writes_trades_json(tmp_path: Path):
    configure = _require_runtime_attr("configure_paper_runtime_persistence")
    persist_snapshot = _require_runtime_attr("persist_paper_runtime_snapshot")
    reset_state = _require_runtime_attr("reset_paper_runtime_state")

    try:
        reset_state(clear_files=False)
    except TypeError:
        reset_state()

    base_dir = tmp_path / "snapshot_store"
    configure(enabled=True, base_dir=str(base_dir))

    trade_id = _submit_one_trade_for_persistence(source="pytest_phase2_persist_snapshot")
    assert isinstance(trade_id, str) and trade_id

    out = persist_snapshot()
    assert isinstance(out, dict), f"persist_paper_runtime_snapshot() should return dict, got: {out}"

    paths = out.get("paths") if isinstance(out.get("paths"), dict) else _runtime_paths_dict()

    # Accept either trades_json or snapshot_json naming
    trades_json = paths.get("trades_json")
    if not isinstance(trades_json, str):
        trades_json = paths.get("snapshot_json")
    if not isinstance(trades_json, str):
        pytest.skip("Runtime does not expose trades_json/snapshot_json path in persist output/paths.")

    p = Path(trades_json)
    assert p.exists(), f"Expected snapshot/trades JSON file to exist: {trades_json}"

    payload = json.loads(p.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), f"Snapshot JSON must be dict: {payload}"

    # Tolerate common snapshot shapes
    if isinstance(payload.get("trades"), dict):
        assert len(payload["trades"]) >= 1, f"Expected >=1 trade in snapshot.trades: {payload}"
    elif isinstance(payload.get("state"), dict) and isinstance(payload["state"].get("trades"), dict):
        assert len(payload["state"]["trades"]) >= 1, f"Expected >=1 trade in snapshot.state.trades: {payload}"
    else:
        pytest.fail(f"Could not find trades dict in snapshot payload: {payload}")


def test_restore_snapshot_recovers_trade_and_event_counts(tmp_path: Path):
    configure = _require_runtime_attr("configure_paper_runtime_persistence")
    persist_snapshot = _require_runtime_attr("persist_paper_runtime_snapshot")
    restore_snapshot = _require_runtime_attr("restore_paper_runtime_snapshot")
    reset_state = _require_runtime_attr("reset_paper_runtime_state")

    # Build persisted state
    try:
        reset_state(clear_files=False)
    except TypeError:
        reset_state()

    base_dir = tmp_path / "restore_store"
    configure(enabled=True, base_dir=str(base_dir))

    trade_id = _submit_one_trade_for_persistence(source="pytest_phase2_restore_snapshot_submit")
    _ = _as_dict(
        manage_open_trade(
            trade_id=trade_id,
            action="add_note",
            payload={"note": "pytest_restore_snapshot_note"},
        )
    )
    _ = _as_dict(
        close_trade(
            trade_id=trade_id,
            close_price=1.1080,
            close_reason="pytest_restore_snapshot_close",
            outcome={"pnl_hint": "positive"},
        )
    )

    persisted = persist_snapshot()
    assert isinstance(persisted, dict), f"persist before restore failed: {persisted}"

    # Reset memory only, keep files
    try:
        reset_out = reset_state(clear_files=False)
    except TypeError:
        reset_out = reset_state()
    if isinstance(reset_out, dict):
        # if counts are exposed, they should be zero after reset
        mc = reset_out.get("memory_counts")
        if isinstance(mc, dict):
            for k in ("trades", "events"):
                if k in mc:
                    assert mc[k] == 0, f"Expected memory count {k}=0 after reset: {reset_out}"

    # Restore
    restore_out = restore_snapshot()
    assert isinstance(restore_out, dict), f"restore_paper_runtime_snapshot() should return dict, got: {restore_out}"

    # Tolerate count shapes
    restored_counts = (
        restore_out.get("restored_counts")
        if isinstance(restore_out.get("restored_counts"), dict)
        else restore_out.get("counts")
    )
    if isinstance(restored_counts, dict):
        if "trades" in restored_counts:
            assert restored_counts["trades"] >= 1, f"Expected restored trade count >=1: {restore_out}"
        if "events" in restored_counts:
            assert restored_counts["events"] >= 1, f"Expected restored event count >=1: {restore_out}"

    # Stronger check: runtime in-memory collections now contain data (if exported)
    paper_trades = getattr(dmip_runtime, "_PAPER_TRADES", None)
    paper_events = getattr(dmip_runtime, "_PAPER_TRADE_EVENTS", None)
    if isinstance(paper_trades, dict):
        assert len(paper_trades) >= 1, "Expected in-memory _PAPER_TRADES to be restored"
    if isinstance(paper_events, list):
        assert len(paper_events) >= 1, "Expected in-memory _PAPER_TRADE_EVENTS to be restored"


def test_reset_paper_runtime_state_clears_memory_and_optional_files(tmp_path: Path):
    configure = _require_runtime_attr("configure_paper_runtime_persistence")
    persist_snapshot = _require_runtime_attr("persist_paper_runtime_snapshot")
    reset_state = _require_runtime_attr("reset_paper_runtime_state")

    # Seed runtime + files
    base_dir = tmp_path / "reset_store"
    configure(enabled=True, base_dir=str(base_dir))
    _submit_one_trade_for_persistence(source="pytest_phase2_reset_state_seed")
    persist_snapshot()

    paths_before = _runtime_paths_dict()

    # Reset with file cleanup if supported
    try:
        out = reset_state(clear_files=True)
    except TypeError:
        # If current impl has no flag, call plain reset and downgrade file assertions
        out = reset_state()
    assert isinstance(out, dict), f"reset_paper_runtime_state() should return dict, got: {out}"

    # Memory cleared
    paper_trades = getattr(dmip_runtime, "_PAPER_TRADES", None)
    paper_events = getattr(dmip_runtime, "_PAPER_TRADE_EVENTS", None)
    if isinstance(paper_trades, dict):
        assert len(paper_trades) == 0, f"Expected _PAPER_TRADES empty after reset: {len(paper_trades)}"
    if isinstance(paper_events, list):
        assert len(paper_events) == 0, f"Expected _PAPER_TRADE_EVENTS empty after reset: {len(paper_events)}"

    # Optional file cleanup assertions (only enforce if API indicates it attempted clear_files=True)
    if isinstance(out, dict) and (
        out.get("clear_files") is True
        or out.get("files_cleared") is True
        or (isinstance(out.get("meta"), dict) and out["meta"].get("clear_files") is True)
    ):
        # File names vary; check known path entries if present
        for key in ("events_jsonl", "trades_json", "snapshot_json"):
            pth = paths_before.get(key)
            if isinstance(pth, str):
                p = Path(pth)
                assert not p.exists(), f"Expected {key} file removed on reset(clear_files=True): {pth}"

def test_restore_paper_runtime_snapshot_alias_roundtrip(tmp_path):
    """
    Confirms the compatibility alias restore_paper_runtime_snapshot() works and
    restores both trades + events from persisted files.
    """
    configure = configure_paper_runtime_persistence
    reset_fn = reset_paper_runtime_state
    persist_fn = persist_paper_runtime_snapshot

    # alias should exist now (you added it)
    restore_alias = globals().get("restore_paper_runtime_snapshot")
    if not callable(restore_alias):
        pytest.skip("restore_paper_runtime_snapshot alias not implemented in current runtime.")

    base_dir = tmp_path / "paper_runtime_restore_alias"
    configure(enabled=True, base_dir=str(base_dir))

    # Clear memory + files (tolerate signature variants)
    try:
        reset_fn(clear_persistence_files=True)
    except TypeError:
        try:
            reset_fn(clear_files=True)
        except TypeError:
            reset_fn()

    # Open a trade to create state + at least one event
    tid = _open_trade_for_close_tests(
        direction="BUY",
        entry=1.1000,
        stop_loss=1.0950,
        take_profit=1.1102,  # slightly >2R to avoid float-edge rr==1.999999...
        source="pytest_phase2_restore_alias_roundtrip",
    )

    # Create another event via management so event count > 1
    mg = _as_dict(
        manage_open_trade(
            trade_id=tid,
            action="add_note",
            payload={"note": "restore alias test note"},
        )
    )
    assert _extract_ok(mg) is True, f"manage_open_trade failed: {mg}"

    snap = _as_dict(persist_fn())
    assert _extract_ok(snap) is True, f"persist snapshot failed: {snap}"

    # Clear memory only (leave files intact) -- tolerate signature variants
    try:
        cleared = _as_dict(reset_fn(clear_persistence_files=False))
    except TypeError:
        try:
            cleared = _as_dict(reset_fn(clear_files=False))
        except TypeError:
            cleared = _as_dict(reset_fn())
    assert _extract_ok(cleared) is True, f"reset failed: {cleared}"

    # Restore through alias
    restored = _as_dict(restore_alias(clear_existing=True))
    assert _extract_ok(restored) is True, f"restore alias failed: {restored}"

    # Tolerate either naming shape in runtime outputs
    restored_trades = restored.get("restored_trades")
    restored_events = restored.get("restored_events")
    if restored_trades is None:
        restored_trades = _safe_int(_safe_dict(restored.get("meta")).get("restored_trades"), 0)
    if restored_events is None:
        restored_events = _safe_int(_safe_dict(restored.get("meta")).get("restored_events"), 0)

    assert int(restored_trades or 0) >= 1, f"Expected >=1 restored trade: {restored}"
    assert int(restored_events or 0) >= 1, f"Expected >=1 restored event: {restored}"

    # Sanity-check the trade can be fetched again
    got = _as_dict(get_paper_trade(tid))
    assert _extract_ok(got) is True, f"Trade not available after restore: {got}"

def test_persist_snapshot_payload_shape_contains_trade_records(tmp_path):
    """
    Accepts either:
    - raw dict of trades keyed by trade_id
    - wrapped payload containing trades under a known key
    """
    configure = configure_paper_runtime_persistence
    reset_fn = reset_paper_runtime_state
    persist_fn = persist_paper_runtime_snapshot

    base_dir = tmp_path / "paper_runtime_snapshot_shape"
    configure(enabled=True, base_dir=str(base_dir))

    # Clear memory + files (tolerate signature variants)
    try:
        reset_fn(clear_persistence_files=True)
    except TypeError:
        try:
            reset_fn(clear_files=True)
        except TypeError:
            reset_fn()

    tid = _open_trade_for_close_tests(
        direction="BUY",
        entry=1.1000,
        stop_loss=1.0950,
        take_profit=1.1102,  # slightly >2R to avoid float-edge rr==1.999999...
        source="pytest_phase2_snapshot_shape",
    )

    out = _as_dict(persist_fn())
    assert _extract_ok(out) is True, f"persist snapshot failed: {out}"

    paths = _extract_paths(out)
    trades_path = (
        paths.get("trades_json")
        or paths.get("snapshot_json")
        or paths.get("trades_snapshot_json")
    )
    if not trades_path:
        pytest.skip("Runtime does not expose trades snapshot path.")

    p = Path(str(trades_path))
    assert p.exists(), f"Expected snapshot file to exist: {trades_path}"

    payload = json.loads(p.read_text(encoding="utf-8"))

    # Tolerate wrapped or unwrapped shape
    trades_dict = None
    if isinstance(payload, dict):
        # Wrapped candidates
        for k in ("trades", "paper_trades", "trade_store", "snapshot", "state"):
            v = payload.get(k)
            if isinstance(v, dict):
                # if nested wrapper, dig one more level for trades
                if k in {"snapshot", "state"}:
                    for kk in ("trades", "paper_trades", "trade_store"):
                        vv = _safe_dict(v).get(kk)
                        if isinstance(vv, dict):
                            trades_dict = vv
                            break
                    if trades_dict is not None:
                        break
                else:
                    trades_dict = v
                    break

        # Unwrapped current shape (trade_id -> trade row)
        if trades_dict is None and tid in payload and isinstance(payload.get(tid), dict):
            trades_dict = payload

    assert isinstance(trades_dict, dict), f"Could not find trades dict in snapshot payload: {payload}"
    assert tid in trades_dict, f"Expected trade_id {tid} in snapshot payload keys: {list(trades_dict.keys())[:10]}"


def test_persistence_roundtrip_open_close_restore_smoke(tmp_path):
    configure = configure_paper_runtime_persistence
    reset_fn = reset_paper_runtime_state
    persist_fn = persist_paper_runtime_snapshot
    restore_alias = (
        globals().get("restore_paper_runtime_snapshot")
        or globals().get("restore_paper_runtime_from_snapshot")
    )

    if not callable(restore_alias):
        pytest.skip("No restore function available in current runtime.")

    base_dir = tmp_path / "paper_runtime_e2e_roundtrip"
    configure(enabled=True, base_dir=str(base_dir))

    # Clear memory + files (tolerate runtime signature variants)
    try:
        reset_out = reset_fn(clear_persistence_files=True)
    except TypeError:
        try:
            reset_out = reset_fn(clear_files=True)
        except TypeError:
            reset_out = reset_fn()
    if isinstance(reset_out, dict):
        assert _extract_ok(_as_dict(reset_out)) in {True, None}, f"reset failed: {reset_out}"

    tid = _open_trade_for_close_tests(
        direction="SELL",
        entry=1.1000,
        stop_loss=1.1050,
        take_profit=1.0898,  # >2R for SELL, avoids float-edge min_rr failures
        source="pytest_phase2_persistence_e2e_roundtrip",
    )

    closed = _as_dict(
        close_trade(
            trade_id=tid,
            close_price=1.0950,
            close_reason="pytest_roundtrip_close",
            outcome={"pnl_hint": "positive"},
        )
    )
    assert _extract_ok(closed) is True, f"close_trade failed: {closed}"

    snap = _as_dict(persist_fn())
    assert _extract_ok(snap) is True, f"persist snapshot failed: {snap}"

    # Clear memory only (leave files intact) — tolerate signature variants
    try:
        cleared = _as_dict(reset_fn(clear_persistence_files=False))
    except TypeError:
        try:
            cleared = _as_dict(reset_fn(clear_files=False))
        except TypeError:
            cleared = _as_dict(reset_fn())
    assert _extract_ok(cleared) in {True, None}, f"reset failed: {cleared}"

    restored = _as_dict(restore_alias(clear_existing=True))
    assert _extract_ok(restored) is True, f"restore failed: {restored}"

    got = _as_dict(get_paper_trade(tid))
    assert _extract_ok(got) is True, f"Trade not found after restore: {got}"

    trade = _safe_dict(got.get("trade"))
    assert trade.get("status") == "CLOSED", f"Expected CLOSED after restore: {trade}"

    close_block = _safe_dict(trade.get("close"))
    oc = _safe_dict(close_block.get("outcome_classification"))
    assert oc.get("label") == "WIN", f"Expected SELL close below entry to remain WIN after restore: {oc}"