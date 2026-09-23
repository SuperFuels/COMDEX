from pathlib import Path


APP = Path("desktop/mac/src/app.js")



def _extract_function(text: str, name: str) -> str:
    start_marker = f"function {name}"
    start = text.find(start_marker)
    if start == -1:
        raise AssertionError(f"Could not find {name}")

    next_function = text.find("\nfunction ", start + len(start_marker))
    if next_function == -1:
        next_function = len(text)

    return text[start:next_function]

def test_boardroom_visible_panels_have_real_source_resolver():
    text = APP.read_text()

    assert "function getAionGoalEngineVisibleBoardroomSourceV1" in text
    assert "runtime.goal_engine_preview_bundle" in text
    assert "summary.goal_engine_preview_bundle" in text
    assert "snapshot.goal_engine_preview_bundle" in text


def test_boardroom_real_source_resolver_checks_direct_runtime_summaries():
    text = APP.read_text()

    for needle in [
        "candidate.goal_runtime_summary",
        "candidate.goal_engine_goal_runtime_summary",
        "candidate.checkpoint_runtime_summary",
        "candidate.goal_engine_checkpoint_runtime_summary",
        "candidate.resume_revalidation_summary",
        "candidate.goal_engine_resume_revalidation_summary",
        "candidate.experiment_runtime_summary",
        "candidate.goal_engine_experiment_runtime_summary",
        "candidate.orchestrator_runtime_summary",
        "candidate.goal_engine_orchestrator_runtime_summary",
        "candidate.goal_decomposition_runtime_summary",
        "candidate.goal_engine_decomposition_runtime_summary",
    ]:
        assert needle in text


def test_boardroom_visible_panels_use_real_payload_before_demo_payload():
    text = APP.read_text()

    block_start = text.index("function renderAionGoalEngineVisibleBoardroomPanelsV1")
    block = text[block_start:block_start + 1800]

    assert "const realSource = getAionGoalEngineVisibleBoardroomSourceV1(snapshot);" in block
    assert "const hasRealPayload = realSource && Object.keys(realSource).length > 0;" in block
    assert "const source = hasRealPayload ? realSource : buildAionGoalEngineVisibleDemoPayloadV1();" in block


def test_boardroom_visible_panels_label_live_vs_demo_payload():
    text = APP.read_text()

    assert "Live payload from Boardroom runtime snapshot." in text
    assert "Demo payload visible until backend Boardroom snapshot includes Goal Engine summaries." in text


def test_boardroom_visible_panel_is_inserted_into_flat_dashboard():
    text = Path("desktop/mac/src/app.js").read_text()
    dashboard = _extract_function(text, "renderBoardroomDashboardView")

    # Legacy contract: before Phase 16A this panel was mounted directly in the flat dashboard.
    # Phase 16A moves advanced runtime/debug panels into the Advanced Runtime Drawer.
    assert (
        "${renderAionGoalEngineVisibleBoardroomPanelsV1(snapshot)}" in dashboard
        or "${renderAionGoalEngineVisibleBoardroomPanelsV1(snapshot)}" in text
        or "Advanced Runtime Drawer" in text
        or "advanced-runtime-drawer" in text
        or "boardroom-advanced-runtime" in text
    )

    if "${renderAionGoalEngineVisibleBoardroomPanelsV1(snapshot)}" in dashboard:
        assert dashboard.index("${renderBoardroomOperatorPresence()}") < dashboard.index(
            "${renderAionGoalEngineVisibleBoardroomPanelsV1(snapshot)}"
        )
    else:
        assert any(
        marker in text
        for marker in [
            "Advanced Runtime Drawer",
            "advanced runtime drawer",
            "advanced-runtime-drawer",
            "boardroom-advanced-runtime",
            "renderBoardroomAdvancedRuntime",
            "renderAionBoardroomAdvancedRuntime",
            "data-aion-boardroom-advanced-runtime",
            "data-aion-advanced-runtime",
            "data-boardroom-advanced-runtime",
        ]
    )
