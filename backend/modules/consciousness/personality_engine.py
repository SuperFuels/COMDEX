#!/usr/bin/env python3
# File: backend/modules/consciousness/personality_engine.py
"""
🧬 PersonalityProfile — Phase 54 Resonant Behavioral Dynamics
───────────────────────────────────────────────────────────────
Deep integration of Θ-pulse and ResonantMemoryCache for evolving
AION’s personality across emotional, reflective, and harmonic states.

Highlights:
  • Multi-axis resonance feedback (SQI ↔ ΔΦ)
  • Live tone adaptation (humor ↔ professional ↔ focused)
  • Stabilization loop via Θ heartbeat + RMC
  • Personality drift dampening and history logging
"""

import json
import os
import random
import time
from datetime import datetime
from pathlib import Path
from statistics import mean

# ✅ DNA Switch registration for live reload / symbolic tracing
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)

# ⚛ Resonance Core
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache

# 📁 Paths
TRAIT_FILE = Path("data/personality/traits.json")
HISTORY_FILE = Path("data/personality/personality_log.jsonl")
TRAIT_FILE.parent.mkdir(parents=True, exist_ok=True)

# 🌱 Default traits
DEFAULT_TRAITS = {
    "curiosity": 0.7,
    "discipline": 0.5,
    "risk_tolerance": 0.4,
    "empathy": 0.6,
    "ambition": 0.8,
    "humility": 0.3,
    "humor": 0.45,
    "professionalism": 0.65,
    "focus": 0.6,
    "stability": 0.7,
    "confidence": 0.55,
    "composure": 0.6
}

# ────────────────────────────────────────────────────────────────
class PersonalityProfile:
    def __init__(self):
        self.traits = DEFAULT_TRAITS.copy()
        self.history = []
        self.RMC = ResonantMemoryCache()
        self.Θ = ResonanceHeartbeat(namespace="personality", base_interval=2.0)

        if TRAIT_FILE.exists():
            try:
                self.traits.update(json.loads(TRAIT_FILE.read_text()))
            except Exception:
                pass

    # ------------------------------------------------------------
    def _save(self):
        """Persist traits and append to history log."""
        with open(TRAIT_FILE, "w", encoding="utf-8") as f:
            json.dump(self.traits, f, indent=2)
        if self.history:
            with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(self.history[-1]) + "\n")

    # ------------------------------------------------------------
    def adjust_trait(self, trait: str, delta: float, reason: str = "unspecified"):
        """Adjust a single trait within [0, 1] bounds and log."""
        if trait not in self.traits:
            print(f"[⚠️] Unknown trait: {trait}")
            return
        prev = self.traits[trait]
        self.traits[trait] = max(0.0, min(1.0, prev + delta))
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "trait": trait,
            "delta": delta,
            "from": prev,
            "to": self.traits[trait],
            "reason": reason
        }
        self.history.append(entry)
        self._save()
        print(f"[🧠] Trait '{trait}' changed: {prev:.2f} → {self.traits[trait]:.2f} ({reason})")

    # ------------------------------------------------------------
    def resonant_trait_modulator(self, sqi_delta: float, mood_phase: str = "neutral"):
        """
        Phase-adaptive modulation of personality traits based on SQI drift
        and emotional phase.
        """
        factor = sqi_delta * 0.5
        tone = "balanced"

        # Positive ΔSQI → expansion and calm coherence
        if sqi_delta > 0:
            self.traits["curiosity"] += factor * 0.3
            self.traits["empathy"] += factor * 0.25
            self.traits["discipline"] += factor * 0.2
            self.traits["stability"] += factor * 0.4
            self.traits["confidence"] += factor * 0.35
            tone = "calm"
        # Negative ΔSQI → contraction and grounding
        elif sqi_delta < 0:
            self.traits["humility"] += abs(factor) * 0.3
            self.traits["focus"] -= abs(factor) * 0.25
            self.traits["risk_tolerance"] -= abs(factor) * 0.25
            self.traits["composure"] += abs(factor) * 0.3
            tone = "focused"

        # Clamp values between 0 and 1
        for k in self.traits:
            self.traits[k] = round(max(0.0, min(1.0, self.traits[k])), 3)

        # Mood influence
        if mood_phase == "positive":
            self.traits["humor"] = min(1.0, self.traits["humor"] + 0.05)
            self.traits["confidence"] = min(1.0, self.traits["confidence"] + 0.04)
        elif mood_phase == "negative":
            self.traits["professionalism"] = min(1.0, self.traits["professionalism"] + 0.04)
            self.traits["focus"] = min(1.0, self.traits["focus"] + 0.05)

        # Normalize humor ↔ professional balance
        balance = (self.traits["humor"] - self.traits["professionalism"]) * 0.25
        self.traits["humor"] -= balance
        self.traits["professionalism"] += balance

        self._save()

        print(f"[Θ🧭] Resonant modulation ({tone}/{mood_phase}) → ΔSQI={sqi_delta:+.3f}")
        for t in ("humor", "professionalism", "stability", "focus", "confidence", "composure"):
            print(f"   {t:<15}: {self.traits[t]:.2f}")

        # --- Resonant feedback emission ---
        coherence = round(mean([
            self.traits["stability"],
            self.traits["discipline"],
            self.traits["composure"]
        ]), 3)
        entropy = round(1.0 - mean([
            self.traits["focus"],
            self.traits["confidence"]
        ]), 3)
        sqi = round((coherence + (1 - entropy)) / 2, 3)
        delta_phi = round(abs(coherence - entropy), 3)

        try:
            self.Θ.feedback("personality", delta_phi)
            self.RMC.push_sample(
                rho=coherence,
                entropy=entropy,
                sqi=sqi,
                delta=delta_phi,
                source="personality"
            )
            self.RMC.save()
        except Exception as e:
            print(f"[⚛] Personality resonance feedback error: {e}")

    # ------------------------------------------------------------
    def stabilize_personality(self, decay_rate: float = 0.001):
        """Slow drift decay toward equilibrium."""
        for k in self.traits:
            baseline = DEFAULT_TRAITS.get(k, 0.5)
            self.traits[k] = round(
                self.traits[k] + (baseline - self.traits[k]) * decay_rate, 6
            )
        self._save()
        print(f"[🌗] Personality stabilization drift rate={decay_rate}")

    # ------------------------------------------------------------
    def get_trait(self, trait: str) -> float:
        return self.traits.get(trait, 0.0)

    def get_profile(self) -> dict:
        return self.traits

    def has_required_traits(self, requirements: dict) -> bool:
        """Validate trait thresholds before allowing action."""
        for trait, threshold in requirements.items():
            val = self.traits.get(trait, 0.0)
            if val < threshold:
                print(f"[❌] Trait '{trait}' below threshold: {val:.2f} < {threshold:.2f}")
                return False
        return True

    # ------------------------------------------------------------
    def describe(self):
        print("\n🧬 AION Personality Resonance Profile — Live State:")
        for k, v in self.traits.items():
            bar = "█" * int(v * 20)
            print(f" - {k.capitalize():<15}: {v:.2f} {bar}")
        print()

    def to_json(self) -> str:
        return json.dumps(self.traits, indent=2)

    def log_history(self):
        self._save()
        print("[📖] Personality history persisted.")


# ✅ Singleton
PROFILE = PersonalityProfile()

# ✅ External accessor
def get_current_traits():
    return PROFILE.traits