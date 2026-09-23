from backend.services.aion_custom_function_sandbox import run_custom_function_dry_run


def test_phase19e3_sandbox_returns_safe_preview() -> None:
    result = run_custom_function_dry_run(
        language="javascript",
        code="return { ok: true, label: input.message }",
        sample_input={"email": "customer@example.com", "message": "quote please"},
    )

    assert result["ok"] is True
    assert result["source"] == "custom.function.sandbox.dry_run"
    assert result["dry_run"] is True
    assert result["frontend_code_execution"] is False
    assert result["backend_code_execution"] is False
    assert result["external_writes_enabled"] is False
    assert result["live_execution_enabled"] is False
    assert result["requires_human_approval"] is True
    assert result["output"]["result"]["code_saved"] is True


def test_phase19e3_sandbox_blocks_network_and_external_write_tokens() -> None:
    result = run_custom_function_dry_run(
        language="javascript",
        code="fetch('https://example.com'); sendEmail('x@y.com')",
        sample_input={"message": "unsafe"},
    )

    assert result["ok"] is False
    assert result["source"] == "custom.function.sandbox.blocked"
    assert result["error"]["type"] == "blocked_capability"
    assert "fetch(" in result["error"]["blocked_tokens"]
    assert "sendEmail" in result["error"]["blocked_tokens"]
    assert result["external_writes_enabled"] is False
    assert result["live_execution_enabled"] is False


def test_phase19e3_sandbox_blocks_filesystem_secrets_and_process_tokens() -> None:
    result = run_custom_function_dry_run(
        language="python",
        code="open('/tmp/x').read(); process.env.SECRET",
        sample_input={"message": "unsafe"},
    )

    assert result["ok"] is False
    assert "open(" in result["error"]["blocked_tokens"]
    assert "process.env" in result["error"]["blocked_tokens"]


def test_phase19e3_sandbox_never_uses_eval_or_exec_contract_tokens() -> None:
    from pathlib import Path

    text = Path("backend/services/aion_custom_function_sandbox.py").read_text()

    forbidden_runtime_patterns = [
        "eval(code",
        "exec(code",
        "compile(code",
        "__import__(",
        "subprocess.",
        "socket.",
    ]

    for token in forbidden_runtime_patterns:
        assert token not in text
