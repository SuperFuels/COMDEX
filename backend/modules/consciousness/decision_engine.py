# backend/modules.consciousness.decision_engine.py

import random
from typing import Optional
from datetime import datetime

class DecisionEngine:
    """
    AION's basic free will engine. Responsible for making decisions
    based on internal state, goals, and situation. Currently uses
    random weighted logic for simplicity, but is designed for extensibility.
    """

    def __init__(self):
        self.last_decision: Optional[str] = None
        self.last_timestamp: Optional[str] = None

    def decide(self, context: Optional[dict] = None) -> str:
        """
        Make a basic decision. If a goal or situation is provided,
        it can influence the choice.
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

        weights = [
            0.1,  # sleep
            0.1,  # reflect
            0.2,  # prioritize goals
            0.2,  # plan tasks
            0.1,  # interact
            0.1,  # memory
            0.05, # news
            0.1,  # conserve
            0.05  # self-check
        ]

        decision = random.choices(options, weights)[0]
        self.last_decision = decision
        self.last_timestamp = datetime.utcnow().isoformat()

        return decision

    def get_last(self):
        return {
            "decision": self.last_decision,
            "timestamp": self.last_timestamp
        }

# For manual testing
if __name__ == "__main__":
    engine = DecisionEngine()
    print("🤖 Decision:", engine.decide())