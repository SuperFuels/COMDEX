from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _text() -> str:
    return APP.read_text(encoding="utf-8")


def _function_block(name: str) -> str:
    text = _text()
    start = text.index(f"function {name}(")
    next_function = text.find("\nfunction ", start + 1)
    if next_function == -1:
        return text[start:]
    return text[start:next_function]


def test_clean_draft_state_resolver_is_tab_aware() -> None:
    block = _function_block("getAionWorkflowDraftState")
    assert "CLEAN TAB GRAPH RESOLVER" in block
    assert "__aionActiveWorkflowTab" in block
    assert "__aionActiveGlyphWorkflowTabCode" in block
    assert "__aionActiveGlyphWorkflowCode" in block
    assert "__aionOpenedGlyphWorkflowGraphsByCode" in block
    assert "__aionOpenedGlyphWorkflowGraph" in block
    assert "__aionWorkflowMainGraph" in block


def test_clean_draft_state_uses_glyph_store_before_main_graph() -> None:
    block = _function_block("getAionWorkflowDraftState")
    glyph_store_pos = block.index("__aionOpenedGlyphWorkflowGraphsByCode")
    main_graph_pos = block.index("__aionWorkflowMainGraph")
    assert glyph_store_pos < main_graph_pos


def test_clean_persist_keeps_glyph_graph_out_of_main_local_storage() -> None:
    block = _function_block("persistAionWorkflowDraftState")
    assert 'activeTab === "glyph"' in block
    assert "__aionOpenedGlyphWorkflowGraphsByCode[activeGlyphCode] = compactGraph" in block
    assert "return compactGraph;" in block

    glyph_return_pos = block.index("__aionOpenedGlyphWorkflowGraphsByCode[activeGlyphCode] = compactGraph")
    local_storage_pos = block.index("localStorage.setItem")
    assert glyph_return_pos < local_storage_pos


def test_clean_open_workflow_stores_graph_by_glyph_code() -> None:
    text = _text()
    assert "function openWorkflow(code)" in text
    assert "__aionOpenedGlyphWorkflowGraphsByCode[openedCode] = openedGraph" in text
    assert "__aionActiveGlyphWorkflowCode = openedCode" in text
    assert "__aionActiveGlyphWorkflowTabCode = openedCode" in text
    assert '__aionActiveWorkflowTab = "glyph"' in text


def test_clean_top_tabs_use_active_tab_code() -> None:
    text = _text()
    assert "function renderTopTabs()" in text
    assert 'const active = String(window.__aionActiveGlyphWorkflowTabCode || "main")' in text
    assert 'class="aion-glyph-top-tab ${isActive ? "active" : ""}"' in text
    assert 'data-aion-glyph-top-tab-select="${code}"' in text


def test_no_old_e13_to_e18_patch_blocks_left() -> None:
    text = _text()
    obsolete_markers = [
        "Real Active Workflow Graph Resolver E13",
        "Per-Glyph Workflow Tab Graph Isolation E14",
        "Final Per-Glyph Workflow Graph Authority E15",
        "Capture Opened Glyph Graphs By Tab Code E16",
        "Glyph Workflow Tab Active Highlight E17",
        "Glyph Workflow Tab Visual Authority E18",
    ]
    for marker in obsolete_markers:
        assert marker not in text
