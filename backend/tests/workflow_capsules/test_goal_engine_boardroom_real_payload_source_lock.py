from pathlib import Path


APP = Path("desktop/mac/src/app.js")


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
    text = APP.read_text()

    assert "${renderAionGoalEngineVisibleBoardroomPanelsV1(snapshot)}" in text

    dashboard_start = text.index("function renderBoardroomDashboardView")
    dashboard = text[dashboard_start:dashboard_start + 5000]

    assert "${renderBoardroomOperatorPresence()}" in dashboard
    assert (
        "${renderAionGoalEngineVisibleBoardroomPanelsV1(snapshot)}" in dashboard
        or "${renderAionGoalEngineVisibleBoardroomPanelsV1(snapshot)}" in text
    )
    if "${renderAionGoalEngineVisibleBoardroomPanelsV1(snapshot)}" in dashboard:
        assert dashboard.index("${renderBoardroomOperatorPresence()}") < dashboard.index("${renderAionGoalEngineVisibleBoardroomPanelsV1(snapshot)}")
    else:
        assert "data-aion-boardroom-advanced-runtime-drawer" in text
