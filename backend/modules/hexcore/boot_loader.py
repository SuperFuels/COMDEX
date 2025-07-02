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

def load_boot_goals():
    boot_skills = load_json(BOOTLOADER_FILE)
    memory_data = load_json(MEMORY_FILE)

    memory_titles = {entry["title"] for entry in memory_data}
    new_entries = []

    for skill in boot_skills:
        title = skill.get("title")
        tags = skill.get("tags", [])
        role = skill.get("role", "core")
        agent = skill.get("agent", None)

        if not title:
            continue  # Skip malformed

        if title in memory_titles:
            continue  # Already loaded

        skill_entry = {
            "title": title,
            "tags": tags,
            "role": role,
            "agent": agent,
            "status": "queued",
            "source": "bootloader",
            "added_on": datetime.utcnow().isoformat()
        }

        new_entries.append(skill_entry)

    if new_entries:
        memory_data.extend(new_entries)
        save_json(MEMORY_FILE, memory_data)
        print(f"✅ Bootloader added {len(new_entries)} new skills to memory.")
    else:
        print("ℹ️ No new skills to load. All are already in memory.")

if __name__ == "__main__":
    load_boot_goals()
