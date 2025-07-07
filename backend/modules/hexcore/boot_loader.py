import json
import os
from datetime import datetime
from backend.modules.skills.milestone_tracker import MilestoneTracker

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
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

def dependencies_met(skill, memory_data):
    """Check if all dependencies are learned."""
    learned_titles = {entry["title"] for entry in memory_data if entry.get("status") == "learned"}
    for dep in skill.get("dependencies", []):
        if dep not in learned_titles:
            return False
    return True

# Enhanced Bootloader core
def load_boot_goals():
    boot_skills = load_json(BOOTLOADER_FILE)
    memory_data = load_json(MEMORY_FILE)

    memory_titles = {entry["title"] for entry in memory_data}
    tracker = MilestoneTracker()
    updated_memory = memory_data.copy()
    new_entries = []
    promoted_count = 0

    # Add new skills from bootloader file if missing
    for skill in boot_skills:
        title = skill.get("title")
        tags = skill.get("tags", [])
        if title not in memory_titles:
            milestone_ready = tracker.is_milestone_triggered(tags)
            # If milestone triggered AND dependencies met, mark 'ready' else 'queued'
            status = "ready" if milestone_ready else "queued"
            skill_entry = {
                "title": title,
                "tags": tags,
                "description": skill.get("description", ""),
                "status": status,
                "source": "bootloader",
                "added_on": datetime.utcnow().isoformat(),
                "priority": skill.get("priority", 1),
                "dependencies": skill.get("dependencies", []),
                "learned_on": None
            }
            new_entries.append(skill_entry)

    if new_entries:
        updated_memory.extend(new_entries)
        print(f"✅ {len(new_entries)} new skills added to memory.")

    # Promote 'ready' skills to 'queued' if dependencies met
    for entry in updated_memory:
        if entry.get("status") == "ready":
            if dependencies_met(entry, updated_memory):
                entry["status"] = "queued"
                promoted_count += 1

    if promoted_count > 0:
        print(f"⬆️ Promoted {promoted_count} skills from 'ready' to 'queued' based on dependencies.")

    # Save updated memory
    save_json(MEMORY_FILE, updated_memory)

    if not new_entries and promoted_count == 0:
        print("ℹ️ No new bootloader skills added or promoted. Memory is up to date.")

if __name__ == "__main__":
    load_boot_goals()