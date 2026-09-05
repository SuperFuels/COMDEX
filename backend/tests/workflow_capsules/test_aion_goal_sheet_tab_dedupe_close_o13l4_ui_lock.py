from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    start = APP_JS.index("BEGIN AION O13L4 GOAL SHEET TAB DEDUPE AND CLOSE LOCK")
    end = APP_JS.index("END AION O13L4 GOAL SHEET TAB DEDUPE AND CLOSE LOCK")
    return APP_JS[start:end]


def test_o13l4_installed():
    text = block()
    assert "O13L.4 exact fix" in text
    assert "dedupeGoalSheetTabsO13L4" in text
    assert "closeTabO13L4" in text


def test_o13l4_dedupes_goal_sheet_tabs_by_id():
    text = block()
    assert "seenGoalSheetIds" in text
    assert "seenGoalSheetIds.has(id)" in text
    assert "seenGoalSheetIds.add(id)" in text


def test_o13l4_intercepts_goal_sheet_close_button():
    text = block()
    assert "data-aion-workflow-main-tab-close" in text
    assert "handleCloseO13L4" in text
    assert "event.stopImmediatePropagation" in text


def test_o13l4_wraps_existing_tab_renderer():
    text = block()
    assert "previousRender" in text
    assert "window.__aionRenderWorkflowCanvasTabs = wrapped" in text
    assert "wrapped.__aionO13L4Wrapped = true" in text


def test_o13l4_exposes_debug_helpers():
    text = block()
    assert "window.aionDedupeGoalSheetTabsO13L4" in text
    assert "window.aionCloseGoalSheetTabO13L4" in text


def test_goal_sheet_selection_router_does_not_consume_close_control():
    start = APP_JS.index("BEGIN AION O13L3 GOAL SHEET TAB CLICK ROUTER PREEMPT LOCK")
    end = APP_JS.index("END AION O13L3 GOAL SHEET TAB CLICK ROUTER PREEMPT LOCK")
    text = APP_JS[start:end]
    handler = text[text.index("function handleGoalSheetTabClickO13L3"):]
    close_guard = handler.index('closest?.("[data-aion-workflow-main-tab-close]")')
    tab_router = handler.index('const tabEl = event.target?.closest?.(')
    assert close_guard < tab_router


def test_visible_workflow_strip_owns_document_name_and_autosave_state():
    assert "aion-workflow-document-strip" in APP_JS
    assert 'aria-label="Worksheet name"' in APP_JS
    assert "Saved automatically as a local workflow draft" in APP_JS
    assert ">Autosaved</strong>" in APP_JS

    render_start = APP_JS.index('<section class="aion-workflow-canvas-shell"')
    render_end = APP_JS.index('<div class="aion-workflow-top-actions">', render_start)
    render = APP_JS[render_start:render_end]
    assert "Aion Workflow Builder · local draft" not in render
    assert "activeWorkflowId" not in render
    assert "nodes</b>" in render
    assert "edges</b>" in render


def test_tab_close_is_a_real_sibling_button_and_not_nested_interactive_content():
    phase_start = APP_JS.index("AION PATCH: Phase 19B Workflow Plus Tabs Lock")
    phase_end = APP_JS.index("AION PATCH: Workflow Tab Active Graph Isolation E9", phase_start)
    text = APP_JS[phase_start:phase_end]
    assert 'document.createElement("div")' in text
    assert 'document.createElement("button")' in text
    assert 'shell.appendChild(button)' in text
    assert 'shell.appendChild(close)' in text
    assert 'button.appendChild(close)' not in text
    assert 'data-aion-phase19b-workflow-tab-shell' in text


def test_close_router_handles_every_workflow_tab_not_only_goal_sheets():
    text = block()
    handler = text[text.index("function handleCloseO13L4"):text.index("const previousRender")]
    assert "if (!tab) return;" in handler
    assert "!isGoalSheetTabO13L4(tab)" not in handler


def test_workflow_chrome_measures_shared_header_and_removes_gap():
    assert "function getSharedExecutiveHeaderHeight()" in APP_JS
    assert "--aion-shared-executive-header-h" in APP_JS
    assert "const tabbarTop = sharedHeaderHeight + 42" in APP_JS
    assert 'tabbar.style.setProperty("top", `${tabbarTop}px`, "important")' in APP_JS
    assert "height: 42px !important" in APP_JS


def test_worksheet_name_is_labelled_and_active_tab_is_a_rename_shortcut():
    assert '<span>Worksheet name</span>' in APP_JS
    assert 'data-aion-workflow-tab-name' in APP_JS
    assert "The active tab name is a direct rename shortcut" in APP_JS
    assert 'document.querySelector("[data-aion-workflow-title-input=\'true\']")' in APP_JS
    assert "titleInput.focus({ preventScroll: true })" in APP_JS
    assert "titleInput.select?.()" in APP_JS


def test_historic_duplicate_starter_tabs_are_canonicalised_before_render_and_save():
    phase_start = APP_JS.index("AION PATCH: Phase 19B Workflow Plus Tabs Lock")
    phase_end = APP_JS.index("AION PATCH: Workflow Tab Active Graph Isolation E9", phase_start)
    text = APP_JS[phase_start:phase_end]
    assert "function canonicalWorkflowTabs" in text
    assert "if (isEmptyWorkflowGraph(graph) && title) key = `empty:${title}`" in text
    assert "window.__aionWorkflowTabs = canonicalWorkflowTabs" in text
    assert "canonicalWorkflowTabs(parsed.tabs.map" in text


def test_closing_last_worksheet_persists_an_intentionally_empty_workspace():
    phase_start = APP_JS.index("AION PATCH: Phase 19B Workflow Plus Tabs Lock")
    phase_end = APP_JS.index("AION PATCH: Workflow Tab Active Graph Isolation E9", phase_start)
    text = APP_JS[phase_start:phase_end]
    assert "window.__aionWorkflowTabsAllowEmpty = true" in text
    assert 'window.__aionActiveWorkflowTabId = ""' in text
    assert "allow_empty: window.__aionWorkflowTabsAllowEmpty === true && tabs.length === 0" in text
    assert 'makeBlankGraph("Workflow 1")' not in text[text.index("function closeWorkflowTab"):text.index("function renameWorkflowTab")]


def test_closed_goal_sheet_is_not_silently_reopened_on_reload():
    start = APP_JS.index("BEGIN AION O13L GOAL SHEET WORKFLOW TAB REGISTRY LOCK")
    end = APP_JS.index("END AION O13L GOAL SHEET WORKFLOW TAB REGISTRY LOCK")
    text = APP_JS[start:end]
    assert "aion.workflow_builder.closed_tab_ids.v1" in text
    assert "if (!isClosedTabO13L(graphIdO13L(boardroom)))" in text
    assert "reopenTabO13L(graphIdO13L(safeGraph))" in text


def test_empty_workspace_clears_the_last_graph_instead_of_rendering_closed_content():
    assert "window.__aionEmptyWorkflowWorkspaceGraph" in APP_JS
    assert 'workflow_id: "__aion_empty_workspace__"' in APP_JS
    assert "if (!workspaceEmpty) maybeLoadAionWorkflowFromBusinessContainerOnce()" in APP_JS
    assert "No worksheet open" in APP_JS
    assert "Use the + menu above to create a blank worksheet or reopen a recent one." in APP_JS


def test_plus_opens_new_or_recent_menu_without_automatically_reopening_boardroom():
    phase_start = APP_JS.index("AION PATCH: Phase 19B Workflow Plus Tabs Lock")
    phase_end = APP_JS.index("AION PATCH: Workflow Tab Active Graph Isolation E9", phase_start)
    text = APP_JS[phase_start:phase_end]
    assert "aion.workflow_builder.recent_tabs.v1" in text
    assert 'data-aion-workflow-new-blank' in text
    assert 'data-aion-workflow-open-recent' in text
    assert "recentWorkflowTabs().filter" in text
    assert "recent.slice(0, 5)" in text
    plus_handler = text[text.index('const plus = event.target?.closest?.("[data-aion-phase19b-workflow-plus='):]
    assert "menu.hidden = !menu.hidden" in plus_handler
