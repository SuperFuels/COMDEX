import json
from pathlib import Path

MEMORY_FILE = Path(__file__).parent / "aion_memory.json"

# Milestone keyword patterns to flag during memory storage
MILESTONE_KEYWORDS = {
    "first_dream": ["dream_reflection"],
    "cognitive_reflection": ["self-awareness", "introspection", "echoes of existence"],
    "voice_activation": ["speak", "vocal", "communication interface"],
    "wallet_integration": ["wallet", "crypto storage", "store of value"],
    "nova_connection": ["frontend", "interface", "nova"]
}

class MemoryEngine:
    def __init__(self):
        """Initialize memory engine and load existing memory from file."""
        self.memory = []
        self.load_memory()

    def load_memory(self):
        """Load memory from the JSON file, handle corruption or wrong types gracefully."""
        if MEMORY_FILE.exists():
            try:
                with open(MEMORY_FILE, "r") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.memory = data
                    else:
                        print("⚠️ Memory file was not a list. Resetting.")
                        self.memory = []
            except json.JSONDecodeError:
                print("⚠️ Failed to decode memory file. Starting fresh.")
                self.memory = []

    def save_memory(self):
        """Save current memory state to JSON file."""
        with open(MEMORY_FILE, "w") as f:
            json.dump(self.memory, f, indent=2)

    def detect_tags(self, content):
        """Check content for milestone keywords and return list of tags."""
        tags = []
        for tag, keywords in MILESTONE_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in content.lower():
                    tags.append(tag)
                    break  # Avoid duplicate tags for the same trigger
        return tags

    def store(self, memory_obj):
        """
        Store a memory object with required 'label' and 'content'.
        Auto-tag milestone-related content.
        """
        if isinstance(memory_obj, dict) and "label" in memory_obj and "content" in memory_obj:
            content = memory_obj["content"]
            tags = self.detect_tags(content)
            if tags:
                memory_obj["milestone_tags"] = tags
            self.memory.append(memory_obj)
            self.save_memory()
        else:
            raise ValueError("Memory object must include 'label' and 'content' keys.")

    def get_all(self):
        """Return all stored memories."""
        return self.memory

    def get(self, label):
        """Return all memories with the specified label."""
        return [m for m in self.memory if m.get("label") == label]