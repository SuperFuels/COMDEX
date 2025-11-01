# 📁 backend/modules/photon_memory/photon_memory_grid.py
import json, threading, time
from pathlib import Path
from typing import Dict, List, Optional

from backend.modules.photon_memory.photon_memory_entry import PhotonMemoryEntry

class PhotonMemoryGrid:
    """
    Central photon state archive - stores coherence and resonance traces.
    Supports in-memory caching + JSON persistence.
    """

    def __init__(self, storage_path: str = "backend/modules/photon_memory/photon_memory_store.json"):
        self.storage_path = Path(storage_path)
        self._lock = threading.Lock()
        self.entries: Dict[str, PhotonMemoryEntry] = {}
        self._load_from_disk()

    # ─────────────────────────────────────────────────────
    def _load_from_disk(self):
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                for d in data:
                    e = PhotonMemoryEntry(**d)
                    self.entries[e.uid] = e
            except Exception:
                print("[PMG] Warning: failed to load existing photon memory store.")
        else:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.storage_path.write_text("[]", encoding="utf-8")

    # ─────────────────────────────────────────────────────
    def _save_to_disk(self):
        with self._lock:
            data = [e.to_dict() for e in self.entries.values()]
            self.storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # ─────────────────────────────────────────────────────
    def record(self, entry: PhotonMemoryEntry):
        """Add new photon memory entry to grid."""
        with self._lock:
            self.entries[entry.uid] = entry
        self._save_to_disk()
        print(f"[PMG] Recorded wave {entry.wave_id} -> coh={entry.coherence:.3f} ent={entry.entropy:.3f}")

    # ─────────────────────────────────────────────────────
    def query(self, *, operator: Optional[str] = None, min_coh: float = 0.0) -> List[PhotonMemoryEntry]:
        """Query entries by operator and/or coherence threshold."""
        return [
            e for e in self.entries.values()
            if (operator is None or e.operator == operator) and e.coherence >= min_coh
        ]

    # ─────────────────────────────────────────────────────
    def latest(self, limit: int = 10) -> List[PhotonMemoryEntry]:
        return sorted(self.entries.values(), key=lambda e: e.timestamp, reverse=True)[:limit]

    # ─────────────────────────────────────────────────────
    def summarize(self) -> Dict[str, float]:
        """Return average coherence, entropy, and amplitude."""
        if not self.entries:
            return {"avg_coherence": 0, "avg_entropy": 0, "avg_amplitude": 0}
        n = len(self.entries)
        return {
            "avg_coherence": sum(e.coherence for e in self.entries.values()) / n,
            "avg_entropy": sum(e.entropy for e in self.entries.values()) / n,
            "avg_amplitude": sum(e.amplitude for e in self.entries.values()) / n,
        }

# Global singleton instance
PHOTON_MEMORY_GRID = PhotonMemoryGrid()