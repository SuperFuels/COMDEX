# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class AgentMemory:
    """
    Lightweight memory storage for an agent.
    Can be upgraded later with embedding/vector support.
    """

    def __init__(self):
        self.goals = []
        self.messages = []
        self.completed_tasks = []

    def remember_goal(self, goal):
        self.goals.append(goal)

    def remember_message(self, message):
        self.messages.append(message)

    def mark_complete(self, goal):
        self.completed_tasks.append(goal)

    def dump(self):
        return {
            "goals": self.goals,
            "messages": self.messages,
            "completed": self.completed_tasks,
        }
