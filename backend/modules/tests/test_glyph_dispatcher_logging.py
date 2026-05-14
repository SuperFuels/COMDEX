# -*- coding: utf-8 -*-
# File: backend/modules/tests/test_glyph_dispatcher_logging.py

import json
import pytest

from backend.modules.glyphos.glyph_dispatcher import GlyphDispatcher
from backend.modules.consciousness.state_manager import StateManager


def extract_logs(output: str):
    """Helper: parse [LOG] lines into JSON dicts."""
    logs = []
    for line in output.splitlines():
        if line.startswith("[LOG]"):
            payload = json.loads(line.replace("[LOG] ", ""))
            logs.append(payload)
    return logs


@pytest.fixture
def dispatcher():
    state = StateManager()
    return GlyphDispatcher(state)


def test_dispatch_success_log(capsys, dispatcher):
    # Known glyph op: "log"
    glyph = {"action": "log", "message": "HelloGlyph"}
    result = dispatcher.dispatch(glyph)

    # Dispatcher should return ok result
    assert result["status"] == "ok"

    # Logs should include a structured [LOG] entry
    output = capsys.readouterr().out
    logs = extract_logs(output)
    assert logs, "Expected at least one log line"
    log = logs[-1]
    assert log["event"] == "registry_execute"
    assert log["op"] == "log"
    assert log["canonical"] == "glyph:log"
    assert log["status"] == "ok"
    assert log["result"] == result


def test_dispatch_error_log(capsys, dispatcher):
    # Fake glyph op: should fail
    glyph = {"action": "FAKE_GLYPH"}
    result = dispatcher.dispatch(glyph)

    # Dispatcher should fall back and return unknown
    assert result["status"] == "unknown"

    # Logs should include an error/stub entry
    output = capsys.readouterr().out
    logs = extract_logs(output)
    assert logs, "Expected at least one log line"
    log = logs[-1]
    assert log["event"] == "registry_execute"
    assert log["op"] == "FAKE_GLYPH"
    assert log["canonical"] == "glyph:FAKE_GLYPH"
    assert log["status"] in ("error", "stub")