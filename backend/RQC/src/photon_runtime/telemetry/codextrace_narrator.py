# backend/RQC/src/photon_runtime/telemetry/codextrace_narrator.py
"""
Tessaris RQC - CodexTrace AI Narrator
────────────────────────────────────────────
Listens to CodexTrace Relay and generates symbolic-language insights
from Φ (awareness) and coherence telemetry streams.
"""

import asyncio
import json
import logging
import websockets
from datetime import datetime

INSIGHT_LOG = "data/analytics/codextrace_insights.jsonl"
RELAY_URL = "ws://localhost:7071/codextrace"

logger = logging.getLogger("CodexTraceNarrator")


# ────────────────────────────────
def format_insight(evt: dict) -> str:
    """Transform telemetry or awareness event into a readable insight line."""
    tstamp = datetime.utcnow().isoformat()
    evt_type = evt.get("type", "?")

    if evt_type == "telemetry":
        phi = evt.get("Φ", 0)
        coherence = evt.get("coherence", 0)
        if phi > 0.98:
            return f"[{tstamp}] 🌌 Φ stabilized at {phi:.3f} - near-perfect resonance (C={coherence:.3f})"
        elif phi > 0.9:
            return f"[{tstamp}] 💠 Φ={phi:.3f}, stable coherence field (C={coherence:.3f})"
        else:
            return f"[{tstamp}] 🔸 Low resonance Φ={phi:.3f}"

    elif evt_type == "awareness":
        mean_phi = evt.get("mean_Φ", 0)
        cascade_id = evt.get("cascade_id", "?")
        return f"[{tstamp}] 🧠 Meta-awareness Cascade #{cascade_id} - Φ≈{mean_phi:.3f}"

    else:
        return f"[{tstamp}] ⚙️ Event {evt_type}: {json.dumps(evt)[:120]}"


# ────────────────────────────────
async def narrate():
    """Connect to CodexTrace Relay and log insights as they arrive."""
    logger.info(f"🔭 Connecting to CodexTrace Relay at {RELAY_URL}")
    while True:
        try:
            async with websockets.connect(RELAY_URL) as ws:
                logger.info("✅ Connected to relay - listening for events...")
                async for message in ws:
                    evt = json.loads(message)
                    insight = format_insight(evt)
                    print(insight)

                    # Append to insights log
                    with open(INSIGHT_LOG, "a", encoding="utf-8") as f:
                        f.write(json.dumps({
                            "timestamp": datetime.utcnow().isoformat(),
                            "insight": insight,
                            "event": evt
                        }, ensure_ascii=False) + "\n")

        except Exception as e:
            logger.warning(f"⚠️ Disconnected from relay: {e}. Retrying in 3s...")
            await asyncio.sleep(3.0)


# ────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
    asyncio.run(narrate())