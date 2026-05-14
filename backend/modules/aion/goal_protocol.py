import random

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class GoalProtocol:
    """
    Handles negotiation, acceptance, rejection, and confirmation
    of delegated goals between agents.
    """

    def __init__(self):
        self.negotiation_log = []

    def evaluate_goal(self, goal: str, agent_traits: dict = None):
        """
        Simulate decision to accept or reject based on traits or randomness.
        """
        decision = "accepted" if random.random() > 0.2 else "rejected"
        self.negotiation_log.append({"goal": goal, "decision": decision})
        return decision

    def get_log(self):
        return self.negotiation_log
