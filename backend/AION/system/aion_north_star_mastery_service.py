#!/usr/bin/env python3
"""Continuously reconstruct AION's North Star mastery and goal portfolio."""
from __future__ import annotations

import os
import time
from pathlib import Path

from backend.modules.hexcore.constitutional_north_star_mastery_registry import run


def run_service() -> None:
    repo_root = Path(os.getenv("AION_REPO_ROOT", ".")).resolve()
    interval = max(60.0, float(os.getenv("AION_NORTH_STAR_INTERVAL", "900")))
    while True:
        apprentice_state = repo_root / "backend/modules/hexcore/data/autonomous_general_apprentice/state.json"
        if apprentice_state.exists():
            run(
                repo_root=repo_root,
                apprentice_state_path=apprentice_state,
                state_path=repo_root / "backend/modules/hexcore/data/constitutional_north_star/state.json",
                result_path=repo_root / "results/hexcore_constitutional_north_star_mastery_registry.json",
            )
        time.sleep(interval)


if __name__ == "__main__":
    run_service()
