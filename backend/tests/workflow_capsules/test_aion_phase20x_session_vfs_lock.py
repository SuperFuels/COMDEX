import pytest

from backend.services.aion_mission_mode.session_vfs import (
    ALLOWED_SESSION_SUBSPACES,
    SessionVFSContext,
    build_cross_mission_transfer_approval,
    can_read_session_vfs_record,
    can_transfer_between_missions,
    session_namespace,
    session_vfs_path,
    validate_no_live_secrets,
    vector_workspace_id,
    write_session_vfs_record,
)


def make_ctx(**overrides) -> SessionVFSContext:
    data = {
        "mission_id": "mission_home_fixed_lead_campaign_001",
        "mission_run_id": "run_001",
        "business_id": "home_fixed",
        "mission_hash": "sha256:missionhash",
    }
    data.update(overrides)
    return SessionVFSContext(**data)


def test_phase20x_allowed_subspaces_are_locked() -> None:
    assert ALLOWED_SESSION_SUBSPACES == {
        "drafts",
        "tmp",
        "vectors",
        "repair",
        "previews",
        "logs",
        "receipts",
    }


def test_phase20x_namespace_is_deterministic_and_mission_scoped() -> None:
    first = session_namespace(make_ctx())
    second = session_namespace(make_ctx())

    other = session_namespace(make_ctx(mission_run_id="run_002"))

    assert first == second
    assert first != other


def test_phase20x_vector_workspace_is_salted_by_mission_hash() -> None:
    first = vector_workspace_id(make_ctx(mission_hash="sha256:a"))
    second = vector_workspace_id(make_ctx(mission_hash="sha256:b"))

    assert first.startswith("vector_")
    assert first != second


def test_phase20x_session_path_contains_mission_scope_and_namespace() -> None:
    ctx = make_ctx()
    path = session_vfs_path(ctx=ctx, subspace="drafts", name="Advert Draft")

    assert path["mission_id"] == ctx.mission_id
    assert path["mission_run_id"] == ctx.mission_run_id
    assert f"/{ctx.mission_id}/{ctx.mission_run_id}/" in path["relative_path"]
    assert "/drafts/advert_draft.json" in path["relative_path"]
    assert path["path_hash"].startswith("sha256:")


def test_phase20x_rejects_invalid_subspace() -> None:
    with pytest.raises(ValueError):
        session_vfs_path(ctx=make_ctx(), subspace="global", name="bad")


def test_phase20x_write_record_is_session_vfs_only() -> None:
    record = write_session_vfs_record(
        ctx=make_ctx(),
        subspace="drafts",
        name="draft",
        payload={"draft": "safe"},
    )

    assert record["storage_state"] == "session_vfs_draft"
    assert record["session_vfs_only"] is True
    assert record["record_hash"].startswith("sha256:")


def test_phase20x_blocks_live_secret_payloads() -> None:
    assert validate_no_live_secrets({"draft": "ok"}) is True
    assert validate_no_live_secrets({"nested": {"api_key": "secret"}}) is False
    assert validate_no_live_secrets({"items": [{"prod_database_url": "postgres://prod"}]}) is False


def test_phase20x_write_rejects_live_secret_payload() -> None:
    with pytest.raises(ValueError):
        write_session_vfs_record(
            ctx=make_ctx(),
            subspace="tmp",
            name="bad",
            payload={"token": "secret-token"},
        )


def test_phase20x_same_mission_can_read_own_record() -> None:
    ctx = make_ctx()
    record = write_session_vfs_record(
        ctx=ctx,
        subspace="repair",
        name="repair_payload",
        payload={"draft": "safe"},
    )

    assert can_read_session_vfs_record(ctx=ctx, record=record) is True


def test_phase20x_other_mission_cannot_read_record_by_default() -> None:
    source_ctx = make_ctx()
    other_ctx = make_ctx(mission_id="mission_other", mission_run_id="run_999")

    record = write_session_vfs_record(
        ctx=source_ctx,
        subspace="repair",
        name="repair_payload",
        payload={"draft": "safe"},
    )

    assert can_read_session_vfs_record(ctx=other_ctx, record=record) is False


def test_phase20x_cross_mission_transfer_requires_approval() -> None:
    source_ctx = make_ctx()
    target_ctx = make_ctx(mission_id="mission_target", mission_run_id="run_002")

    record = write_session_vfs_record(
        ctx=source_ctx,
        subspace="drafts",
        name="draft",
        payload={"draft": "safe"},
    )

    assert can_transfer_between_missions(source_record=record, target_ctx=target_ctx) is False

    approval = build_cross_mission_transfer_approval(
        source_mission_id=source_ctx.mission_id,
        target_mission_id=target_ctx.mission_id,
        approved_by="kevin_robinson",
        reason="governed transfer into follow-up mission",
        approved=True,
    )

    assert can_transfer_between_missions(
        source_record=record,
        target_ctx=target_ctx,
        approval=approval,
    ) is True


def test_phase20x_cross_mission_transfer_rejects_wrong_approval_target() -> None:
    source_ctx = make_ctx()
    target_ctx = make_ctx(mission_id="mission_target", mission_run_id="run_002")

    record = write_session_vfs_record(
        ctx=source_ctx,
        subspace="drafts",
        name="draft",
        payload={"draft": "safe"},
    )

    approval = build_cross_mission_transfer_approval(
        source_mission_id=source_ctx.mission_id,
        target_mission_id="wrong_target",
        approved_by="kevin_robinson",
        reason="wrong",
        approved=True,
    )

    assert can_transfer_between_missions(
        source_record=record,
        target_ctx=target_ctx,
        approval=approval,
    ) is False
