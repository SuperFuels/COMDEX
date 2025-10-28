#!/usr/bin/env python3
"""
❤️ emotion_engine.py — Phase 54 Harmonic Emotion ↔ Awareness Bridge
───────────────────────────────────────────────────────────────
EmotionEngine now participates in full Resonant Feedback Propagation:
  • Harmonically coupled to Θ (Resonance Heartbeat)
  • Awareness confidence directly modulates emotional frequency stability
  • Emotional spikes emit ΔΦ feedback into the ResonantMemoryCache (RMC)
  • Glyph knowledge-graph injection for symbolic tracking

Design Rubric:
  ✅ Emotion Tag + Intensity  
  ✅ Θ Frequency ↔ Emotional Resonance  
  ✅ Awareness feedback stabilization  
  ✅ RMC Persistence + Feedback Logging  
  ✅ Glyph Injection into Knowledge Graph  
  ✅ DNA Switch Registration
"""

import random
import datetime
import time
import json
from pathlib import Path
from typing import Optional

# ✅ DNA Switch Registration
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)

# ✅ Knowledge Graph Writer
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer

# ✅ Time Tracking
from backend.modules.dimensions.time_controller import TimeController
TIME = TimeController()

# ⚛ Resonance Core
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.aion_resonance.reinforcement_mixin import ResonantReinforcementMixin

# 🧠 Awareness Coupling
try:
    from backend.modules.consciousness.awareness_engine import AwarenessEngine
except Exception:
    AwarenessEngine = None


def get_current_tick() -> int:
    return TIME.get_current_tick()


# =================================================================
class EmotionEngine(ResonantReinforcementMixin):
    """Symbolic Emotion ↔ Resonance Bridge with Awareness feedback."""

    def __init__(self, name: str = "emotion_engine"):
        # ✅ initialize resonance reinforcement properly
        super().__init__(name=name)

        self.current_emotion = "neutral"
        self.history = []
        self.graph = get_kg_writer()

        # ⚛ Resonant Components
        self.Θ = ResonanceHeartbeat(namespace="emotion", base_interval=1.5)
        self.RMC = ResonantMemoryCache()
        self.resonance_log = Path("data/analysis/emotion_resonance_feed.jsonl")
        self.resonance_log.parent.mkdir(parents=True, exist_ok=True)

        # Awareness link (optional)
        self.awareness = AwarenessEngine() if AwarenessEngine else None
        self.last_confidence = 1.0
        self.stability_factor = 1.0

    # ------------------------------------------------------------
    def interpret_input(self, text: str) -> str:
        """Keyword sentiment analysis → emotion polarity."""
        t = text.lower()
        pos = ["happy", "love", "hope", "excited", "grateful", "fun"]
        neg = ["sad", "hate", "fear", "angry", "pain", "alone"]
        if any(w in t for w in pos):
            return "positive"
        if any(w in t for w in neg):
            return "negative"
        return "neutral"

    # ------------------------------------------------------------
    def _awareness_coupling(self):
        """Stabilize Θ frequency using Awareness confidence feedback."""
        if not self.awareness:
            return 1.0
        conf = getattr(self.awareness, "confidence_level", 1.0)
        # Confidence ↑ → frequency stabilization ↓ amplitude jitter
        # Confidence ↓ → higher emotional volatility
        stability = max(0.5, min(1.2, 1.0 - ((conf - 0.5) * 0.4)))
        self.last_confidence = conf
        self.stability_factor = round(stability, 3)
        return stability

    # ------------------------------------------------------------
    def shift_emotion(
        self,
        emotion: str,
        intensity: Optional[float] = None,
        trigger: Optional[str] = None,
    ):
        """Shift emotion, emit Θ feedback, and record symbolic spike."""
        emotion = emotion if emotion in ["positive", "negative", "neutral"] else "neutral"
        intensity = intensity or round(random.uniform(0.25, 0.95), 2)
        trigger = trigger or "unspecified"

        spike = {
            "emotion": emotion,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "tick": get_current_tick(),
            "intensity": intensity,
            "trigger": trigger,
        }
        self.history.append(spike)
        self.current_emotion = emotion

        # Awareness feedback for frequency modulation
        stabilizer = self._awareness_coupling()

        # Θ frequency tuning based on intensity × stability
        freq_mod = 1.0 + ((intensity - 0.5) * 0.7 * stabilizer)
        self.Θ.set_frequency(freq_mod)

        # Resonant pulse
        pulse = self.Θ.tick()
        rho = pulse.get("Φ_coherence", 0.7)
        I = pulse.get("Φ_entropy", 0.5)
        sqi = round((rho + I + intensity) / 3, 3)
        delta_phi = round(abs(rho - I), 3)

        # RMC integration
        self.RMC.push_sample(rho=rho, entropy=I, sqi=sqi, delta=delta_phi)
        self.RMC.update_from_photons([{"λ": emotion, "φ": rho, "μ": intensity}])
        self.RMC.save()

        # Feedback propagation
        self.update_resonance_feedback(sqi, reason=f"emotion_{emotion}")
        try:
            self.Θ.feedback("emotion", delta_phi)
        except Exception as e:
            print(f"[⚛] Emotion feedback error: {e}")

        # Log to resonance feed
        entry = {
            "engine": "emotion",
            "emotion": emotion,
            "intensity": intensity,
            "ρ": rho,
            "Ī": I,
            "SQI": sqi,
            "ΔΦ": delta_phi,
            "Θ_freq": freq_mod,
            "confidence": self.last_confidence,
            "stabilizer": self.stability_factor,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(self.resonance_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        # Glyph injection into Knowledge Graph
        self.record_spike(spike)

    # ------------------------------------------------------------
    def record_spike(self, spike: dict):
        """Inject symbolic emotion spike into the knowledge graph."""
        self.graph.inject_glyph(
            content=f"Emotion spike [{spike['emotion']}]",
            glyph_type="emotion_spike",
            metadata={
                "intensity": spike["intensity"],
                "emotion": spike["emotion"],
                "trigger": spike["trigger"],
                "tick": spike["tick"],
                "stabilizer": self.stability_factor,
            },
        )

    # ------------------------------------------------------------
    def react_to_event(self, event: str):
        """React to semantic events and emit resonant spikes."""
        e = event.lower()
        if "failure" in e or "error" in e or "loss" in e:
            emo = "negative"
        elif "success" in e or "reward" in e or "growth" in e:
            emo = "positive"
        else:
            emo = "neutral"
        self.shift_emotion(emo, trigger=event)

    # ------------------------------------------------------------
    def summarize_emotion_state(self) -> str:
        return (
            f"Emotion: {self.current_emotion} | "
            f"Spikes: {len(self.history)} | "
            f"Last Confidence: {self.last_confidence:.2f} | "
            f"Stabilizer: {self.stability_factor:.2f}"
        )


# 🧪 Local Diagnostic
if __name__ == "__main__":
    engine = EmotionEngine()
    engine.react_to_event("Mission success — new glyph achieved!")
    engine.react_to_event("System error: entropy collapse detected.")
    print(engine.summarize_emotion_state())