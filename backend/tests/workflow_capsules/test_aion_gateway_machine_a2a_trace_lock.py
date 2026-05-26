from backend.modules.aion_gateway.machine_trace import (
    A2A_TRACE_SCHEMA_VERSION,
    build_machine_a2a_trace,
)


def _job():
    return {
        "job_id": "job_001",
        "business_id": "biz_costa_001",
        "workflow_run_id": "run_001",
        "goal_id": "goal_001",
        "current_stage": "scheduled",
        "next_expected_event": "provider_arrival",
        "blocked_reason": "",
    }


def test_machine_a2a_trace_builds_canonical_trace():
    trace = build_machine_a2a_trace(
        fulfilment_job=_job(),
        evidence_state={"evidence_count": 2, "job_proof_hash": "hash_abc"},
        approval_state={"requires_human_review": True, "status": "pending"},
        exception_state={"status": "none"},
        settlement_readiness_state={"payment_ready": False},
        proof_commitment_state={"committed": False},
    )

    assert trace["schema_version"] == A2A_TRACE_SCHEMA_VERSION
    assert trace["trace_type"] == "aion_machine_a2a_trace"
    assert trace["job_id"] == "job_001"
    assert trace["business_id"] == "biz_costa_001"
    assert trace["workflow_run_id"] == "run_001"
    assert trace["goal_id"] == "goal_001"
    assert trace["current_stage"] == "scheduled"
    assert trace["next_expected_event"] == "provider_arrival"


def test_machine_a2a_trace_returns_required_state_sections():
    trace = build_machine_a2a_trace(
        fulfilment_job=_job(),
        evidence_state={"job_proof_hash": "hash_abc"},
        approval_state={"status": "pending"},
        exception_state={"status": "none"},
        settlement_readiness_state={"payment_ready": False},
        proof_commitment_state={"status": "not_committed"},
    )

    assert trace["evidence_state"]["job_proof_hash"] == "hash_abc"
    assert trace["approval_state"]["status"] == "pending"
    assert trace["exception_state"]["status"] == "none"
    assert trace["settlement_readiness_state"]["payment_ready"] is False
    assert trace["proof_commitment_state"]["status"] == "not_committed"


def test_machine_a2a_trace_is_dry_run_and_non_mutating():
    trace = build_machine_a2a_trace(fulfilment_job=_job())

    assert trace["dry_run_only"] is True
    assert trace["would_execute_goal_engine"] is False
    assert trace["would_write_externally"] is False
    assert trace["would_mutate_business_state"] is False
    assert trace["would_grant_permission"] is False


def test_machine_a2a_trace_hash_is_stable_for_same_content():
    first = build_machine_a2a_trace(
        fulfilment_job=_job(),
        evidence_state={"b": 2, "a": 1},
    )
    second = build_machine_a2a_trace(
        fulfilment_job=dict(reversed(list(_job().items()))),
        evidence_state={"a": 1, "b": 2},
    )

    assert first["machine_trace_hash"] == second["machine_trace_hash"]


def test_machine_a2a_trace_hash_changes_when_stage_changes():
    first_job = _job()
    second_job = _job()
    second_job["current_stage"] = "completed"

    first = build_machine_a2a_trace(fulfilment_job=first_job)
    second = build_machine_a2a_trace(fulfilment_job=second_job)

    assert first["machine_trace_hash"] != second["machine_trace_hash"]


def test_machine_a2a_trace_preserves_provider_assignment_and_eta():
    trace = build_machine_a2a_trace(
        fulfilment_job=_job(),
        provider_assignment={"provider_id": "provider_001", "status": "assigned"},
        eta={"arrival_window": "2026-05-27T10:00:00Z/2026-05-27T12:00:00Z"},
    )

    assert trace["provider_assignment"]["provider_id"] == "provider_001"
    assert trace["eta"]["arrival_window"]


def test_machine_a2a_trace_preserves_human_boardroom_alignment():
    trace = build_machine_a2a_trace(
        fulfilment_job=_job(),
        human_boardroom_alignment={
            "human_boardroom_stage": "scheduled",
            "drift_detected": False,
        },
    )

    assert trace["human_boardroom_alignment"]["human_boardroom_stage"] == "scheduled"
    assert trace["human_boardroom_alignment"]["drift_detected"] is False
