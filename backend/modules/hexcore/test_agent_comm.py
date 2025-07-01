import asyncio
from modules.aion.agent_manager import AgentManager
from modules.aion.sample_agent import SampleAgent

async def main():
    manager = AgentManager()

    agent_a = SampleAgent("AgentA")
    agent_b = SampleAgent("AgentB")

    manager.register_agent("AgentA", agent_a)
    manager.register_agent("AgentB", agent_b)

    # Subscribe agent_b to an event
    manager.comm.subscribe("test_event", agent_b.on_event)

    # Send direct message AgentA -> AgentB
    await manager.send("AgentA", "AgentB", "Hello from AgentA!")

    # Broadcast an event from AgentA
    await manager.broadcast("AgentA", "test_event", {"info": "Event data payload"})

    # Print log
    print("Communication Log:", manager.get_log())

asyncio.run(main())
