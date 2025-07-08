# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class AgentMemory:
    """
    Simple memory store for agents to track tasks/goals received.
    """

    def __init__(self):
        self.goals = []

    def remember_goal(self, goal: str):
        self.goals.append(goal)

    def list_goals(self):
        return self.goals

    def clear_goals(self):
        self.goals = []
