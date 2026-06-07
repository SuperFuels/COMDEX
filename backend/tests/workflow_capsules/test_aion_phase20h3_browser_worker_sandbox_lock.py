import pytest

from backend.services.aion_mission_mode.browser_worker_sandbox import (
    assert_browser_session_scope,
    create_browser_evidence,
    create_browser_session,
    evaluate_browser_action,
    kill_browser_session,
    transition_browser_session,
)


def _session():
    return create_browser_session(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="business_001",
        provider="vercel",
        browser_worker_id="browser_001",
        provider_context_hash="sha256:context",
        allowed_domains=["https://vercel.com"],
    )


def test_phase20h3_browser_session_hash_is_deterministic() -> None:
    first = _session()
    second = _session()
    assert first["session_hash"] == second["session_hash"]


def test_phase20h3_browser_session_scope_allowed() -> None:
    session = _session()
    result = assert_browser_session_scope(
        session=session,
        mission_id="mission_001",
        mission_run_id="run_001",
        provider="vercel",
    )
    assert result["scope_allowed"] is True


def test_phase20h3_cross_mission_browser_session_blocked() -> None:
    session = _session()
    result = assert_browser_session_scope(
        session=session,
        mission_id="mission_999",
        mission_run_id="run_001",
        provider="vercel",
    )
    assert result["scope_allowed"] is False
    assert "browser_session_mission_mismatch" in result["reasons"]


def test_phase20h3_cross_provider_browser_session_blocked() -> None:
    session = _session()
    result = assert_browser_session_scope(
        session=session,
        mission_id="mission_001",
        mission_run_id="run_001",
        provider="meta",
    )
    assert result["scope_allowed"] is False
    assert "browser_session_provider_mismatch" in result["reasons"]


def test_phase20h3_read_page_allowed_inside_domain() -> None:
    session = _session()
    result = evaluate_browser_action(
        session=session,
        action_type="read_page",
        target_url="https://vercel.com/dashboard",
    )
    assert result["allowed"] is True


def test_phase20h3_search_allowed_inside_domain() -> None:
    session = _session()
    result = evaluate_browser_action(
        session=session,
        action_type="search",
        target_url="https://vercel.com/search",
        staged_payload={"query": "homefixed deploy"},
    )
    assert result["allowed"] is True


def test_phase20h3_target_url_outside_allowed_domain_blocked() -> None:
    session = _session()
    result = evaluate_browser_action(
        session=session,
        action_type="read_page",
        target_url="https://evil.example.com",
    )
    assert result["allowed"] is False
    assert "target_url_outside_allowed_domains" in result["reasons"]


def test_phase20h3_staged_form_fill_allowed() -> None:
    session = _session()
    result = evaluate_browser_action(
        session=session,
        action_type="fill_form_staged",
        target_url="https://vercel.com/new",
        staged_payload={"project": "homefixed"},
    )
    assert result["allowed"] is True


def test_phase20h3_secret_in_staged_payload_blocked() -> None:
    session = _session()
    result = evaluate_browser_action(
        session=session,
        action_type="fill_form_staged",
        target_url="https://vercel.com/new",
        staged_payload={"password": "plaintext"},
    )
    assert result["allowed"] is False
    assert "staged_payload_contains_secret_key" in result["reasons"]


def test_phase20h3_final_submit_blocked_even_with_approval_in_v0() -> None:
    session = _session()
    payload = {"project": "homefixed"}
    result = evaluate_browser_action(
        session=session,
        action_type="final_submit",
        target_url="https://vercel.com/new",
        staged_payload=payload,
        approval_hash="sha256:approval",
        approved_payload_hash="sha256:not_used_v0",
    )
    assert result["allowed"] is False
    assert "browser_worker_v0_final_submit_blocked" in result["reasons"]


def test_phase20h3_production_deploy_blocked() -> None:
    session = _session()
    result = evaluate_browser_action(
        session=session,
        action_type="production_deploy",
        target_url="https://vercel.com/deploy",
        staged_payload={"project": "homefixed"},
    )
    assert result["allowed"] is False
    assert "browser_worker_v0_final_submit_blocked" in result["reasons"]


def test_phase20h3_kill_switch_blocks_browser_action() -> None:
    session = kill_browser_session(session=_session(), reason="operator_stop")
    result = evaluate_browser_action(
        session=session,
        action_type="read_page",
        target_url="https://vercel.com/dashboard",
    )
    assert result["allowed"] is False
    assert "browser_worker_kill_switch_active" in result["reasons"]


def test_phase20h3_browser_evidence_for_allowed_action() -> None:
    session = _session()
    evaluation = evaluate_browser_action(
        session=session,
        action_type="capture_screenshot",
        target_url="https://vercel.com/dashboard",
    )
    evidence = create_browser_evidence(
        action_evaluation=evaluation,
        screenshot_hash="sha256:screenshot",
        page_state_hash="sha256:page",
        dom_summary_hash="sha256:dom",
    )
    assert evidence["evidence_hash"].startswith("sha256:")


def test_phase20h3_browser_evidence_rejected_for_blocked_action() -> None:
    session = _session()
    evaluation = evaluate_browser_action(
        session=session,
        action_type="read_page",
        target_url="https://evil.example.com",
    )
    with pytest.raises(ValueError):
        create_browser_evidence(action_evaluation=evaluation)


def test_phase20h3_session_transition_hash_changes() -> None:
    session = _session()
    transitioned = transition_browser_session(
        session=session,
        next_state="waiting_approval",
        reason="staged_payload_ready",
    )
    assert transitioned["session_hash"] != session["session_hash"]
    assert transitioned["session_state"] == "waiting_approval"


def test_phase20h3_unknown_session_state_rejected() -> None:
    with pytest.raises(ValueError):
        transition_browser_session(
            session=_session(),
            next_state="unknown",
            reason="bad_state",
        )


def test_phase20h3_killed_session_scope_blocked() -> None:
    killed = kill_browser_session(session=_session(), reason="operator_stop")
    assertion = assert_browser_session_scope(
        session=killed,
        mission_id="mission_001",
        mission_run_id="run_001",
        provider="vercel",
    )
    assert assertion["scope_allowed"] is False
    assert "browser_worker_kill_switch_active" in assertion["reasons"]
