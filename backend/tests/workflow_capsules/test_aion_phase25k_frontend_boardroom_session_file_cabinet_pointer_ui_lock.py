from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase25k_frontend_has_boardroom_session_artifact_preview_key():
    assert "AION_BOARDROOM_SESSION_ARTIFACTS_STORAGE_KEY" in TEXT
    assert "aion.boardroomCouncil.sessionArtifacts.v1" in TEXT


def test_phase25k_frontend_builds_business_container_packet():
    assert "function buildAionBoardroomSessionPacket" in TEXT
    assert "aion.boardroom_session_artifact_payload.v0" in TEXT
    assert "business_context_packet" in TEXT
    assert "department_intelligence_packet" in TEXT
    assert "department_context_packet" in TEXT
    assert "user_added_context" in TEXT
    assert "previous_session_refs" in TEXT
    assert "approval_gated: true" in TEXT
    assert "live_external_side_effects_performed: false" in TEXT


def test_phase25k_frontend_uses_business_container_target_not_loose_file():
    assert "function commitAionBoardroomSessionArtifactPreview" in TEXT
    assert 'sub_container: "pilot"' in TEXT
    assert 'artifact_type: "boardroom_session"' in TEXT
    assert "business_containers/${businessContainerId}/pilot/${artifactId}.json" in TEXT
    assert "session_vfs_only: false" in TEXT
    assert "file_cabinet_role: \"index_pointer_only\"" in TEXT


def test_phase25k_file_cabinet_has_boardroom_session_pointer_folders():
    assert "function addAionBoardroomSessionPointerToFileCabinet" in TEXT
    assert "folder_boardroom" in TEXT
    assert "folder_boardroom_sessions" in TEXT
    assert "folder_boardroom_business_plans" in TEXT
    assert "folder_boardroom_department_plans" in TEXT
    assert "folder_boardroom_evidence_receipts" in TEXT
    assert 'type: "business_container_artifact"' in TEXT
    assert 'source_of_truth: "business_container"' in TEXT


def test_phase25k_file_cabinet_renders_business_container_artifact_rows():
    assert "data-aion-file-cabinet-open-artifact" in TEXT
    assert 'node.type === "business_container_artifact"' in TEXT
    assert "Business container artifact" in TEXT


def test_phase25k_terminal_save_uses_artifact_preview_and_previous_refs():
    assert "commitAionBoardroomSessionArtifactPreview(sessionType)" in TEXT
    assert "await persistAionBoardroomSessionArtifactV2(record)" in TEXT
    assert "Boardroom minutes saved to the business container" in TEXT
    assert "window.__aionVisibleAskBoardResult" in TEXT
    assert "&gt; Previous boardroom sessions:" in TEXT
