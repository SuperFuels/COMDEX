# backend/modules/codex/codex_scheduler.py

"""
Codex Scheduler

Handles symbolic triggering and conditional glyph execution.
Supports:
- If/Then logic via glyph rules
- Scheduled or delayed execution
- Contextual activation from memory, goals, or container state
"""

import time
from typing import Callable, List, Dict
from backend.modules.codex.codex_core import CodexCore

class ScheduledGlyph:
    def __init__(self, glyph: str, condition: Callable = None, delay: float = 0):
        self.glyph = glyph
        self.condition = condition  # Callable returning bool
        self.delay = delay  # Time to wait before execution
        self.created_at = time.time()
        self.executed = False

class CodexScheduler:
    def __init__(self):
        self.queue: List[ScheduledGlyph] = []
        self.codex = CodexCore()

    def schedule_glyph(self, glyph: str, condition: Callable = None, delay: float = 0):
        sg = ScheduledGlyph(glyph, condition, delay)
        self.queue.append(sg)
        return sg

    def run_tick(self):
        now = time.time()
        for sg in self.queue:
            if sg.executed:
                continue

            if sg.delay > 0 and now - sg.created_at < sg.delay:
                continue

            if sg.condition and not sg.condition():
                continue

            print(f"⏱ Executing scheduled glyph: {sg.glyph}")
            self.codex.execute(sg.glyph)
            sg.executed = True

    def flush(self):
        self.queue.clear()

    def pending(self):
        return [g for g in self.queue if not g.executed]


# Example usage:
if __name__ == "__main__":
    scheduler = CodexScheduler()

    def condition():
        return True

    scheduler.schedule_glyph("\u27e6 Logic | Trigger: Grow \u2192 \u2b50 \u27e7", condition=condition)

    while True:
        scheduler.run_tick()
        time.sleep(1)