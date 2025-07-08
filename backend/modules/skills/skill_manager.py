import json
from datetime import datetime
from pathlib import Path

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

MEMORY_FILE = Path(__file__).resolve().parent / "aion_memory.json"

class SkillManager:
    def __init__(self):
        self.memory = self.load_memory()

    def load_memory(self):
        if MEMORY_FILE.exists():
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        return []

    def save_memory(self):
        with open(MEMORY_FILE, "w") as f:
            json.dump(self.memory, f, indent=2)

    def get_next_skill(self):
        for i, entry in enumerate(self.memory):
            if entry.get("status") == "queued":
                self.memory[i]["status"] = "in_progress"
                self.memory[i]["started_on"] = datetime.utcnow().isoformat()
                self.save_memory()
                return self.memory[i]
        return None

    def reflect_on_skill(self, title, success=True, notes=None):
        for i, entry in enumerate(self.memory):
            if entry.get("title") == title:
                self.memory[i]["status"] = "learned" if success else "failed"
                self.memory[i]["completed_on"] = datetime.utcnow().isoformat()
                self.memory[i]["notes"] = notes or ""
                self.save_memory()
                return self.memory[i]
        return None

    def get_skill_queue(self):
        return {
            "queued": [s for s in self.memory if s.get("status") == "queued"],
            "in_progress": [s for s in self.memory if s.get("status") == "in_progress"],
            "learned": [s for s in self.memory if s.get("status") == "learned"],
            "failed": [s for s in self.memory if s.get("status") == "failed"]
        }

    def update(self, updated_skill):
        """
        Updates a skill entry in memory by title.
        """
        for i, skill in enumerate(self.memory):
            if skill.get("title") == updated_skill.get("title"):
                self.memory[i] = updated_skill
                self.save_memory()
                return True
        return False