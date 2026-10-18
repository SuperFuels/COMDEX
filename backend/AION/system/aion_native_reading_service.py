#!/usr/bin/env python3
"""Dedicated bounded loop for Aion's online and local reading academy."""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import tempfile
import time

from backend.modules.aion_cognition.native_reading_academy import NativeReadingAcademy
from backend.modules.aion_cognition.native_lexical_intelligence import default_database_path


RUNNING = True


def _resource_status(root: Path) -> dict:
    """Keep background reading away from macOS swap-emergency conditions."""
    minimum_free = max(
        5 * 1024**3,
        # The reader streams a bounded batch and discards downloaded source
        # material after extraction.  Fifteen GiB still leaves a substantial
        # emergency reserve, while avoiding a permanent pause on Macs whose
        # normal free-space level sits just below the former 20 GiB default.
        int(os.getenv("AION_READING_MIN_FREE_BYTES", str(15 * 1024**3))),
    )
    free_bytes = shutil.disk_usage(root).free
    return {
        "safe": free_bytes >= minimum_free,
        "free_bytes": free_bytes,
        "minimum_free_bytes": minimum_free,
    }


def _stop(_signum: int, _frame: object) -> None:
    global RUNNING
    RUNNING = False


def _write_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent,
        prefix="native-reading-state-", suffix=".tmp", delete=False,
    ) as handle:
        json.dump(state, handle, ensure_ascii=False, default=str)
        temporary = Path(handle.name)
    temporary.replace(path)


def run_service() -> None:
    root = Path(os.getenv("AION_REPO_ROOT", ".")).resolve()
    if os.getenv("AION_NATIVE_READING_ENABLED", "0") not in {"1", "true", "True"}:
        return
    interval = max(30.0, float(os.getenv("AION_READING_ACADEMY_INTERVAL", "60")))
    batch = max(1, min(100, int(os.getenv("AION_READING_ACADEMY_BATCH", "40"))))
    lock_path = root / "backend/modules/hexcore/data/service_locks/native_reading.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_handle = lock_path.open("a+")
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return
    state_path = default_database_path(root).parent / "native_reading_service_state.json"
    initial_resources = _resource_status(root)
    try:
        _write_state(state_path, {
            "status": "initializing",
            "pid": os.getpid(),
            "batch_size": batch,
            "interval_seconds": interval,
            "resources": initial_resources,
            "updated_epoch": time.time(),
        })
    except OSError:
        pass
    academy = NativeReadingAcademy(repo_root=root)
    while RUNNING:
        started = time.time()
        resources = _resource_status(root)
        if not resources["safe"]:
            state = {
                "status": "paused_resource_pressure",
                "pid": os.getpid(),
                "batch_size": batch,
                "interval_seconds": interval,
                "resources": resources,
                "updated_epoch": time.time(),
            }
            try:
                _write_state(state_path, state)
            except OSError:
                pass
            time.sleep(min(60.0, interval))
            continue
        try:
            # Publish the transition before a potentially long parsing batch;
            # otherwise the dashboard continues to show the previous
            # resource-pressure pause for the entire active cycle.
            _write_state(state_path, {
                "status": "running",
                "pid": os.getpid(),
                "batch_size": batch,
                "interval_seconds": interval,
                "resources": resources,
                "cycle_started_epoch": started,
                "updated_epoch": time.time(),
            })
            outcome = academy.run_cycle(limit=batch)
            state = {"status": "healthy", "pid": os.getpid(), "batch_size": batch,
                     "interval_seconds": interval, "cycle": outcome,
                     "resources": resources,
                     "updated_epoch": time.time()}
        except Exception as exc:
            state = {"status": "error", "pid": os.getpid(), "batch_size": batch,
                     "interval_seconds": interval,
                     "error": f"{type(exc).__name__}: {exc}",
                     "updated_epoch": time.time()}
        try:
            _write_state(state_path, state)
        except OSError:
            pass
        remaining = max(0.25, interval - (time.time() - started))
        deadline = time.time() + remaining
        while RUNNING and time.time() < deadline:
            time.sleep(min(0.5, deadline - time.time()))


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    run_service()
