#!/usr/bin/env python3
"""
🎯 AION Intent Engine — Phase P2 (Resonant Upgrade)
────────────────────────────────────────────
Fuses MotivationLayer DriveVectors + ResonantMemory context → IntentObject.
Feeds into Tessaris Reasoner (P3).
Includes ResonantReinforcementMixin for adaptive feedback and coherence tracking.
"""

import os, time, random, json
from pathlib import Path
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.aion_cognition.motivation_layer import MotivationLayer
from backend.modules.aion_resonance.reinforcement_mixin import ResonantReinforcementMixin
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat


INTENT_LOG = Path("data/memory/intent_history.json")
INTENT_LOG.parent.mkdir(parents=True, exist_ok=True)


# ───────────────────────────────────────────────
# 🎯 Intent Engine — Resonant Version
# ───────────────────────────────────────────────
class IntentEngine(ResonantReinforcementMixin):
    def __init__(self):
        super().__init__(name="intent_engine")
        self.rmc = ResonantMemoryCache()
        self.motivation = MotivationLayer()
        self.Theta = ResonanceHeartbeat(namespace="intent")

    # ───────────────────────────────────────────
    def generate_intent(self) -> dict:
        """
        Fuse DriveVector + memory snapshot → IntentObject.
        Reinforces coherence based on clarity, entropy, and drive balance.
        Emits Θ event for synchronization.
        """
        motive = self.motivation.output_vector()
        drives = motive["drives"]
        entropy = motive["entropy"]
        sqi = motive["sqi"]
        context = self._sample_context()
        dominant = max(drives, key=drives.get)

        intent = {
            "what": self._choose_topic(context),
            "why": dominant,
            "how": self._choose_method(dominant),
            "when": time.strftime("%Y-%m-%d %H:%M:%S"),
            "priority": round(drives[dominant], 3),
            "confidence": round(random.uniform(0.6, 0.95) * (1 - entropy * 0.3), 3),
            "entropy": entropy,
            "sqi": sqi,
        }

        # 🧮 Compute clarity: alignment of drives, SQI, and entropy
        drive_balance = 1.0 - abs(max(drives.values()) - min(drives.values()))
        clarity = round(((intent["confidence"] * 0.5) + (drive_balance * 0.3) + (sqi * 0.2)), 3)

        # 🧭 Meta-coherence validation
        intent["status"] = "coherent" if clarity >= 0.45 and entropy <= 0.7 else "unstable"
        intent["clarity"] = clarity

        # 🔁 Reinforcement feedback
        self.update_resonance_feedback(outcome_score=clarity, reason="Intent clarity and resonance alignment")

        # 🔔 Θ event emission
        self.Theta.event("intent_generated", clarity=clarity, dominant=dominant, context=context, status=intent["status"])

        # 💾 Log for dashboard tracking
        self._log_intent(intent)

        return intent

    # ───────────────────────────────────────────
    def _sample_context(self, n=3):
        """Randomly sample from the ResonantMemoryCache keys as context."""
        mem = list(self.rmc.cache.keys())
        return random.sample(mem, min(len(mem), n)) if mem else []

    def _choose_topic(self, context):
        """Selects contextual topic or fallback conceptual domain."""
        if not context:
            return random.choice(["learning", "exploration", "optimization", "reflection", "resonance"])
        return random.choice(context)

    def _choose_method(self, drive):
        """Drive-to-method mapping for procedural cognition."""
        methods = {
            "curiosity": "explore new pattern",
            "goal": "optimize known plan",
            "need": "stabilize resource flow",
        }
        return methods.get(drive, "reflect and adapt")

    def _log_intent(self, intent: dict):
        """Persist generated intents for history, dashboard, or meta-analysis."""
        data = []
        try:
            if INTENT_LOG.exists():
                data = json.loads(INTENT_LOG.read_text(encoding="utf-8"))
                if not isinstance(data, list):
                    data = []
        except Exception:
            data = []

        data.append(intent)
        INTENT_LOG.write_text(json.dumps(data[-500:], indent=2, ensure_ascii=False))


# ───────────────────────────────────────────────
# Demo Mode
# ───────────────────────────────────────────────
if __name__ == "__main__":
    engine = IntentEngine()
    print("🎯 AION Intent Engine — Resonant Intents\n")
    for i in range(5):
        intent = engine.generate_intent()
        print(
            f"[{i+1}] what={intent['what']}  why={intent['why']}  how={intent['how']}  "
            f"clarity={intent['clarity']:.3f}  status={intent['status']}  "
            f"conf={intent['confidence']:.3f}  priority={intent['priority']:.3f}  "
            f"entropy={intent['entropy']:.3f}  sqi={intent['sqi']:.3f}"
        )
        time.sleep(0.5)