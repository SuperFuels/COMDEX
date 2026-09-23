from pathlib import Path

APP = Path("desktop/mac/src/app.js")
CSS = Path("desktop/mac/src/styles.css")

def test_goal_engine_demo_payload_hydrates_visibility_audit_sections():
    text = APP.read_text()

    block = text[
        text.index("function buildAionGoalEngineVisibleDemoPayloadV1"):
        text.index("function renderAionGoalEngineContainerProjectionV1")
    ]

    for token in [
        "provider_capability_manifest",
        "goal_engine_container_projection",
        "provider_audit",
        "memory_runtime_summary",
        "evidence_pointer_previews",
        "variant_outcome_score_preview",
        "experiment_result_evidence_preview",
    ]:
        assert token in block

def test_goal_engine_demo_payload_contains_provider_manifest_and_container_projection_contracts():
    text = APP.read_text()

    block = text[
        text.index("function buildAionGoalEngineVisibleDemoPayloadV1"):
        text.index("function renderAionGoalEngineContainerProjectionV1")
    ]

    assert "aion.business.provider_capability_manifest.v1" in block
    assert "aion.business.goal_engine_container_projection.v1" in block
    assert "business_containers" in block
    assert "boardroom_projection_only: true" in block

def test_goal_engine_demo_payload_contains_viewer_contracts():
    text = APP.read_text()

    block = text[
        text.index("function buildAionGoalEngineVisibleDemoPayloadV1"):
        text.index("function renderAionGoalEngineContainerProjectionV1")
    ]

    assert "aion.goal_engine.evidence_pointer.v1" in block
    assert "aion.goal_engine.variant_outcome_score.v1" in block
    assert "aion.goal_engine.experiment_result_evidence.v1" in block
    assert "manual_decision_required" in block
    assert "winner_declared: false" in block

def test_visibility_audit_softened_css_exists():
    text = CSS.read_text()

    assert "AION-GOAL-ENGINE-VISIBILITY-AUDIT-SOFTEN-V1:START" in text
    assert ".aion-boardroom-goal-engine-visibility-audit" in text
    assert "background: #ffffff" in text
