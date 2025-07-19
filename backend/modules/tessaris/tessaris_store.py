# File: backend/modules/tessaris/tessaris_store.py

import os
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from backend.modules.tessaris.thought_branch import ThoughtBranch, BranchNode
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # ✅ DNA tracking

SNAPSHOT_PATH = "data/thoughts/.tessaris.json"
SNAPSHOT_DIR = Path(SNAPSHOT_PATH).parent
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

class TessarisStore:
    def __init__(self, cache_enabled: bool = True):
        self.cache_enabled = cache_enabled
        self._cache: List[ThoughtBranch] = []

    def save_branch(self, branch: ThoughtBranch):
        """
        Save a ThoughtBranch to disk and optionally to memory cache.
        """
        if self.cache_enabled:
            self._cache.append(branch)

        payload = self._load_all_json()
        payload.append({
            "timestamp": datetime.utcnow().isoformat(),
            "branch": branch.to_dict(),
            "origin_id": branch.origin_id
        })

        with open(SNAPSHOT_PATH, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"✅ ThoughtBranch saved to {SNAPSHOT_PATH}")

    def load_all_branches(self) -> List[ThoughtBranch]:
        """
        Load all saved ThoughtBranches from disk.
        """
        try:
            raw = self._load_all_json()
            return [ThoughtBranch.from_dict(entry["branch"]) for entry in raw]
        except Exception as e:
            print(f"[⚠️] Failed to load branches: {e}")
            return []

    def load_tessaris_snapshot(self, thought_id: str) -> Optional[ThoughtBranch]:
        """
        Load a specific ThoughtBranch by its origin_id.
        """
        try:
            all_data = self._load_all_json()
            for entry in reversed(all_data):  # most recent match first
                if entry.get("origin_id") == thought_id:
                    return ThoughtBranch.from_dict(entry["branch"])
        except Exception as e:
            print(f"[❌] Error loading snapshot for {thought_id}: {e}")
        return None

    def get_cache(self) -> List[ThoughtBranch]:
        """
        Return in-memory cache (if enabled).
        """
        return self._cache if self.cache_enabled else []

    def clear_cache(self):
        self._cache = []

    def _load_all_json(self) -> List[dict]:
        if not os.path.exists(SNAPSHOT_PATH):
            return []
        try:
            with open(SNAPSHOT_PATH, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"⚠️ Corrupt snapshot file at {SNAPSHOT_PATH}, resetting.")
            return []

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """
        Return raw snapshot metadata for inspection or filtering.
        """
        try:
            return self._load_all_json()
        except:
            return []

    def export_latest_snapshot_to_context(self, context: dict):
        """
        Load latest saved branch and attach as tessaris_snapshot to context.
        """
        all_branches = self.load_all_branches()
        if not all_branches:
            print("⚠️ No branches available to export to context.")
            return
        latest = all_branches[-1]
        context["tessaris_snapshot"] = latest.root.to_dict()

    def save_direct_branchnode(self, node: BranchNode):
        """
        Lightweight method to save a BranchNode directly without full ThoughtBranch wrapper.
        """
        payload = self._load_all_json()
        payload.append({
            "timestamp": datetime.utcnow().isoformat(),
            "branch": node.to_dict(),
            "origin_id": node.id if hasattr(node, 'id') else None
        })
        with open(SNAPSHOT_PATH, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"✅ Direct BranchNode saved to {SNAPSHOT_PATH}")

    def save_snapshot(self, snapshot: dict, name: Optional[str] = None):
        """
        Save a raw snapshot dictionary to a separate file under /snapshots.
        """
        snapshot_dir = Path("data/thoughts/snapshots")
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        name = name or datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        filename = snapshot_dir / f"{name}.tessaris.json"

        try:
            with open(filename, "w") as f:
                json.dump(snapshot, f, indent=2)
            print(f"🧠 Tessaris snapshot saved: {filename.name}")
        except Exception as e:
            print(f"❌ Failed to save snapshot: {e}")

# ✅ Singleton export
TESSARIS_STORE = TessarisStore()

# 🔁 Global importable function for tessaris_engine
def load_tessaris_snapshot(thought_id: str) -> Optional[ThoughtBranch]:
    return TESSARIS_STORE.load_tessaris_snapshot(thought_id)

# 🧠 Global snapshot saver for tessaris_engine
def save_snapshot(snapshot: dict, name: Optional[str] = None):
    TESSARIS_STORE.save_snapshot(snapshot, name)

if __name__ == "__main__":
    print("🧠 Saved Tessaris Thought Branches:")
    for entry in TESSARIS_STORE.list_snapshots():
        print(f" - {entry.get('timestamp')}: {entry['branch'].get('glyphs')}")