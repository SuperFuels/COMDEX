"""
AION Phase 19E.3 Custom Function Sandbox Runner

Contract:
- Dry-run only.
- JSON input only.
- JSON output only.
- No network.
- No filesystem.
- No secrets.
- Timeout guarded.
- Deterministic preview supported.
- This module must not use eval or exec for user code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


FORBIDDEN_TOKENS = (
    "fetch(",
    "XMLHttpRequest",
    "WebSocket",
    "sendEmail",
    "process.env",
    "require(",
    "import ",
    "open(",
    "readFile",
    "writeFile",
    "subprocess",
    "socket",
    "requests.",
    "http.",
    "https.",
    "eval(",
    "exec(",
    "new Function",
)


@dataclass(frozen=True)
class SandboxResult:
    ok: bool
    mode: str
    source: str
    dry_run: bool
    frontend_code_execution: bool
    backend_code_execution: bool
    external_writes_enabled: bool
    live_execution_enabled: bool
    requires_human_approval: bool
    language: str
    input: dict[str, Any]
    output: dict[str, Any] | None
    error: dict[str, Any] | None


def _safe_json_object(value: Any, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return fallback or {}


def _detect_forbidden(code: str) -> list[str]:
    return [token for token in FORBIDDEN_TOKENS if token in code]


def run_custom_function_dry_run(
    *,
    code: str,
    language: str = "javascript",
    sample_input: dict[str, Any] | None = None,
    timeout_ms: int = 3000,
    memory_mb: int = 64,
) -> dict[str, Any]:
    """
    Return a safe deterministic dry-run preview.

    This intentionally does not execute user code yet. It is the backend
    sandbox contract and guard surface. The future real runner must remain
    behind this same contract.
    """

    safe_input = _safe_json_object(sample_input, {"source": "custom_function_sandbox_sample"})
    safe_language = str(language or "javascript").lower().strip()
    safe_code = str(code or "")
    blocked = _detect_forbidden(safe_code)

    if blocked:
      result = SandboxResult(
          ok=False,
          mode="backend_custom_function_sandbox_dry_run",
          source="custom.function.sandbox.blocked",
          dry_run=True,
          frontend_code_execution=False,
          backend_code_execution=False,
          external_writes_enabled=False,
          live_execution_enabled=False,
          requires_human_approval=True,
          language=safe_language,
          input=safe_input,
          output=None,
          error={
              "type": "blocked_capability",
              "message": "Custom function dry-run blocked unsafe capability token.",
              "blocked_tokens": blocked,
          },
      )
      return result.__dict__

    preview_output = {
        "ok": True,
        "mode": "backend_sandbox_preview_only",
        "language": safe_language,
        "input": safe_input,
        "result": {
            "dry_run_preview": True,
            "code_saved": bool(safe_code.strip()),
            "code_preview_chars": len(safe_code),
            "timeout_ms": int(timeout_ms),
            "memory_mb": int(memory_mb),
            "note": "Backend sandbox contract validated. User code was not executed.",
        },
    }

    result = SandboxResult(
        ok=True,
        mode="backend_custom_function_sandbox_dry_run",
        source="custom.function.sandbox.dry_run",
        dry_run=True,
        frontend_code_execution=False,
        backend_code_execution=False,
        external_writes_enabled=False,
        live_execution_enabled=False,
        requires_human_approval=True,
        language=safe_language,
        input=safe_input,
        output=preview_output,
        error=None,
    )

    return result.__dict__
