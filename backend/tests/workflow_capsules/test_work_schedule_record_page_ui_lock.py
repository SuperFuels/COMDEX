from pathlib import Path


WORK_SCHEDULE_JS = Path("desktop/mac/src/aion_work_schedule_workspace.js")
WORK_SCHEDULE_CSS = Path("desktop/mac/src/aion_work_schedule_workspace.css")


def test_work_items_open_as_a_durable_full_page_record():
    source = WORK_SCHEDULE_JS.read_text(encoding="utf-8")

    assert 'class="ws-detail-panel ws-record-page"' in source
    assert "WORK RECORD ·" in source
    assert "Record reference" in source
    assert "linked work ${customerRecords === 1 ? 'record' : 'records'}" in source
    assert "← Back to ${esc(returnLabels[state.ui.view]" in source
    assert "const selectedRecord = state.ui.selectedId ? renderDetailPanel() : ''" in source
    assert "${selectedRecord || workspace}" in source
    assert "ws-panel-backdrop" not in source
    assert "ws-panel-layer" not in source


def test_work_record_uses_the_normal_tessaris_page_surface_not_a_drawer():
    styles = WORK_SCHEDULE_CSS.read_text(encoding="utf-8")

    assert ".ws-record-header" in styles
    assert ".ws-record-summary" in styles
    assert ".ws-record-tabs" in styles
    assert "grid-template-columns: repeat(6, minmax(0, 1fr))" in styles
    assert ".ws-record-tabs button.active" in styles
    assert "border-radius: 0 !important" in styles
    assert "box-shadow: none !important" in styles
    assert "position: relative; width: 100%; min-height:" in styles
    assert ".ws-panel-backdrop" not in styles
    assert ".ws-panel-layer" not in styles
