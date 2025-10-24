"""
Adaptive Reasoning Refiner — Phase 44C
-------------------------------------
Links EmotionalToneModulator → reasoning control.
Dynamically scales reasoning depth, exploration, and response style.

Author: Tessaris Research Group
Date: Phase 44C — October 2025
"""

import time
from backend.modules.aion_language.emotional_tone_modulator import TONE
from backend.modules.aion_photon.goal_engine import GOALS
from backend.modules.aion_language.meaning_field_engine import MFG

class AdaptiveReasoningRefiner:
    def __init__(self):
        self.last_adjustment = None
        self.reasoning_bias = {"depth": 1.0, "exploration": 1.0, "verbosity": 1.0}
        print("🧮 AdaptiveReasoningRefiner global instance initialized as REASON")

    def compute_bias(self):
        """Translate tone/confidence/energy into reasoning parameters."""
        tone = TONE.state.get("tone", "neutral")
        conf = TONE.state.get("confidence", 0.5)
        energy = TONE.state.get("energy", 0.5)

        bias = {"depth": 1.0, "exploration": 1.0, "verbosity": 1.0}

        if tone == "calm":
            bias.update({"depth": 0.7, "exploration": 0.6, "verbosity": 0.8})
        elif tone == "analytical":
            bias.update({"depth": 1.3, "exploration": 1.0, "verbosity": 1.0})
        elif tone == "reflective":
            bias.update({"depth": 1.1, "exploration": 0.9, "verbosity": 1.2})
        elif tone == "curious":
            bias.update({"depth": 1.0, "exploration": 1.4, "verbosity": 1.1})
        elif tone == "empathetic":
            bias.update({"depth": 0.9, "exploration": 1.0, "verbosity": 1.3})
        elif tone == "confident":
            bias.update({"depth": 1.2, "exploration": 1.1, "verbosity": 1.0})
        elif tone == "uncertain":
            bias.update({"depth": 0.8, "exploration": 1.2, "verbosity": 0.9})

        # Scale by confidence and energy
        scale = (conf + energy) / 2.0
        for k in bias:
            bias[k] = round(bias[k] * (0.8 + 0.4 * scale), 2)

        self.reasoning_bias = bias
        self.last_adjustment = time.time()
        print(f"[AdaptiveReasoningRefiner] 🧭 Bias set → {bias}")
        return bias

    def refine_reasoning(self, query: str):
        """Apply bias before reasoning through MFG."""
        bias = self.compute_bias()
        print(f"[AdaptiveReasoningRefiner] 🧠 Refining reasoning for tone '{TONE.state['tone']}'")

        # Example: modify query or reasoning behavior
        reasoning_depth = bias["depth"]
        exploration = bias["exploration"]

        result = MFG.reason(query, depth_scale=reasoning_depth, explore_scale=exploration)
        GOALS.log_reasoning_event(query, result, bias)
        return {"query": query, "result": result, "bias": bias}

# Global instance
try:
    REASON
except NameError:
    REASON = AdaptiveReasoningRefiner()