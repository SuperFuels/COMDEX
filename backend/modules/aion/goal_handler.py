import asyncio

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class GoalHandler:
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.goal_queue = []

    async def handle_goal(self, goal: str, sender: str):
        print(f"[{self.agent_name}] Handling goal '{goal}' from {sender}")
        await asyncio.sleep(0.5)  # simulate delay
        self.goal_queue.append(goal)
        print(f"[{self.agent_name}] Goal '{goal}' accepted and queued.")

    def list_goals(self):
        return self.goal_queue
