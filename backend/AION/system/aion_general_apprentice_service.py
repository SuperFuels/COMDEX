#!/usr/bin/env python3
"""Supervise evidence refresh, autonomous curriculum and delayed outcomes."""
from __future__ import annotations

import os
import time
from pathlib import Path

from backend.modules.hexcore.autonomous_general_apprentice import (
    AutonomousGeneralApprentice,
)


def run_service() -> None:
    repo_root = Path(os.getenv("AION_REPO_ROOT", ".")).resolve()
    state_path = repo_root / "backend/modules/hexcore/data/autonomous_general_apprentice/state.json"
    interval = max(30.0, float(os.getenv("AION_GENERAL_APPRENTICE_INTERVAL", "300")))
    while True:
        apprentice = AutonomousGeneralApprentice(state_path=state_path, repo_root=repo_root)
        if apprentice.state.get("mission"):
            apprentice.refresh_evidence()
            outcome = apprentice.bind_new_delayed_outcome()
            if outcome.get("status") == "bound":
                apprentice.close_generation()
                apprentice.next_task()
        time.sleep(interval)


if __name__ == "__main__":
    run_service()
