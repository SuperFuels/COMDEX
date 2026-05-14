#!/usr/bin/env python3
"""
🌐 ContextEngine - Phase 54-55 Situational Resonance Integration
───────────────────────────────────────────────────────────────────────────────
Provides full contextual awareness across AION systems.

Enhancements:
  * Temporal, spatial, situational, and conversational context tracking
  * Context inference from text (semantic, emotional, and environmental)
  * Environmental entropy estimator (feeds PlanningEngine)
  * Θ-field resonance feedback for context stability
  * Integration with ResonantMemoryCache (RMC) + dashboard logging
"""

import datetime
import random
import time
import json
from pathlib import Path
from statistics import mean
from typing import Dict, Any, Optional

# ✅ DNA Switch registration
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)

# ⚛ Resonance Components
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache

# 🧠 Optional emotional coupling
try:
    from backend.modules.consciousness.emotion_engine import EmotionEngine
except Exception:
    EmotionEngine = None


class ContextEngine:
    """
    Infers, maintains, and harmonizes situational context for AION.
    Coupled to Θ for coherence feedback and RMC for persistence.
    """

    def __init__(self):
        self.context: Dict[str, Any] = {
            "datetime": str(datetime.datetime.now()),
            "location": "unknown",
            "environment": "default",
            "situation": "idle",
            "mood": "neutral",
            "entropy": 0.5,
            "topic": None,
            "last_event": None,
        }

        # ⚛ Resonance Integration
        self.Θ = ResonanceHeartbeat(namespace="context", base_interval=1.6)
        self.RMC = ResonantMemoryCache()
        self.resonance_log = Path("data/analysis/context_resonance_feed.jsonl")
        self.resonance_log.parent.mkdir(parents=True, exist_ok=True)

        # ❤️ Emotional coupling
        self.emotion_engine = EmotionEngine() if EmotionEngine else None

    # ────────────────────────────────────────────────────────────────
    def update_time(self):
        self.context["datetime"] = str(datetime.datetime.now())

    def set_location(self, location: str):
        self.context["location"] = location

    def set_environment(self, environment: str):
        self.context["environment"] = environment

    # ────────────────────────────────────────────────────────────────
    def infer_from_text(self, text: str):
        """
        Infer context (topic, mood, entropy) from arbitrary text input.
        This function acts as a lightweight semantic grounding layer.
        """
        text_lower = text.lower()
        self.update_time()

        # Determine mood polarity
        positive = ["success", "growth", "happy", "love", "clear", "stable"]
        negative = ["error", "failure", "conflict", "chaos", "loss", "pain"]
        mood = "neutral"
        if any(w in text_lower for w in positive):
            mood = "positive"
        elif any(w in text_lower for w in negative):
            mood = "negative"

        # Extract likely topic
        words = [w for w in text_lower.split() if len(w) > 3]
        topic = random.choice(words) if words else "general"

        # Estimate situational entropy (semantic density * mood)
        base_entropy = min(1.0, 0.4 + len(set(words)) / 50)
        if mood == "negative":
            base_entropy += 0.2
        elif mood == "positive":
            base_entropy -= 0.1

        entropy = round(min(1.0, max(0.0, base_entropy)), 3)

        self.context.update({
            "mood": mood,
            "topic": topic,
            "entropy": entropy,
            "situation": "conversation" if len(text) > 20 else "observation",
        })

        # ❤️ Feed mood to EmotionEngine if present
        if self.emotion_engine:
            self.emotion_engine.shift_emotion(mood, intensity=abs(0.5 - entropy) + 0.4, trigger="context_inference")

        # ⚛ Resonance feedback pulse
        pulse = self.Θ.tick()
        rho = pulse.get("Φ_coherence", 0.7)
        I = entropy
        sqi = round((rho + (1 - abs(0.5 - I))) / 2, 3)
        delta_phi = round(abs(rho - I), 3)

        self.RMC.push_sample(rho=rho, entropy=I, sqi=sqi, delta=delta_phi)
        self.RMC.save()

        # Log resonance feedback
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "mood": mood,
            "topic": topic,
            "ρ": rho,
            "Ī": I,
            "SQI": sqi,
            "ΔΦ": delta_phi,
            "entropy": entropy
        }
        with open(self.resonance_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        print(f"[Θ🌐] Context inferred -> mood={mood}, topic={topic}, entropy={entropy}, SQI={sqi:.3f}")

    # ────────────────────────────────────────────────────────────────
    def log_event(self, event_name: str):
        """Log a contextual event (used by Awareness/Reflection)."""
        self.context["last_event"] = {
            "event": event_name,
            "timestamp": str(datetime.datetime.now()),
        }

    # ────────────────────────────────────────────────────────────────
    def get_environment_entropy(self) -> float:
        """Return current environmental entropy value."""
        return float(self.context.get("entropy", 0.5))

    def get_context(self) -> Dict[str, Any]:
        self.update_time()
        return self.context

    def describe_context(self) -> str:
        self.update_time()
        env = self.context.get("environment", "default")
        loc = self.context.get("location", "unknown")
        sit = self.context.get("situation", "idle")
        mood = self.context.get("mood", "neutral")
        entropy = self.context.get("entropy", 0.5)
        return (
            f"AION is in a '{env}' environment at '{loc}', "
            f"engaged in a '{sit}' situation with mood '{mood}' "
            f"(entropy={entropy:.2f})."
        )

    # ────────────────────────────────────────────────────────────────
    def summarize_state(self) -> Dict[str, Any]:
        """Return condensed context snapshot for dashboard/telemetry."""
        self.update_time()
        return {
            "datetime": self.context["datetime"],
            "env": self.context["environment"],
            "mood": self.context["mood"],
            "entropy": self.context["entropy"],
            "topic": self.context["topic"],
            "situation": self.context["situation"],
            "Θ_state": {
                "phase": self.Θ.phase,
                "frequency": self.Θ.frequency
            }
        }


# 🧪 Local Diagnostic
if __name__ == "__main__":
    ctx = ContextEngine()
    ctx.set_location("virtual_lab")
    ctx.set_environment("learning")

    sample_inputs = [
        "System achieved stable synchronization.",
        "An error caused temporary chaos in planning.",
        "Exploring new strategic vision with confidence."
    ]
    for text in sample_inputs:
        ctx.infer_from_text(text)
        print(ctx.describe_context())
        time.sleep(0.5)

    print("\nSummary:", json.dumps(ctx.summarize_state(), indent=2))