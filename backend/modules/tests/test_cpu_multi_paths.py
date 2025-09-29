# -*- coding: utf-8 -*-
# File: backend/modules/tests/test_cpu_multi_paths.py
"""
Multi-path tests for VirtualCPU logging
- Success-only sequence
- Error-only sequence
- Mixed valid+invalid sequence
"""

import json
import pytest
from backend.codexcore_virtual.cpu_executor import VirtualCPU


def extract_logs(output: str):
    """Return parsed JSON logs from raw stdout."""
    lines = [line for line in output.splitlines() if line.startswith("[LOG]")]
    return [json.loads(line.replace("[LOG] ", "")) for line in lines]


def test_success_only_sequence(capsys):
    cpu = VirtualCPU()
    cpu.load_program([
        "LOG FirstMessage",
        "LOG SecondMessage",
        "LOG ThirdMessage",
    ])
    cpu.run()

    output = capsys.readouterr().out
    logs = extract_logs(output)

    # Expect 3 successful logs
    assert len(logs) == 3
    for payload in logs:
        assert payload["status"] == "ok"
        assert payload["event"] == "registry_execute"
        assert payload["error"] is None


def test_error_only_sequence(capsys):
    cpu = VirtualCPU()
    cpu.load_program([
        "FAKE_OP",
    ])

    with pytest.raises(Exception):
        cpu.run()

    output = capsys.readouterr().out
    logs = extract_logs(output)

    # Expect exactly 1 log with error
    assert len(logs) == 1
    payload = logs[0]
    assert payload["status"] == "error"
    assert "Unknown instruction" in payload["error"]


def test_mixed_valid_and_invalid_sequence(capsys):
    cpu = VirtualCPU()
    cpu.load_program([
        "LOG BeforeError",
        "FAKE_OP",
        "LOG AfterError",  # should never run
    ])

    with pytest.raises(Exception):
        cpu.run()

    output = capsys.readouterr().out
    logs = extract_logs(output)

    # Expect 2 logs: one success, then one error
    assert len(logs) == 2
    assert logs[0]["status"] == "ok"
    assert logs[1]["status"] == "error"