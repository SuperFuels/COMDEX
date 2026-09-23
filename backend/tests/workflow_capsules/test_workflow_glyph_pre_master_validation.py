from pathlib import Path


APP_JS = Path("desktop/mac/src/app.js")
NODE_EDITOR_JS = Path("desktop/mac/src/workflow/nodeEditor/nodeEditor.js")


def read_app():
    return APP_JS.read_text(encoding="utf-8")


def read_node_editor():
    return NODE_EDITOR_JS.read_text(encoding="utf-8")


def test_compiled_glyph_contract_contains_callable_metadata():
    text = read_app()

    assert "glyph_type" in text
    assert "workflow_capsule" in text
    assert "callable" in text
    assert "inputs_schema" in text
    assert "outputs_schema" in text
    assert "required_connectors" in text
    assert "approval_policy" in text
    assert "risk_tier" in text
    assert "boardroom_events" in text


def test_workflow_glyph_can_save_list_and_load_from_business_container():
    text = read_app()

    assert "saveAionWorkflowToBusinessContainer" in text
    assert "loadAionWorkflowFromBusinessContainer" in text
    assert "listAionWorkflowGlyphCapsules" in text
    assert "glyph_capsule_registry_item" in text
    assert "compiled_glyph" in text


def test_callable_workflow_glyph_runtime_exists():
    text = read_node_editor()

    assert "executeCallWorkflowGlyphNode" in text
    assert "resolveCallableWorkflowGlyph" in text
    assert "call_workflow_glyph" in text
    assert "child_trace" in text
    assert "child_output" in text
    assert "child_approval_policy" in text
    assert "recursive" in text.lower() or "prevent" in text.lower()


def test_boardroom_event_trace_hook_exists():
    text = read_node_editor()

    assert "normaliseAionBoardroomEventDeclarations" in text
    assert "buildNodeBoardroomEvents" in text
    assert "collectBoardroomEventsFromItems" in text
    assert "boardroom_events" in text


def test_glyph_library_read_only_drawer_exists():
    text = read_app()

    assert "Workflow Glyph Library" in text
    assert "renderAionWorkflowGlyphLibraryDrawer" in text
    assert "listAionWorkflowGlyphLibraryItems" in text
    assert "required_connectors" in text
    assert "inputs_schema" in text
    assert "outputs_schema" in text
