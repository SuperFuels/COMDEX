import json
import os
from datetime import datetime

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "aion_memory.json")
REQUEST_LOG = os.path.join(os.path.dirname(__file__), "aion_requests.log")

CURIOSITY_TRIGGERS = [
    "how", "why", "what if", "explore", "understand", "unknown", "learn more", "unclear"
]

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return []
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def log_request(skill_title, reason):
    with open(REQUEST_LOG, "a") as f:
        f.write(f"[{datetime.utcnow().isoformat()}] 🤖 AION requested: {skill_title} — Reason: {reason}\n")

def inference_request():
    memory = load_memory()
    learned_titles = {s["title"] for s in memory if s.get("status") == "learned"}

    suggestions = []

    for skill in memory:
        if skill.get("status") == "learned":
            title = skill.get("title", "").lower()
            for trigger in CURIOSITY_TRIGGERS:
                if trigger in title:
                    suggested = f"Deeper Understanding of {skill['title']}"
                    if suggested not in learned_titles:
                        suggestions.append({
                            "title": suggested,
                            "tags": skill.get("tags", []) + ["inferred"],
                            "status": "queued",
                            "source": "inference",
                            "added_on": datetime.utcnow().isoformat()
                        })
                        log_request(suggested, f"Triggered by: {skill['title']}")

    if suggestions:
        memory.extend(suggestions)
        save_memory(memory)
        print(f"🧠 AION inferred {len(suggestions)} new skills to learn.")
    else:
        print("ℹ️ No new inferences. All curiosity paths explored.")

if __name__ == "__main__":
    inference_request()
