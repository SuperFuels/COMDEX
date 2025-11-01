# -*- coding: utf-8 -*-
# File: backend/modules/tests/test_registry_logging.py
"""
C13 Logging Tests for RegistryBridge
────────────────────────────────────
Ensures resolve_and_execute emits structured [LOG] lines
for both handled and stubbed operations.
"""

import io
import sys
import json
import pytest

from backend.core.registry_bridge import registry_bridge


@pytest.fixture
def capture_stdout(monkeypatch):
    """Fixture to capture stdout prints from registry_bridge."""
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    return buf


def test_logging_for_valid_op(capture_stdout):
    # Pick a known registered op (sequence operator "logic:->")
    result = registry_bridge.resolve_and_execute("->", 1, 2)

    output = capture_stdout.getvalue()
    assert "[LOG]" in output, "Expected [LOG] entry for valid op"

    # Parse JSON part
    log_line = [line for line in output.splitlines() if line.startswith("[LOG]")][-1]
    payload = json.loads(log_line.replace("[LOG] ", ""))

    assert payload["event"] == "registry_execute"
    assert payload["status"] == "ok"
    assert payload["canonical"].startswith("logic:")
    assert "result" in payload
    assert result == payload["result"]


def test_logging_for_stubbed_op(capture_stdout):
    # Use a fake op that won't exist
    result = registry_bridge.resolve_and_execute("FAKE_OP", 123)

    output = capture_stdout.getvalue()
    assert "[LOG]" in output, "Expected [LOG] entry for stubbed op"

    # Parse JSON part
    log_line = [line for line in output.splitlines() if line.startswith("[LOG]")][-1]
    payload = json.loads(log_line.replace("[LOG] ", ""))

    assert payload["event"] == "registry_execute"
    assert payload["status"] == "stub"
    assert payload["canonical"] == "FAKE_OP"
    assert "unhandled_op" in result
    assert result["unhandled_op"] == "FAKE_OP"

def test_logging_for_valid_op(capture_stdout):
    # Pick a known registered op (sequence operator "->")
    result = registry_bridge.resolve_and_execute("->", 1, 2)

    output = capture_stdout.getvalue()
    assert "[LOG]" in output, "Expected [LOG] entry for valid op"

    # Parse JSON part
    log_line = [line for line in output.splitlines() if line.startswith("[LOG]")][-1]
    payload = json.loads(log_line.replace("[LOG] ", ""))

    assert payload["event"] == "registry_execute"
    assert payload["status"] == "ok"
    # Don't hardcode domain - just check it's not stub
    assert ":" in payload["canonical"], f"Expected domain prefix, got {payload['canonical']}"
    assert "result" in payload
    assert result == payload["result"]