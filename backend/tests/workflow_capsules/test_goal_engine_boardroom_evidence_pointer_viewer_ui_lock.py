from pathlib import Path

APP = Path("desktop/mac/src/app.js")
CSS = Path("desktop/mac/src/styles.css")


def test_boardroom_evidence_pointer_viewer_renderer_exists():
    text = APP.read_text()

    assert "AION-GOAL-ENGINE-EVIDENCE-POINTER-VIEWER-V1:START" in text
    assert "function renderAionGoalEngineEvidencePointerViewerV1" in text
    assert 'data-aion-goal-engine-evidence-viewer="v1"' in text


def test_boardroom_evidence_pointer_viewer_reads_canonical_preview_rows():
    text = APP.read_text()

    assert 'value.trace_type === "evidence_pointer_preview"' in text
    assert "evidence_pointers" in text
    assert "evidence_pointer_previews" in text
    assert "reference_pointer" in text
    assert "evidence_hash" in text
    assert "blocked_reasons" in text


def test_boardroom_evidence_pointer_viewer_is_ui_only_and_safe():
    text = APP.read_text()
    block = text[
        text.index("AION-GOAL-ENGINE-EVIDENCE-POINTER-VIEWER-V1:START"):
        text.index("AION-GOAL-ENGINE-EVIDENCE-POINTER-VIEWER-V1:END")
    ]

    assert "does not resolve connectors" in block
    assert "does not read external systems" in block
    assert "does not write external systems" in block
    assert "does not grant permission" in block
    assert "fetch(" not in block
    assert ".send(" not in block
    assert "write_goal_engine_container_record" not in block


def test_boardroom_evidence_pointer_viewer_wraps_boardroom_renderer_without_observer_loop():
    text = APP.read_text()
    block = text[
        text.index("AION-GOAL-ENGINE-EVIDENCE-POINTER-VIEWER-V1:START"):
        text.index("AION-GOAL-ENGINE-EVIDENCE-POINTER-VIEWER-V1:END")
    ]

    assert "installAionGoalEngineEvidencePointerViewerV1" in block
    assert "__aionGoalEngineEvidencePointerViewerInstalledV1" in block
    assert "renderAionGoalEngineBoardroomRuntimePreviewV1" in block
    assert "MutationObserver" not in block
    assert "setInterval" not in block


def test_boardroom_evidence_pointer_viewer_css_exists():
    text = CSS.read_text()

    assert "AION-GOAL-ENGINE-EVIDENCE-POINTER-VIEWER-CSS-V1:START" in text
    assert ".aion-boardroom-evidence-pointer-viewer" in text
    assert ".aion-boardroom-evidence-pointer-row" in text
    assert ".aion-boardroom-evidence-pointer-ref" in text
