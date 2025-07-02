# backend/modules/aion/basic_agents.py

import asyncio

class BasicAgent:
    def __init__(self, name, manager):
        self.name = name
        self.manager = manager
        self.manager.register_agent(name, self)

    async def receive_message(self, message):
        print(f"[{self.name}] Received message: {message}")
        msg_type = message.get("type")
        
        if msg_type == "task_request":
            await self.handle_task(message)
        elif msg_type == "task_response":
            await self.handle_response(message)
        else:
            print(f"[{self.name}] Unhandled message type: {msg_type}")

    async def handle_task(self, message):
        task = message.get("task")
        print(f"[{self.name}] Handling task: {task}")
        # Simulate task processing time
        await asyncio.sleep(1)
        print(f"[{self.name}] Completed task: {task}")

        # Send completion broadcast
        await self.manager.broadcast(self.name, "task_completed", {"task": task})

    async def handle_response(self, message):
        print(f"[{self.name}] Received response: {message}")

class MemoryAgent(BasicAgent):
    async def handle_task(self, message):
        print(f"[MemoryAgent] Processing memory task...")
        await asyncio.sleep(1)
        # Simulate memory update or reflection
        print(f"[MemoryAgent] Memory task done.")
        await self.manager.broadcast(self.name, "memory_updated", {"info": "Memory updated"})

class PlanningAgent(BasicAgent):
    async def handle_task(self, message):
        print(f"[PlanningAgent] Creating plan...")
        await asyncio.sleep(1)
        print(f"[PlanningAgent] Plan created.")
        await self.manager.broadcast(self.name, "plan_ready", {"plan": "Sample plan"})

class TaskAgent(BasicAgent):
    async def handle_task(self, message):
        print(f"[TaskAgent] Executing delegated task...")
        await asyncio.sleep(2)
        print(f"[TaskAgent] Task execution complete.")
        await self.manager.broadcast(self.name, "task_done", {"task": message.get("task")})