from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text()


def test_phase21h_frontend_bridge_symbols_exist():
    assert "PHASE 21H LOCK: Pilot Artifact Preview Backend Bridge" in TEXT
    assert "getAionPilotArtifactPreviewUrl" in TEXT
    assert "buildAionPilotArtifactPreviewPayload" in TEXT
    assert "fetchAionPilotArtifactPreviewIntoPilotState" in TEXT
    assert "applyAionPilotArtifactPreviewPayload" in TEXT


def test_phase21h_safe_work_runner_calls_backend_artifact_preview():
    assert "fetchAionPilotArtifactPreviewIntoPilotState(plan, pilotState)" in TEXT
    assert "backend_artifact_preview" in TEXT
    assert "Backend artifact saved" in TEXT


def test_phase21h_frontend_uses_real_backend_artifact_fields():
    assert "backend_artifact_card" in TEXT
    assert "business_container_relative_path" in TEXT
    assert "artifact_receipt_hash" in TEXT
    assert "pilotState.artifact_path" in TEXT
