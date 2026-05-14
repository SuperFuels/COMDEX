"""
GoalFeedbackBridge - Phase 36C : Awareness-Emotion Feedback Coupling
--------------------------------------------------------------------
Synchronizes GoalEngine satisfaction levels with Awareness and Emotion states.
"""

import time
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from backend.modules.aion_photon.goal_engine import GOALS
except Exception:
    GOALS = None

try:
    # Optional emotion/awareness engines if available
    from backend.modules.aion_emotion.emotion_engine import EMOTION
except Exception:
    EMOTION = None

try:
    from backend.modules.aion_awareness.awareness_engine import AWARENESS
except Exception:
    AWARENESS = None

LOG_PATH = Path("data/analysis/goal_feedback_events.jsonl")

class GoalFeedbackBridge:
    """Links emotional/awareness feedback to active goals."""

    def __init__(self, reinforce_gain: float = 0.05, decay_rate: float = 0.03):
        self.reinforce_gain = reinforce_gain
        self.decay_rate = decay_rate

    def get_emotional_snapshot(self):
        """Return (valence, arousal, coherence Φ)."""
        v = getattr(EMOTION, "valence", 0.0) if EMOTION else 0.0
        a = getattr(EMOTION, "arousal", 0.0) if EMOTION else 0.0
        phi = getattr(AWARENESS, "phi_coherence", 0.5) if AWARENESS else 0.5
        return v, a, phi

    def run_once(self):
        """One feedback synchronization step."""
        if not GOALS or not GOALS.active_goals:
            logger.info("[FeedbackBridge] No active goals to modulate.")
            return []

        v, a, phi = self.get_emotional_snapshot()
        updates = []
        for gid, goal in GOALS.active_goals.items():
            delta = 0.0
            if phi > 0.6 and v > 0.0:
                delta += self.reinforce_gain * (v + phi) / 2
            if phi < 0.4 or a > 0.7:
                delta -= self.decay_rate * (a + (1 - phi)) / 2

            if abs(delta) > 0.0:
                GOALS.update_satisfaction(gid, delta)
                updates.append((gid, delta))

                LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
                with open(LOG_PATH, "a") as f:
                    f.write(json.dumps({
                        "timestamp": time.time(),
                        "goal_id": gid,
                        "intent": goal.intent,
                        "delta": delta,
                        "valence": v,
                        "arousal": a,
                        "phi": phi
                    }) + "\n")

        logger.info(f"[FeedbackBridge] Updated {len(updates)} goals.")
        return updates