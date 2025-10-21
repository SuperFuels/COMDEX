"""
==========================================================
🧠 AION Reflection Layer — Phase 3: Linguistic Summarization
----------------------------------------------------------
Consumes symbolic + cognitive events and produces
short natural-language reflections for the Thought Stream.
Integrates later with Conceptual Learning Arena (Phase 4).
==========================================================
"""

import asyncio
import datetime
import random
from typing import Dict, Any

from backend.modules.aion_resonance.thought_stream import broadcast_event
from backend.modules.hexcore.memory_engine import MemoryEngine

memory = MemoryEngine()

# ----------------------------------------------------------
# 🔡 Simple linguistic templates (expand later with LLM)
# ----------------------------------------------------------
TEMPLATES = {
    "move": [
        "Movement registered. Coherence steady, curiosity intact.",
        "Curiosity-driven exploration extended symbolic reach.",
        "AION moved within stable Φ-field."
    ],
    "collect": [
        "Pattern recognized and integrated — coherence amplified.",
        "Symbolic object acquired; entropy stabilized.",
        "AION collected a semantic construct from the grid."
    ],
    "danger": [
        "Entropy spike detected; Φ-stability breached.",
        "Encountered destabilizing resonance; self-correction initiated.",
        "Collapse ∇ event — danger acknowledged."
    ],
    "symbol": [
        "New symbolic form emerged; reflective encoding updated.",
        "Resonant glyph observed — meaning expansion in progress.",
        "Symbolic resonance logged for later abstraction."
    ]
}


def summarize_event(event: Dict[str, Any]) -> str:
    """Return a short reflection string for an incoming event."""
    etype = event.get("type", "move")
    tone = event.get("tone", "neutral")
    msg = event.get("message", "")
    template = random.choice(TEMPLATES.get(etype, ["Reflective event noted."]))
    return f"{template} (tone: {tone}) [{msg[:60]}...]"


# ----------------------------------------------------------
# 🌀 Main reflection handler
# ----------------------------------------------------------
async def process_reflection(event: Dict[str, Any]):
    """Consume raw event → produce linguistic reflection → broadcast + store."""
    summary = summarize_event(event)

    reflection_event = {
        "type": "aion_reflection",
        "tone": "reflective",
        "message": summary,
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    }

    # Broadcast to the live Thought Stream
    await broadcast_event(reflection_event)

    # Store in memory
    memory.store({
        "label": "aion_reflection",
        "content": summary
    })

    print(f"[Reflection] 🧠 {summary}")


# ----------------------------------------------------------
# 🔄 Demo / Test Runner
# ----------------------------------------------------------
async def run_reflection_demo():
    """Standalone demo for the Reflection Layer."""
    demo_events = [
        {"type": "move", "tone": "curious", "message": "Agent explored grid"},
        {"type": "collect", "tone": "focused", "message": "Symbolic object acquired"},
        {"type": "danger", "tone": "alert", "message": "Entropy spike detected"},
        {"type": "symbol", "tone": "inspired", "message": "New glyph resonance"}
    ]
    for e in demo_events:
        await process_reflection(e)
        await asyncio.sleep(0.3)


if __name__ == "__main__":
    asyncio.run(run_reflection_demo())