"""
🟢 GWave Replay Emitter — SRK-19 Task 4
Replays recorded .gwv holographic visualization data into GHX/QFC runtime bridges.

Features:
 • Loads validated .gwv snapshot files
 • Sequentially emits frames back into GHX/QFC visualization layers
 • Supports playback control (pause/resume/loop)
 • Optional validation via safe_validate_gwv()

Usage Example:
    from backend.modules.glyphwave.emit_gwave_replay import emit_gwave_frames
    await emit_gwave_frames(ghx_bridge, "snapshots/gwv/test_overlay_20251014.gwv")
"""

import os
import json
import asyncio
from typing import Any, Dict, AsyncGenerator, Optional

from backend.modules.glyphwave.schema.validate_gwv import safe_validate_gwv


async def load_gwv_file(path: str) -> Dict[str, Any]:
    """Load and validate a .gwv file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"GWV file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Post-load validation (non-fatal but logged)
    safe_validate_gwv(path)
    return data


async def emit_gwave_frames(
    ghx_bridge,
    gwv_path: str,
    delay: float = 0.15,
    loop: bool = False,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Replay frames from a .gwv file into the GHX/QFC bridge.
    Yields each frame for external listeners.
    """
    gwv_data = await load_gwv_file(gwv_path)
    frames = gwv_data.get("frames", [])

    if not frames:
        raise ValueError(f"No frames found in {gwv_path}")

    while True:
        for entry in frames:
            frame = entry.get("frame", {})
            if not frame:
                continue

            # Emit to GHX bridge if available
            if hasattr(ghx_bridge, "ingest_frame"):
                await ghx_bridge.ingest_frame(frame)

            yield frame
            await asyncio.sleep(delay)

        if not loop:
            break


class ReplayController:
    """Controls playback of GWave replays."""

    def __init__(self, ghx_bridge, gwv_path: str, delay: float = 0.15, loop: bool = False):
        self.ghx_bridge = ghx_bridge
        self.gwv_path = gwv_path
        self.delay = delay
        self.loop = loop
        self._task: Optional[asyncio.Task] = None
        self._paused = asyncio.Event()
        self._paused.set()  # initially unpaused

    async def _run(self):
        async for frame in emit_gwave_frames(
            self.ghx_bridge, self.gwv_path, delay=self.delay, loop=self.loop
        ):
            await self._paused.wait()  # wait if paused
            # (Optional) could log or update UI
        return True

    async def start(self):
        if self._task and not self._task.done():
            return  # already running
        self._task = asyncio.create_task(self._run())

    def pause(self):
        self._paused.clear()

    def resume(self):
        self._paused.set()

    def stop(self):
        if self._task:
            self._task.cancel()