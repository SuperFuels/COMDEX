from backend.modules.aion_business.runtime.business_container_service import BusinessContainerService


WORKSPACE_ID = "costa-conexion"


def test_goal_engine_write_without_human_review_is_blocked():
    service = BusinessContainerService()
    service.ensure_canonical_containers(WORKSPACE_ID)

    result = service.write_goal_engine_container_record(
        WORKSPACE_ID,
        container_kind="goal_engine_state",
        record_type="goal",
        record={
            "goal_id": "goal_blocked_without_review",
            "title": "Should not persist without review",
        },
        approval_token=None,
    )

    assert result["ok"] is False
    assert result["blocked"] is True
    assert "human_review_required" in result["blocked_reasons"]


def test_goal_engine_write_with_human_review_token_persists_record():
    service = BusinessContainerService()
    service.ensure_canonical_containers(WORKSPACE_ID)

    result = service.write_goal_engine_container_record(
        WORKSPACE_ID,
        container_kind="goal_engine_state",
        record_type="goal",
        record={
            "goal_id": "goal_guarded_write_test",
            "title": "Persist only after human review",
        },
        approval_token={
            "status": "approved",
            "approved_by": "kevin",
            "approval_id": "approval_guarded_write_test",
        },
    )

    assert result["ok"] is True
    assert result["blocked"] is False
    assert result["container_kind"] == "goal_engine_state"
    assert result["record_type"] == "goal"

    payload = service.repository.load_dict(WORKSPACE_ID, "goal_engine_state")
    records = payload.get("records", [])

    assert any(
        item.get("record", {}).get("goal_id") == "goal_guarded_write_test"
        for item in records
    )


def test_goal_engine_memory_write_uses_memory_container_only():
    service = BusinessContainerService()
    service.ensure_canonical_containers(WORKSPACE_ID)

    result = service.write_goal_engine_container_record(
        WORKSPACE_ID,
        container_kind="goal_engine_memory",
        record_type="memory",
        record={
            "memory_id": "mem_guarded_write_test",
            "tier": "goal",
            "content_ref": "goal://guarded-write",
            "source_ref": "approval://guarded-write",
            "confidence": 0.8,
        },
        approval_token={
            "status": "approved",
            "approved_by": "kevin",
            "approval_id": "approval_memory_guarded_write_test",
        },
    )

    assert result["ok"] is True

    memory_payload = service.repository.load_dict(WORKSPACE_ID, "goal_engine_memory")
    state_payload = service.repository.load_dict(WORKSPACE_ID, "goal_engine_state")

    assert any(
        item.get("record", {}).get("memory_id") == "mem_guarded_write_test"
        for item in memory_payload.get("records", [])
    )

    assert not any(
        item.get("record", {}).get("memory_id") == "mem_guarded_write_test"
        for item in state_payload.get("records", [])
    )


def test_goal_engine_write_rejects_unknown_container_kind():
    service = BusinessContainerService()

    result = service.write_goal_engine_container_record(
        WORKSPACE_ID,
        container_kind="boardroom_snapshot",
        record_type="goal",
        record={"goal_id": "bad"},
        approval_token={"status": "approved"},
    )

    assert result["ok"] is False
    assert result["blocked"] is True
    assert "unsupported_goal_engine_container" in result["blocked_reasons"]


def test_goal_engine_write_records_audit_metadata():
    service = BusinessContainerService()
    service.ensure_canonical_containers(WORKSPACE_ID)

    result = service.write_goal_engine_container_record(
        WORKSPACE_ID,
        container_kind="goal_engine_evidence",
        record_type="evidence",
        record={
            "evidence_id": "ev_guarded_write_test",
            "source": "manual_confirmation",
            "confidence": 0.9,
        },
        approval_token={
            "status": "approved",
            "approved_by": "kevin",
            "approval_id": "approval_evidence_guarded_write_test",
        },
    )

    assert result["ok"] is True

    payload = service.repository.load_dict(WORKSPACE_ID, "goal_engine_evidence")
    match = next(
        item for item in payload.get("records", [])
        if item.get("record", {}).get("evidence_id") == "ev_guarded_write_test"
    )

    assert match["record_type"] == "evidence"
    assert match["approval"]["status"] == "approved"
    assert match["approval"]["approved_by"] == "kevin"
    assert match["dry_run_only"] is False
    assert match["would_write_container"] is True
