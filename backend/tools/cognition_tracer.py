#!/usr/bin/env python3
"""
🧠 Cognition Tracer — monitors SQI deltas in real time
Decides when to:
  • enter dream mode (SQI decay / low innovation)
  • wake and commit (SQI improvement threshold)
"""

import time
import asyncio
from datetime import datetime
from backend.modules.resonant_memory.resonant_memory_cache import ResonantMemoryCache

rmc = ResonantMemoryCache()

MIN_DELTA = 0.01   # mutate noise floor
DREAM_THRESHOLD = -0.05  # if SQI consistently drops → dream
WAKE_THRESHOLD = 0.04    # if SQI gains → wake & commit

history = []

async def run_tracer():
    print("✨ Cognition Tracer active...")
    state = "awake"

    while True:
        last = rmc.cache.get("last_sample")
        if not last:
            await asyncio.sleep(0.5)
            continue

        sqi = last.get("sqi", 0.0)
        delta = last.get("delta", 0.0)
        ts = last.get("ts", time.time())

        if abs(delta) < MIN_DELTA:
            await asyncio.sleep(0.3)
            continue

        history.append(delta)
        history[:] = history[-100:]

        avg = sum(history)/len(history)

        print(f"[{datetime.utcnow().isoformat(timespec='seconds')}] SQI {sqi:.3f} Δ {delta:+.3f} μΔ={avg:+.3f} → {state}")

        # 💤 Enter dream mode
        if state == "awake" and avg < DREAM_THRESHOLD:
            print("🌙 Entering dream mode (SQI stagnation)")
            state = "dream"
            rmc.push_sample(source="dream_loop", sqi=sqi, rho=sqi, delta=avg)

        # 🚀 Wake up & commit
        if state == "dream" and avg > WAKE_THRESHOLD:
            print("⚡ Waking cognition (creative breakthrough)")
            state = "awake"
            # future: push commit to SCI / atoms
            rmc.push_sample(source="wake_up", sqi=sqi, rho=sqi, delta=avg)

        await asyncio.sleep(0.3)


if __name__ == "__main__":
    asyncio.run(run_tracer())
    ```
---

## ✅ Step 2 — Hook dream state into Python cognition kernel

Find your pattern engine loop (likely `pattern_engine.py`).

Add:

```python
# dream kernel flag
self.dream_mode = False

def enter_dream(self):
    self.dream_mode = True
    print("🌙 Pattern engine entering dream mode")
    # explore distant glyphs / chaos mutation

def exit_dream(self):
    self.dream_mode = False
    print("⚡ Resuming focused cognition")