import os
from datetime import datetime

AGENT_TEMPLATE = '''
import asyncio

# ✅ DNA Switch Registered
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)

class {class_name}:
    def __init__(self, name):
        self.name = name

    async def receive_message(self, message):
        print(f"[{self.name}] Received message: {message}")

    async def on_event(self, data):
        print(f"[{self.name}] Received event data: {data}")
'''

def create_agent(agent_name, output_dir="backend/modules/aion/agents"):
    os.makedirs(output_dir, exist_ok=True)
    class_name = agent_name.replace("_", " ").title().replace(" ", "")
    file_name = f"{agent_name}.py"
    file_path = os.path.join(output_dir, file_name)

    if os.path.exists(file_path):
        print(f"❌ Agent already exists: {file_path}")
        return

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(AGENT_TEMPLATE.format(class_name=class_name))

    print(f"✅ Created new agent: {file_path}")
    return file_path

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create a new AION agent with DNA Switch embedded.")
    parser.add_argument("agent_name", type=str, help="Name of the agent (e.g. scout_agent)")
    args = parser.parse_args()

    create_agent(args.agent_name)
