# backend/modules/hexcore/memory_core.py

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH

DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

log = logging.getLogger(__name__)

# ✅ IGI Knowledge Graph integration
try:
    from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer  # type: ignore
except Exception:
    get_kg_writer = None  # type: ignore

# ✅ AION MemoryEngine (rich memory + glyphs + dedupe, etc.)
from backend.modules.hexcore.memory_engine import MEMORY  # global MemoryEngine instance

MEMORY_FILE = Path(__file__).parent / "aion_memory.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class MemoryCore:
    """
    Legacy AION memory shell.

    Acts as:
      - a simple JSON log for debugging (aion_memory.json)
      - a thin adapter into the unified MemoryEngine pipeline
      - an optional bridge into the IGI knowledge graph

    Design goals:
      - never crash HexCore on memory/KG write failure
      - preserve backward-compatible store/recall/list_labels API
      - fail open when optional dependencies are unavailable
    """

    def __init__(self, kg_writer: Optional[Any] = None):
        self.memories: list[dict[str, Any]] = []
        self.writer = self._resolve_writer(kg_writer)
        self.load()

    # ----------------- dependency resolution -----------------

    def _resolve_writer(self, kg_writer: Optional[Any]) -> Optional[Any]:
        """
        Resolve KG writer safely.

        Priority:
          1) explicit injected writer
          2) singleton helper if available
          3) None
        """
        if kg_writer is not None:
            return kg_writer

        if get_kg_writer is None:
            log.debug("[MemoryCore] get_kg_writer unavailable.")
            return None

        try:
            return get_kg_writer()
        except Exception as e:
            log.warning(f"[MemoryCore] KG writer unavailable: {e}")
            return None

    # ----------------- basic disk persistence -----------------

    def load(self) -> None:
        if not MEMORY_FILE.exists():
            self.memories = []
            return

        try:
            raw = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
            self.memories = raw if isinstance(raw, list) else []
        except Exception as e:
            log.warning(f"[MemoryCore] load failed: {e}")
            self.memories = []

    def save(self) -> None:
        try:
            MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            MEMORY_FILE.write_text(
                json.dumps(self.memories, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            # best-effort; don't crash HexCore over debug log
            log.warning(f"[MemoryCore] save failed: {e}")

    # ----------------- helpers -----------------

    def _append_local_entry(self, label: str, content: str, timestamp: str) -> dict[str, Any]:
        entry = {
            "timestamp": timestamp,
            "label": str(label),
            "content": str(content),
        }
        self.memories.append(entry)
        self.save()
        return entry

    def _write_to_kg(self, label: str, content: str, timestamp: str) -> None:
        if self.writer is None:
            return

        inject_glyph = getattr(self.writer, "inject_glyph", None)
        if not callable(inject_glyph):
            log.debug("[MemoryCore] KG writer has no inject_glyph method.")
            return

        try:
            inject_glyph(
                content=f"{label}: {content}",
                glyph_type="memory",
                metadata={"label": label, "timestamp": timestamp},
                region="memory_core",
                plugin="MemoryCore",
            )
        except Exception as e:
            # KG write should never crash AION
            log.debug(f"[MemoryCore] KG inject failed: {e}")

    def _forward_to_memory_engine(self, label: str, content: str, timestamp: str) -> None:
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
            log.warning(f"[MemoryCore] MemoryEngine forward failed: {e}")

    # ----------------- main API -----------------

    def store(self, label: str, content: str) -> None:
        """
        Store a memory entry.

        1) Append to local JSON file (legacy debug log)
        2) Inject into IGI KG as a glyph, if available
        3) Forward into MemoryEngine pipeline
        """
        timestamp = _utc_now_iso()

        self._append_local_entry(label=label, content=content, timestamp=timestamp)
        self._write_to_kg(label=label, content=content, timestamp=timestamp)
        self._forward_to_memory_engine(label=label, content=content, timestamp=timestamp)

        print(f"🧠 Memory stored: {label}")

    def recall(self, label: str) -> Optional[str]:
        label_s = str(label)
        results = [m for m in self.memories if str(m.get("label")) == label_s]
        if not results:
            return None
        return results[-1].get("content")

    def list_labels(self) -> list[str]:
        return sorted(
            {
                str(m.get("label"))
                for m in self.memories
                if m.get("label") is not None
            }
        )


if __name__ == "__main__":
    core = MemoryCore()
    print("🧠 Stored Memory Labels:")
    for label in core.list_labels():
        print(f" - {label}")