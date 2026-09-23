from backend.services.aion_mission_mode.pilot_filesystem_container_view import (
    PilotFilesystemContainerView,
    PilotFilesystemContractError,
)


def _artifact(**overrides):
    base = {
        "artifact_id": "artifact_pdf_001",
        "artifact_type": "pdf",
        "title": "Home Fixed Draft Brochure",
        "business_id": "home-fixed",
        "mission_id": "mission_001",
        "mission_run_id": "run_001",
        "step_id": "step_pdf",
        "container_path": "business/home-fixed/missions/mission_001/runs/run_001/artifacts/home_fixed_brochure.pdf",
        "artifact_hash": "sha256:artifact",
        "receipt_hash": "sha256:receipt",
        "status": "draft",
        "preview_status": "draft_only",
    }
    base.update(overrides)
    return base


def test_phase21e_builds_artifact_view_with_required_visibility_fields():
    view = PilotFilesystemContainerView.build_artifact_view(_artifact())

    assert view["artifact_type"] == "pdf"
    assert view["business_id"] == "home-fixed"
    assert view["mission_id"] == "mission_001"
    assert view["mission_run_id"] == "run_001"
    assert view["step_id"] == "step_pdf"
    assert view["container_path"].startswith("business/home-fixed/")
    assert view["artifact_hash"] == "sha256:artifact"
    assert view["receipt_hash"] == "sha256:receipt"
    assert view["status"] == "draft"
    assert view["preview_status"] == "draft_only"
    assert view["filesystem_view_hash"].startswith("sha256:")


def test_phase21e_buttons_are_read_model_buttons_not_live_actions():
    view = PilotFilesystemContainerView.build_artifact_view(_artifact())

    assert view["open_output_enabled"] is True
    assert view["download_output_enabled"] is True
    assert view["view_receipt_enabled"] is True
    assert view["live_external_action_enabled"] is False


def test_phase21e_blocks_artifact_outside_business_container():
    bad = _artifact(container_path="tmp/home_fixed_brochure.pdf")

    try:
        PilotFilesystemContainerView.build_artifact_view(bad)
        assert False, "expected container escape to be blocked"
    except PilotFilesystemContractError as exc:
        assert "escapes business mission run container" in str(exc)


def test_phase21e_blocks_parent_directory_traversal():
    bad = _artifact(
        container_path="business/home-fixed/missions/mission_001/runs/run_001/artifacts/../secret.pdf"
    )

    try:
        PilotFilesystemContainerView.build_artifact_view(bad)
        assert False, "expected traversal to be blocked"
    except PilotFilesystemContractError as exc:
        assert "parent traversal" in str(exc)


def test_phase21e_rejects_secret_like_fields():
    bad = _artifact(api_key="raw-secret")

    try:
        PilotFilesystemContainerView.build_artifact_view(bad)
        assert False, "expected secret field to be blocked"
    except PilotFilesystemContractError as exc:
        assert "secret-like field" in str(exc)


def test_phase21e_file_tree_is_read_model_only():
    tree = PilotFilesystemContainerView.build_file_tree(
        "home-fixed",
        [
            _artifact(artifact_id="a2", container_path="business/home-fixed/missions/mission_001/runs/run_001/artifacts/b.pdf"),
            _artifact(artifact_id="a1", container_path="business/home-fixed/missions/mission_001/runs/run_001/artifacts/a.pdf"),
        ],
    )

    assert tree["view_type"] == "pilot_business_container_file_tree"
    assert tree["read_model_only"] is True
    assert tree["raw_tool_execution_enabled"] is False
    assert tree["live_external_action_buttons_enabled"] is False
    assert tree["credential_visibility"] == "masked"
    assert tree["artifact_count"] == 2
    assert tree["artifacts"][0]["container_path"].endswith("/a.pdf")
    assert tree["file_tree_hash"].startswith("sha256:")


def test_phase21e_rejects_cross_business_artifacts():
    try:
        PilotFilesystemContainerView.build_file_tree(
            "home-fixed",
            [_artifact(business_id="other-business", container_path="business/other-business/missions/mission_001/runs/run_001/artifacts/a.pdf")],
        )
        assert False, "expected cross-business artifact to be blocked"
    except PilotFilesystemContractError as exc:
        assert "business_id does not match" in str(exc)


def test_phase21e_empty_tree_is_valid():
    tree = PilotFilesystemContainerView.build_empty_file_tree("home-fixed")

    assert tree["business_id"] == "home-fixed"
    assert tree["artifact_count"] == 0
    assert tree["artifacts"] == []
    assert tree["file_tree_hash"].startswith("sha256:")


def test_phase21e_artifact_hash_is_deterministic():
    one = PilotFilesystemContainerView.build_artifact_view(_artifact())
    two = PilotFilesystemContainerView.build_artifact_view(_artifact())

    assert one["filesystem_view_hash"] == two["filesystem_view_hash"]


def test_phase21e_tree_hash_is_deterministic():
    one = PilotFilesystemContainerView.build_file_tree("home-fixed", [_artifact()])
    two = PilotFilesystemContainerView.build_file_tree("home-fixed", [_artifact()])

    assert one["file_tree_hash"] == two["file_tree_hash"]
