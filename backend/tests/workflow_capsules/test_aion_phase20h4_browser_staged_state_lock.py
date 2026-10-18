import pytest

from backend.services.aion_mission_mode.browser_staged_state import (
    assert_staged_state_commit_allowed,
    canonical_payload_hash,
    commit_staged_state,
    create_staged_browser_state,
    create_staged_state_receipt,
    transition_staged_state,
)


def _payload():
    return {
        "domain": "homefixed.es",
        "cost": 11.99,
        "provider": "domain_provider",
    }


def _state(now: float = 100.0, expires: float = 200.0):
    return create_staged_browser_state(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="business_001",
        provider="domain_provider",
        browser_worker_id="browser_001",
        provider_context_hash="sha256:context",
        browser_session_hash="sha256:session",
        action_type="prepare_domain_purchase",
        target_url="https://godaddy.com/cart",
        staged_payload=_payload(),
        staged_state_expires_at=expires,
        now=now,
    )


def _approval_for(state):
    return {
        "approval_hash": "sha256:approval",
        "approved_payload_hash": state["staged_payload_hash"],
    }


def test_phase20h4_canonical_payload_hash_is_deterministic() -> None:
    assert canonical_payload_hash(_payload()) == canonical_payload_hash(_payload())


def test_phase20h4_staged_state_hash_is_deterministic() -> None:
    assert _state()["browser_session_staged_state_hash"] == _state()["browser_session_staged_state_hash"]


def test_phase20h4_state_created_as_staged_before_expiry() -> None:
    state = _state(now=100.0, expires=200.0)
    assert state["staged_state"] == "staged"
    assert state["requires_restaging"] is False


def test_phase20h4_state_created_as_expired_after_expiry() -> None:
    state = _state(now=300.0, expires=200.0)
    assert state["staged_state"] == "expired"
    assert state["requires_restaging"] is True


def test_phase20h4_commit_allowed_for_exact_unexpired_approved_payload() -> None:
    state = _state()
    approval = _approval_for(state)
    result = assert_staged_state_commit_allowed(
        staged_state=state,
        current_payload=_payload(),
        approval_hash=approval["approval_hash"],
        approved_payload_hash=approval["approved_payload_hash"],
        now=150.0,
    )
    assert result["commit_allowed"] is True


def test_phase20h4_missing_approval_blocks_commit() -> None:
    state = _state()
    result = assert_staged_state_commit_allowed(
        staged_state=state,
        current_payload=_payload(),
        approval_hash=None,
        approved_payload_hash=None,
        now=150.0,
    )
    assert result["commit_allowed"] is False
    assert "missing_approval_hash" in result["reasons"]
    assert "missing_approved_payload_hash" in result["reasons"]


def test_phase20h4_expired_state_blocks_commit() -> None:
    state = _state()
    approval = _approval_for(state)
    result = assert_staged_state_commit_allowed(
        staged_state=state,
        current_payload=_payload(),
        approval_hash=approval["approval_hash"],
        approved_payload_hash=approval["approved_payload_hash"],
        now=250.0,
    )
    assert result["commit_allowed"] is False
    assert "staged_state_expired" in result["reasons"]


def test_phase20h4_payload_mutation_blocks_commit() -> None:
    state = _state()
    approval = _approval_for(state)
    changed_payload = dict(_payload())
    changed_payload["cost"] = 14.99
    result = assert_staged_state_commit_allowed(
        staged_state=state,
        current_payload=changed_payload,
        approval_hash=approval["approval_hash"],
        approved_payload_hash=approval["approved_payload_hash"],
        now=150.0,
    )
    assert result["commit_allowed"] is False
    assert "staged_payload_mutated" in result["reasons"]


def test_phase20h4_approved_payload_hash_mismatch_blocks_commit() -> None:
    state = _state()
    result = assert_staged_state_commit_allowed(
        staged_state=state,
        current_payload=_payload(),
        approval_hash="sha256:approval",
        approved_payload_hash="sha256:wrong",
        now=150.0,
    )
    assert result["commit_allowed"] is False
    assert "approved_payload_hash_mismatch" in result["reasons"]


def test_phase20h4_abandoned_state_blocks_commit() -> None:
    state = transition_staged_state(
        staged_state=_state(),
        next_state="abandoned",
        now=120.0,
        reason="user_cancelled",
    )
    approval = _approval_for(state)
    result = assert_staged_state_commit_allowed(
        staged_state=state,
        current_payload=_payload(),
        approval_hash=approval["approval_hash"],
        approved_payload_hash=approval["approved_payload_hash"],
        now=150.0,
    )
    assert result["commit_allowed"] is False
    assert "staged_state_not_committable" in result["reasons"]
    assert "restaging_required" in result["reasons"]


def test_phase20h4_transition_unknown_state_rejected() -> None:
    with pytest.raises(ValueError):
        transition_staged_state(
            staged_state=_state(),
            next_state="unknown",
            now=120.0,
            reason="bad_state",
        )


def test_phase20h4_commit_state_changes_hash_and_sets_committed() -> None:
    state = _state()
    approval = _approval_for(state)
    assertion = assert_staged_state_commit_allowed(
        staged_state=state,
        current_payload=_payload(),
        approval_hash=approval["approval_hash"],
        approved_payload_hash=approval["approved_payload_hash"],
        now=150.0,
    )
    committed = commit_staged_state(
        staged_state=state,
        commit_assertion=assertion,
        now=160.0,
        provider_response_hash="sha256:provider_response",
    )

    assert committed["staged_state"] == "committed"
    assert committed["commit_count"] == 1
    assert committed["browser_session_staged_state_hash"] != state["browser_session_staged_state_hash"]


def test_phase20h4_committed_state_cannot_commit_twice() -> None:
    state = _state()
    approval = _approval_for(state)
    assertion = assert_staged_state_commit_allowed(
        staged_state=state,
        current_payload=_payload(),
        approval_hash=approval["approval_hash"],
        approved_payload_hash=approval["approved_payload_hash"],
        now=150.0,
    )
    committed = commit_staged_state(
        staged_state=state,
        commit_assertion=assertion,
        now=160.0,
        provider_response_hash="sha256:provider_response",
    )

    second = assert_staged_state_commit_allowed(
        staged_state=committed,
        current_payload=_payload(),
        approval_hash=approval["approval_hash"],
        approved_payload_hash=approval["approved_payload_hash"],
        now=170.0,
    )

    assert second["commit_allowed"] is False
    assert "staged_state_not_committable" in second["reasons"]
    assert "staged_state_already_committed" in second["reasons"]


def test_phase20h4_blocked_assertion_cannot_commit() -> None:
    state = _state()
    assertion = assert_staged_state_commit_allowed(
        staged_state=state,
        current_payload={"domain": "changed"},
        approval_hash=None,
        approved_payload_hash=None,
        now=150.0,
    )
    with pytest.raises(ValueError):
        commit_staged_state(
            staged_state=state,
            commit_assertion=assertion,
            now=160.0,
            provider_response_hash="sha256:provider_response",
        )


def test_phase20h4_receipt_created_for_committed_state() -> None:
    state = _state()
    approval = _approval_for(state)
    assertion = assert_staged_state_commit_allowed(
        staged_state=state,
        current_payload=_payload(),
        approval_hash=approval["approval_hash"],
        approved_payload_hash=approval["approved_payload_hash"],
        now=150.0,
    )
    committed = commit_staged_state(
        staged_state=state,
        commit_assertion=assertion,
        now=160.0,
        provider_response_hash="sha256:provider_response",
    )
    receipt = create_staged_state_receipt(committed_state=committed)
    assert receipt["receipt_hash"].startswith("sha256:")


def test_phase20h4_receipt_rejected_for_uncommitted_state() -> None:
    with pytest.raises(ValueError):
        create_staged_state_receipt(committed_state=_state())


def test_phase20h4_commit_assertion_hash_is_deterministic() -> None:
    state = _state()
    approval = _approval_for(state)
    first = assert_staged_state_commit_allowed(
        staged_state=state,
        current_payload=_payload(),
        approval_hash=approval["approval_hash"],
        approved_payload_hash=approval["approved_payload_hash"],
        now=150.0,
    )
    second = assert_staged_state_commit_allowed(
        staged_state=state,
        current_payload=_payload(),
        approval_hash=approval["approval_hash"],
        approved_payload_hash=approval["approved_payload_hash"],
        now=150.0,
    )
    assert first["commit_assertion_hash"] == second["commit_assertion_hash"]
