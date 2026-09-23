from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def source() -> str:
    return APP.read_text(encoding="utf-8")


def phase19b_block() -> str:
    text = source()
    start = text.index("AION PATCH: Phase 19B Workflow Plus Tabs Lock")
    end = text.index("AION PATCH: Workflow Tab Active Graph Isolation E9", start)
    return text[start:end]


def test_phase19b_installed() -> None:
    text = source()
    assert "AION PATCH: Phase 19B Workflow Plus Tabs Lock" in text
    assert "installAionPhase19BWorkflowPlusTabsLock" in text
    assert "__aionCreateWorkflowCanvasTab" in text
    assert "__aionRenderWorkflowCanvasTabs" in text


def test_phase19b_adds_visible_plus_tab() -> None:
    block = phase19b_block()
    assert 'data-aion-phase19b-workflow-plus' in block
    assert "New workflow canvas" in block
    assert "createWorkflowTab()" in block
    assert "aion-phase19b-workflow-plus-tab" in block


def test_phase19b_supports_multiple_main_workflow_tabs() -> None:
    block = phase19b_block()
    assert "__aionWorkflowTabs" in block
    assert "__aionActiveWorkflowTabId" in block
    assert "createWorkflowTab" in block
    assert "selectWorkflowTab" in block
    assert "closeWorkflowTab" in block
    assert "renameWorkflowTab" in block


def test_phase19b_keeps_glyph_tabs_separate() -> None:
    block = phase19b_block()
    assert 'window.__aionActiveWorkflowTab = "main"' in block
    assert "window.__aionGlyphWorkflowTabOpen = false" in block
    assert "__aionPersistActiveGlyphWorkflowGraph" in block
    assert "activeTabType === \"glyph\"" in block or "activeTabType !== \"glyph\"" in block


def test_phase19b_persists_workflow_tabs_locally() -> None:
    block = phase19b_block()
    assert "aion.workflow_builder.workflow_tabs.v1" in block
    assert "localStorage.setItem(STORAGE_KEY" in block
    assert "localStorage.getItem(STORAGE_KEY)" in block
    assert "persistWorkflowTabs" in block
    assert "hydrateWorkflowTabs" in block


def test_phase19b_does_not_enable_live_execution() -> None:
    block = phase19b_block()
    forbidden = [
        "fetch(",
        "sendEmail",
        "payment_created = true",
        "booking_created = true",
        "external_writes_enabled = true",
    ]
    for token in forbidden:
        assert token not in block
