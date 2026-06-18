from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def text():
    return APP.read_text()


def phase23c_block():
    src = text()
    start = src.index("PHASE 23C LOCK: Frontend Mission Preview Runtime Bridge")
    end = src.index("END PHASE 23C LOCK", start)
    return src[start:end]


def continue_runner_block():
    src = text()
    start = src.index("async function runAionPilotSafeWorkPreview")
    end = src.index("/* END PHASE 21T LOCK */", start)
    return src[start:end]


def test_phase23c_frontend_bridge_targets_backend_mission_preview_endpoint():
    block = phase23c_block()

    assert "function getAionPilotMissionPreviewUrl" in block
    assert "/api/local-node/aion/pilot/mission-preview" in block
    assert "async function fetchAionPilotMissionPreviewIntoPilotState" in block
    assert "applyAionPilotMissionPreviewPayload" in block
    assert 'method: "POST"' in block


def test_phase23c_payload_includes_business_context_inputs():
    block = phase23c_block()

    assert "brand_foundation_state" in block
    assert "marketing_form" in block
    assert "marketing_summary" in block
    assert "available_vault_requirements" in block
    assert "plan_text" in block
    assert "current_draft" in block


def test_phase23c_continue_runner_no_longer_uses_old_generic_output_first():
    block = continue_runner_block()

    assert "fetchAionPilotMissionPreviewIntoPilotState" in block
    assert "executeAndAppendAionPilotMissionMapStepOutput" in block
    assert "business_context_mission_map_ready" in block

    old_terms = [
        "Preparing ${plan.output_label",
        "getAionPilotOutputPreviewText(plan",
        "frontend_step1_artifact",
        "frontend_step1_receipt",
    ]

    for term in old_terms:
        assert term not in block


def test_phase23c_visible_output_mentions_task_map_context_and_vault_boundary():
    source = APP.read_text()

    assert "fetchAionPilotExecuteSafeStep" in source
    assert "executeAndAppendAionPilotMissionMapStepOutput" in source
    assert "raw credentials" not in source.lower()


def test_phase23c_bridge_does_not_add_live_side_effect_controls():
    block = phase23c_block() + continue_runner_block()

    forbidden = [
        "sendExternalMessage(",
        "createPayment(",
        "createBooking(",
        "deployProduction(",
        "publishPost(",
        "createEscrow(",
        "writeLiveChain(",
    ]

    for term in forbidden:
        assert term not in block
