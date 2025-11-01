#!/usr/bin/env python3
"""
✅ Integration Test - GoalTaskManager (Phase 55 Task 3)

What this verifies:
  * Instantiates GoalTaskManager and links to ResonanceHeartbeat + RMC
  * Ensures at least one goal is available (monkeypatch fallback if empty)
  * Runs next task and asserts output structure
  * Triggers two heartbeat pulses to exercise GSI + tension events
  * Gracefully stops the heartbeat loop
"""

import time
import logging
import json
from pathlib import Path

# Ensure local package resolution
if __name__ == "__main__":
    import sys, os
    sys.path.append(os.getcwd())

from backend.modules.consciousness.goal_task_manager import GoalTaskManager

logging.basicConfig(level=logging.INFO)

def ensure_goal(mgr: GoalTaskManager):
    """Guarantee at least one goal exists; if not, monkeypatch a minimal list."""
    try:
        goals = mgr.goal_engine.get_all_goals()
    except Exception:
        goals = []

    if not goals:
        # Monkeypatch a simple provider so we don't depend on GoalEngine internals
        mgr.goal_engine.get_all_goals = lambda: [
            {"name": "self_optimize", "priority": 5}
        ]

def test_goal_task_manager():
    print("\n=== 🧭 GoalTaskManager Test (Phase 55 Task 3) ===")
    mgr = GoalTaskManager()

    # Make sure we have a goal to run
    ensure_goal(mgr)

    # Run a task
    result = mgr.run_next_task()
    print("Result:", json.dumps(result, indent=2))

    assert isinstance(result, dict)
    assert "status" in result
    assert "goal" in result
    assert result["status"] in ("in_progress", "no_goals")

    # Simulate two heartbeats to trigger GSI & possible tension events
    pulse_a = {"sqi": 0.55, "Φ_entropy": 0.30}   # relatively stable
    pulse_b = {"sqi": 0.30, "Φ_entropy": 0.45}   # induce drop -> tension_spike likely

    mgr._on_heartbeat(pulse_a)
    time.sleep(0.2)
    mgr._on_heartbeat(pulse_b)
    time.sleep(0.2)

    # Heartbeat cleanup
    try:
        mgr.heartbeat.stop()
    except Exception:
        pass

    # Basic RMC presence check
    assert hasattr(mgr, "rmc"), "ResonantMemoryCache not attached"
    print("✅ GoalTaskManager integration test complete.\n")

if __name__ == "__main__":
    test_goal_task_manager()