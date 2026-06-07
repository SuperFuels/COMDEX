from backend.services.aion_mission_mode.boardroom_replay_sync import (
    compile_boardroom_replay_packet,
    compile_replay_timeline,
    create_human_in_loop_marker,
    create_replay_event,
    create_visual_anchor,
)


def _event(index: int = 0, event_type: str = "mission_started"):
    return create_replay_event(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        event_type=event_type,
        event_index=index,
        source_hash=f"sha256:source{index}",
        consensus_hash="sha256:consensus",
        payload={"step": index},
    )


def test_phase20i2_creates_deterministic_replay_event() -> None:
    first = _event()
    second = _event()
    assert first["event_hash"] == second["event_hash"]


def test_phase20i2_rejects_invalid_replay_event_type() -> None:
    try:
        create_replay_event(
            mission_id="mission_001",
            mission_run_id="run_001",
            business_id="home_fixed",
            event_type="unknown",
            event_index=0,
            source_hash="sha256:source",
            consensus_hash="sha256:consensus",
        )
    except ValueError as exc:
        assert "invalid replay event type" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_phase20i2_compile_valid_timeline() -> None:
    e0 = _event(0)
    e1 = _event(1, "autonomous_step_completed")

    timeline = compile_replay_timeline(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        events=[e1, e0],
    )

    assert timeline["timeline_valid"] is True
    assert timeline["timeline_state"] == "boardroom_replay_ready"
    assert timeline["event_hashes"] == [e0["event_hash"], e1["event_hash"]]


def test_phase20i2_timeline_detects_duplicate_event_index() -> None:
    e0 = _event(0, "mission_started")
    e1 = _event(0, "mission_completed")

    timeline = compile_replay_timeline(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        events=[e0, e1],
    )

    assert timeline["timeline_valid"] is False
    assert "duplicate_event_index:0" in timeline["reasons"]


def test_phase20i2_timeline_detects_tampered_event() -> None:
    e0 = _event(0)
    e0["payload"] = {"tampered": True}

    timeline = compile_replay_timeline(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        events=[e0],
    )

    assert timeline["timeline_valid"] is False
    assert "event_hash_mismatch:0" in timeline["reasons"]


def test_phase20i2_create_visual_anchor() -> None:
    event = _event(0)
    anchor = create_visual_anchor(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        event_hash=event["event_hash"],
        anchor_type="timeline_marker",
        title="Mission started",
        summary="AION Pilot started the mission.",
        visible_state="completed",
        evidence_hashes=["sha256:b", "sha256:a"],
    )

    assert anchor["evidence_hashes"] == ["sha256:a", "sha256:b"]
    assert anchor["anchor_hash"].startswith("sha256:")


def test_phase20i2_rejects_invalid_visual_anchor_type() -> None:
    event = _event(0)
    try:
        create_visual_anchor(
            mission_id="mission_001",
            mission_run_id="run_001",
            business_id="home_fixed",
            event_hash=event["event_hash"],
            anchor_type="unknown",
            title="Bad",
            summary="Bad",
            visible_state="bad",
        )
    except ValueError as exc:
        assert "invalid visual anchor type" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_phase20i2_compile_boardroom_replay_packet() -> None:
    event = _event(0)
    timeline = compile_replay_timeline(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        events=[event],
    )
    anchor = create_visual_anchor(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        event_hash=event["event_hash"],
        anchor_type="timeline_marker",
        title="Mission started",
        summary="Started",
        visible_state="completed",
    )

    packet = compile_boardroom_replay_packet(
        timeline=timeline,
        visual_anchors=[anchor],
        consensus_hash="sha256:consensus",
        proof_hash="sha256:proof",
    )

    assert packet["allowed"] is True
    assert packet["packet_state"] == "boardroom_replay_packet_ready"
    assert packet["anchor_count"] == 1


def test_phase20i2_packet_blocks_anchor_not_in_timeline() -> None:
    event = _event(0)
    other_event = _event(1)
    timeline = compile_replay_timeline(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        events=[event],
    )
    anchor = create_visual_anchor(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        event_hash=other_event["event_hash"],
        anchor_type="timeline_marker",
        title="Other",
        summary="Other",
        visible_state="blocked",
    )

    packet = compile_boardroom_replay_packet(
        timeline=timeline,
        visual_anchors=[anchor],
        consensus_hash="sha256:consensus",
        proof_hash="sha256:proof",
    )

    assert packet["allowed"] is False
    assert "anchor_event_not_in_timeline" in packet["reasons"]


def test_phase20i2_packet_blocks_invalid_timeline() -> None:
    e0 = _event(0)
    e1 = _event(0, "mission_completed")
    timeline = compile_replay_timeline(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        events=[e0, e1],
    )

    packet = compile_boardroom_replay_packet(
        timeline=timeline,
        visual_anchors=[],
        consensus_hash="sha256:consensus",
        proof_hash="sha256:proof",
    )

    assert packet["allowed"] is False
    assert "timeline_invalid" in packet["reasons"]


def test_phase20i2_create_human_in_loop_marker() -> None:
    event = _event(0, "human_approval_required")

    marker = create_human_in_loop_marker(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        event_hash=event["event_hash"],
        marker_type="approval_required",
        required_action="Approve exact payload before deploy.",
        approval_or_task_hash="sha256:approval",
    )

    assert marker["marker_hash"].startswith("sha256:")
    assert marker["marker_type"] == "approval_required"


def test_phase20i2_rejects_invalid_human_marker_type() -> None:
    event = _event(0)
    try:
        create_human_in_loop_marker(
            mission_id="mission_001",
            mission_run_id="run_001",
            business_id="home_fixed",
            event_hash=event["event_hash"],
            marker_type="bad",
            required_action="Bad",
            approval_or_task_hash="sha256:x",
        )
    except ValueError as exc:
        assert "invalid human-in-loop marker type" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_phase20i2_packet_hash_is_deterministic() -> None:
    event = _event(0)
    timeline = compile_replay_timeline(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        events=[event],
    )

    first = compile_boardroom_replay_packet(
        timeline=timeline,
        visual_anchors=[],
        consensus_hash="sha256:consensus",
        proof_hash="sha256:proof",
    )
    second = compile_boardroom_replay_packet(
        timeline=timeline,
        visual_anchors=[],
        consensus_hash="sha256:consensus",
        proof_hash="sha256:proof",
    )

    assert first["packet_hash"] == second["packet_hash"]
