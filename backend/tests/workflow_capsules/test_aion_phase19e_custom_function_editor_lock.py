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

def phase19e_real_takeover_block() -> str:
    text = source()
    start = text.index("AION PATCH: Phase 19E Real Node Editor Takeover Lock")
    end = text.index('console.log("[AION] Phase 19E real node editor takeover lock installed");', start)
    return text[start:end]


def test_phase19e_real_node_editor_takeover_installed() -> None:
    block = phase19e_real_takeover_block()
    assert "installAionPhase19ERealNodeEditorTakeoverLock" in block
    assert "findVisibleNodeEditor" in block
    assert "findParametersColumn" in block
    assert "applyTakeover" in block


def test_phase19e_real_takeover_replaces_generic_parameter_panel() -> None:
    block = phase19e_real_takeover_block()
    assert 'data-aion-phase19e-generic-params-hidden' in block
    assert "FIELD" in block
    assert "OPERATOR" in block
    assert "VALUE" in block
    assert "PARAMETERS" in block


def test_phase19e_real_takeover_detects_custom_logic_screenshot_node() -> None:
    block = phase19e_real_takeover_block()
    assert "custom logic" in block
    assert "sandboxed function" in block
    assert "json in/out" in block
    assert "custom_function" in block


def test_phase19e_real_takeover_explains_execution_contract() -> None:
    block = phase19e_real_takeover_block()
    assert "Receives JSON from the previous node" in block
    assert "returns JSON to the next node" in block
    assert "Sample input JSON" in block
    assert "Input schema" in block
    assert "Output schema" in block


def test_phase19e_real_takeover_is_safe_and_dry_run_only() -> None:
    block = phase19e_real_takeover_block()
    assert "dry_run_only" in block
    assert "No frontend code execution" in block
    assert "No external writes" in block
    assert "external_writes_enabled = false" in block
    assert "live_execution_enabled = false" in block
    assert "requires_human_approval = true" in block


def test_phase19e_real_takeover_does_not_execute_code() -> None:
    block = phase19e_real_takeover_block()
    forbidden = [
        "eval(",
        "new Function",
        "fetch(",
        "sendEmail",
        "external_writes_enabled = true",
        "live_execution_enabled = true",
    ]
    for token in forbidden:
        assert token not in block

def test_phase19e_final_visible_takeover_installed() -> None:
    text = source()
    assert "Phase 19E Final Visible Custom Function Editor Takeover" in text
    assert "installAionPhase19EFinalVisibleCustomFunctionEditorTakeover" in text
    assert "__aionPhase19EApplyFinalVisibleCustomFunctionTakeover" in text


def test_phase19e_final_visible_takeover_replaces_generic_parameters() -> None:
    text = source()
    start = text.index("Phase 19E Final Visible Custom Function Editor Takeover")
    end = text.index("Phase 19E final visible custom function editor takeover installed", start)
    block = text[start:end]
    assert "visibleCustomFunctionEditor" in block
    assert "parametersColumn" in block
    assert "column.innerHTML = editorHtml(node)" in block
    assert "FIELD" in block
    assert "OPERATOR" in block
    assert "VALUE" in block


def test_phase19e_final_visible_takeover_has_editor_fields() -> None:
    text = source()
    start = text.index("Phase 19E Final Visible Custom Function Editor Takeover")
    end = text.index("Phase 19E final visible custom function editor takeover installed", start)
    block = text[start:end]
    assert "Custom Function Editor" in block
    assert 'data-aion-phase19e-final-input="language"' in block
    assert 'data-aion-phase19e-final-input="code"' in block
    assert 'data-aion-phase19e-final-input="inputs_schema"' in block
    assert 'data-aion-phase19e-final-input="outputs_schema"' in block
    assert 'data-aion-phase19e-final-input="sample_input"' in block


def test_phase19e_final_visible_takeover_does_not_enable_live_execution() -> None:
    text = source()
    start = text.index("Phase 19E Final Visible Custom Function Editor Takeover")
    end = text.index("Phase 19E final visible custom function editor takeover installed", start)
    block = text[start:end]
    forbidden = [
        "eval(",
        "new Function",
        "fetch(",
        "sendEmail",
        "external_writes_enabled = true",
        "live_execution_enabled = true",
    ]
    for token in forbidden:
        assert token not in block

def phase19e_real_modal_grid_block() -> str:
    text = source()
    start = text.index("AION PATCH: Phase 19E Real Modal Grid Replacement Lock")
    end = text.index("console.log(\"[AION] Phase 19E real modal grid replacement lock installed\");", start)
    return text[start:end]


def test_phase19e_replaces_actual_visible_node_editor_grid() -> None:
    block = phase19e_real_modal_grid_block()
    assert ".aion-node-editor-modal" in block
    assert ".aion-node-editor-grid" in block
    assert "data-aion-phase19e-modal-grid-replaced" in block
    assert "Custom Function Editor" in block

    rendered = block.split("grid.innerHTML = `", 1)[1].split("`;", 1)[0]
    assert "FIELD" not in rendered
    assert "OPERATOR" not in rendered
    assert "VALUE" not in rendered


def test_phase19e_real_grid_has_code_and_schema_fields() -> None:
    block = phase19e_real_modal_grid_block()
    assert 'data-aion-phase19e-modal-input="language"' in block
    assert 'data-aion-phase19e-modal-input="code"' in block
    assert 'data-aion-phase19e-modal-input="sample_input"' in block
    assert 'data-aion-phase19e-modal-input="inputs_schema"' in block
    assert 'data-aion-phase19e-modal-input="outputs_schema"' in block


def test_phase19e_real_grid_is_config_only_no_execution() -> None:
    block = phase19e_real_modal_grid_block()
    assert "no frontend code execution" in block.lower()
    assert "external_writes_enabled = false" in block
    assert "live_execution_enabled = false" in block
    assert "requires_human_approval = true" in block
    for token in ["eval(", "new Function", "fetch(", "sendEmail", "external_writes_enabled = true", "live_execution_enabled = true"]:
        assert token not in block

def test_phase19e_real_editor_grid_is_scrollable() -> None:
    block = phase19e_real_modal_grid_block()
    assert "max-height:" in block and "100vh" in block
    assert "overflow-y: auto !important" in block
    assert "overscroll-behavior: contain !important" in block
    assert ".aion-node-editor-modal:has(.aion-phase19e-modal-custom-function-editor)" in block

def phase19e2_block() -> str:
    text = source()
    start = text.index("AION PATCH: Phase 19E.2 Custom Function Dry-Run Proof Lock")
    end = text.index('console.log("[AION] Phase 19E.2 custom function dry-run proof lock installed");', start)
    return text[start:end]


def test_phase19e2_custom_function_dry_run_proof_installed() -> None:
    block = phase19e2_block()
    assert "installAionPhase19E2CustomFunctionDryRunProofLock" in block
    assert "__aionPhase19E2TransformCustomFunctionDryRunResult" in block
    assert "__aionPhase19E2BuildCustomFunctionPreview" in block


def test_phase19e2_save_button_feedback_exists() -> None:
    block = phase19e2_block()
    assert "saveFeedback" in block
    assert "Saved ✓" in block
    assert 'data-aion-phase19e-save-state", "saved"' in block
    assert "Save custom function" in block


def test_phase19e2_custom_function_no_longer_generic_step() -> None:
    block = phase19e2_block()
    assert "custom.function.dry_run" in block
    assert "custom_function_dry_run" in block
    assert "generic.step" not in block


def test_phase19e2_uses_sample_input_for_preview() -> None:
    block = phase19e2_block()
    assert "sample_input" in block
    assert "parseJson(config.sample_input" in block
    assert "input_items_preview" in block
    assert "output_items_preview" in block
    assert "custom_result" in block


def test_phase19e2_never_executes_frontend_code_or_external_writes() -> None:
    block = phase19e2_block()
    assert "frontend_code_execution: false" in block
    assert "external_writes_enabled: false" in block
    assert "live_execution_enabled: false" in block
    forbidden = [
        "eval(",
        "new Function",
        "fetch(",
        "sendEmail",
        "external_writes_enabled = true",
        "live_execution_enabled = true",
    ]
    for token in forbidden:
        assert token not in block

def phase19e3_block() -> str:
    text = source()
    start = text.index("AION PATCH: Phase 19E.3 Custom Function Save Button Hard Fix")
    end = text.index('console.log("[AION] Phase 19E.3 custom function save button hard fix installed");', start)
    return text[start:end]


def test_phase19e3_save_button_hard_fix_installed() -> None:
    block = phase19e3_block()
    assert "installAionPhase19E3CustomFunctionSaveButtonHardFix" in block
    assert "__aionPhase19E3SaveVisibleCustomFunction" in block
    assert "saveVisibleCustomFunction" in block


def test_phase19e3_save_button_has_visible_feedback_and_autoclose() -> None:
    block = phase19e3_block()
    assert "Saved ✓" in block
    assert 'data-aion-phase19e-save-state", "saved"' in block
    assert "window.setTimeout" in block
    assert "close.click" in block


def test_phase19e3_save_reads_all_visible_editor_inputs() -> None:
    block = phase19e3_block()
    assert "data-aion-phase19e-final-input" in block
    assert "data-aion-phase19e-modal-input" in block
    assert "data-aion-phase19e-real-custom-function-input" in block
    assert "data-aion-phase19e-custom-function-input" in block


def test_phase19e3_save_persists_safely_without_execution() -> None:
    block = phase19e3_block()
    assert "phase19e3_custom_function_saved" in block
    assert "persistAionWorkflowDraftState" in block
    assert "__aionPersistActiveGlyphWorkflowGraph" in block
    assert "external_writes_enabled: false" in block
    assert "live_execution_enabled: false" in block
    for token in ["eval(", "new Function", "fetch(", "sendEmail", "external_writes_enabled: true", "live_execution_enabled: true"]:
        assert token not in block

def test_phase19e3_frontend_backend_sandbox_contract_marker_exists() -> None:
    text = source()
    assert "Phase 19E.3 Backend Custom Function Sandbox Contract Lock" in text
    assert "custom.function.sandbox.dry_run" in text
    assert "fallback_source: \"custom.function.dry_run\"" in text
    assert "frontend_code_execution: false" in text
    assert "backend_code_execution: false" in text
    assert "external_writes_enabled: false" in text
    assert "live_execution_enabled: false" in text
    assert "network_access: false" in text
    assert "filesystem_access: false" in text
    assert "secrets_access: false" in text

def phase19e4_block() -> str:
    text = source()
    start = text.index("AION PATCH: Phase 19E.4 Custom Function Sandbox Dry-Run Contract Bridge")
    end = text.index('console.log("[AION] Phase 19E.4 custom function sandbox dry-run contract bridge installed");', start)
    return text[start:end]


def test_phase19e4_sandbox_bridge_installed() -> None:
    block = phase19e4_block()
    assert "installAionPhase19E4CustomFunctionSandboxDryRunContractBridge" in block
    assert "__aionPhase19E4BuildBackendSandboxContractPreview" in block
    assert "__aionPhase19E4TransformCustomFunctionSandboxDryRunResult" in block


def test_phase19e4_returns_backend_sandbox_contract_shape() -> None:
    block = phase19e4_block()
    assert "custom.function.sandbox.dry_run" in block
    assert "backend_custom_function_sandbox_dry_run" in block
    assert "backend_sandbox_preview_only" in block
    assert "sandbox_policy" in block
    assert "network_access: false" in block
    assert "filesystem_access: false" in block
    assert "secrets_access: false" in block


def test_phase19e4_replaces_config_preview_route() -> None:
    block = phase19e4_block()
    assert "custom_function_backend_sandbox_contract_dry_run" in block
    assert "custom.function.sandbox_dry_run" in block
    assert "custom_function_sandbox_dry_run" in block
    assert "config_preview_only" not in block


def test_phase19e4_never_executes_code_or_external_writes() -> None:
    block = phase19e4_block()
    assert "frontend_code_execution: false" in block
    assert "backend_code_execution: false" in block
    assert "external_writes_enabled: false" in block
    assert "live_execution_enabled: false" in block
    forbidden = [
        "eval(",
        "new Function",
        "sendEmail",
        "external_writes_enabled: true",
        "live_execution_enabled: true",
    ]
    for token in forbidden:
        assert token not in block

