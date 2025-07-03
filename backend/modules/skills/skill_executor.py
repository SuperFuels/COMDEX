import json
import os
from datetime import datetime

# File paths
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "aion_memory.json")
EXECUTION_LOG = os.path.join(os.path.dirname(__file__), "skill_execution_log.json")
GOAL_SKILL_LOG = os.path.join(os.path.dirname(__file__), "goal_skill_log.json")  # Track skill-goal-strategy links

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return []
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)

def save_memory(memory_data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory_data, f, indent=2)

def load_goal_skill_log():
    if not os.path.exists(GOAL_SKILL_LOG):
        return []
    with open(GOAL_SKILL_LOG, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_goal_skill_log(log_data):
    with open(GOAL_SKILL_LOG, "w") as f:
        json.dump(log_data, f, indent=2)

def execute_skill(skill, linked_goal=None, linked_strategy_id=None):
    print(f"🚀 Executing skill: {skill['title']}")
    print(f"🛠️ Simulating skill logic for '{skill['title']}'...")

    log_entry = {
        "title": skill["title"],
        "executed_at": datetime.utcnow().isoformat(),
        "status": "completed",
        "linked_goal": linked_goal,
        "linked_strategy_id": linked_strategy_id
    }

    # Load existing execution log
    execution_log = []
    if os.path.exists(EXECUTION_LOG):
        with open(EXECUTION_LOG, "r") as f:
            execution_log = json.load(f)

    execution_log.append(log_entry)

    # Save updated execution log
    with open(EXECUTION_LOG, "w") as f:
        json.dump(execution_log, f, indent=2)

    # Update memory entry status to learned
    memory = load_memory()
    for s in memory:
        if s["title"] == skill["title"]:
            s["status"] = "learned"
            s["learned_on"] = datetime.utcnow().isoformat()

    save_memory(memory)
    print(f"✅ Skill '{skill['title']}' marked as learned.")

    # Log skill-goal-strategy linkage for traceability
    goal_skill_log = load_goal_skill_log()
    linkage_entry = {
        "skill_title": skill["title"],
        "linked_goal": linked_goal,
        "linked_strategy_id": linked_strategy_id,
        "executed_at": datetime.utcnow().isoformat()
    }
    goal_skill_log.append(linkage_entry)
    save_goal_skill_log(goal_skill_log)
    print(f"🔍 Logged skill-goal-strategy linkage: {linkage_entry}")

if __name__ == "__main__":
    memory = load_memory()
    queued_skills = [s for s in memory if s.get("status") == "queued"]
    if not queued_skills:
        print("ℹ️ No queued skills found.")
    else:
        # For standalone runs, no linkage info available, pass None
        execute_skill(queued_skills[0])