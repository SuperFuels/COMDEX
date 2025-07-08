import json
import os
from datetime import datetime
from backend.modules.skills.milestone_tracker import MilestoneTracker

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# Paths
BASE_DIR = os.path.dirname(__file__)
BOOTLOADER_FILE = os.path.join(BASE_DIR, "matrix_bootloader.json")
MEMORY_FILE = os.path.join(BASE_DIR, "aion_memory.json")

# Loaders & Savers
def load_json(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        return json.load(f)

def save_json(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

# Bootloader core
def load_boot_goals():
    boot_skills = load_json(BOOTLOADER_FILE)
    memory_data = load_json(MEMORY_FILE)

    memory_titles = {entry["title"] for entry in memory_data}
    tracker = MilestoneTracker()
    new_entries = []

    for skill in boot_skills:
        title = skill.get("title")
        tags = skill.get("tags", [])
        if title not in memory_titles:
            milestone_ready = tracker.is_milestone_triggered(tags)
            skill_entry = {
                "title": title,
                "tags": tags,
                "description": skill.get("description", ""),
                "status": "queued" if not milestone_ready else "ready",
                "source": "bootloader",
                "added_on": datetime.utcnow().isoformat(),
                "priority": skill.get("priority", 1),
                "dependencies": skill.get("dependencies", []),
                "learned_on": None
            }
            new_entries.append(skill_entry)

    if new_entries:
        memory_data.extend(new_entries)
        save_json(MEMORY_FILE, memory_data)
        print(f"✅ {len(new_entries)} new skills queued or ready based on milestones.")
    else:
        print("ℹ️ No new bootloader skills added. Memory is up to date.")

if __name__ == "__main__":
    load_boot_goals()
