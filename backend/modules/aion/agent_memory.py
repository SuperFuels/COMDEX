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
