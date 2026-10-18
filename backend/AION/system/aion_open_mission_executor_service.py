#!/usr/bin/env python3
"""Run bounded unmatched mission work while the governor owns evidence."""
from __future__ import annotations

import json
import os
import time
import traceback
from pathlib import Path

from backend.modules.hexcore.file_locking import acquire_process_lock
from backend.modules.hexcore.wall_clock_scheduler import wait_for_wall_clock
from backend.modules.hexcore.open_mission_compounding_executor import (
    run, run_due_retention, run_public_change, run_repository_repair,
    run_structured_repair_portfolio,
)
from backend.modules.hexcore.standalone_task_governance import governed_standalone_task


def run_service() -> None:
    repo_root = Path(os.getenv("AION_REPO_ROOT", ".")).resolve()
    lock = acquire_process_lock(
        repo_root / "backend/modules/hexcore/data/service_locks/open_mission_executor.lock"
    )
    if lock is None:
        return
    status_path = repo_root / "results/aion_open_mission_executor_status.json"
    interval = max(60.0, float(os.getenv("AION_OPEN_MISSION_EXECUTOR_INTERVAL", "900")))
    while True:
        try:
            with governed_standalone_task(
                repo_root=repo_root,
                service_id="open_mission_executor",
                task_text=(
                    "Execute the next bounded open mission, repository repair, structured repair, "
                    "public-change forecast and due closed-book retention check"
                ),
            ) as governed:
                result = run(repo_root=repo_root)
                repository_result = run_repository_repair(repo_root=repo_root)
                structured_result = run_structured_repair_portfolio(repo_root=repo_root)
                public_result = run_public_change(repo_root=repo_root)
                public_snapshot = public_result.get("snapshot")
                if public_result.get("status") == "bound":
                    # Do not leave a gap between scoring one public outcome and
                    # freezing the next forecast.  The next row must remain unseen
                    # when its commitment is made.
                    next_public = run_public_change(repo_root=repo_root)
                    next_public["last_scored"] = {
                        "revealed_cycle": public_result.get("revealed_cycle"),
                        "arms": [
                            {"arm": row.get("arm"), "score": row.get("score")}
                            for row in public_result.get("arms") or []
                        ],
                    }
                    public_result = next_public
                retention_result = run_due_retention(repo_root=repo_root)
                governed.finish(
                    {"status": "cycle_complete", "mission_id": result.get("mission_id")},
                    verified=False,
                )
            latest_snapshot = public_snapshot or public_result.get("snapshot") or result["snapshot"]
            status = {
                "status": "cycle_complete",
                "mission_id": result["mission_id"],
                "repository_mission_id": repository_result["mission_id"],
                "structured_mission_ids": [
                    row["mission_id"] for row in structured_result["missions"]
                ],
                "next_mission_wave": structured_result.get("next_wave"),
                "cohort_complete_missions": latest_snapshot["cohort_complete_missions"],
                "ten_x_claim_gate_passed": latest_snapshot["ten_x_claim_gate_passed"],
                "public_change": public_result,
                "retention": retention_result,
                "updated_at": time.time(),
            }
        except Exception as error:
            status = {
                "status": "error", "error": str(error),
                "traceback": traceback.format_exc()[-6000:], "updated_at": time.time(),
            }
        temporary = status_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(status_path)
        wait_for_wall_clock(interval)


if __name__ == "__main__":
    run_service()
