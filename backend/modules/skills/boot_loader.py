import json
import os
from datetime import datetime

# Paths
BOOTLOADER_FILE = os.path.join(os.path.dirname(__file__), "matrix_bootloader.json")
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "aion_memory.json")

def load_json(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        return json.load(f)

def save_json(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

def bootload_skills():
    boot_skills = load_json(BOOTLOADER_FILE)
    memory_data = load_json(MEMORY_FILE)

    memory_titles = {entry["title"] for entry in memory_data}
    new_entries = []

    for skill in boot_skills:
        if skill["title"] not in memory_titles:
            skill_entry = {
                "title": skill["title"],
                "tags": skill.get("tags", []),
                "status": "queued",
                "source": "bootloader",
                "added_on": datetime.utcnow().isoformat()
            }
            new_entries.append(skill_entry)

    if new_entries:
        memory_data.extend(new_entries)
        save_json(MEMORY_FILE, memory_data)
        print(f"✅ {len(new_entries)} new skills bootloaded into memory.")
    else:
        print("ℹ️ No new skills to load. All are already in memory.")

if __name__ == "__main__":
    bootload_skills()
