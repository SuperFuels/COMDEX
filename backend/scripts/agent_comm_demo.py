# backend/scripts/agent_comm_demo.py

import asyncio
from backend.modules.hexcore.agent_manager import AgentManager 
from backend.modules.aion.sample_agent import SampleAgent

async def main():
    manager = AgentManager()

    alice = SampleAgent("Alice")
    bob = SampleAgent("Bob")

    manager.register_agent("Alice", alice)
    manager.register_agent("Bob", bob)

    # Alice delegates a goal to Bob
    await manager.delegate_goal("Analyze market trends", "Alice", "Bob")

    # Start a negotiation broadcast event
    await manager.negotiate_goals()

    # Print communication log
    print("\nCommunication Log:")
    for entry in manager.get_log():
        print(entry)

if __name__ == "__main__":
    asyncio.run(main())