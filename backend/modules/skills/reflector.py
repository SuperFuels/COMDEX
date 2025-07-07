import json
import os
from datetime import datetime

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

REFLECTED_SKILLS_FILE = os.path.join(os.path.dirname(__file__), "reflected_skills.json")

def load_reflected():
    if not os.path.exists(REFLECTED_SKILLS_FILE):
        return []
    with open(REFLECTED_SKILLS_FILE, "r") as f:
        return json.load(f)

def save_reflected(data):
    with open(REFLECTED_SKILLS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def reflect_on_skill(title: str, success: bool, notes: str = ""):
    reflected = load_reflected()
    timestamp = datetime.utcnow().isoformat()

    updated = False
    for item in reflected:
        if item["title"] == title:
            item["status"] = "learned" if success else "skipped"
            item["reflection"] = notes
            item["reflected_on"] = timestamp
            updated = True
            break

    if not updated:
        reflected.append({
            "title": title,
            "status": "learned" if success else "skipped",
            "reflection": notes,
            "reflected_on": timestamp
        })

    save_reflected(reflected)
    return [r for r in reflected if r["title"] == title][0]