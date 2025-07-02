import asyncio
from modules.aion.goal_handler import GoalHandler

class SampleAgent:
    def __init__(self, name):
        self.name = name
        self.goal_handler = GoalHandler(name)

    async def receive_message(self, message):
        print(f"[{self.name}] Received message: {message}")
        if isinstance(message, dict) and message.get("type") == "goal_delegation":
            goal = message.get("goal")
            sender = message.get("from")
            await self.goal_handler.handle_goal(goal, sender)

    async def on_event(self, data):
        print(f"[{self.name}] Received event data: {data}")
