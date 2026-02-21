# /workspaces/COMDEX/backend/tests/test_aion_trading_orchestrator_routing.py

from __future__ import annotations

from backend.modules.aion_conversation.conversation_orchestrator import ConversationOrchestrator


def _run(orch: ConversationOrchestrator, text: str, session_id: str = "test-trading-routing-session"):
    return orch.handle_turn(
        session_id=session_id,
        user_text=text,
        include_debug=True,
        include_metadata=True,
    )


def _orchestrator_meta(out: dict) -> dict:
    return dict((out.get("metadata") or {}).get("orchestrator") or {})


def _trace(out: dict) -> dict:
    return dict((out.get("debug") or {}).get("orchestrator_trace") or {})


def test_trading_route_curriculum_skill():
    orch = ConversationOrchestrator()
    out = _run(orch, "show forex curriculum", session_id="t-curriculum-1")

    meta = _orchestrator_meta(out)
    trace = _trace(out)

    assert out["ok"] is True
    assert meta.get("skill_attempted") is True
    assert meta.get("skill_executed_ok") is True
    assert meta.get("skill_id") == "skill.trading_get_curriculum"

    skill_req = trace.get("skill_request") or {}
    assert skill_req.get("skill_id") == "skill.trading_get_curriculum"


def test_trading_route_list_strategies_skill():
    orch = ConversationOrchestrator()
    out = _run(orch, "list trading strategies", session_id="t-strategy-list-1")

    meta = _orchestrator_meta(out)
    trace = _trace(out)

    assert out["ok"] is True
    assert meta.get("skill_attempted") is True
    assert meta.get("skill_executed_ok") is True
    assert meta.get("skill_id") == "skill.trading_list_strategies"

    skill_req = trace.get("skill_request") or {}
    assert skill_req.get("skill_id") == "skill.trading_list_strategies"


def test_trading_route_get_strategy_tier3_skill():
    orch = ConversationOrchestrator()
    out = _run(orch, "show strategy tier 3", session_id="t-get-strategy-tier3-1")

    meta = _orchestrator_meta(out)
    trace = _trace(out)

    assert out["ok"] is True
    assert meta.get("skill_attempted") is True
    assert meta.get("skill_executed_ok") is True
    assert meta.get("skill_id") == "skill.trading_get_strategy"

    skill_req = trace.get("skill_request") or {}
    assert skill_req.get("skill_id") == "skill.trading_get_strategy"
    assert (skill_req.get("inputs") or {}).get("strategy_tier") == "tier3_smc_intraday"


def test_trading_route_dmip_pre_market_skill():
    orch = ConversationOrchestrator()
    out = _run(orch, "run pre-market dmip", session_id="t-dmip-pre-market-1")

    meta = _orchestrator_meta(out)
    trace = _trace(out)

    assert out["ok"] is True
    assert meta.get("skill_attempted") is True
    assert meta.get("skill_executed_ok") is True
    assert meta.get("skill_id") == "skill.trading_run_dmip_checkpoint"

    skill_req = trace.get("skill_request") or {}
    assert skill_req.get("skill_id") == "skill.trading_run_dmip_checkpoint"
    assert (skill_req.get("inputs") or {}).get("checkpoint") == "pre_market"


def test_trading_route_validate_trade_risk_skill():
    orch = ConversationOrchestrator()
    out = _run(orch, "validate trade risk eur/usd buy", session_id="t-risk-basic-1")

    meta = _orchestrator_meta(out)
    trace = _trace(out)

    assert out["ok"] is True
    assert meta.get("skill_attempted") is True
    assert meta.get("skill_executed_ok") is True
    assert meta.get("skill_id") == "skill.trading_validate_risk"

    skill_req = trace.get("skill_request") or {}
    assert skill_req.get("skill_id") == "skill.trading_validate_risk"
    inputs = dict(skill_req.get("inputs") or {})
    assert inputs.get("account_mode") == "paper"  # important safety default
    assert inputs.get("pair") == "EUR/USD"
    assert inputs.get("direction") == "BUY"


def test_no_false_positive_skill_route_for_unrelated_prompt():
    orch = ConversationOrchestrator()
    out = _run(orch, "explain that in more detail", session_id="t-no-fp-1")

    meta = _orchestrator_meta(out)
    trace = _trace(out)

    # This should remain normal local/composer handling, not trading skill routing
    assert out["ok"] is True
    assert meta.get("skill_attempted") in (False, None)
    assert meta.get("skill_id") in (None, "")
    assert trace.get("skill_request") in (None, {})


def test_trading_route_validate_risk_parses_values():
    orch = ConversationOrchestrator()
    out = orch.handle_turn(
        session_id="t-risk-parse-1",
        user_text="validate trade risk buy EUR/USD entry 1.1025 sl 1.0990 tp 1.1095 risk 0.5% equity 25000",
        include_metadata=True,
        include_debug=True,
    )

    assert out["ok"] is True
    meta = _orchestrator_meta(out)
    assert meta.get("skill_attempted") is True
    assert meta.get("skill_executed_ok") is True
    assert meta.get("skill_id") == "skill.trading_validate_risk"

    skill_req = _trace(out).get("skill_request") or {}
    inputs = dict(skill_req.get("inputs") or {})

    assert inputs.get("account_mode") == "paper"
    assert inputs.get("pair") == "EUR/USD"
    assert inputs.get("direction") == "BUY"
    assert float(inputs.get("entry")) == 1.1025
    assert float(inputs.get("stop_loss")) == 1.0990
    assert float(inputs.get("take_profit")) == 1.1095
    assert float(inputs.get("risk_pct")) == 0.5
    assert float(inputs.get("account_equity")) == 25000.0


def test_trading_route_validate_risk_partial_parse_keeps_defaults():
    orch = ConversationOrchestrator()
    out = orch.handle_turn(
        session_id="t-risk-parse-2",
        user_text="check trade risk short gbpusd",
        include_metadata=True,
        include_debug=True,
    )

    assert out["ok"] is True
    meta = _orchestrator_meta(out)
    assert meta.get("skill_attempted") is True
    assert meta.get("skill_executed_ok") is True
    assert meta.get("skill_id") == "skill.trading_validate_risk"

    skill_req = _trace(out).get("skill_request") or {}
    inputs = dict(skill_req.get("inputs") or {})

    assert inputs.get("pair") == "GBP/USD"
    assert inputs.get("direction") == "SELL"
    assert inputs.get("account_mode") == "paper"  # hard lock remains
    # defaults still present
    assert float(inputs.get("entry")) == 1.1000


def test_dmip_capture_and_journal_keys_present_in_metadata_and_debug():
    """
    Confirms orchestrator exposes trading_journal/trading_journal_summary
    in both metadata + debug for DMIP path (even if runtime APIs vary / return None).
    """
    orch = ConversationOrchestrator()
    out = _run(orch, "run pre-market dmip", session_id="t-dmip-journal-keys-1")

    assert out["ok"] is True
    assert isinstance(out.get("response"), str)
    assert out["response"].strip() != ""

    meta = _orchestrator_meta(out)
    trace = _trace(out)

    # Skill route sanity
    assert meta.get("skill_attempted") is True
    assert meta.get("skill_executed_ok") is True
    assert meta.get("skill_id") == "skill.trading_run_dmip_checkpoint"

    # Required keys requested for explicit assertions
    assert "trading_journal" in meta
    assert "trading_journal_summary" in meta
    assert "trading_journal" in trace

    # Debug mirror keys also exist in current implementation
    assert "trading_journal_summary_before" in trace
    assert "trading_journal_summary_after" in trace
    assert "trading_capture_result" in trace

    # Shape checks (allow None because runtime/capture may be unavailable in some environments)
    tj = meta.get("trading_journal")
    tjs = meta.get("trading_journal_summary")
    trace_tj = trace.get("trading_journal")

    assert tj is None or isinstance(tj, dict)
    assert tjs is None or isinstance(tjs, dict)
    assert trace_tj is None or isinstance(trace_tj, dict)

    # If present, debug and metadata should align for the same summarized journal object
    if isinstance(tj, dict) and isinstance(trace_tj, dict):
        assert trace_tj == tj


def test_risk_capture_and_journal_keys_present_in_metadata_and_debug():
    """
    Same as DMIP test but for risk validation capture path.
    """
    orch = ConversationOrchestrator()
    out = _run(
        orch,
        "validate trade risk buy EUR/USD entry 1.1025 sl 1.0990 tp 1.1095 risk 1% equity 10000",
        session_id="t-risk-journal-keys-1",
    )

    assert out["ok"] is True
    assert isinstance(out.get("response"), str)
    assert out["response"].strip() != ""

    meta = _orchestrator_meta(out)
    trace = _trace(out)

    assert meta.get("skill_attempted") is True
    assert meta.get("skill_executed_ok") is True
    assert meta.get("skill_id") == "skill.trading_validate_risk"

    # Explicit key assertions requested
    assert "trading_journal" in meta
    assert "trading_journal_summary" in meta
    assert "trading_journal" in trace

    # Additional current debug keys
    assert "trading_capture_result" in trace
    assert "trading_learning_event" in trace

    tj = meta.get("trading_journal")
    tjs = meta.get("trading_journal_summary")
    trace_tj = trace.get("trading_journal")

    assert tj is None or isinstance(tj, dict)
    assert tjs is None or isinstance(tjs, dict)
    assert trace_tj is None or isinstance(trace_tj, dict)

    if isinstance(tj, dict) and isinstance(trace_tj, dict):
        assert trace_tj == tj


def test_dmip_capture_runtime_failure_is_non_breaking(monkeypatch):
    """
    Failure injection: trading capture hook raises.
    Contract: turn still succeeds, response still produced, and capture metadata stays non-breaking.
    """
    orch = ConversationOrchestrator()

    def _boom(*args, **kwargs):
        raise RuntimeError("forced capture failure for test")

    # Force failure inside the orchestrator's capture dispatch wrapper call site.
    monkeypatch.setattr(orch, "_capture_trading_skill_event_if_applicable", _boom, raising=True)

    out = _run(orch, "run pre-market dmip", session_id="t-dmip-capture-fail-1")

    # Non-breaking behavior
    assert out["ok"] is True
    assert isinstance(out.get("response"), str)
    assert out["response"].strip() != ""

    meta = _orchestrator_meta(out)
    trace = _trace(out)

    # Skill still executes
    assert meta.get("skill_attempted") is True
    assert meta.get("skill_executed_ok") is True
    assert meta.get("skill_id") == "skill.trading_run_dmip_checkpoint"

    # Capture failure should not crash the turn; wrapper in handle_turn swallows and sets None
    assert trace.get("trading_capture_result") is None

    # Metadata/orchestrator exposes boolean derived from capture result
    # False/None acceptable depending on serialization path, but current code returns bool(None) => False
    assert meta.get("trading_capture_recorded") in (False, None)

    # Journal keys should still exist for consumers
    assert "trading_journal" in meta
    assert "trading_journal_summary" in meta
    assert "trading_journal" in trace


def test_trading_capture_runtime_failure_is_non_breaking_dmip():
    orch = ConversationOrchestrator()

    # Inject a failing capture runtime method (Sprint 3.1 journal capture path)
    class _FailingCaptureRuntime:
        def capture_dmip_event(self, event):
            raise RuntimeError("forced dmip capture failure")

        # optional summary API so orchestrator can still probe safely
        def build_summary(self):
            return {
                "schema_version": "aion.trading_learning_journal_summary.v1",
                "total_events": 0,
                "total_dmip_captures": 0,
                "total_risk_validations": 0,
                "risk_fail_count": 0,
                "fail_rate": 0.0,
            }

    orch.trading_learning_capture = _FailingCaptureRuntime()

    out = orch.handle_turn(
        session_id="t-capture-failure-dmip",
        user_text="run pre-market dmip",
        include_metadata=True,
        include_debug=True,
    )

    assert out["ok"] is True
    assert isinstance(out.get("response"), str) and out["response"].strip() != ""

    meta = ((out.get("metadata") or {}).get("orchestrator") or {})
    trace = ((out.get("debug") or {}).get("orchestrator_trace") or {})

    # Core skill path still succeeds
    assert meta.get("skill_attempted") is True
    assert meta.get("skill_executed_ok") is True
    assert meta.get("skill_id") == "skill.trading_run_dmip_checkpoint"

    # Capture failure must not break turn handling
    cap = trace.get("trading_capture_result")
    assert cap is None or isinstance(cap, dict)

    # If failure is surfaced, verify shape
    if isinstance(cap, dict):
        assert cap.get("ok") is False
        assert cap.get("event_type") == "trading_dmip_checkpoint"
        assert cap.get("reason") in {"capture_exception", "unsupported_dmip_signature", "no_supported_capture_method"}

    # Journal keys should still exist in trace/meta contract (even if None)
    assert "trading_journal" in trace
    assert "trading_journal_summary_before" in trace
    assert "trading_journal_summary_after" in trace
    assert "trading_journal" in meta
    assert "trading_journal_summary" in meta


def test_trading_capture_runtime_failure_is_non_breaking_risk_validation():
    orch = ConversationOrchestrator()

    class _FailingCaptureRuntime:
        def capture_risk_validation_event(self, event):
            raise RuntimeError("forced risk capture failure")

        def build_summary(self):
            return {
                "schema_version": "aion.trading_learning_journal_summary.v1",
                "total_events": 0,
                "total_dmip_captures": 0,
                "total_risk_validations": 0,
                "risk_fail_count": 0,
                "fail_rate": 0.0,
            }

    orch.trading_learning_capture = _FailingCaptureRuntime()

    out = orch.handle_turn(
        session_id="t-capture-failure-risk",
        user_text="validate trade risk eur/usd buy",
        include_metadata=True,
        include_debug=True,
    )

    assert out["ok"] is True
    assert isinstance(out.get("response"), str) and out["response"].strip() != ""

    meta = ((out.get("metadata") or {}).get("orchestrator") or {})
    trace = ((out.get("debug") or {}).get("orchestrator_trace") or {})

    assert meta.get("skill_attempted") is True
    assert meta.get("skill_executed_ok") is True
    assert meta.get("skill_id") == "skill.trading_validate_risk"

    cap = trace.get("trading_capture_result")
    assert cap is None or isinstance(cap, dict)
    if isinstance(cap, dict):
        assert cap.get("ok") is False
        assert cap.get("event_type") == "trading_risk_validation"
        assert cap.get("reason") in {"capture_exception", "unsupported_risk_signature", "no_supported_capture_method"}

    assert "trading_journal" in trace
    assert "trading_journal" in meta
    assert "trading_journal_summary" in meta


def test_trading_route_update_decision_influence_weights_dry_run_default():
    orch = ConversationOrchestrator()
    out = _run(orch, "update decision influence weights dry run")

    meta = _orchestrator_meta(out)
    trace = _trace(out)

    assert out["ok"] is True
    assert isinstance(out.get("response"), str) and out.get("response")

    assert meta.get("skill_attempted") is True
    assert meta.get("skill_executed_ok") is True
    assert meta.get("skill_id") == "skill.trading_update_decision_influence_weights"

    skill_req = trace.get("skill_request") or {}
    assert skill_req.get("skill_id") == "skill.trading_update_decision_influence_weights"
    inputs = dict(skill_req.get("inputs") or {})
    assert inputs.get("dry_run") is True  # safety default

    # existing trading journal/debug keys should remain present/non-breaking
    assert "trading_journal" in meta
    assert "trading_journal_summary" in meta
    assert "trading_journal" in trace


def test_trading_route_update_decision_influence_capture_runtime_failure_is_non_breaking(monkeypatch):
    orch = ConversationOrchestrator()

    # Force capture hook failure (post-skill observational path) and ensure turn still succeeds
    def _boom(*args, **kwargs):
        raise RuntimeError("forced capture failure for test")

    monkeypatch.setattr(orch, "_capture_trading_skill_event_if_applicable", _boom, raising=True)

    out = _run(orch, "update decision influence weights dry run")

    meta = _orchestrator_meta(out)
    trace = _trace(out)

    assert out["ok"] is True
    assert isinstance(out.get("response"), str) and out.get("response")

    assert meta.get("skill_attempted") is True
    # skill may still execute fine even if capture path fails
    assert meta.get("skill_id") == "skill.trading_update_decision_influence_weights"

    # non-breaking capture behavior
    # depending on your contract it may be None or failure-shaped; current orchestrator swallows to None
    assert trace.get("trading_capture_result") in (None, {}) or isinstance(trace.get("trading_capture_result"), dict)


def test_trading_route_update_decision_influence_debug_metadata_shape():
    orch = ConversationOrchestrator()
    out = _run(orch, "decision influence dry run")

    meta = _orchestrator_meta(out)
    trace = _trace(out)

    assert out["ok"] is True

    # Explicit keys requested
    assert "trading_journal" in meta
    assert "trading_journal_summary" in meta
    assert "trading_journal" in trace

    # Optional sanity on orchestrator debug presence
    assert isinstance(trace, dict)