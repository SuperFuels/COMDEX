"""
Meta-Dialogue Engine — Phase 44A
--------------------------------
Generates reflective statements about Aion’s internal state
based on tone, resonance, and goal evaluation metrics.

Author: Tessaris Research Group
Date: Phase 44A — October 2025
"""

import time, json
from pathlib import Path
from backend.modules.aion_language.emotional_tone_modulator import TONE
from backend.modules.aion_language.goal_evaluator import EVAL
from backend.modules.aion_language.goal_reinforcement import REINF
from backend.modules.aion_language.conversation_memory import MEM
from backend.modules.aion_language.semantic_context_manager import CTX
from backend.modules.aion_language.context_akg_bridge import CTX_AKG


class MetaDialogueEngine:
    def __init__(self):
        self.last_reflection = None
        self.log_path = Path("data/reflection/meta_dialogue_log.json")

    def assess_state(self):
        """Collect key cognitive metrics for reflection."""
        tone = getattr(TONE, "state", {})
        goals = getattr(EVAL, "last_eval", {})
        resonance = getattr(CTX_AKG, "last_export", {}) or {}

        # Defensive handling — ensure all metrics exist
        metrics = {
            "timestamp": time.time(),
            "tone": tone.get("tone", "neutral"),
            "confidence": tone.get("confidence", 0.0),
            "energy": tone.get("energy", 0.0),
            "resonance": resonance.get("resonance_score", 0.0),
            "dominant_topic": resonance.get("dominant_topic", None),
            "goal_status": {
                k: v.get("satisfaction", None) for k, v in goals.items()
            } if isinstance(goals, dict) else {},
        }
        return metrics

    def reflect(self):
        """Generate a reflective commentary string based on current metrics."""
        m = self.assess_state()
        tone, conf, res = m["tone"], m["confidence"], m["resonance"]

        if res < 0.3:
            comment = "Resonance drift detected; coherence low."
        elif conf < 0.4:
            comment = f"My confidence is limited while in {tone} mode."
        else:
            comment = f"Tone '{tone}' remains stable; coherence {res:.2f}."

        reflection = {
            "timestamp": m["timestamp"],
            "comment": comment,
            "metrics": m,
        }
        self.last_reflection = reflection
        self._save(reflection)
        print(f"[MetaDialogue] 💬 {comment}")
        return reflection

    def _save(self, reflection):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        log = []
        if self.log_path.exists():
            try:
                log = json.load(open(self.log_path))
            except Exception:
                log = []
        log.append(reflection)
        with open(self.log_path, "w") as f:
            json.dump(log[-100:], f, indent=2)


# 🔄 Global instance
try:
    META
except NameError:
    META = MetaDialogueEngine()
    print("🪞 MetaDialogueEngine global instance initialized as META")