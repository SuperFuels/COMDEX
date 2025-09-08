# File: backend/tests/test_beam_tick_loop.py

import os
import json
import pytest
from unittest.mock import patch, MagicMock

from backend.modules.codex.beam_model import Beam
from backend.modules.runtime.beam_tick_loop import beam_tick_loop
from backend.modules.sqi.metrics import collapse_timeline_writer


def test_beam_tick_execution(tmp_path):
    """
    Runs a basic test on the beam_tick_loop to ensure beam evolution,
    SQI scoring, coherence change, and collapse event logging.
    """

    container_id = "ucs_ephemeral"
    timeline_path = os.path.join("logs", "collapse_timeline", f"{container_id}.timeline.jsonl")

    # 🔧 Patch collapse logging to force test path
    def patched_log_collapse_event(beam, tick_num, container_id=None):
        return collapse_timeline_writer.log_collapse_event(beam, tick_num, container_id=container_id)

    # ❌ Clean old logs
    if os.path.exists(timeline_path):
        os.remove(timeline_path)

    test_beam = Beam(
        id="tick_test_001",
        logic_tree={
            "type": "root",
            "children": [{"type": "leaf", "label": "⊗ AND", "children": []}]
        },
        glyphs=[],
        phase=0.5,
        amplitude=1.0,
        coherence=1.0,
        origin_trace=["test"]
    )
    test_beam.container_id = container_id  # ✅ Add container_id for logging

    # ✅ Patch collapse logging and disable container injection
    with patch("backend.modules.runtime.beam_tick_loop.log_collapse_event", patched_log_collapse_event), \
         patch("backend.modules.runtime.beam_tick_loop.inject_beam_into_container", MagicMock()):

        result = beam_tick_loop([test_beam], max_ticks=5, delay=0, container_id=container_id)

    # ✅ Basic checks
    assert isinstance(result, list)
    assert any(beam.id == "tick_test_001" for beam in result)

    mutated_beam = result[0]
    assert hasattr(mutated_beam, "sqi_score")
    assert isinstance(mutated_beam.sqi_score, float)
    assert 0.0 <= mutated_beam.coherence <= 1.0
    assert mutated_beam.phase != 0.5

    # ✅ Validate timeline file exists and contains events
    assert os.path.exists(timeline_path), f"Collapse timeline file should exist: {timeline_path}"

    with open(timeline_path, "r") as f:
        lines = f.readlines()

    assert len(lines) >= 1, "Collapse timeline should contain at least 1 event"
    event = json.loads(lines[0])
    assert "tick" in event
    assert "beam_id" in event
    assert "coherence" in event
    assert isinstance(event["sqi_score"], float)

    print(f"✅ Collapse timeline entry: {event}")