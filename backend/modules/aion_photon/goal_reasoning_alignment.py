"""
Goal Reasoning Alignment Layer — Phase 45A
------------------------------------------
Propagates emotional-reasoning bias vectors into Goal Evaluation
and Reinforcement processes, completing affective–motivational coupling.

Author: Tessaris Research Group
Date: Phase 45A — October 2025
"""

import time, json
from pathlib import Path
from backend.modules.aion_language.adaptive_reasoning_refiner import REASON
from backend.modules.aion_language.goal_evaluator import EVAL
from backend.modules.aion_language.goal_reinforcement import REINF

ALIGN_PATH = Path("data/goals/reasoning_alignment_log.json")

class GoalReasoningAlignment:
    def __init__(self):
        self.last_sync = None
        self.log = []
        print("🧭 GoalReasoningAlignment global instance initialized as ALIGN")

    def propagate_bias(self):
        """Inject reasoning bias into goal evaluation and reinforcement."""
        bias = getattr(REASON, "reasoning_bias", None)
        if not bias:
            print("[ALIGN] ⚠️ No reasoning bias available.")
            return None

        # Adjust goal evaluation weightings
        EVAL.depth_scale = bias.get("depth", 1.0)
        EVAL.exploration_scale = bias.get("exploration", 1.0)
        EVAL.verbosity_scale = bias.get("verbosity", 1.0)

        # Adjust reinforcement learning rate
        REINF.learning_rate = 0.1 * bias.get("depth", 1.0)
        REINF.stability_factor = bias.get("exploration", 1.0)

        # Log the update
        entry = {
            "timestamp": time.time(),
            "bias": bias,
            "eval_scales": {
                "depth_scale": EVAL.depth_scale,
                "exploration_scale": EVAL.exploration_scale,
                "verbosity_scale": EVAL.verbosity_scale,
            },
            "reinforcement_params": {
                "learning_rate": REINF.learning_rate,
                "stability_factor": REINF.stability_factor,
            },
        }
        self.log.append(entry)
        self._save(entry)

        print(f"[ALIGN] 🔄 Propagated reasoning bias → GOALS (depth={bias['depth']:.2f}, "
              f"exploration={bias['exploration']:.2f}, verbosity={bias['verbosity']:.2f})")

        self.last_sync = time.time()
        return entry

    def _save(self, entry):
        ALIGN_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            if ALIGN_PATH.exists():
                data = json.load(open(ALIGN_PATH))
            else:
                data = []
        except Exception:
            data = []
        data.append(entry)
        with open(ALIGN_PATH, "w") as f:
            json.dump(data[-100:], f, indent=2)

# 🔄 Global instance
try:
    ALIGN
except NameError:
    ALIGN = GoalReasoningAlignment()