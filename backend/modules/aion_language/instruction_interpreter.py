"""
Instruction Interpreter - Phase 42A
-----------------------------------
Maps natural-language instructions to internal Aion actions.
Bridges QueryResonanceAPI (semantic field) -> GoalEngine (intent) -> subsystem calls.

Examples:
  "focus on equilibrium"  -> AVATAR.focus(target="equilibrium")
  "stabilize drift"       -> HSE.stabilize()
  "forecast next harmonic"-> RFE.forecast()

Author: Tessaris Research Group
Date: Phase 42A - October 2025
"""

import re, time, logging
from backend.modules.aion_language.query_resonance_api import QRA
from backend.modules.aion_photon.goal_engine import GOALS
from backend.modules.aion_language.harmonic_stabilizer_engine import HSE
from backend.modules.aion_avatar.observer_core import AVATAR
from backend.modules.aion_language.resonant_forecaster import RFE
from backend.modules.aion_language.integrative_resonant_controller import IRC

logger = logging.getLogger(__name__)

class InstructionInterpreter:
    def __init__(self):
        # Define base verb-to-action mapping
        self.action_map = {
            "focus": self._act_focus,
            "observe": self._act_focus,
            "stabilize": self._act_stabilize,
            "correct": self._act_stabilize,
            "harmonize": self._act_stabilize,
            "forecast": self._act_forecast,
            "predict": self._act_forecast,
            "analyze": self._act_forecast,
            "balance": self._act_control,
            "control": self._act_control,
            "regulate": self._act_control,
        }

    # ─────────────────────────────────────────────
    def interpret(self, text: str):
        """
        Main entry point - interpret a natural language command
        and trigger the corresponding internal goal and subsystem action.
        """
        if not text or not isinstance(text, str):
            logger.warning("[Interpreter] Empty or invalid input.")
            return None

        cmd = text.lower().strip()
        words = re.findall(r"[a-zA-Z_]+", cmd)

        if not words:
            logger.warning("[Interpreter] No recognizable tokens.")
            return None

        # Identify candidate action verb
        action = None
        for w in words:
            if w in self.action_map:
                action = w
                break

        if not action:
            # fallback: use QRA to find nearest known verb using semantic distance
            for w in words:
                nearest = self._find_nearest_action(w)
                if nearest:
                    action = nearest
                    break

        if not action:
            logger.info(f"[Interpreter] No matching action found in: '{text}'")
            return None

        # Extract target concept (noun or concept-like word)
        target = None
        for w in reversed(words):
            if w != action:
                target = w
                break

        # Generate a formal goal within the GoalEngine
        goal_name = f"{action}_{target or 'none'}"
        if hasattr(GOALS, 'create'):
            GOALS.create(goal_name, priority=0.6, source="InstructionInterpreter")
        elif hasattr(GOALS, 'create_goal'):
            GOALS.create_goal(goal_name, priority=0.6)

        logger.info(f"[Interpreter] Matched '{text}' -> action={action}, target={target}")
        
        # Execute the mapped function
        fn = self.action_map.get(action)
        result = fn(target)
        
        return {
            "action": action, 
            "target": target, 
            "result": result, 
            "goal": goal_name,
            "timestamp": time.time()
        }

    # ─────────────────────────────────────────────
    def _find_nearest_action(self, word):
        """Semantic fallback using resonance field proximity via QRA."""
        min_dist = 1.0
        best_match = None
        for act in self.action_map:
            # QRA.semantic_distance returns 1 - |resonance| (lower is closer)
            dist = QRA.semantic_distance(word, act)
            if dist is not None and dist < min_dist:
                min_dist = dist
                best_match = act
        
        # Threshold of 0.7 ensures we don't pick wildy unrelated concepts
        return best_match if min_dist < 0.7 else None

    # ─────────────────────────────────────────────
    # Subsystem Action Wrappers
    # ─────────────────────────────────────────────
    
    def _act_focus(self, target):
        """Directs AVATAR attention to a specific concept."""
        if not target:
            target = "equilibrium"
        print(f"[Interpreter] -> AVATAR.focus('{target}')")
        return AVATAR.focus(f"concept:{target}", strength=0.85)

    def _act_stabilize(self, target):
        """Triggers HSE to correct resonance drift."""
        print(f"[Interpreter] -> HSE.stabilize() for '{target}'")
        return HSE.stabilize()

    def _act_forecast(self, target):
        """Engages RFE to predict harmonic stability."""
        print(f"[Interpreter] -> RFE.forecast() horizon=5")
        return RFE.forecast(horizon=5)

    def _act_control(self, target):
        """Activates the IRC integrative loop."""
        print(f"[Interpreter] -> IRC.start(duration=10)")
        return IRC.start(duration=10)

# ─────────────────────────────────────────────
# Global instance for system-wide access
# ─────────────────────────────────────────────
try:
    INT
except NameError:
    INT = InstructionInterpreter()
    print("🗣️ InstructionInterpreter global instance initialized as INT")