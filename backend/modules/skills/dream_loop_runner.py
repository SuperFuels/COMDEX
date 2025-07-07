import subprocess
import json
import os
from datetime import datetime

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

DIR = os.path.dirname(__file__)
MEMORY_FILE = os.path.join(DIR, "aion_memory.json")
LOG_FILE = os.path.join(DIR, "aion_dreams.log")

def run_script(name):
    subprocess.run(["python", os.path.join(DIR, name)])

def promote_learned():
    if not os.path.exists(MEMORY_FILE):
        return

    with open(MEMORY_FILE, "r") as f:
        data = json.load(f)

    updated = False
    for entry in data:
        if entry.get("status") == "in_progress":
            entry["status"] = "learned"
            entry["last_learned"] = datetime.utcnow().isoformat()
            log(f"🎓 Promoted to learned: {entry['title']}")
            updated = True

    if updated:
        with open(MEMORY_FILE, "w") as f:
            json.dump(data, f, indent=2)

def log(message):
    with open(LOG_FILE, "a") as f:
        f.write(f"[{datetime.utcnow().isoformat()}] {message}\n")

def run_learning_cycle():
    log("🔁 Starting autonomous AION learning loop...")
    run_script("aion_dream_runner.py")
    promote_learned()
    run_script("curiosity_engine.py")
    log("✅ Cycle complete.\n")

if __name__ == "__main__":
    run_learning_cycle()
