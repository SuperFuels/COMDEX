import json
import os
from datetime import datetime
from pathlib import Path

BOOTLOADER_FILE = Path(__file__).resolve().parent.parent / "modules/skills/matrix_bootloader.json"
MEMORY_FILE = Path(__file__).resolve().parent.parent / "modules/skills/aion_memory.json"

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def register_skills_by_tag(tag):
    matrix = load_json(BOOTLOADER_FILE)
    memory = load_json(MEMORY_FILE)
    memory_titles = {m["title"] for m in memory}
    new_skills = []

    for skill in matrix:
        if tag in skill.get("tags", []) and skill["title"] not in memory_titles:
            new_entry = {
                "title": skill["title"],
                "tags": skill.get("tags", []),
                "description": skill.get("description", ""),
                "status": "queued",
                "source": "bootloader",
                "added_on": datetime.utcnow().isoformat(),
                "priority": skill.get("priority", 1),
                "dependencies": skill.get("dependencies", []),
                "learned_on": None
            }
            new_skills.append(new_entry)

    if new_skills:
        memory.extend(new_skills)
        save_json(MEMORY_FILE, memory)
        print(f"✅ Registered {len(new_skills)} skills with tag '{tag}'.")
    else:
        print(f"ℹ️ No new skills found with tag '{tag}'.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python register_boot_skills.py <tag>")
    else:
        register_skills_by_tag(sys.argv[1])