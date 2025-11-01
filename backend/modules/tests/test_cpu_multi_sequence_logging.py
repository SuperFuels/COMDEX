# -*- coding: utf-8 -*-
# File: backend/modules/tests/test_cpu_multi_sequence_logging.py

import pytest
import json
from backend.codexcore_virtual.cpu_executor import VirtualCPU

def test_multi_instruction_sequence(capsys):
    cpu = VirtualCPU()

    # Program: TELEPORT (will error because CPU doesn't handle glyph ops),
    # then LOG (never reached), then FAKE_OP (never reached).
    cpu.load_program([
        "TELEPORT ZetaSector",
        "LOG HelloSequence",
        "FAKE_OP",
    ])

    # Run until error stops execution
    with pytest.raises(Exception):
        cpu.run()

    captured = capsys.readouterr()
    output = captured.out.splitlines()

    # Extract only log lines
    log_lines = [line for line in output if line.startswith("[LOG]")]

    # ✅ Strict mode: only the first op (TELEPORT) executes and logs error
    assert len(log_lines) == 1

    payload = json.loads(log_lines[0].replace("[LOG] ", ""))
    assert payload["event"] == "registry_execute"
    assert payload["op"] == "TELEPORT"
    assert payload["status"] == "error"
    assert "Unknown instruction" in payload["error"]