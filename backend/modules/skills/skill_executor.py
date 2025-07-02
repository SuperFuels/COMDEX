import json
import os
from datetime import datetime

# File paths
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "aion_memory.json")
EXECUTION_LOG = os.path.join(os.path.dirname(__file__), "skill_execution_log.json")

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return []
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)

def save_memory(memory_data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory_data, f, indent=2)

def execute_skill(skill):
    print(f"🚀 Executing skill: {skill['title']}")
    print(f"🛠️ Simulating skill logic for '{skill['title']}'...")

    log_entry = {
        "title": skill["title"],
        "executed_at": datetime.utcnow().isoformat(),
        "status": "completed"
    }

    # Load existing log
    execution_log = []
    if os.path.exists(EXECUTION_LOG):
        with open(EXECUTION_LOG, "r") as f:
            execution_log = json.load(f)

    execution_log.append(log_entry)

    # Save updated log
    with open(EXECUTION_LOG, "w") as f:
        json.dump(execution_log, f, indent=2)

    # Update memory entry
    memory = load_memory()
    for s in memory:
        if s["title"] == skill["title"]:
            s["status"] = "learned"
            s["learned_on"] = datetime.utcnow().isoformat()

    save_memory(memory)
    print(f"✅ Skill '{skill['title']}' marked as learned.")

if __name__ == "__main__":
    memory = load_memory()
    queued_skills = [s for s in memory if s.get("status") == "queued"]
    if not queued_skills:
        print("ℹ️ No queued skills found.")
    else:
        execute_skill(queued_skills[0])
