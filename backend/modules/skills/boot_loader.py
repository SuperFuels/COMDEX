import json
from pathlib import Path
from backend.modules.skills.goal_engine import GoalEngine

BOOT_FILE = Path(__file__).parent / "boot_skills.json"

def load_boot_goals():
    engine = GoalEngine()
    if engine.goals:
        print("🧠 Existing goals found. Boot loading skipped.")
        return

    if BOOT_FILE.exists():
        with open(BOOT_FILE) as f:
            data = json.load(f)
            for goal in data.get("goals", []):
                engine.assign_goal(goal)
        print("🚀 Boot goals loaded successfully.")
    else:
        print("⚠️ No boot_skills.json found.")
