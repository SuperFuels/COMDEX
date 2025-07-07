import json
from pathlib import Path
from datetime import datetime
from sentence_transformers import SentenceTransformer, util
import torch  # added import for PyTorch

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

MEMORY_FILE = Path(__file__).parent / "aion_memory.json"
EMBEDDING_FILE = Path(__file__).parent / "aion_embeddings.json"

MILESTONE_KEYWORDS = {
    "first_dream": ["dream_reflection"],
    "cognitive_reflection": ["self-awareness", "introspection", "echoes of existence"],
    "voice_activation": ["speak", "vocal", "communication interface"],
    "wallet_integration": ["wallet", "crypto storage", "store of value"],
    "nova_connection": ["frontend", "interface", "nova"]
}

class MemoryEngine:
    def __init__(self):
        self.memory = []
        self.embeddings = []
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.agents = []

        self.load_memory()
        self.load_embeddings()

    def detect_tags(self, content):
        tags = []
        content_lower = content.lower()
        if len(content_lower) < 30:
            return tags
        for tag, keywords in MILESTONE_KEYWORDS.items():
            if any(keyword.lower() in content_lower for keyword in keywords):
                tags.append(tag)
        return tags

    def is_duplicate(self, new_embedding):
        if not self.embeddings:
            return False
        # Stack embeddings into a single tensor if stored as list
        embeddings_tensor = torch.stack(self.embeddings) if isinstance(self.embeddings, list) else self.embeddings
        similarities = util.cos_sim(new_embedding, embeddings_tensor)[0]
        max_sim = float(similarities.max())
        return max_sim > 0.95  # Threshold

    def list_labels(self):
        return sorted(set(m.get("label") for m in self.memory if "label" in m))

    def get(self, label):
        return [m for m in self.memory if m.get("label") == label]

    def get_all(self):
        return self.memory

    def load_memory(self):
        if MEMORY_FILE.exists():
            try:
                with open(MEMORY_FILE, "r") as f:
                    self.memory = json.load(f)
            except Exception:
                self.memory = []
        else:
            self.memory = []

    def load_embeddings(self):
        if EMBEDDING_FILE.exists():
            try:
                with open(EMBEDDING_FILE, "r") as f:
                    loaded = json.load(f)
                    # convert loaded list of lists to list of float32 tensors
                    self.embeddings = [torch.tensor(e, dtype=torch.float32) for e in loaded]
            except Exception:
                self.embeddings = []
        else:
            self.embeddings = []

    def save_memory(self):
        try:
            with open(MEMORY_FILE, "w") as f:
                json.dump(self.memory, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save memory file: {e}")

    def save_embeddings(self):
        try:
            # Convert tensors back to list for JSON serialization
            with open(EMBEDDING_FILE, "w") as f:
                json.dump([e.tolist() for e in self.embeddings], f)
        except Exception as e:
            print(f"⚠️ Failed to save embeddings file: {e}")

    def register_agent(self, agent):
        if agent not in self.agents:
            self.agents.append(agent)
            print(f"✅ Agent registered: {agent.name}")

    def send_message_to_agents(self, message):
        for agent in self.agents:
            agent.receive_message(message)

    def save(self, label: str, content: str):
        self.store({"label": label, "content": content})

    def store(self, memory_obj):
        if not isinstance(memory_obj, dict):
            raise ValueError("Memory object must be a dict.")
        if "label" not in memory_obj or "content" not in memory_obj:
            raise ValueError("Memory must contain 'label' and 'content' keys.")

        content = memory_obj["content"]
        # Encode with convert_to_tensor=True to get a PyTorch tensor directly
        embedding = self.model.encode(content, convert_to_tensor=True)
        embedding = embedding.to(torch.float32)  # ensure float32 dtype

        if self.is_duplicate(embedding):
            print(f"⚠️ Duplicate memory ignored: {memory_obj['label']}")
            return

        memory_obj["timestamp"] = datetime.now().isoformat()
        tags = self.detect_tags(content)
        if tags:
            memory_obj["milestone_tags"] = tags

        self.memory.append(memory_obj)
        self.embeddings.append(embedding)
        self.save_memory()
        self.save_embeddings()

        print(f"✅ Memory stored: {memory_obj['label']}")
        self.send_message_to_agents({
            "type": "new_memory",
            "memory": memory_obj
        })