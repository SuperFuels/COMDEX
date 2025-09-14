import os
import json
from pathlib import Path
from datetime import datetime
from sentence_transformers import SentenceTransformer, util
import torch
import requests

from backend.modules.dna_chain.switchboard import DNA_SWITCH
from backend.config import GLYPH_API_BASE_URL
from backend.modules.codex.codex_scroll_builder import build_scroll_from_glyph
# 🔥 Lazy import fix: Removed top-level KnowledgeGraphWriter import to avoid circular dependency
from backend.modules.dna_chain.container_index_writer import add_to_index  # ✅ R1f, ⏱️ H1

DNA_SWITCH.register(__file__)

MEMORY_DIR = "data/memory_logs"
ENABLE_GLYPH_LOGGING = True  # ✅ R1g

# --- Sanitizers (Stage D) -----------------------------------------------------
# 1) Generic sanitizer for the boot_loader's list-of-dicts file that must have "title"
def sanitize_memory_file_at(path) -> None:
    """
    Ensure file at `path` is a JSON list of dicts containing 'title' (str).
    If malformed, it will rewrite to a safe list.
    """
    try:
        if not os.path.exists(path):
            # nothing to sanitize; create an empty list to be safe
            with open(path, "w") as f:
                json.dump([], f)
            print(f"🧽 sanitize_memory_file_at: created empty list at {path}")
            return

        with open(path, "r") as f:
            raw = json.load(f)

        if not isinstance(raw, list):
            print(f"⚠️ sanitize_memory_file_at: not a list at {path}; writing empty list.")
            with open(path, "w") as f:
                json.dump([], f)
            return

        cleaned = [r for r in raw if isinstance(r, dict) and isinstance(r.get("title"), str)]
        dropped = len(raw) - len(cleaned)
        if dropped:
            print(f"🧽 sanitize_memory_file_at: dropped {dropped} malformed rows at {path}.")
        with open(path, "w") as f:
            json.dump(cleaned, f, indent=2)

    except Exception as e:
        print(f"🚨 sanitize_memory_file_at failed for {path}: {e}")

# 2) Local sanitizer for this engine’s per-container memory file (expects 'label')
def sanitize_engine_memory_file(path) -> None:
    """
    Ensure MemoryEngine’s own on-disk file is a JSON list of dicts with 'label' and 'content'.
    """
    try:
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump([], f)
            print(f"🧽 sanitize_engine_memory_file: created empty list at {path}")
            return

        with open(path, "r") as f:
            raw = json.load(f)

        if not isinstance(raw, list):
            print(f"⚠️ sanitize_engine_memory_file: not a list at {path}; writing empty list.")
            with open(path, "w") as f:
                json.dump([], f)
            return

        def ok(d):
            return isinstance(d, dict) and isinstance(d.get("label"), str) and isinstance(d.get("content"), str)

        cleaned = [r for r in raw if ok(r)]
        dropped = len(raw) - len(cleaned)
        if dropped:
            print(f"🧽 sanitize_engine_memory_file: dropped {dropped} malformed rows at {path}.")
        with open(path, "w") as f:
            json.dump(cleaned, f, indent=2)

    except Exception as e:
        print(f"🚨 sanitize_engine_memory_file failed for {path}: {e}")

MILESTONE_KEYWORDS = {
    "first_dream": ["dream_reflection"],
    "cognitive_reflection": ["self-awareness", "introspection", "echoes of existence"],
    "voice_activation": ["speak", "vocal", "communication interface"],
    "wallet_integration": ["wallet", "crypto storage", "store of value"],
    "nova_connection": ["frontend", "interface", "nova"]
}

class MemoryEngine:
    def __init__(self, container_id: str = "global"):
        self.container_id = container_id
        self.memory = []
        self.embeddings = []
        self.model = SentenceTransformer("./models/all-MiniLM-L6-v2", local_files_only=True)
        self.agents = []
        self.duplicate_threshold = 0.95

        self.memory_file = Path(__file__).parent / f"memory_{self.container_id}.json"
        self.embedding_file = Path(__file__).parent / f"embeddings_{self.container_id}.json"

        # ✅ Removed KnowledgeGraphWriter from __init__ to break circular imports
        self.kg_writer = None  

        self.load_memory()
        self.load_embeddings()

    def _get_kg_writer(self):
        """Lazy + safe import to avoid errors during tests."""
        if self.kg_writer is None:
            try:
                from backend.modules.knowledge_graph.kg_writer_singleton import kg_writer
                self.kg_writer = kg_writer
            except Exception:
                self.kg_writer = None
        return self.kg_writer

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
        """
        Robust duplicate check:
        - Handles empty store
        - Normalizes shapes to (1, D) vs (N, D)
        - Early-returns on dim mismatch instead of crashing
        """
        # No baseline embeddings? nothing to compare
        if not self.embeddings:
            return False

        # --- normalize new_embedding -> torch.FloatTensor (1, D)
        try:
            if isinstance(new_embedding, torch.Tensor):
                ne = new_embedding.detach().to(torch.float32)
            else:
                ne = torch.tensor(new_embedding, dtype=torch.float32)
            if ne.ndim == 1:
                ne = ne.unsqueeze(0)
            if ne.numel() == 0:
                return False
        except Exception:
            return False

        # --- normalize existing embeddings -> torch.FloatTensor (N, D)
        try:
            if isinstance(self.embeddings, list):
                emb_list = []
                for e in self.embeddings:
                    if isinstance(e, torch.Tensor):
                        emb_list.append(e.detach().to(torch.float32))
                    else:
                        emb_list.append(torch.tensor(e, dtype=torch.float32))
                if not emb_list:
                    return False
                E = torch.stack(emb_list, dim=0)
            else:
                E = self.embeddings
                if isinstance(E, torch.Tensor):
                    E = E.detach().to(torch.float32)
                else:
                    E = torch.tensor(E, dtype=torch.float32)
            if E.ndim == 1:
                E = E.unsqueeze(0)
            if E.numel() == 0:
                return False
        except Exception:
            return False

        # --- dimension mismatch? do not attempt similarity
        if ne.shape[-1] != E.shape[-1]:
            return False

        try:
            sims = util.cos_sim(ne, E)[0]  # (N,)
            max_sim = float(sims.max()) if sims.numel() else 0.0
            threshold = getattr(self, "duplicate_threshold", 0.95)
            return max_sim >= threshold
        except Exception:
            return False

    @staticmethod
    def get_runtime_entropy_snapshot():
        return f"MemoryCount:{len(MEMORY.memory)};Timestamp:{datetime.utcnow().isoformat()}"

    def list_labels(self):
        return sorted(set(m.get("label") for m in self.memory if "label" in m))

    def get(self, label):
        return [m for m in self.memory if m.get("label") == label]

    def get_all(self):
        return self.memory

    def load_memory(self):
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r") as f:
                    self.memory = json.load(f)
            except Exception:
                self.memory = []
        else:
            self.memory = []

    def load_embeddings(self):
        if self.embedding_file.exists():
            try:
                with open(self.embedding_file, "r") as f:
                    loaded = json.load(f)
                    self.embeddings = [torch.tensor(e, dtype=torch.float32) for e in loaded]
            except Exception:
                self.embeddings = []
        else:
            self.embeddings = []

    def save_memory(self):
        try:
            with open(self.memory_file, "w") as f:
                json.dump(self.memory, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save memory file: {e}")

    def save_embeddings(self):
        try:
            with open(self.embedding_file, "w") as f:
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
        label = memory_obj["label"]

        # 🔒 Ensure content is a string for the embedder
        if not isinstance(content, str):
            try:
                content = json.dumps(content, ensure_ascii=False)
            except Exception:
                content = str(content)
        memory_obj["content"] = content

        # Encode to a dense vector (D,)
        embedding = self.model.encode(content, convert_to_tensor=True)
        if not isinstance(embedding, torch.Tensor):
            embedding = torch.tensor(embedding, dtype=torch.float32)
        else:
            embedding = embedding.to(torch.float32)

        if self.is_duplicate(embedding):
            print(f"⚠️ Duplicate memory ignored: {label}")
            return

        memory_obj["timestamp"] = datetime.now().isoformat()
        tags = self.detect_tags(content)
        if tags:
            memory_obj["milestone_tags"] = tags

        # ✅ Attach scrolls if glyph available (and is structured)
        glyph_payload = memory_obj.get("glyph") or memory_obj.get("glyph_tree")
        if isinstance(glyph_payload, (dict, list)):
            try:
                scroll_data = build_scroll_from_glyph(glyph_payload)
                memory_obj["scroll_preview"] = scroll_data.get("codexlang")
                memory_obj["scroll_tree"] = scroll_data.get("tree")
                print("🌀 Attached scroll to memory entry.")
            except Exception as e:
                print(f"⚠️ Failed to build scroll from glyph: {e}")

        self.memory.append(memory_obj)
        self.embeddings.append(embedding)
        self.save_memory()
        self.save_embeddings()

        print(f"✅ Memory stored: {label}")
        self.send_message_to_agents({
            "type": "new_memory",
            "memory": memory_obj
        })

        # 🧬 Trigger synthesis
        try:
            print("🧬 Synthesizing glyphs from memory...")
            synth_response = requests.post(
                f"{GLYPH_API_BASE_URL}/api/aion/synthesize-glyphs",
                json={"text": content, "source": "memory"}
            )
            if synth_response.status_code == 200:
                result = synth_response.json()
                print(f"✅ Synthesized {len(result.get('glyphs', []))} glyphs from memory.")
            else:
                print(f"⚠️ Glyph synthesis failed: {synth_response.status_code} {synth_response.text}")
        except Exception as e:
            print(f"🚨 Glyph synthesis error (memory): {e}")

        # ✅ ⏱️ H1: Inject glyph trace into container
        if ENABLE_GLYPH_LOGGING:
            try:
                writer = self._get_kg_writer()
                if writer:
                    writer.inject_glyph(
                        content=content,
                        glyph_type="memory",
                        metadata={
                            "label": label,
                            "timestamp": memory_obj["timestamp"],
                            "tags": tags,
                            "container": self.container_id
                        },
                        plugin="MemoryEngine"
                    )
                    print(f"🧠 Glyph injected into container for {label}")
                    add_to_index("memory_index.glyph", {
                        "text": content,
                        "timestamp": memory_obj["timestamp"],
                        "hash": hash(content)
                    })
            except Exception as e:
                print(f"⚠️ Glyph injection failed: {e}")

# 🔧 Logging utilities

def _ensure_dir():
    os.makedirs(MEMORY_DIR, exist_ok=True)

def store_memory_entry(kind: str, data: dict):
    _ensure_dir()
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    path = os.path.join(MEMORY_DIR, f"{kind}_{date_str}.log.jsonl")

    full_entry = {
        "kind": kind,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data
    }

    with open(path, "a") as f:
        f.write(json.dumps(full_entry) + "\n")

    print(f"[🧠] Stored memory entry: {kind} | {data.get('context', '')}")

def store_memory_packet(packet: dict):
    label = packet.get("label", "memory:unlabeled")
    content = packet.get("content", "")
    MEMORY.store({
        "label": label,
        "content": content
    })

def store_container_metadata(container: dict):
    container_id = container.get("id", "unknown")
    label = f"container:{container_id}"

    exits = container.get("exits", {})
    connections = ", ".join([f"{k} → {v}" for k, v in exits.items()]) if exits else "None"

    dna = container.get("dna_switch", {})
    dna_id = dna.get("id", "none")
    dna_state = dna.get("state", "undefined")

    summary = {
        "Container ID": container_id,
        "Name": container.get("name", ""),
        "Description": container.get("description", ""),
        "Origin": container.get("origin", ""),
        "Created On": container.get("created_on", ""),
        "Container Type": container.get("type", "generic"),
        "Total Cubes": len(container.get("cubes", [])),
        "Mutations": len(container.get("mutations", [])),
        "Connections": connections,
        "DNA Switch": f"{dna_id} ({dna_state})"
    }

    readable = "\n".join([f"{k}: {v}" for k, v in summary.items()])
    MEMORY.store({
        "label": label,
        "content": f"[📦] Container metadata\n{readable}"
    })

# 🧠 Global memory instance
MEMORY = MemoryEngine()
store_memory = MEMORY.store

class MemoryBridge:
    @staticmethod
    def store_entry(entry: dict):
        MEMORY.store(entry)

    @staticmethod
    def log_codex_execution(glyph: str, result: str, context: dict):
        MEMORY.store({
            "label": "codex_execution",
            "type": "execution",
            "glyph": glyph,
            "result": result,
            "context": context
        })

def get_recent_memory_glyphs(limit: int = 10) -> list[str]:
        """
        Returns the most recent glyphs stored in memory for GHX encoding.
        Pulls from MEMORY.store() log or in-memory buffer.

        Args:
            limit (int): Maximum number of recent glyphs to retrieve.

        Returns:
            list[str]: List of glyph strings.
        """
        try:
            # If MEMORY supports a 'recent' API
            if hasattr(MEMORY, "get_recent"):
                return [entry.get("glyph") for entry in MEMORY.get_recent(limit=limit) if entry.get("glyph")]

            # Fallback: manually scan MEMORY log (if stored in-memory)
            if hasattr(MEMORY, "log"):
                recent = list(MEMORY.log)[-limit:]
                return [entry.get("glyph") for entry in recent if entry.get("glyph")]

        except Exception as e:
            print(f"⚠️ Failed to retrieve recent memory glyphs: {e}")

        return []

def log_memory(container_id: str, data: dict):
    mem = MemoryEngine(container_id)
    mem.store(data)

def get_runtime_entropy_snapshot():
    return MemoryEngine.get_runtime_entropy_snapshot()