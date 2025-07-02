import json
from datetime import datetime
from pathlib import Path

MEMORY_FILE = Path(__file__).resolve().parent / "aion_memory.json"

def load_memory():
    if MEMORY_FILE.exists():
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_memory(data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_next_skill():
    memory = load_memory()
    for i, entry in enumerate(memory):
        if entry.get("status") == "queued":
            memory[i]["status"] = "in_progress"
            memory[i]["started_on"] = datetime.utcnow().isoformat()
            save_memory(memory)
            return memory[i]
    return None

def reflect_on_skill(title, success=True, notes=None):
    memory = load_memory()
    for i, entry in enumerate(memory):
        if entry.get("title") == title:
            memory[i]["status"] = "learned" if success else "failed"
            memory[i]["completed_on"] = datetime.utcnow().isoformat()
            memory[i]["notes"] = notes or ""
            save_memory(memory)
            return memory[i]
    return None

def get_skill_queue():
    memory = load_memory()
    return {
        "queued": [s for s in memory if s.get("status") == "queued"],
        "in_progress": [s for s in memory if s.get("status") == "in_progress"],
        "learned": [s for s in memory if s.get("status") == "learned"],
        "failed": [s for s in memory if s.get("status") == "failed"]
    }