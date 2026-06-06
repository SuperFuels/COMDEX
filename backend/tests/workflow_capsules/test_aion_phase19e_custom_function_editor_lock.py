from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def source() -> str:
    return APP.read_text(encoding="utf-8")


def phase19e_block() -> str:
    text = source()
    start = text.index("AION PATCH: Phase 19E Custom Function Node Editor Lock")
    end = text.index('console.log("[AION] Phase 19E custom function node editor lock installed");', start)
    return text[start:end]


def test_phase19e_custom_function_editor_installed() -> None:
    block = phase19e_block()
    assert "installAionPhase19ECustomFunctionNodeEditorLock" in block
    assert "__aionOpenPhase19ECustomFunctionEditor" in block
    assert "__aionSavePhase19ECustomFunctionEditor" in block
    assert "__aionIsPhase19ECustomFunctionNode" in block


def test_phase19e_has_tailored_code_editor_fields() -> None:
    block = phase19e_block()
    assert "aion-phase19e-custom-function-code" in block
    assert 'data-aion-phase19e-custom-function-input="language"' in block
    assert 'data-aion-phase19e-custom-function-input="code"' in block
    assert 'data-aion-phase19e-custom-function-input="inputs_schema"' in block
    assert 'data-aion-phase19e-custom-function-input="outputs_schema"' in block
    assert 'data-aion-phase19e-custom-function-input="safety_mode"' in block


def test_phase19e_custom_function_is_dry_run_only() -> None:
    block = phase19e_block()
    assert "dry_run_only" in block
    assert "external_writes_enabled = false" in block
    assert "live_execution_enabled = false" in block
    assert "requires_human_approval = true" in block
    assert "This editor never enables live execution" in block


def test_phase19e_persists_to_active_workflow_or_glyph_graph() -> None:
    block = phase19e_block()
    assert "persistGraph" in block
    assert "persistAionWorkflowDraftState" in block
    assert "__aionPersistActiveGlyphWorkflowGraph" in block
    assert "phase19e_custom_function_saved" in block


def test_phase19e_detects_custom_function_nodes() -> None:
    block = phase19e_block()
    assert "isCustomFunctionNode" in block
    assert "custom_function" in block
    assert "custom function" in block
    assert "function node" in block


def test_phase19e_does_not_enable_live_execution() -> None:
    block = phase19e_block()
    forbidden = [
        "fetch(",
        "sendEmail",
        "payment_created = true",
        "booking_created = true",
        "external_writes_enabled = true",
        "live_execution_enabled = true",
    ]
    for token in forbidden:
        assert token not in block
