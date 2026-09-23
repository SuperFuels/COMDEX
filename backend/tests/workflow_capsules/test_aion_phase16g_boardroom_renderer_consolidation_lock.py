from pathlib import Path
import re

APP = Path("desktop/mac/src/app.js")
CSS = Path("desktop/mac/src/styles.css")
DOC = Path("docs/rfc/aion_phase16g_boardroom_renderer_consolidation_lock.tex")


def _function_count(text: str, name: str) -> int:
    return text.count(f"function {name}(")


def _deprecated_function_count(text: str, name: str) -> int:
    needle = f"function __deprecatedPhase16Duplicate_"
    return sum(
        1
        for line in text.splitlines()
        if needle in line and f"_{name}(" in line
    )


def _extract_last_function(text: str, name: str) -> str:
    marker = f"function {name}("
    start = text.rfind(marker)
    assert start != -1, f"missing {name}"

    next_start = text.find("\nfunction ", start + len(marker))
    end_marker = text.find("/* END PHASE", start)
    candidates = [x for x in [next_start, end_marker] if x != -1]
    end = min(candidates) if candidates else len(text)

    return text[start:end]


def test_phase16g_lock_markers_exist():
    text = APP.read_text()
    assert "PHASE 16G LOCK: Boardroom renderer consolidation" in text
    assert DOC.exists()


def test_phase16g_has_single_active_founder_demo_renderer_and_handler():
    text = APP.read_text()
    assert _function_count(text, "renderBoardroomFounderDemoLoopPanel") == 1
    assert _function_count(text, "handleBoardroomFounderDemoPreviewAction") == 1


def test_phase16g_has_single_active_frontpage_support_renderers():
    text = APP.read_text()
    assert _function_count(text, "renderBoardroomA2ASetupPanel") == 1
    assert _function_count(text, "renderBoardroomWorkflowWidgetPanel") == 1
    assert _function_count(text, "renderBoardroomProofReplayPanel") == 1


def test_phase16g_founder_demo_active_renderer_is_functional_phase16f_version():
    text = APP.read_text()
    panel = _extract_last_function(text, "renderBoardroomFounderDemoLoopPanel")

    for phrase in [
        "Run Home Fixed preview",
        "Open human review",
        "View proof receipt",
        "Replay boardroom trace",
        "data-aion-founder-demo-active-state",
        "data-founder-demo-action",
        "renderAionFounderDemoStepButton",
    ]:
        assert phrase in panel


def test_phase16g_action_handler_preserves_side_effect_guards():
    text = APP.read_text()
    handler = _extract_last_function(text, "handleBoardroomFounderDemoPreviewAction")

    for phrase in [
        "booking_created: false",
        "payment_created: false",
        "escrow_created: false",
        "external_message_sent: false",
        "live_chain_write: false",
        "live_execution_allowed: false",
        "human_review_required: true",
        "replay_hash_available: true",
    ]:
        assert phrase in handler

def test_phase16g_missing_safety_strip_helper_is_defined():
    text = APP.read_text()
    assert "function renderBoardroomFounderDemoSafetyStrip" in text
    assert "renderBoardroomFounderDemoSafetyStrip(sideEffectGuards)" in text
    assert "data-aion-founder-demo-safety-strip" in text

def test_phase16g_proof_replay_never_joins_optional_payload_arrays_directly():
    text = APP.read_text()
    panel = _extract_last_function(text, "renderBoardroomProofReplayPanel")

    assert "const routeSteps = safeArray(" in panel
    assert "const guardLabels = safeArray(" in panel
    assert "const legacyPhase16DMarkers = safeArray(" in panel

    forbidden = [
        "payload.route_steps.join",
        "payload.steps.join",
        "payload.side_effects.join",
        "payload.guards.join",
        "payload.proof_route.join",
    ]
    for item in forbidden:
        assert item not in panel

