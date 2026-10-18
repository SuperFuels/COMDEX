#!/usr/bin/env python3
"""Persistent Arena v15 observation service for week-scale evidence."""
from __future__ import annotations

import json
import os
import tempfile
import time
import traceback
from pathlib import Path

from backend.modules.hexcore.long_duration_real_outcome_campaign import run_cycle
from backend.modules.hexcore.file_locking import acquire_process_lock
from backend.modules.hexcore.wall_clock_scheduler import wait_for_wall_clock
from backend.modules.hexcore.standalone_task_governance import governed_standalone_task


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.{os.getpid()}.", suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def run_service() -> None:
    repo_root = Path(os.getenv("AION_REPO_ROOT", ".")).resolve()
    process_lock = acquire_process_lock(
        repo_root / "backend/modules/hexcore/data/service_locks/long_duration_campaign.lock")
    if process_lock is None:
        return
    interval = max(300.0, float(os.getenv("AION_LONG_CAMPAIGN_INTERVAL", "7200")))
    state_path = repo_root / "results/hexcore_long_duration_campaign_v15_state.json"
    ledger_path = repo_root / "results/hexcore_long_duration_campaign_v15_ledger.jsonl"
    service_path = repo_root / "results/aion_long_duration_campaign_service_status.json"
    while True:
        try:
            with governed_standalone_task(
                repo_root=repo_root,
                service_id="long_duration_campaign",
                task_text="Observe and independently score the next mature long-duration campaign outcome",
            ) as governed:
                state = run_cycle(
                    repo_root=repo_root,
                    state_path=state_path,
                    ledger_path=ledger_path,
                    minimum_hours=24.0,
                    minimum_cycles=12,
                )
                governed.finish(
                    state,
                    verified=bool(state.get("status") == "complete"),
                    evidence_refs=[str(ledger_path)] if ledger_path.exists() else [],
                )
            status = {
                "status": "active",
                "updated_epoch": time.time(),
                "next_observation_after_seconds": interval,
                "campaign_status": state.get("status"),
                "completed_cycles": len(state.get("cycles") or []),
                "last_cycle_epoch": state.get("last_cycle_epoch"),
                "persistent_until_stopped": True,
            }
        except Exception as error:
            status = {
                "status": "error",
                "updated_epoch": time.time(),
                "next_observation_after_seconds": min(interval, 900.0),
                "error": type(error).__name__,
                "detail": str(error),
                "traceback": traceback.format_exc()[-4000:],
                "persistent_until_stopped": True,
            }
        _write(service_path, status)
        wait_for_wall_clock(float(status["next_observation_after_seconds"]))


if __name__ == "__main__":
    run_service()
