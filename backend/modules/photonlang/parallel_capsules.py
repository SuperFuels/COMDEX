# Photon v0.2 - Parallel Capsule Engine
# Async + fairness + telemetry

import asyncio
import time
from collections import deque
from backend.modules.photonlang.telemetry import emit_sqi_event
from backend.modules.photonlang.executor import execute_capsule

DEFAULT_TIMEOUT = 2.0  # seconds


class ParallelCapsuleExecutor:
    def __init__(self, max_parallel=4):
        self.max_parallel = max_parallel
        self.queue = deque()
        self.running = set()
        self._stop = False

    def submit(self, capsule):
        self.queue.append(capsule)

    def stop(self):
        self._stop = True

    async def _run_capsule(self, capsule):
        cid = capsule.get("id") or f"cap-{id(capsule)}"
        start = time.time()

        # Telemetry start
        emit_sqi_event("capsule_start", {"id": cid})

        try:
            result = await asyncio.wait_for(
                execute_capsule(capsule),
                timeout=DEFAULT_TIMEOUT
            )
            status = "ok"

        except asyncio.TimeoutError:
            result = {"error": "timeout"}
            status = "timeout"

        except Exception as e:
            result = {"error": str(e)}
            status = "error"

        elapsed = round(time.time() - start, 4)

        # Telemetry finish
        emit_sqi_event("capsule_done", {
            "id": cid,
            "status": status,
            "elapsed": elapsed,
        })

        self.running.remove(cid)
        return result

    async def run(self):
        while not self._stop or self.queue:
            # launch new tasks respecting parallel cap
            while len(self.running) < self.max_parallel and self.queue:
                cap = self.queue.popleft()
                cid = cap.get("id") or f"cap-{id(cap)}"
                self.running.add(cid)
                asyncio.create_task(self._run_capsule(cap))

            await asyncio.sleep(0.001)  # fairness tick