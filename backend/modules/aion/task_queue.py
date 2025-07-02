import asyncio

class TaskQueue:
    """
    Handles async execution and management of tasks for agents.
    """

    def __init__(self):
        self.queue = asyncio.Queue()

    async def add_task(self, task: str):
        await self.queue.put(task)

    async def run(self):
        while not self.queue.empty():
            task = await self.queue.get()
            print(f"🚀 Executing task: {task}")
            await asyncio.sleep(1)  # Simulate delay
            print(f"✅ Task completed: {task}")
