# backend/modules/dimensions/time_controller.py

import time
from datetime import datetime
from typing import Dict, Optional
from collections import defaultdict
from copy import deepcopy

class TimeController:
    def __init__(self):
        self.container_time: Dict[str, int] = defaultdict(int)  # tick per container
        self.snapshots: Dict[str, Dict[int, dict]] = defaultdict(dict)  # container_id -> tick -> snapshot
        self.loop_enabled: Dict[str, bool] = defaultdict(lambda: False)
        self.loop_range: Dict[str, tuple] = defaultdict(lambda: (0, 0))
        self.decay_enabled: Dict[str, bool] = defaultdict(lambda: False)
        self.last_decay: Dict[str, float] = defaultdict(lambda: time.time())

    def tick(self, container_id: str, state: dict):
        tick = self.container_time[container_id] + 1
        self.container_time[container_id] = tick
        self.snapshots[container_id][tick] = deepcopy(state)

        # Decay logic
        if self.decay_enabled[container_id] and time.time() - self.last_decay[container_id] > 3.0:
            self._apply_decay(container_id)
            self.last_decay[container_id] = time.time()

        # Loop logic
        if self.loop_enabled[container_id]:
            loop_start, loop_end = self.loop_range[container_id]
            if tick >= loop_end:
                self.container_time[container_id] = loop_start

    def rewind(self, container_id: str, target_tick: int) -> Optional[dict]:
        if target_tick in self.snapshots[container_id]:
            self.container_time[container_id] = target_tick
            return deepcopy(self.snapshots[container_id][target_tick])
        return None

    def _apply_decay(self, container_id: str):
        current_tick = self.container_time[container_id]
        state = self.snapshots[container_id].get(current_tick)
        if not state: return

        for coord, cube in state.get("cubes", {}).items():
            glyph = cube.get("glyph", "")
            if glyph and len(glyph) > 1:
                cube["glyph"] = glyph[:-1]  # shrink glyph
        self.snapshots[container_id][current_tick] = state

    def enable_loop(self, container_id: str, start_tick: int, end_tick: int):
        self.loop_enabled[container_id] = True
        self.loop_range[container_id] = (start_tick, end_tick)

    def disable_loop(self, container_id: str):
        self.loop_enabled[container_id] = False

    def enable_decay(self, container_id: str):
        self.decay_enabled[container_id] = True

    def disable_decay(self, container_id: str):
        self.decay_enabled[container_id] = False

    def get_tick(self, container_id: str) -> int:
        return self.container_time[container_id]

    def get_snapshot(self, container_id: str, tick: int) -> Optional[dict]:
        return deepcopy(self.snapshots[container_id].get(tick))

    def get_status(self, container_id: str) -> dict:
        return {
            "tick": self.get_tick(container_id),
            "loop_enabled": self.loop_enabled[container_id],
            "loop_range": self.loop_range[container_id],
            "decay_enabled": self.decay_enabled[container_id],
        }