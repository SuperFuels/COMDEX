#!/usr/bin/env python3
"""Continuously reconstruct AION's North Star mastery and goal portfolio."""
from __future__ import annotations

import os
import time
from pathlib import Path

from backend.modules.hexcore.constitutional_north_star_mastery_registry import run
from backend.modules.hexcore.wall_clock_scheduler import wait_for_wall_clock
from backend.modules.hexcore.standalone_task_governance import governed_standalone_task


def run_service() -> None:
    repo_root = Path(os.getenv("AION_REPO_ROOT", ".")).resolve()
    interval = max(60.0, float(os.getenv("AION_NORTH_STAR_INTERVAL", "900")))
    while True:
        apprentice_state = repo_root / "backend/modules/hexcore/data/autonomous_general_apprentice/state.json"
        if apprentice_state.exists():
            result_path = repo_root / "results/hexcore_constitutional_north_star_mastery_registry.json"
            with governed_standalone_task(
                repo_root=repo_root,
                service_id="north_star_mastery",
                task_text="Reconstruct the constitutional North-Star mastery and goal portfolio",
            ) as governed:
                result = run(
                    repo_root=repo_root,
                    apprentice_state_path=apprentice_state,
                    state_path=repo_root / "backend/modules/hexcore/data/constitutional_north_star/state.json",
                    result_path=result_path,
                )
                governed.finish(
                    result,
                    verified=bool(isinstance(result, dict) and result.get("passed") is True),
                    evidence_refs=[str(result_path)] if result_path.exists() else [],
                )
        wait_for_wall_clock(interval)


if __name__ == "__main__":
    run_service()
