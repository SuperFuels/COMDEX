import json
from pathlib import Path

boot_path = Path(__file__).parent / "boot_skills.json"
goal_path = Path(__file__).parent / "goals.json"

with open(boot_path) as f:
    boot_data = json.load(f)

boot_goals = boot_data.get("goals", [])

if goal_path.exists():
    with open(goal_path) as f:
        current_data = json.load(f)
else:
    current_data = {"goals": [], "completed": []}

existing_names = {g["name"] for g in current_data["goals"]}
new_goals = [g for g in boot_goals if g["name"] not in existing_names]
current_data["goals"].extend(new_goals)

with open(goal_path, "w") as f:
    json.dump(current_data, f, indent=2)

print(f"✅ Imported {len(new_goals)} new goals into goals.json.")
