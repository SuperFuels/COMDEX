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

# top of file
ENABLE_GLYPH_SYNTH = os.getenv("ENABLE_GLYPH_SYNTH", "0") == "1"
GLYPH_API_BASE_URL = os.getenv("GLYPH_API_BASE_URL", "http://localhost:8000")

# inside _store_impl, replace the synth block with:
if ENABLE_GLYPH_SYNTH:
    try:
        synth_response = requests.post(
            f"{GLYPH_API_BASE_URL}/api/aion/synthesize-glyphs",
            json={"text": content, "source": "memory"},
            timeout=2.5,
        )
        if synth_response.ok:
            result = synth_response.json()
            print(f"✅ Synthesized {len(result.get('glyphs', []))} glyphs from memory.")
        else:
            print(f"⚠️ Glyph synthesis failed: {synth_response.status_code}")
    except Exception:
        # stay quiet if the synth service is down
        pass

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

def _normalize_legacy_memory_args(memory_obj=None, **kwargs):
    """
    Accepts legacy calls like MemoryEngine.store({...}) or MemoryEngine.store(label="x", content={...})
    and normalizes to {"label": ..., "content": ...}.
    """
    if memory_obj is None:
        memory_obj = {}
    if isinstance(memory_obj, dict):
        memory_obj = {**memory_obj, **kwargs}
    else:
        memory_obj = {"content": {"value": memory_obj}, **kwargs}

    if "label" not in memory_obj:
        memory_obj["label"] = memory_obj.get("type", "log")

    if "content" not in memory_obj:
        # fallback: use the rest as content
        memory_obj["content"] = {k: v for k, v in memory_obj.items() if k != "label"}

    return memory_obj

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

        # --- dedupe controls ---------------------------------------------------
        import hashlib  # local import is fine in this section
        self._hashlib = hashlib
        self.dedupe_mode = os.getenv("MEMORY_DEDUPE_MODE", "exact")  # "exact" or "semantic"
        self.hashes_file = Path(__file__).parent / f"memhashes_{self.container_id}.json"
        self._hashes = set()
        try:
            if self.hashes_file.exists():
                self._hashes = set(json.load(open(self.hashes_file)))
        except Exception:
            self._hashes = set()

        # Labels that should NEVER be dropped by semantic dedupe (high-frequency tick logs)
        self.ticky_labels = {
            "glyph_tick",
            "codex_runtime_result",
            "runtime_tick_summary",
        }

        # ✅ Removed KnowledgeGraphWriter from __init__ to break circular imports
        self.kg_writer = None

        self.load_memory()
        # --- optional filtering controls ---
        # hard-drop certain labels completely
        self.drop_labels = {"glyph_tick"}  # add others like "codex_runtime_result", "runtime_tick_summary"

        # sample certain labels (store only 1 of every N)
        from collections import defaultdict
        self._label_counts = defaultdict(int)
        self.sample_labels = {
            "glyph_tick": 10,            # keep 1 of every 10 ticks
            # "codex_runtime_result": 5, # example: keep 1 of every 5
        }
        self.load_embeddings()
        self.drop_labels.update({"codex_runtime_result"})
        self.sample_labels.update({
            "codex_trace:executed": 5,
            "runtime_tick_summary": 3,
        })

    # --- helpers ---------------------------------------------------------------
    def _get_kg_writer(self):
        """Lazy + safe import to avoid errors during tests."""
        if self.kg_writer is None:
            try:
                from backend.modules.knowledge_graph.kg_writer_singleton import kg_writer
                self.kg_writer = kg_writer
            except Exception:
                self.kg_writer = None
        return self.kg_writer

    def _content_hash(self, text: str) -> str:
        return self._hashlib.sha256(text.encode("utf-8")).hexdigest()

    # --- compatibility / convenience ------------------------------------------
    def get_recent(self, limit: int = 50):
        """
        Returns most recent memory entries sorted by timestamp descending.
        """
        try:
            if not hasattr(self, "memory"):
                return []
            valid = [
                m for m in self.memory
                if isinstance(m, dict) and "timestamp" in m
            ]
            sorted_mem = sorted(valid, key=lambda x: x["timestamp"], reverse=True)
            return sorted_mem[:limit]
        except Exception as e:
            print(f"⚠️ get_recent() failed: {e}")
            return []

    def _save_hashes(self):
        try:
            with open(self.hashes_file, "w") as f:
                json.dump(list(self._hashes), f)
        except Exception as e:
            print(f"⚠️ Failed to save hashes: {e}")

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
        Robust duplicate check (semantic):
        - Handles empty store
        - Normalizes shapes to (1, D) vs (N, D)
        - Early-returns on dim mismatch instead of crashing
        """
        if not self.embeddings:
            return False

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

    # --- public API (back-compat) ---------------------------------------------
    def save(self, label: str, content: str):
        self._store_impl({"label": label, "content": content})

    def store(self, memory_obj):
        self._store_impl(memory_obj)

    # --- core storage ----------------------------------------------------------
    def _store_impl(self, memory_obj):
        if not isinstance(memory_obj, dict):
            raise ValueError("Memory object must be a dict.")
        if "label" not in memory_obj or "content" not in memory_obj:
            raise ValueError("Memory must contain 'label' and 'content' keys.")

        content = memory_obj["content"]
        label = memory_obj["label"]
        # --- early exits for noisy labels ---
        # A) hard drop list
        if label in self.drop_labels:
            return

        # B) sampling per label (store 1 of every N)
        if label in self.sample_labels:
            self._label_counts[label] += 1
            if self._label_counts[label] % self.sample_labels[label] != 0:
                return

        # 🔒 Ensure content is a string for the embedder
        if not isinstance(content, str):
            try:
                content = json.dumps(content, ensure_ascii=False)
            except Exception:
                content = str(content)
        memory_obj["content"] = content

        # --- dedupe policy selection ------------------------------------------
        allow_duplicate = bool(memory_obj.pop("_allow_duplicate", False))
        is_ticky = (
            label in self.ticky_labels
            or label.startswith("container:")
            or label.startswith("codex_trace:")
        )

        # Exact-dedupe first (fast / content-identical)
        #   - always on for ticky labels
        #   - on when dedupe_mode == "exact"
        if (self.dedupe_mode == "exact" or is_ticky) and not allow_duplicate:
            ch = self._content_hash(content)
            if ch in self._hashes:
                print(f"⚠️ Duplicate memory ignored: {label}")
                return
            self._hashes.add(ch)
            self._save_hashes()

        # Should we perform semantic dedupe?
        do_semantic_check = (self.dedupe_mode == "semantic") and not is_ticky and not allow_duplicate

        # Encode to a dense vector (D,)
        embedding = self.model.encode(content, convert_to_tensor=True)
        if not isinstance(embedding, torch.Tensor):
            embedding = torch.tensor(embedding, dtype=torch.float32)
        else:
            embedding = embedding.to(torch.float32)

        if do_semantic_check and self.is_duplicate(embedding):
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

        # Persist in-memory and on-disk
        self.memory.append(memory_obj)
        self.embeddings.append(embedding)
        self.save_memory()
        self.save_embeddings()

        print(f"✅ Memory stored: {label}")
        self.send_message_to_agents({"type": "new_memory", "memory": memory_obj})

        # 🧬 Trigger synthesis → glyph service (best-effort)
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

        # ✅ Inject glyph trace + index (best-effort)
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

# --- Compatibility wrapper so both instance and class calls work:
# - MEMORY.store({...})  (instance style) ✔
# - MemoryEngine.store({...}) (legacy class style) ✔

def _store_compat(*args, **kwargs):
    """
    Dispatch:
      - If called as instance method (first arg is MemoryEngine), forward to _store_impl(self, memory_obj)
      - If called as class/static (no self), forward to global MEMORY._store_impl(...)
    """
    # Instance-style: MEMORY.store({...})
    if args and isinstance(args[0], MemoryEngine):
        self = args[0]
        # support MEMORY.store(label="x", content="y") or MEMORY.store({...})
        memory_obj = args[1] if len(args) > 1 else kwargs if kwargs else None
        if memory_obj is None:
            raise ValueError("Memory object must be provided.")
        # If kwargs were used, normalize into a dict
        if not isinstance(memory_obj, dict):
            memory_obj = {"content": memory_obj}
        if "label" not in memory_obj and "type" in memory_obj:
            memory_obj["label"] = memory_obj["type"]
        if "label" not in memory_obj:
            memory_obj["label"] = "log"
        if "content" not in memory_obj:
            memory_obj["content"] = {k: v for k, v in memory_obj.items() if k != "label"}
        return self._store_impl(memory_obj)

    # Class-style: MemoryEngine.store({...})
    memory_obj = args[0] if args else kwargs if kwargs else None
    if memory_obj is None:
        raise ValueError("Memory object must be provided.")
    normalized = _normalize_legacy_memory_args(memory_obj)
    # NOTE: we will bind MEMORY below after it's created.
    return _GLOBAL_MEMORY._store_impl(normalized)

# 🧠 Global memory instance (with compat binding)
_GLOBAL_MEMORY = MemoryEngine()
MEMORY = _GLOBAL_MEMORY  # keep existing name for backwards-compat

# Bind the compatibility wrapper AFTER the class is defined and the instance exists.
# This makes BOTH of these work:
#   - MEMORY.store({...})          (instance-style)
#   - MemoryEngine.store({...})    (legacy class-style)
MemoryEngine.store = _store_compat

# Convenience alias preserved
store_memory = MEMORY.store


class MemoryBridge:
    @staticmethod
    def store_entry(entry: dict):
        # Accepts either full dict or kwargs via the compat wrapper
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
    Pulls from MEMORY.get_recent() when available, otherwise scans the in-memory store.
    """
    try:
        # If MEMORY exposes a 'get_recent' API
        if hasattr(MEMORY, "get_recent") and callable(getattr(MEMORY, "get_recent")):
            return [
                entry.get("glyph")
                for entry in MEMORY.get_recent(limit=limit)
                if isinstance(entry, dict) and entry.get("glyph")
            ]

        # Fallback: scan the in-memory list (newest last)
        recent = MEMORY.get_all()[-limit:]
        return [
            entry.get("glyph")
            for entry in recent
            if isinstance(entry, dict) and entry.get("glyph")
        ]
    except Exception as e:
        print(f"⚠️ Failed to retrieve recent memory glyphs: {e}")
        return []


def log_memory(container_id: str, data: dict):
    # Per-container memory write, using instance API (still routed via compat)
    mem = MemoryEngine(container_id)
    mem.store(data)


def get_runtime_entropy_snapshot():
    return MemoryEngine.get_runtime_entropy_snapshot()

def store_memory_entry(kind: str, data: dict):
    _ensure_dir()
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    path = os.path.join(MEMORY_DIR, f"{kind}_{date_str}.log.jsonl")
    full_entry = {"kind": kind, "timestamp": datetime.utcnow().isoformat(), "data": data}
    with open(path, "a") as f:
        f.write(json.dumps(full_entry) + "\n")
    print(f"[🧠] Stored memory entry: {kind} | {data.get('context', '')}")

def store_memory_packet(packet: dict):
    label = packet.get("label", "memory:unlabeled")
    content = packet.get("content", "")
    MEMORY.store({"label": label, "content": content})

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
    MEMORY.store({"label": label, "content": f"[📦] Container metadata\n{readable}"})

# =========================================================
# 🔁 Compatibility Helper: retrieve_recent_memories
# =========================================================
def retrieve_recent_memories(limit: int = 20):
    """
    Returns the N most recent memory entries from the global MEMORY instance.
    Backwards-compatible API for CodexMemoryTrigger.
    """
    try:
        if hasattr(MEMORY, "get_all"):
            return MEMORY.get_all()[-limit:]
        else:
            return []
    except Exception as e:
        print(f"⚠️ retrieve_recent_memories() failed: {e}")
        return []