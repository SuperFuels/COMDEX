#!/usr/bin/env python3
"""Supervise evidence refresh, autonomous curriculum and delayed outcomes."""
from __future__ import annotations

import os
import time
from pathlib import Path

from backend.modules.hexcore.autonomous_general_apprentice import (
    AutonomousGeneralApprentice,
)
from backend.modules.hexcore.wall_clock_scheduler import wait_for_wall_clock
from backend.modules.hexcore.standalone_task_governance import governed_standalone_task


def run_service() -> None:
    repo_root = Path(os.getenv("AION_REPO_ROOT", ".")).resolve()
    state_path = repo_root / "backend/modules/hexcore/data/autonomous_general_apprentice/state.json"
    interval = max(30.0, float(os.getenv("AION_GENERAL_APPRENTICE_INTERVAL", "300")))
    while True:
        apprentice = AutonomousGeneralApprentice(state_path=state_path, repo_root=repo_root)
        if apprentice.state.get("mission"):
            mission = apprentice.state.get("mission") or {}
            task_text = str(
                mission.get("objective") or mission.get("description")
                or mission.get("mission_id") or "Refresh apprentice evidence and bind delayed outcome"
            )
            with governed_standalone_task(
                repo_root=repo_root,
                service_id="general_apprentice",
                task_text=task_text,
            ) as governed:
                apprentice.refresh_evidence()
                outcome = apprentice.bind_new_delayed_outcome()
                if outcome.get("status") == "bound":
                    apprentice.close_generation()
                    apprentice.next_task()
                governed.finish(outcome, verified=False)
        wait_for_wall_clock(interval)


if __name__ == "__main__":
    run_service()
