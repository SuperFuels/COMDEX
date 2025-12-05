# backend/modules/hexcore/memory_core.py

import json
from pathlib import Path
from datetime import datetime

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# ✅ IGI Knowledge Graph integration
try:
    from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer  # type: ignore
except Exception:
    get_kg_writer = None

# ✅ AION MemoryEngine (rich memory + glyphs + dedupe, etc.)
from backend.modules.hexcore.memory_engine import MEMORY  # global MemoryEngine instance

MEMORY_FILE = Path(__file__).parent / "aion_memory.json"


class MemoryCore:
    """
    Legacy AION memory shell.

    Now acts as:
      - a simple JSON log for debugging (aion_memory.json)
      - a thin adapter into the unified MemoryEngine pipeline
        via the global MEMORY instance.
    """

    def __init__(self):
        self.memories = []
        self.writer = kg_writer
        self.load()

    # ----------------- basic disk persistence -----------------

    def load(self):
        if MEMORY_FILE.exists():
            try:
                self.memories = json.loads(MEMORY_FILE.read_text())
            except Exception:
                self.memories = []

    def save(self):
        try:
            MEMORY_FILE.write_text(json.dumps(self.memories, indent=2))
        except Exception:
            # best-effort; don't crash HexCore over debug log
            pass

    # ----------------- main API -----------------

    def store(self, label: str, content: str):
        """
        Store a memory entry.

        1) Append to local JSON file (legacy debug log).
        2) Inject into IGI KG as a glyph.
        3) Forward into MemoryEngine pipeline (embeddings, glyph synth, indices).
        """
        timestamp = datetime.utcnow().isoformat()

        # 1) Local JSON log (legacy)
        entry = {
            "timestamp": timestamp,
            "label": label,
            "content": content,
        }
        self.memories.append(entry)
        self.save()

        # 2) Inject into IGI knowledge graph (legacy behavior)
        try:
            self.writer.inject_glyph(
                content=f"{label}: {content}",
                glyph_type="memory",
                metadata={"label": label, "timestamp": timestamp},
                region="memory_core",
                plugin="MemoryCore",
            )
        except Exception:
            # KG write should never crash AION
            pass

        # 3) Forward into unified MemoryEngine
        try:
            MEMORY.store(
                {
                    "label": label,
                    "content": content,
                    "timestamp": timestamp,
                    "source": "MemoryCore",
                }
            )
        except Exception as e:
            print(f"⚠️ MemoryCore → MemoryEngine forward failed: {e}")

        print(f"🧠 Memory stored: {label}")

    def recall(self, label: str):
        results = [m for m in self.memories if m.get("label") == label]
        return results[-1]["content"] if results else None

    def list_labels(self):
        return sorted({m.get("label") for m in self.memories if "label" in m})


if __name__ == "__main__":
    core = MemoryCore()
    print("🧠 Stored Memory Labels:")
    for label in core.list_labels():
        print(f" - {label}")