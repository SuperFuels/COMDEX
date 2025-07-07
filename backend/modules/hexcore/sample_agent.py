import asyncio

import asyncio

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class SampleAgent:
    def __init__(self, name):
        self.name = name

    async def receive_message(self, message):
        print(f"[{self.name}] Received message: {message}")

    async def on_event(self, data):
        print(f"[{self.name}] Received event data: {data}")

    # You can add other methods here for goal handling, negotiation, etc.