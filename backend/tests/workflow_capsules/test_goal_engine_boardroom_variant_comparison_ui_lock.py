from pathlib import Path

APP = Path("desktop/mac/src/app.js")
CSS = Path("desktop/mac/src/styles.css")


def test_boardroom_variant_comparison_renderer_exists():
    text = APP.read_text()

    assert "AION-GOAL-ENGINE-VARIANT-COMPARISON-VIEWER-V1:START" in text
    assert "function renderAionGoalEngineVariantComparisonViewerV1" in text
    assert 'data-aion-goal-engine-variant-comparison="v1"' in text


def test_boardroom_variant_comparison_reads_canonical_previews():
    text = APP.read_text()

    assert 'value.trace_type === "variant_outcome_score_preview"' in text
    assert 'value.trace_type === "experiment_result_evidence_preview"' in text
    assert "variant_outcome_scores" in text
    assert "experiment_result_evidence" in text
    assert "variant_scores" in text


def test_boardroom_variant_comparison_is_ui_only_and_safe():
    text = APP.read_text()
    block = text[
        text.index("AION-GOAL-ENGINE-VARIANT-COMPARISON-VIEWER-V1:START"):
        text.index("AION-GOAL-ENGINE-VARIANT-COMPARISON-VIEWER-V1:END")
    ]

    assert "does not select a winner automatically" in block
    assert "does not pause loser variants" in block
    assert "does not mutate goals" in block
    assert "does not write externally" in block
    assert "winner declared" in block
    assert "manual decision required" in block
    assert "fetch(" not in block
    assert ".send(" not in block
    assert "write_goal_engine_container_record" not in block


def test_boardroom_variant_comparison_wraps_renderer_without_observer_loop():
    text = APP.read_text()
    block = text[
        text.index("AION-GOAL-ENGINE-VARIANT-COMPARISON-VIEWER-V1:START"):
        text.index("AION-GOAL-ENGINE-VARIANT-COMPARISON-VIEWER-V1:END")
    ]

    assert "installAionGoalEngineVariantComparisonViewerV1" in block
    assert "__aionGoalEngineVariantComparisonViewerInstalledV1" in block
    assert "renderAionGoalEngineBoardroomRuntimePreviewV1" in block
    assert "MutationObserver" not in block
    assert "setInterval" not in block


def test_boardroom_variant_comparison_css_exists():
    text = CSS.read_text()

    assert "AION-GOAL-ENGINE-VARIANT-COMPARISON-CSS-V1:START" in text
    assert ".aion-boardroom-variant-comparison-viewer" in text
    assert ".aion-boardroom-variant-score-row" in text
    assert ".aion-boardroom-variant-rank" in text
