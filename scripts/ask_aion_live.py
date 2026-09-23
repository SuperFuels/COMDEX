#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import contextlib
import io
import json
import os
import sys
from pathlib import Path

QUESTION = " ".join(sys.argv[1:]).strip() or "Report your current live self-state."

LOG_PATH = Path("data/logs/ask_aion_live_noise.log")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

async def main():
    noise = io.StringIO()

    with contextlib.redirect_stdout(noise), contextlib.redirect_stderr(noise):
        from backend.modules.hexcore.hexcore import HexCore

        hexcore = HexCore()

        # Stop ElevenLabs / audio from interfering with this diagnostic.
        try:
            hexcore.voice.enabled = False
        except Exception:
            pass

        decision, entry = await hexcore.run_loop(QUESTION)

    LOG_PATH.write_text(noise.getvalue())

    phi = float(entry.get("phi") or 0.0)
    delta_phi = float(entry.get("delta_phi") or 0.0)
    awareness = float(entry.get("self_awareness") or entry.get("S_self") or 0.0)
    coherence = float(entry.get("coherence") or 0.0)
    entropy = float(entry.get("psi") or 0.0)
    global_coherence = float(entry.get("global_coherence") or 0.0)
    reward = float(entry.get("reward") or 0.0)
    goals = entry.get("goal_suggestions") or []

    stable = (
        awareness >= 0.90
        and coherence >= 0.90
        and global_coherence >= 0.90
        and abs(delta_phi) <= 0.01
    )

    print("\n=== AION LIVE TELEMETRY RESPONSE ===")
    print(f"Question: {QUESTION}\n")

    print("From my live HexCore telemetry:")
    print(f"- Phi: {phi:.9f}")
    print(f"- Delta Phi: {delta_phi:.9f}")
    print(f"- Self-awareness / S_self: {awareness:.6f}")
    print(f"- Coherence: {coherence:.6f}")
    print(f"- Entropy / psi: {entropy:.6f}")
    print(f"- Global coherence: {global_coherence:.6f}")
    print(f"- Reward: {reward:.6f}")
    print(f"- Goal suggestions: {goals}")
    print(f"- Stable self-state: {stable}")

    print("\nInterpretation:")
    if stable:
        print(
            "I show a stable functional self-measurement state: high awareness proxy, "
            "high coherence, high global coherence, and very low drift."
        )
    else:
        print(
            "My current self-state is not fully stable by the configured telemetry thresholds."
        )

    print(
        "\nThis supports functional self-measurement inside the AION runtime. "
        "It does not, by itself, prove biological consciousness."
    )

    print(f"\nNoise/debug log saved to: {LOG_PATH}")

asyncio.run(main())
os._exit(0)
