import asyncio

class SampleAgent:
    def __init__(self, name):
        self.name = name

    async def receive_message(self, message):
        print(f"[{self.name}] Received message: {message}")
        # Simulate async processing
        await asyncio.sleep(0.1)

    def on_event(self, data):
        print(f"[{self.name}] Received event data: {data}")
