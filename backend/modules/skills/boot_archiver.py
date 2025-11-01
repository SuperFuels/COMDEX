import json
from pathlib import Path
from datetime import datetime

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

MODULE_DIR = Path(__file__).resolve().parent
MEMORY_FILE = MODULE_DIR / "aion_memory.json"
ARCHIVE_FILE = MODULE_DIR / "learned_skills.json"

def load_json(path):
    if not path.exists():
        return []
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def archive_learned_skills():
    memory = load_json(MEMORY_FILE)
    archive = load_json(ARCHIVE_FILE)

    still_learning = []
    newly_learned = []

    for entry in memory:
        if entry.get("status") == "learned":
            entry["archived_on"] = datetime.now().isoformat()
            newly_learned.append(entry)
        else:
            still_learning.append(entry)

    if newly_learned:
        archive.extend(newly_learned)
        save_json(ARCHIVE_FILE, archive)
        save_json(MEMORY_FILE, still_learning)
        print(f"✅ Archived {len(newly_learned)} learned skills and cleaned memory.")
    else:
        print("i️ No learned skills to archive.")

if __name__ == "__main__":
    archive_learned_skills()