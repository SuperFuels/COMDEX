#!/usr/bin/env python3
"""Publish and supervise the frozen open-mission compounding campaign."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from backend.modules.hexcore.file_locking import acquire_process_lock
from backend.modules.hexcore.wall_clock_scheduler import wait_for_wall_clock
from backend.modules.hexcore.open_mission_compounding_governor import (
    OpenMissionCompoundingGovernor,
)
from backend.modules.hexcore.standalone_task_governance import governed_standalone_task


def _consume_json_inbox(governor, inbox: Path, rejected: Path) -> None:
    inbox.mkdir(parents=True, exist_ok=True)
    rejected.mkdir(parents=True, exist_ok=True)
    for path in sorted(inbox.glob("*.json")):
        try:
            packet = json.loads(path.read_text(encoding="utf-8"))
            kind = packet.pop("kind", "mission")
            if kind == "mission":
                governor.register_mission(packet)
            elif kind == "outcome":
                governor.record_outcome(packet)
            elif kind == "repair":
                governor.record_repair(packet)
            elif kind == "source_close":
                governor.close_source(mission_id=str(packet["mission_id"]))
            elif kind == "retention":
                governor.record_retention(packet)
            else:
                raise ValueError(f"unsupported packet kind: {kind}")
            path.rename(path.with_suffix(".consumed"))
        except Exception as error:
            destination = rejected / path.name
            destination.write_text(json.dumps({
                "packet": path.name, "error": str(error),
            }, indent=2, sort_keys=True), encoding="utf-8")
            path.rename(path.with_suffix(".rejected"))


def run_service() -> None:
    repo_root = Path(os.getenv("AION_REPO_ROOT", ".")).resolve()
    lock = acquire_process_lock(
        repo_root / "backend/modules/hexcore/data/service_locks/open_mission_compounding.lock"
    )
    if lock is None:
        return
    data_root = repo_root / "backend/modules/hexcore/data/open_mission_compounding"
    state_path = data_root / "state.json"
    interval = max(5.0, float(os.getenv("AION_OPEN_MISSION_INTERVAL", "30")))
    while True:
        # The matched executor is an independent writer.  Reload the
        # authority-owned state every cycle so this publisher cannot overwrite
        # a newer executor result with a stale in-memory snapshot.
        with governed_standalone_task(
            repo_root=repo_root,
            service_id="open_mission_compounding",
            task_text="Reconcile governed mission packets and publish the frozen compounding evidence snapshot",
        ) as governed:
            governor = OpenMissionCompoundingGovernor(state_path=state_path)
            _consume_json_inbox(governor, data_root / "inbox", data_root / "rejected")
            snapshot_path = repo_root / "results/aion_open_mission_compounding_status.json"
            result = governor.publish_snapshot(snapshot_path)
            governed.finish(result or {"status": "snapshot_published"}, verified=False)
        wait_for_wall_clock(interval)


if __name__ == "__main__":
    run_service()
