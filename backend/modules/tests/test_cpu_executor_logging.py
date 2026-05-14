# -*- coding: utf-8 -*-
# File: backend/modules/tests/test_cpu_executor_logging.py

import io
import json
import sys
import pytest

from backend.codexcore_virtual.cpu_executor import VirtualCPU


@pytest.fixture
def capture_stdout(monkeypatch):
    """Fixture to capture stdout into a StringIO buffer."""
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    return buf


def test_cpu_executor_logging_ok(capture_stdout):
    # Minimal CPU with a single fake instruction
    class DummyCPU(VirtualCPU):
        def fetch(self):
            return ("FAKE_OP", [1, 2]) if self.instruction_pointer == 0 else None

        def decode(self, instr):
            return instr  # already tuple

        def execute(self, op, args):
            return sum(args)  # simple success

    cpu = DummyCPU()
    cpu.run()

    output = capture_stdout.getvalue()
    log_lines = [line for line in output.splitlines() if line.startswith("[LOG]")]
    assert log_lines, "Expected at least one [LOG] entry"

    payload = json.loads(log_lines[0].replace("[LOG] ", ""))
    assert payload["event"] == "registry_execute"
    assert payload["op"] == "FAKE_OP"
    assert payload["status"] == "ok"
    assert payload["result"] == 3


def test_cpu_executor_logging_error(capture_stdout):
    # CPU that raises error during execution
    class DummyCPU(VirtualCPU):
        def fetch(self):
            return ("BAD_OP", [42]) if self.instruction_pointer == 0 else None

        def decode(self, instr):
            return instr

        def execute(self, op, args):
            raise RuntimeError("boom")

    cpu = DummyCPU()
    with pytest.raises(RuntimeError):
        cpu.run()

    output = capture_stdout.getvalue()
    log_lines = [line for line in output.splitlines() if line.startswith("[LOG]")]
    assert log_lines, "Expected at least one [LOG] entry"

    payload = json.loads(log_lines[0].replace("[LOG] ", ""))
    assert payload["event"] == "registry_execute"
    assert payload["op"] == "BAD_OP"
    assert payload["status"] == "error"
    assert payload["error"] == "boom"