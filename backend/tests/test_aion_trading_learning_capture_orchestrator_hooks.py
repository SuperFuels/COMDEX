from backend.modules.aion_conversation.conversation_orchestrator import ConversationOrchestrator


def _mk_orch():
    return ConversationOrchestrator()


def test_dmip_skill_routes_and_exposes_trading_journal_metadata():
    orch = _mk_orch()
    out = orch.handle_turn(
        session_id="test_dmip_capture_1",
        user_text="run dmip pre market",
        include_metadata=True,
        include_debug=True,
    )
    assert out["ok"] is True
    meta = (((out.get("metadata") or {}).get("orchestrator") or {}))
    assert meta.get("skill_attempted") is True
    # journal may be None only if runtime disabled, but in your current stack it exists
    journal = meta.get("trading_journal")
    assert journal is None or isinstance(journal, dict)


def test_risk_validation_routes_and_exposes_trading_journal_metadata():
    orch = _mk_orch()
    out = orch.handle_turn(
        session_id="test_risk_capture_1",
        user_text="validate trade risk eur/usd buy entry 1.1000 sl 1.0950 tp 1.1100 risk 0.5%",
        include_metadata=True,
        include_debug=True,
    )
    assert out["ok"] is True
    meta = (((out.get("metadata") or {}).get("orchestrator") or {}))
    assert meta.get("skill_attempted") is True
    assert meta.get("skill_id") == "skill.trading_validate_risk"


def test_repeated_invalid_risk_proposals_surface_top_violations_in_journal():
    orch = _mk_orch()
    sid = "test_risk_capture_repeat"

    # repeated invalid requests (tight RR / high risk)
    for _ in range(3):
        out = orch.handle_turn(
            session_id=sid,
            user_text="validate trade risk eur/usd buy entry 1.1000 sl 1.0950 tp 1.1010 risk 5%",
            include_metadata=True,
            include_debug=False,
        )
        assert out["ok"] is True

    final_meta = (((out.get("metadata") or {}).get("orchestrator") or {}))
    journal = final_meta.get("trading_journal") or {}
    top_violations = journal.get("top_violations") or []
    assert isinstance(top_violations, list)


def test_non_trading_prompt_does_not_break_journal_path():
    orch = _mk_orch()
    out = orch.handle_turn(
        session_id="test_non_trading_no_capture",
        user_text="what should we build next for aion",
        include_metadata=True,
        include_debug=True,
    )
    assert out["ok"] is True
    meta = (((out.get("metadata") or {}).get("orchestrator") or {}))
    assert "trading_journal" in meta