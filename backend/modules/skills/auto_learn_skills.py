import os
import json
from skill_executor import execute_skill

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "aion_memory.json")

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return []
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)

def get_queued_skills(memory_data):
    return [skill for skill in memory_data if skill.get("status") == "queued"]

def auto_learn():
    memory = load_memory()
    queued_skills = get_queued_skills(memory)

    if not queued_skills:
        print("✅ No queued skills found. All skills are up to date.")
        return

    print(f"📚 Found {len(queued_skills)} queued skill(s). Beginning execution...\n")

    for skill in queued_skills:
        execute_skill(skill)

    print("\n✅ All queued skills executed.")

if __name__ == "__main__":
    auto_learn()