import json
import argparse
from pathlib import Path
from datetime import datetime

# 📁 File paths
boot_path = Path(__file__).parent / "boot_skills.json"
goal_path = Path(__file__).parent / "goals.json"
log_path = Path(__file__).parent / "goal_import_log.json"

# 🛠️ Parse CLI arguments (optional dry-run)
parser = argparse.ArgumentParser(description="Import boot goals into AION.")
parser.add_argument("--dry-run", action="store_true", help="Run without modifying goals.json")
args = parser.parse_args()

# 🧠 Load boot goals
with open(boot_path) as f:
    boot_data = json.load(f)

boot_goals = boot_data.get("goals", [])

# 📖 Load current goals (or initialize if missing)
if goal_path.exists():
    with open(goal_path) as f:
        current_data = json.load(f)
else:
    current_data = {"goals": [], "completed": []}

# 🧠 Detect existing goals
existing_names = {g["name"] for g in current_data["goals"]}
new_goals = [g for g in boot_goals if g["name"] not in existing_names]

# 🔗 Track milestone-linked goals
milestone_goals = [g for g in new_goals if "milestone" in g]
standalone_goals = [g for g in new_goals if "milestone" not in g]

# ✅ Update if not dry run
if not args.dry_run:
    current_data["goals"].extend(new_goals)
    with open(goal_path, "w") as f:
        json.dump(current_data, f, indent=2)

    # Optional: log this import event
    import_log = {
        "timestamp": datetime.now().isoformat(),
        "added": len(new_goals),
        "milestone_linked": [g["name"] for g in milestone_goals],
        "standalone": [g["name"] for g in standalone_goals]
    }
    if log_path.exists():
        with open(log_path, "r") as f:
            try:
                full_log = json.load(f)
            except Exception:
                full_log = []
    else:
        full_log = []
    full_log.append(import_log)
    with open(log_path, "w") as f:
        json.dump(full_log, f, indent=2)

# 📊 Print result
print(f"✅ {len(new_goals)} new goals imported into goals.json.")
print(f"🔗 {len(milestone_goals)} linked to milestones.")
print(f"📄 {len(current_data['goals'])} total goals now in file.")
if args.dry_run:
    print("⚠️ Dry-run mode: no changes were saved.")