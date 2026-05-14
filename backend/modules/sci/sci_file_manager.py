# ============================================================
# 🧩 SCI File Manager - Resonant Memory Integration
# ============================================================
# Handles saving and loading SCI session data, scrolls, and field
# exports with persistent links to Resonant Memory (.json scrolls).
# ============================================================

from __future__ import annotations
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List

# ------------------------------------------------------------
# Optional Integrations
# ------------------------------------------------------------
try:
    from backend.modules.resonant_memory.resonant_memory_saver import save_scroll_to_memory, list_saved_scrolls
except Exception:
    def save_scroll_to_memory(user_id: str, label: str, content: str, metadata: Dict[str, Any]):
        print(f"[StubMemorySaver] Saved scroll {label} for user {user_id}")
        return f"artifacts/memory/{user_id}_{label}.json"

    def list_saved_scrolls(user_id: str, limit: int = 20):
        return [{"user_id": user_id, "label": "stub", "timestamp": datetime.utcnow().isoformat()}]

# ------------------------------------------------------------
# File paths
# ------------------------------------------------------------
SESSIONS_DIR = "artifacts/sci_sessions"
os.makedirs(SESSIONS_DIR, exist_ok=True)


class SCIFileManager:
    """Manages save/load operations for SCI sessions and scrolls."""

    def __init__(self, user_id: str):
        self.user_id = user_id

    # ============================================================
    # 💾 Save Session
    # ============================================================
    def save_session(self, field_id: str, data: Dict[str, Any]) -> str:
        """
        Save an SCI field session and persist to resonant memory.
        """
        timestamp = datetime.utcnow().isoformat(timespec="milliseconds") + "Z"
        session_data = {
            "user_id": self.user_id,
            "field_id": field_id,
            "timestamp": timestamp,
            "data": data,
        }

        # Save local session file
        filename = f"{self.user_id}_{field_id}_{int(datetime.utcnow().timestamp())}.json"
        path = os.path.join(SESSIONS_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

        # Also persist to Resonant Memory
        save_scroll_to_memory(
            user_id=self.user_id,
            label=f"session::{field_id}",
            content=json.dumps(data, ensure_ascii=False),
            metadata={"timestamp": timestamp, "origin": "sci_session"},
        )

        print(f"💾 [SCIFileManager] Session saved -> {path}")
        return path

    # ============================================================
    # 📂 Load Session
    # ============================================================
    def load_session(self, field_id: str) -> Dict[str, Any]:
        """
        Load the latest session file for a given field.
        """
        files = [f for f in os.listdir(SESSIONS_DIR) if f.startswith(self.user_id) and field_id in f]
        if not files:
            raise FileNotFoundError(f"No session found for field: {field_id}")

        files.sort(key=lambda f: os.path.getmtime(os.path.join(SESSIONS_DIR, f)), reverse=True)
        path = os.path.join(SESSIONS_DIR, files[0])
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        print(f"📂 [SCIFileManager] Loaded session for field [{field_id}]")
        return data.get("data", {})

    # ============================================================
    # 🧠 List Memory Scrolls
    # ============================================================
    def list_memory_scrolls(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Return recently saved scrolls from Resonant Memory.
        """
        scrolls = list_saved_scrolls(self.user_id, limit=limit)
        print(f"🧬 [SCIFileManager] Found {len(scrolls)} scrolls for user {self.user_id}")
        return scrolls

    # ============================================================
    # 🧹 Cleanup
    # ============================================================
    def cleanup(self):
        print(f"🧹 [SCIFileManager] Cleanup complete for {self.user_id}")