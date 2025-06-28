import json
import os
import random
from datetime import datetime
from aion_inference_engine import inference_request

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "aion_memory.json")
DREAM_LOG = os.path.join(os.path.dirname(__file__), "aion_dreams.log")

def load_json(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        return json.load(f)

def save_json(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

def log_dream(skill):
    with open(DREAM_LOG, "a") as log:
        log.write(f"[{datetime.utcnow().isoformat()}] 🌌 AION dreamt about learning: {skill['title']}\n")

def run_dream_cycle():
    memory_data = load_json(MEMORY_FILE)
    queued_skills = [s for s in memory_data if s.get("status") == "queued"]

    if not queued_skills:
        print("💤 No queued skills to dream about.")
        return

    skill = random.choice(queued_skills)
    log_dream(skill)

    for entry in memory_data:
        if entry["title"] == skill["title"]:
            entry["status"] = "in_progress"
            entry["last_dreamed"] = datetime.utcnow().isoformat()
            break

    save_json(MEMORY_FILE, memory_data)
    print(f"🌌 Dreamed about: {skill['title']} (now in_progress)")

    # 🔁 Run inference engine after each dream
    inference_request()

if __name__ == "__main__":
    run_dream_cycle()