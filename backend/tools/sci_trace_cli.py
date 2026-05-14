#!/usr/bin/env python3
"""
SCI Cognition Tracer
Real-time pattern lifecycle + SQI delta feed
"""

import asyncio
import json
import websockets
from datetime import datetime

WS_URL = "ws://localhost:8003/ws/sci"  # same channel as sci_emit bridge

RESET = "\033[0m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"

def ts():
    return datetime.now().strftime("%H:%M:%S")

def color_for_delta(d):
    if d > 0.05: return GREEN
    if d < -0.05: return RED
    return YELLOW

async def run():
    async with websockets.connect(WS_URL) as ws:
        print(f"{CYAN}👁️  Cognition Tracer Online{RESET}")
        await ws.send(json.dumps({"subscribe": "pattern_events"}))

        async for msg in ws:
            try:
                ev = json.loads(msg)
            except:
                continue

            et = ev.get("event_type")
            name = ev.get("name")
            pid = ev.get("pattern_id")
            sqi = ev.get("sqi")
            delta = ev.get("delta", 0)

            col = color_for_delta(delta)

            if et == "pattern_birth":
                print(f"{MAGENTA}[{ts()}] ✨ Birth {RESET}{name} {CYAN}SQI={sqi:.3f}{RESET}")

            elif et == "pattern_mutation":
                print(f"{col}[{ts()}] 🧬 Mutate {RESET}{name} "
                      f"Δ={delta:+.3f} -> {CYAN}{sqi:.3f}{RESET}")

            elif et == "pattern_collapse":
                print(f"{RED}[{ts()}] 💀 Collapse {RESET}{name} SQI={sqi:.3f}")

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nbye.\n")