"""Sleep helpers that remain prompt after a macOS sleep/wake cycle."""
from __future__ import annotations

import time
from collections.abc import Callable


def wait_for_wall_clock(
    seconds: float,
    *,
    max_chunk_seconds: float = 30.0,
    clock: Callable[[], float] = time.time,
    sleeper: Callable[[float], None] = time.sleep,
) -> None:
    """Wait until a wall-clock deadline, checking frequently after system wake.

    A single long ``time.sleep`` may use a monotonic clock that does not include
    time spent in macOS system sleep.  Small bounded chunks plus a wall-clock
    deadline ensure overdue learning cycles resume within one chunk after wake.
    """
    duration = max(0.0, float(seconds))
    chunk = max(1.0, float(max_chunk_seconds))
    deadline = clock() + duration
    while True:
        remaining = deadline - clock()
        if remaining <= 0:
            return
        sleeper(min(chunk, remaining))
