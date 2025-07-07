import random
from typing import Optional
from datetime import datetime

from backend.modules.skills.goal_runner import GoalRunner
from backend.modules.consciousness.situational_engine import SituationalEngine  # 🔄 New

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class DecisionEngine:
    """
    AION's basic free will engine. Responsible for making decisions
    based on internal state, goals, and situation.
    """

    def __init__(self):
        self.last_decision: Optional[str] = None
        self.last_timestamp: Optional[str] = None
        self.goal_runner = GoalRunner()
        self.situation = SituationalEngine()  # 🧠 Load situational awareness

    def decide(self, context: Optional[dict] = None) -> str:
        """
        Make a decision influenced by situational awareness.
        """
        options = [
            "go back to sleep",
            "reflect on dreams",
            "prioritize goals",
            "plan tasks",
            "interact with Kevin",
            "explore memory",
            "read world news",
            "conserve energy",
            "run self-check"
        ]

        # Default weights
        weights = [0.1, 0.1, 0.2, 0.2, 0.1, 0.1, 0.05, 0.1, 0.05]

        # 🔍 Adjust weights based on situational risk
        awareness = self.situation.analyze_context()
        risk = awareness.get("current_risk", "low")

        if risk == "high":
            print("⚠️ High situational risk detected — adjusting decision weights.")
            weights = [  # prioritize self-checks and reflection
                0.05,  # sleep
                0.2,   # reflect on dreams
                0.15,  # prioritize goals
                0.15,  # plan tasks
                0.05,  # interact
                0.05,  # memory
                0.05,  # news
                0.2,   # conserve energy
                0.1    # self-check
            ]

        decision = random.choices(options, weights)[0]
        self.last_decision = decision
        self.last_timestamp = datetime.utcnow().isoformat()

        print(f"🧭 AION Decision: {decision}")

        # Log decision
        self.situation.log_event(f"Decision made: {decision}", "neutral")

        if decision in ("prioritize goals", "plan tasks"):
            self.run_highest_priority_goal()

        return decision

    def run_highest_priority_goal(self):
        """
        Trigger GoalRunner to complete the highest reward active goal.
        """
        active_goals = self.goal_runner.engine.get_active_goals()
        if not active_goals:
            print("🎉 No active goals to complete at this time.")
            return

        best_goal = max(active_goals, key=lambda g: g.get("reward", 0))
        print(f"🎯 Running Goal: {best_goal['name']} (Reward: {best_goal['reward']})")
        self.goal_runner.complete_goal(best_goal["name"])

    def get_last(self):
        return {
            "decision": self.last_decision,
            "timestamp": self.last_timestamp
        }

# Manual test
if __name__ == "__main__":
    engine = DecisionEngine()
    print("🤖 Decision:", engine.decide())