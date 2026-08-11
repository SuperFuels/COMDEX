"""Unattended completion monitor for already-approved and submitted render jobs."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from backend.modules.aion_business.runtime.creative_render_service import CreativeRenderService


class CreativeRenderPollingService:
    def __init__(self) -> None:
        self.service = CreativeRenderService()
        self.interval = max(10, int(os.getenv("TESSARIS_CREATIVE_RENDER_POLL_SECONDS", "20")))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="tessaris-creative-render-poller", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            self.poll_once()

    def poll_once(self) -> dict[str, int]:
        counts = {"checked": 0, "completed": 0, "failed": 0}
        workspaces = self.service.assets.workspaces_root()
        for path in workspaces.glob("*/marketing/creative_jobs/*/job.json"):
            try:
                job = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if job.get("status") not in {"submitted", "processing", "queued"}:
                continue
            workspace_id = str(job.get("workspace_id") or path.parents[3].name)
            counts["checked"] += 1
            try:
                result = self.service.poll(workspace_id, job["id"])
                if result.get("status") == "completed":
                    counts["completed"] += 1
                elif result.get("status") == "failed":
                    counts["failed"] += 1
            except Exception:
                counts["failed"] += 1
        return counts


CREATIVE_RENDER_POLLER = CreativeRenderPollingService()
