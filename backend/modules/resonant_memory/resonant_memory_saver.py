# ============================================================
# 💾 Resonant Memory Saver
# ============================================================
# Provides a unified interface to persist symbolic scrolls, waveforms,
# or photon resonance states into the Resonant Memory system.
#
# Used by: SCI ScrollEngine, Photon Runtime, and Reflection Core.
# ============================================================

from __future__ import annotations
import os
import json
import time
from datetime import datetime
from typing import Dict, Any

# ------------------------------------------------------------
# Optional AION + Photon Memory Integration
# ------------------------------------------------------------
try:
    from backend.modules.photon_memory.photon_memory_entry import store_photon_memory_entry
except Exception:
    def store_photon_memory_entry(label: str, content: str, metadata: Dict[str, Any]):
        print(f"[StubPhotonMemoryEntry] Stored symbolic memory entry '{label}' (stubbed)")
        return True

# ------------------------------------------------------------
# Config
# ------------------------------------------------------------
MEMORY_DIR = "artifacts/memory"
os.makedirs(MEMORY_DIR, exist_ok=True)

# ------------------------------------------------------------
# 🧬 Save Scroll / Entry
# ------------------------------------------------------------

def save_scroll_to_memory(user_id: str, label: str, content: str, metadata: Dict[str, Any]) -> str:
    """
    Persist a scroll to disk and optionally relay to Photon Memory Grid.

    Args:
        user_id (str): The active SCI user or container context.
        label (str): Scroll label or symbolic identifier.
        content (str): The symbolic or photon data to persist.
        metadata (Dict[str, Any]): Arbitrary scroll metadata.
    Returns:
        str: The saved file path.
    """
    timestamp = datetime.utcnow().isoformat(timespec="milliseconds") + "Z"
    entry = {
        "user_id": user_id,
        "label": label,
        "content": content,
        "metadata": metadata,
        "timestamp": timestamp,
    }

    filename = f"{user_id}_{label.replace(' ', '_')}_{int(time.time())}.json"
    path = os.path.join(MEMORY_DIR, filename)

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=2, ensure_ascii=False)
        print(f"💾 [ResonantMemory] Saved scroll '{label}' for [{user_id}] → {path}")
    except Exception as e:
        print(f"⚠️ [ResonantMemory] Failed to save scroll '{label}': {e}")
        raise

    # Relay to photon memory (optional, non-blocking)
    try:
        store_photon_memory_entry(label, content, metadata)
    except Exception as e:
        print(f"[ResonantMemory] Skipped photon relay: {e}")

    return path

# ------------------------------------------------------------
# 🧹 Maintenance / Listing
# ------------------------------------------------------------

def list_saved_scrolls(user_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    """
    List saved scrolls for a user, sorted by most recent.
    """
    if not os.path.exists(MEMORY_DIR):
        return []
    files = sorted(
        [os.path.join(MEMORY_DIR, f) for f in os.listdir(MEMORY_DIR) if f.endswith(".json")],
        key=os.path.getmtime,
        reverse=True,
    )
    scrolls = []
    for path in files[:limit]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if user_id is None or data.get("user_id") == user_id:
                scrolls.append(data)
        except Exception as e:
            print(f"⚠️ [ResonantMemory] Failed to read scroll: {path} ({e})")
    return scrolls

# ------------------------------------------------------------
# 🔧 CLI Test Harness
# ------------------------------------------------------------

if __name__ == "__main__":
    test_path = save_scroll_to_memory(
        user_id="tester",
        label="μ resonance seed",
        content="⊕↔μ⟲",
        metadata={"context": "test"},
    )
    print(f"✅ Test scroll saved: {test_path}")
    print(json.dumps(list_saved_scrolls("tester", limit=5), indent=2))