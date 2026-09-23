from backend.modules.aion_business.runtime.business_container_service import BusinessContainerService


WORKSPACE_ID = "costa-conexion"


def _approval():
    return {
        "status": "approved",
        "approved_by": "kevin",
        "approval_id": "approval_projection_records_test",
    }


def test_goal_engine_container_projection_reads_persisted_records():
    service = BusinessContainerService()
    service.ensure_canonical_containers(WORKSPACE_ID)

    service.write_goal_engine_container_record(
        WORKSPACE_ID,
        container_kind="goal_engine_state",
        record_type="goal",
        record={
            "goal_id": "goal_projection_test",
            "status": "active",
            "title": "Projection test goal",
        },
        approval_token=_approval(),
    )

    service.write_goal_engine_container_record(
        WORKSPACE_ID,
        container_kind="goal_engine_loops",
        record_type="loop",
        record={
            "loop_id": "loop_projection_test",
            "goal_id": "goal_projection_test",
            "bounded": True,
            "iteration": 3,
        },
        approval_token=_approval(),
    )

    service.write_goal_engine_container_record(
        WORKSPACE_ID,
        container_kind="goal_engine_outcomes",
        record_type="outcome",
        record={
            "outcome_id": "outcome_projection_test",
            "goal_id": "goal_projection_test",
            "outcome_score": 0.72,
            "status": "pending_evidence",
        },
        approval_token=_approval(),
    )

    projection = service.build_goal_engine_business_container_projection(WORKSPACE_ID)

    assert projection["schema_version"] == "aion.business.goal_engine_container_projection.v1"
    assert projection["trace_type"] == "goal_engine_container_projection"
    assert projection["workspace_id"] == WORKSPACE_ID

    assert projection["goal_count"] >= 1
    assert projection["active_goal_count"] >= 1
    assert projection["loop_count"] >= 1
    assert projection["bounded_loop_count"] >= 1
    assert projection["outcome_count"] >= 1

    assert projection["persistent_truth_source"] == "business_containers"
    assert projection["boardroom_projection_only"] is True
    assert projection["dry_run_only"] is False


def test_goal_engine_container_projection_counts_memory_and_evidence():
    service = BusinessContainerService()
    service.ensure_canonical_containers(WORKSPACE_ID)

    service.write_goal_engine_container_record(
        WORKSPACE_ID,
        container_kind="goal_engine_memory",
        record_type="memory",
        record={
            "memory_id": "mem_projection_test",
            "tier": "goal",
            "confidence": 0.88,
        },
        approval_token=_approval(),
    )

    service.write_goal_engine_container_record(
        WORKSPACE_ID,
        container_kind="goal_engine_evidence",
        record_type="evidence",
        record={
            "evidence_id": "ev_projection_test",
            "verified": True,
            "confidence": 0.91,
        },
        approval_token=_approval(),
    )

    projection = service.build_goal_engine_business_container_projection(WORKSPACE_ID)

    assert projection["memory_count"] >= 1
    assert projection["evidence_count"] >= 1
    assert projection["verified_evidence_count"] >= 1


def test_boardroom_payload_includes_goal_engine_container_projection():
    service = BusinessContainerService()
    payload = service.get_boardroom_payload(WORKSPACE_ID)

    assert "goal_engine_container_projection" in payload

    projection = payload["goal_engine_container_projection"]
    assert projection["trace_type"] == "goal_engine_container_projection"
    assert projection["persistent_truth_source"] == "business_containers"
    assert projection["boardroom_projection_only"] is True


def test_projection_does_not_store_preview_bundle_as_truth():
    service = BusinessContainerService()
    projection = service.build_goal_engine_business_container_projection(WORKSPACE_ID)

    assert "goal_engine_preview_bundle" not in projection
    assert "PreviewBundle" not in str(projection)
    assert projection["persistent_truth_source"] == "business_containers"
