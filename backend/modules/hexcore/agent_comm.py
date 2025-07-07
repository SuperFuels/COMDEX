# backend/modules/aion/agent_comm.py

import asyncio
from typing import Callable, Dict, List, Any

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class AgentComm:
    """
    Core communication class for AION agents.
    Supports async message sending, event hooks, and pub-sub.
    """

    def __init__(self):
        self.subscribers: Dict[str, List[Callable[[Any], None]]] = {}

    def subscribe(self, event_name: str, callback: Callable[[Any], None]):
        """Subscribe a callback function to an event."""
        if event_name not in self.subscribers:
            self.subscribers[event_name] = []
        self.subscribers[event_name].append(callback)

    async def publish(self, event_name: str, data: Any):
        """Publish an event asynchronously to all subscribers."""
        if event_name in self.subscribers:
            coros = []
            for callback in self.subscribers[event_name]:
                if asyncio.iscoroutinefunction(callback):
                    coros.append(callback(data))
                else:
                    callback(data)
            if coros:
                await asyncio.gather(*coros)

    async def send_message(self, agent, message: Any):
        """Send a direct message to a specific agent."""
        if hasattr(agent, "receive_message"):
            if asyncio.iscoroutinefunction(agent.receive_message):
                await agent.receive_message(message)
            else:
                agent.receive_message(message)
        else:
            raise AttributeError("Target agent has no 'receive_message' method.")