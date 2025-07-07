import asyncio
from backend.modules.hexcore.agent_manager import AgentManager
from backend.modules.aion.sample_agent import SampleAgent

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

async def main():
    manager = AgentManager()

    agent1 = SampleAgent("AgentAlpha")
    agent2 = SampleAgent("AgentBeta")

    manager.register_agent(agent1.name, agent1)
    manager.register_agent(agent2.name, agent2)

    # Subscribe agent1 to an event
    manager.comm.subscribe("test_event", agent1.on_event)
    # Subscribe agent2 to same event
    manager.comm.subscribe("test_event", agent2.on_event)

    # Broadcast an event to both agents
    await manager.broadcast("system", "test_event", {"msg": "Hello agents!"})

    # Agent1 sends direct message to Agent2
    await manager.send("AgentAlpha", "AgentBeta", {"text": "Direct message from Alpha to Beta"})

    # Test goal delegation async
    await manager.delegate_goal("Complete task X", "AgentAlpha", "AgentBeta")

    # Test negotiation placeholder
    await manager.negotiate_goals()

if __name__ == "__main__":
    asyncio.run(main())