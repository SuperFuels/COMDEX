
SEEDING SCRIPT - AION LERANING CYCLE
PYTHONPATH=backend python backend/scripts/aion_learning_cycle.py


✅ To unlock a boot skill automatically, all of these must happen:
	1.	A memory is stored (e.g. a dream or seeded idea).
	2.	That memory content is reflected on by MemoryReflector.
	3.	🔍 BootSelector scans memory text for matches to bootloader skills.
	4.	If the content matches a skill’s tags, and it’s not yet learned, it’s marked for activation.

⸻

🔗 So yes, you need:

✅ 1. matrix_bootloader.json to contain:
	•	Skills with title, description, and strong tags.
	•	Example for “Swarm Intelligence”:


    {
  "title": "Swarm Intelligence Foundations",
  "description": "Learn how decentralized agents collaborate using swarm-based logic, such as ants or bees. Applications in distributed planning and AION's internal agents.",
  "tags": ["swarm", "decentralized", "agent", "collaboration", "planning"],
  "learned": false
}

✅ 2. A memory that mentions one or more of those tags.

memory.store({
  "label": "manual_seed",
  "content": "AION should explore swarm intelligence to allow distributed agents to cooperate like bees."
})

This would auto-trigger the skill match → load it into AION’s boot sequence.

| File                        | Purpose                                                                 | Triggered by                                           |
|----------------------------|-------------------------------------------------------------------------|--------------------------------------------------------|
| matrix_bootloader.json     | Master list of skills with tags                                         | Queried by `boot_loader.py`                           |
| aion_memory.json           | Active skill memory (queued, ready, learned)                            | Modified by `boot_loader.py`                          |
| boot_loader.py             | Adds new skills from matrix to memory (if not already there)            | ✅ Manual run or dream milestone trigger               |
| boot_skills.json           | Standalone list of boot skills with rewards                             | Used by goal/milestone engine                         |
| milestone_tracker.py       | Detects when memory or reflections match boot skill tags                | ✅ Used in `boot_loader.py`                            |
| register_boot_skills.py    | Helper to add skills based on tags (like `"swarm"` or `"agent"`)        | ✅ You run this manually to inject new skills          |



| Stage                   | Action                                                              |
|-------------------------|---------------------------------------------------------------------|
| matrix_bootloader.json | 📥 Source of potential skills                                        |
| register_boot_skills.py| 🛠 Adds matching-tag skills to memory                                |
| aion_memory.json        | 🧠 Active boot skill memory (queued → ready → learned)              |
| boot_archiver.py        | 📦 Moves learned skills to learned_skills.json                      |
| learned_skills.json     | 🧾 Permanent knowledge library for what AION knows                  |


. Dream → Strategy → Goal Feedback

This is now fully supported and ready:
	•	Dream → triggers Reflection
	•	Reflection → adds Milestones
	•	Milestones → create Goals
	•	Goals → match Skills
	•	Skills → become “learned” → archived





    

H1. How AION Naturally Unlocks Milestones & Learns
	•	MemoryReflector scans AION’s stored memories/dreams, summarizes knowledge, creates new milestones and strategies.
	•	When milestones unlock, GoalEngine creates new goals related to those milestones.
	•	Completing goals rewards AION tokens and new skills, which in turn fuel more learning cycles.

This forms an organic learning feedback loop:
	•	Learn → Reflect → Unlock Milestone → New Goals → Complete Goals → Gain Tokens/Skills → Repeat

⸻

2. Manually Seeding Ideas into Dreams (Memory)

To manually add an idea or concept as a “dream” or memory entry:

from modules.hexcore.memory_engine import MemoryEngine

memory = MemoryEngine()

# Store a new memory/dream manually
memory.store({
    "label": "manual_seed_idea",
    "content": "Explore advanced crypto market making techniques."
})

This adds a new piece of knowledge into AION’s memory for reflection.

⸻

3. Creating New Milestones Manually

Use the MilestoneTracker (commonly imported as tracker) to add milestones directly:

from modules.skills.milestone_goal_integration import tracker

# Add a new milestone manually
tracker.add_milestone(
    name="advanced_crypto_mastery",
    source="manual_seed",
    excerpt="Unlock deeper knowledge and skills in crypto market making."
)

This milestone will be detected by GoalEngine via message passing and create new goals.

⸻

4. Forcing AION to Reflect & Process New Data (Trigger Reflection)

Run the MemoryReflector to process new memories and generate milestones & strategies:

from modules.skills.memory_reflector import MemoryReflector

reflector = MemoryReflector()
reflector.reflect()

5. How to Mint New Tokens (Reward AION)

Typically, tokens are minted when goals complete successfully.

Use the AIWallet instance to manually add tokens:

from modules.aion.ai_wallet import AIWallet

wallet = AIWallet()
wallet.earn("STK", 10)  # Mint 10 $STK tokens to AION wallet

Summary: Quick Command Cheatsheet

Action
Command Example
Seed new memory/idea
memory.store({"label":"idea1","content":"Learn about XYZ."})
Add milestone manually
tracker.add_milestone("milestone_name","manual_seed","desc")
Trigger reflection
MemoryReflector().reflect()
Mint tokens manually
AIWallet().earn("STK", 10)




Great! Let me provide you with the complete sample_agent.py and a simple CLI demo script to test the agent-to-agent communication. This will let you register agents, send messages, and see asynchronous communication in action.

⸻
. sample_agent.py

import asyncio

class SampleAgent:
    def __init__(self, name):
        self.name = name

    async def receive_message(self, message):
        print(f"[{self.name} RECEIVED]: {message}")
        # Example: auto-reply for demonstration
        if isinstance(message, dict) and message.get("type") == "goal_delegation":
            reply = f"Agent {self.name} acknowledges goal: {message.get('goal')}"
            await asyncio.sleep(1)  # simulate thinking delay
            print(f"[{self.name} REPLY]: {reply}")

            2. Simple CLI demo script: agent_demo.py

            import asyncio
from modules.aion.agent_manager import AgentManager
from modules.aion.sample_agent import SampleAgent

async def main():
    manager = AgentManager()

    # Register two agents
    agent_a = SampleAgent("Agent_A")
    agent_b = SampleAgent("Agent_B")
    manager.register_agent("Agent_A", agent_a)
    manager.register_agent("Agent_B", agent_b)

    # Send a direct message
    await manager.send("Agent_A", "Agent_B", {"type": "greeting", "content": "Hello from Agent_A!"})

    # Delegate a goal
    await manager.delegate_goal("Collect resources", "Agent_A", "Agent_B")

    # Broadcast a message
    await manager.broadcast("Agent_A", "system_announcement", {"message": "All agents prepare for action."})

    # Print communication log
    print("\nCommunication Log:")
    for log in manager.get_log():
        print(log)

if __name__ == "__main__":
    asyncio.run(main())


    What to do next:
	1.	Place sample_agent.py inside backend/modules/aion/
	2.	Place agent_demo.py inside backend/scripts/
	3.	Run the demo with:

	PYTHONPATH=backend python backend/scripts/agent_demo.py
