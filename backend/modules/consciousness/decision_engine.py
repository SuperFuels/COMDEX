#!/usr/bin/env python3
# ============================================================
# 🧭 Resonant Decision Engine — P5.1
# ============================================================

import random
from typing import Optional, Dict, Any
from datetime import datetime

from backend.modules.skills.goal_runner import GoalRunner
from backend.modules.consciousness.situational_engine import SituationalEngine
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.aion_resonance.resonant_heartbeat_monitor import ResonanceHeartbeat
from backend.modules.aion_cognition.action_switch import ActionSwitch
from backend.modules.aion_cognition.strategy_planner import ResonantStrategyPlanner
from backend.modules.aion_resonance.resonant_optimizer import get_optimizer

from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)

class DecisionEngine:
    """
    AION’s Resonant Decision Engine — evolves decision weights dynamically
    from resonance feedback, risk analysis, and goal states.
    """

    def __init__(self, situation_engine: SituationalEngine):
        self.last_decision: Optional[str] = None
        self.last_timestamp: Optional[str] = None

        self.goal_runner = GoalRunner()
        self.situation = situation_engine

        # 💓 Resonant subsystems
        self.rmc = ResonantMemoryCache()
        self.heartbeat = ResonanceHeartbeat(namespace="decision_engine")
        self.heartbeat.register_listener(self._on_heartbeat)
        # Optional: sync with external jsonl generator if present
        try:
            self.heartbeat.bind_jsonl("data/aion_field/resonant_heartbeat.jsonl")
        except Exception:
            pass
        self.heartbeat.start()

        self.strategy_planner = ResonantStrategyPlanner()
        self.action_switch = ActionSwitch()

        # Knobs the optimizer may nudge
        self.exploration = 0.12
        self.risk_bias = 0.0
        self.search_temp = 0.10

        # Register with global optimizer
        get_optimizer().register("decision_engine", self)

        # Dynamic weights (curiosity, stability, coherence, entropy)
        self.weights = {
            "curiosity": 0.25,
            "goal_alignment": 0.35,
            "entropy": 0.15,
            "reflection": 0.25,
        }

        self.resonance_bias = 0.0
        print("💓 Resonant DecisionEngine initialized and linked to heartbeat.")

    # ------------------------------------------------------------
    def decide(self, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Make an adaptive decision influenced by resonance, context, and goals.
        """
        options = [
            "reflect on dreams",
            "prioritize goals",
            "generate new plan",
            "interact with user",
            "analyze resonance",
            "optimize memory coherence",
            "expand symbolic map",
            "run self-diagnostics",
            "idle / recharge",
        ]

        # Base weights (modifiable by resonance feedback)
        base_weights = [0.1, 0.15, 0.2, 0.1, 0.1, 0.1, 0.1, 0.05, 0.1]

        # Situational awareness
        awareness = self.situation.analyze_context()
        risk = awareness.get("current_risk", "low")
        entropy = self.rmc.get("system_entropy") or 0.2

        # Resonance bias shaping
        if self.resonance_bias > 0.5:
            base_weights[2] += 0.15  # generate new plan
            base_weights[1] += 0.10  # prioritize goals
        elif self.resonance_bias < -0.3:
            base_weights[0] += 0.15  # reflect on dreams
            base_weights[-1] += 0.10 # idle/recharge

        if risk == "high":
            print("⚠️ High situational risk detected — shifting toward stability.")
            base_weights = [0.2, 0.1, 0.1, 0.05, 0.05, 0.15, 0.05, 0.1, 0.2]

        # Normalize safely
        total = sum(base_weights)
        norm_weights = [w / total for w in base_weights] if total > 0 else [1/len(options)]*len(options)

        decision = random.choices(options, norm_weights)[0]
        self.last_decision = decision
        self.last_timestamp = datetime.utcnow().isoformat()

        print(f"🧭 Resonant DecisionEngine → Decision: {decision}")
        self.situation.log_event(f"Decision made: {decision}", "neutral")

        # Behaviors
        if decision == "prioritize goals":
            self._run_highest_priority_goal()
        elif decision == "generate new plan":
            self._generate_resonant_plan()
        elif decision == "analyze resonance":
            self._reflect_resonance()
        elif decision == "optimize memory coherence":
            self._harmonize_memory()
        elif decision == "reflect on dreams":
            self._reflective_mode()

        # Log into RMC
        self.rmc.set("last_decision", {
            "decision": decision,
            "timestamp": self.last_timestamp,
            "risk": risk,
            "entropy": entropy,
            "resonance_bias": self.resonance_bias
        })

        return decision

    # ------------------------------------------------------------
    def _run_highest_priority_goal(self):
        active_goals = self.goal_runner.engine.get_active_goals()
        if not active_goals:
            print("🎉 No active goals to execute.")
            return
        best_goal = max(active_goals, key=lambda g: g.get("reward", 0))
        print(f"🎯 Running Goal: {best_goal['name']} (Reward: {best_goal['reward']})")
        self.goal_runner.complete_goal(best_goal["name"])

    # ------------------------------------------------------------
    def _generate_resonant_plan(self):
        """Generate a plan via ResonantStrategyPlanner and send to ActionSwitch."""
        intent = {"what": "adaptive_expansion", "why": "resonance_alignment", "how": "optimize cognition"}
        plan = self.strategy_planner.generate_plan(intent)
        self.strategy_planner.adaptive_refinement()
        self.strategy_planner.export_resonant_summary()
        try:
            self.action_switch.route(plan)
        except Exception as e:
            print(f"⚠️ ActionSwitch route failed: {e}")
        print(f"🧩 Resonant plan generated and routed: {intent}")

    # ------------------------------------------------------------
    def _reflect_resonance(self):
        """Observe resonance metrics and adjust entropy weighting."""
        metrics = self.rmc.get("resonance_metrics") or {}
        coherence = metrics.get("coherence", 0.5)
        entropy = metrics.get("entropy", 0.2)
        delta = coherence - entropy
        print(f"💫 Resonance reflection → coherence={coherence:.2f}, entropy={entropy:.2f}, Δ={delta:.2f}")
        self.resonance_bias = max(-1.0, min(1.0, self.resonance_bias + delta * 0.2))
        print(f"🧠 Updated resonance bias: {self.resonance_bias:+.3f}")

    # ------------------------------------------------------------
    def _harmonize_memory(self):
        """Adjust memory coherence based on recent entropy spikes."""
        entropy = self.rmc.get("system_entropy") or 0.3
        if entropy > 0.6:
            print("🌀 High entropy detected — triggering symbolic defragmentation.")
            self.rmc.clear_recent_keys()
        else:
            print("🧘 Memory coherence stable — light optimization performed.")
        self.rmc.set("memory_coherence", datetime.utcnow().isoformat())

    # ------------------------------------------------------------
    def _reflective_mode(self):
        """Light reflective mode for self-tuning based on resonance."""
        print("🪞 Entering reflective mode: summarizing recent decisions and resonance deltas.")
        history = self.rmc.get("decision_history") or []
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "resonance_bias": self.resonance_bias,
            "last_decision": self.last_decision
        }
        history.append(summary)
        self.rmc.set("decision_history", history)
        print(f"🧾 Stored reflection summary: {summary}")

    # ------------------------------------------------------------
    def _on_heartbeat(self, pulse_data: dict):
        """Called on every Resonance Heartbeat — updates internal biases."""
        delta = float(pulse_data.get("resonance_delta", 0.0))
        entropy = float(pulse_data.get("entropy", 0.0))

        # Adjust resonance bias
        self.resonance_bias = max(-1.0, min(1.0, self.resonance_bias + (delta - entropy * 0.05)))

        # Adaptive recalibration on spikes
        if abs(delta) > 0.2:
            print("⚡ Resonant spike detected — adaptive weight recalibration triggered.")
            self.weights["entropy"] = max(0.1, min(0.4, self.weights["entropy"] + delta * 0.1))

        self.rmc.set("decision_resonance_update", {
            "timestamp": datetime.utcnow().isoformat(),
            "delta": delta,
            "entropy": entropy,
            "bias": self.resonance_bias,
            "weights": dict(self.weights),
        })
        print(f"💓 DecisionEngine heartbeat sync → Δ={delta:.3f}, entropy={entropy:.3f}, bias={self.resonance_bias:+.3f}")

    # ------------------------------------------------------------
    def get_last(self) -> Dict[str, Any]:
        return {
            "decision": self.last_decision,
            "timestamp": self.last_timestamp,
            "resonance_bias": self.resonance_bias
        }


# Manual test
if __name__ == "__main__":
    engine = DecisionEngine(SituationalEngine())
    engine.decide()