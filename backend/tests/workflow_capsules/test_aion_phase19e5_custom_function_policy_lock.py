from pathlib import Path

APP = Path("desktop/mac/src/app.js")
DOC = Path("docs/rfc/aion_phase19e5_custom_function_execution_policy_lock.tex")


def source() -> str:
    return APP.read_text(encoding="utf-8")


def phase19e5_block() -> str:
    text = source()
    start = text.index("AION PATCH: Phase 19E.5 Custom Function Execution Policy Lock")
    end = text.index('console.log("[AION] Phase 19E.5 custom function execution policy lock installed");', start)
    return text[start:end]


def test_phase19e5_policy_lock_installed() -> None:
    block = phase19e5_block()
    assert "installAionPhase19E5CustomFunctionExecutionPolicyLock" in block
    assert "__aionPhase19E5CustomFunctionExecutionPolicy" in block
    assert "saved_sandbox_contract" in block


def test_phase19e5_ui_wording_is_clear() -> None:
    block = phase19e5_block()
    assert "Saved sandbox contract" in block
    assert "Dry-run preview only" in block
    assert "Code is stored but not executed yet" in block


def test_phase19e5_policy_forbids_execution() -> None:
    block = phase19e5_block()
    assert "frontend_code_execution: false" in block
    assert "backend_code_execution: false" in block
    assert "external_writes_enabled: false" in block
    assert "live_execution_enabled: false" in block
    assert "requires_human_approval: true" in block


def test_phase19e5_no_dangerous_execution_tokens() -> None:
    block = phase19e5_block()
    forbidden = [
        "eval(",
        "new Function",
        "Function(",
        "fetch(",
        "sendEmail",
        "external_writes_enabled: true",
        "live_execution_enabled: true",
        "frontend_code_execution: true",
        "backend_code_execution: true",
    ]
    for token in forbidden:
        assert token not in block


def test_phase19e5_latex_lock_doc_exists() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "Phase 19E.5" in text
    assert "saved sandbox contract" in text
    assert "MUST NOT evaluate user code" in text
    assert "AION-PHASE19E5-CUSTOM-FUNCTION-EXECUTION-POLICY-LOCK" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
