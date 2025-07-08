import json
from pathlib import Path
from datetime import datetime

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

MEMORY_FILE = Path(__file__).parent / "aion_memory.json"

class MemoryCore:
    def __init__(self):
        self.memories = []
        self.load()

    def load(self):
        if MEMORY_FILE.exists():
            self.memories = json.loads(MEMORY_FILE.read_text())

    def save(self):
        MEMORY_FILE.write_text(json.dumps(self.memories, indent=2))

    def store(self, label, content):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "label": label,
            "content": content
        }
        self.memories.append(entry)
        self.save()
        print(f"🧠 Memory stored: {label}")

    def recall(self, label):
        results = [m for m in self.memories if m["label"] == label]
        return results[-1]["content"] if results else None

    def list_labels(self):
        return sorted(set(m["label"] for m in self.memories))

if __name__ == "__main__":
    core = MemoryCore()
    print("🧠 Stored Memory Labels:")
    for label in core.list_labels():
        print(f" - {label}")
