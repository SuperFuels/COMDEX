import asyncio
from typing import Dict, Any
from backend.modules.hexcore.agent_comm import AgentComm

class AgentManager:
    """
    Manages agents, routes messages, logs communication,
    and coordinates task delegation.
    """

    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.comm = AgentComm()
        self.log = []

    def register_agent(self, name: str, agent):
        self.agents[name] = agent
        print(f"✅ Agent registered: {name}")

    def unregister_agent(self, name: str):
        if name in self.agents:
            del self.agents[name]
            print(f"❌ Agent unregistered: {name}")

    async def send(self, sender_name: str, recipient_name: str, message: Any):
        if recipient_name not in self.agents:
            print(f"⚠️ Recipient agent '{recipient_name}' not found.")
            return
        recipient = self.agents[recipient_name]
        self.log.append({"from": sender_name, "to": recipient_name, "message": message})
        await self.comm.send_message(recipient, message)

    async def broadcast(self, sender_name: str, event_name: str, data: Any):
        self.log.append({"from": sender_name, "to": "all", "event": event_name, "data": data})
        await self.comm.publish(event_name, data)

    def get_log(self):
        return self.log
