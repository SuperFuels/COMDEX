# File: backend/modules/runtime/beam_scheduler.py

"""
beam_scheduler.py
==================

Symbolic beam-aware scheduler.
Handles priority sorting, timed activation, and mutation queue control
for QWave beam processing and GPU/CPU balance.

Supports:
- Heap-based fast scheduling (priority + time)
- Reinjection of mutated beams
- Optional logging or future container hooks
"""

import heapq
import time
import logging
from typing import List, Optional
from backend.modules.glyphwave.core.wave_state import WaveState

logger = logging.getLogger("Scheduler")


class ScheduledBeam:
    def __init__(self, beam: WaveState, priority: int = 0, activate_at: Optional[float] = None):
        self.beam = beam
        self.priority = priority
        self.activate_at = activate_at or time.time()

    def __lt__(self, other):
        # Lower activation time first, higher priority next
        return (self.activate_at, -self.priority) < (other.activate_at, -other.priority)


class BeamScheduler:
    def __init__(self):
        self.queue: List[ScheduledBeam] = []

    def schedule_beam(self, beam: WaveState, priority: int = 0, delay_sec: float = 0.0):
        activation_time = time.time() + delay_sec
        heapq.heappush(self.queue, ScheduledBeam(beam, priority, activation_time))
        logger.debug(f"[Scheduler] 📥 Beam {beam.id} scheduled (priority={priority}, delay={delay_sec}s)")

    def get_ready_beams(self) -> List[WaveState]:
        now = time.time()
        ready: List[WaveState] = []

        while self.queue and self.queue[0].activate_at <= now:
            scheduled = heapq.heappop(self.queue)
            ready.append(scheduled.beam)
            logger.debug(f"[Scheduler] 🚀 Beam {scheduled.beam.id} activated")

        return ready

    def has_pending_beams(self) -> bool:
        return bool(self.queue)

    def peek_next_activation_time(self) -> Optional[float]:
        return self.queue[0].activate_at if self.queue else None

    def clear(self):
        logger.info("[Scheduler] ⚠️ Clearing all scheduled beams")
        self.queue.clear()

    def reinject_beam(self, beam: WaveState, delay_sec: float = 0.1):
        """Requeues a mutated or looped beam with small delay."""
        beam.status = "reinject"
        self.schedule_beam(beam, priority=beam.sqi_score or 0, delay_sec=delay_sec)
        logger.debug(f"[Scheduler] 🔁 Reinjecting beam {beam.id} after mutation")


# Global scheduler instance (can be replaced with per-container schedulers)
global_scheduler = BeamScheduler()