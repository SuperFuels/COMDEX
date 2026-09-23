import pytest

from backend.services.aion_mission_mode.external_callback_signaling_isolation import (
    consume_callback_contract,
    create_callback_contract,
    create_signaling_contract,
    evaluate_callback_ingress,
    evaluate_signaling_message,
    payload_hash,
    summarize_callback_and_signal_assertions,
)


def _payload():
    return {"deployment_id": "dep_123", "status": "ready"}


def _callback_contract(**kwargs):
    base = dict(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="business_001",
        provider="vercel",
        action_type="deploy_to_preview",
        callback_type="deployment_callback",
        callback_url_id="callback_001",
        expected_payload_hash=payload_hash(_payload()),
        staged_state_hash="sha256:staged",
        provider_context_hash="sha256:context",
        nonce="nonce_001",
        expires_at=200.0,
    )
    base.update(kwargs)
    return create_callback_contract(**base)


def _callback_event(**kwargs):
    base = {
        "mission_id": "mission_001",
        "mission_run_id": "run_001",
        "provider": "vercel",
        "callback_type": "deployment_callback",
        "callback_url_id": "callback_001",
        "nonce": "nonce_001",
        "payload": _payload(),
    }
    base.update(kwargs)
    return base


def _signaling_contract(**kwargs):
    base = dict(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="business_001",
        provider="vercel",
        browser_worker_id="browser_001",
        browser_session_hash="sha256:session",
        signaling_channel_id="signal_001",
        allowed_signal_types=["browser_worker_heartbeat", "staged_state_update"],
        expires_at=200.0,
    )
    base.update(kwargs)
    return create_signaling_contract(**base)


def _signal_message(**kwargs):
    base = {
        "mission_id": "mission_001",
        "mission_run_id": "run_001",
        "provider": "vercel",
        "browser_worker_id": "browser_001",
        "browser_session_hash": "sha256:session",
        "signaling_channel_id": "signal_001",
        "signal_type": "browser_worker_heartbeat",
        "payload": {"alive": True},
    }
    base.update(kwargs)
    return base


def test_phase20h6_callback_contract_hash_deterministic() -> None:
    assert _callback_contract()["callback_contract_hash"] == _callback_contract()["callback_contract_hash"]


def test_phase20h6_unknown_callback_type_rejected() -> None:
    with pytest.raises(ValueError):
        _callback_contract(callback_type="unknown_callback")


def test_phase20h6_valid_callback_ingress_allowed() -> None:
    result = evaluate_callback_ingress(
        contract=_callback_contract(),
        callback_event=_callback_event(),
        now=150.0,
    )
    assert result["allowed"] is True


def test_phase20h6_callback_provider_mismatch_quarantined() -> None:
    result = evaluate_callback_ingress(
        contract=_callback_contract(),
        callback_event=_callback_event(provider="stripe"),
        now=150.0,
    )
    assert result["allowed"] is False
    assert "provider_mismatch" in result["reasons"]


def test_phase20h6_callback_mission_mismatch_quarantined() -> None:
    result = evaluate_callback_ingress(
        contract=_callback_contract(),
        callback_event=_callback_event(mission_id="mission_999"),
        now=150.0,
    )
    assert result["allowed"] is False
    assert "mission_mismatch" in result["reasons"]


def test_phase20h6_callback_nonce_mismatch_quarantined() -> None:
    result = evaluate_callback_ingress(
        contract=_callback_contract(),
        callback_event=_callback_event(nonce="wrong"),
        now=150.0,
    )
    assert result["allowed"] is False
    assert "nonce_mismatch" in result["reasons"]


def test_phase20h6_callback_payload_hash_mismatch_quarantined() -> None:
    result = evaluate_callback_ingress(
        contract=_callback_contract(),
        callback_event=_callback_event(payload={"deployment_id": "dep_123", "status": "changed"}),
        now=150.0,
    )
    assert result["allowed"] is False
    assert "callback_payload_hash_mismatch" in result["reasons"]


def test_phase20h6_callback_expiry_quarantined() -> None:
    result = evaluate_callback_ingress(
        contract=_callback_contract(),
        callback_event=_callback_event(),
        now=250.0,
    )
    assert result["allowed"] is False
    assert "callback_contract_expired" in result["reasons"]


def test_phase20h6_callback_replay_quarantined() -> None:
    contract = _callback_contract()
    event = _callback_event()
    first = evaluate_callback_ingress(contract=contract, callback_event=event, now=150.0)
    second = evaluate_callback_ingress(
        contract=contract,
        callback_event=event,
        now=151.0,
        seen_callback_hashes=[first["callback_event_hash"]],
    )
    assert second["allowed"] is False
    assert "callback_replay_detected" in second["reasons"]


def test_phase20h6_forbidden_callback_mutation_quarantined() -> None:
    result = evaluate_callback_ingress(
        contract=_callback_contract(),
        callback_event=_callback_event(requested_mutation="deploy_to_production"),
        now=150.0,
    )
    assert result["allowed"] is False
    assert "forbidden_callback_mutation_blocked" in result["reasons"]


def test_phase20h6_consumes_allowed_callback_contract() -> None:
    contract = _callback_contract()
    assertion = evaluate_callback_ingress(
        contract=contract,
        callback_event=_callback_event(),
        now=150.0,
    )
    consumed = consume_callback_contract(
        contract=contract,
        ingress_assertion=assertion,
        provider_response_hash="sha256:provider",
        now=151.0,
    )
    assert consumed["consumed"] is True
    assert consumed["callback_contract_hash"] != contract["callback_contract_hash"]


def test_phase20h6_blocked_callback_cannot_consume_contract() -> None:
    assertion = evaluate_callback_ingress(
        contract=_callback_contract(),
        callback_event=_callback_event(nonce="wrong"),
        now=150.0,
    )
    with pytest.raises(ValueError):
        consume_callback_contract(
            contract=_callback_contract(),
            ingress_assertion=assertion,
            provider_response_hash="sha256:provider",
            now=151.0,
        )


def test_phase20h6_signaling_contract_hash_deterministic() -> None:
    assert _signaling_contract()["signaling_contract_hash"] == _signaling_contract()["signaling_contract_hash"]


def test_phase20h6_unknown_signal_type_rejected_in_contract() -> None:
    with pytest.raises(ValueError):
        _signaling_contract(allowed_signal_types=["unknown_signal"])


def test_phase20h6_valid_signal_allowed() -> None:
    result = evaluate_signaling_message(
        contract=_signaling_contract(),
        signal_message=_signal_message(),
        now=150.0,
    )
    assert result["allowed"] is True


def test_phase20h6_signal_wrong_channel_quarantined() -> None:
    result = evaluate_signaling_message(
        contract=_signaling_contract(),
        signal_message=_signal_message(signaling_channel_id="wrong"),
        now=150.0,
    )
    assert result["allowed"] is False
    assert "signaling_channel_mismatch" in result["reasons"]


def test_phase20h6_signal_wrong_browser_session_quarantined() -> None:
    result = evaluate_signaling_message(
        contract=_signaling_contract(),
        signal_message=_signal_message(browser_session_hash="sha256:wrong"),
        now=150.0,
    )
    assert result["allowed"] is False
    assert "browser_session_mismatch" in result["reasons"]


def test_phase20h6_signal_type_not_allowed_quarantined() -> None:
    result = evaluate_signaling_message(
        contract=_signaling_contract(),
        signal_message=_signal_message(signal_type="provider_socket_status"),
        now=150.0,
    )
    assert result["allowed"] is False
    assert "signal_type_not_allowed" in result["reasons"]


def test_phase20h6_forbidden_signal_mutation_quarantined() -> None:
    result = evaluate_signaling_message(
        contract=_signaling_contract(),
        signal_message=_signal_message(requested_mutation="mutate_memory"),
        now=150.0,
    )
    assert result["allowed"] is False
    assert "forbidden_signal_mutation_blocked" in result["reasons"]


def test_phase20h6_expired_signal_contract_quarantined() -> None:
    result = evaluate_signaling_message(
        contract=_signaling_contract(),
        signal_message=_signal_message(),
        now=250.0,
    )
    assert result["allowed"] is False
    assert "signaling_contract_expired" in result["reasons"]


def test_phase20h6_signal_assertion_hash_deterministic() -> None:
    first = evaluate_signaling_message(
        contract=_signaling_contract(),
        signal_message=_signal_message(),
        now=150.0,
    )
    second = evaluate_signaling_message(
        contract=_signaling_contract(),
        signal_message=_signal_message(),
        now=150.0,
    )
    assert first["signal_assertion_hash"] == second["signal_assertion_hash"]


def test_phase20h6_summary_quarantines_if_any_blocked() -> None:
    ok = evaluate_signaling_message(
        contract=_signaling_contract(),
        signal_message=_signal_message(),
        now=150.0,
    )
    bad = evaluate_signaling_message(
        contract=_signaling_contract(),
        signal_message=_signal_message(signaling_channel_id="wrong"),
        now=150.0,
    )
    summary = summarize_callback_and_signal_assertions(
        mission_id="mission_001",
        mission_run_id="run_001",
        assertions=[ok, bad],
    )
    assert summary["allowed_count"] == 1
    assert summary["blocked_count"] == 1
    assert summary["runtime_state"] == "callback_signal_quarantine"
    assert "signaling_channel_mismatch" in summary["blocked_reasons"]


def test_phase20h6_summary_hash_deterministic() -> None:
    ok = evaluate_signaling_message(
        contract=_signaling_contract(),
        signal_message=_signal_message(),
        now=150.0,
    )
    first = summarize_callback_and_signal_assertions(
        mission_id="mission_001",
        mission_run_id="run_001",
        assertions=[ok],
    )
    second = summarize_callback_and_signal_assertions(
        mission_id="mission_001",
        mission_run_id="run_001",
        assertions=[ok],
    )
    assert first["summary_hash"] == second["summary_hash"]
