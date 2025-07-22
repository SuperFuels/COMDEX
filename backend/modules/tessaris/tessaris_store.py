# File: backend/modules/tessaris/tessaris_store.py

import os
import json
import hashlib
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pathlib import Path

from backend.modules.tessaris.thought_branch import ThoughtBranch, BranchNode
from backend.modules.dna_chain.switchboard import DNA_SWITCH
from backend.modules.codex.codex_scroll_builder import build_codex_scroll

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
        Save a ThoughtBranch to disk with optional in-memory caching.
        """
        if self.cache_enabled:
            self._cache.append(branch)

        payload = self._load_all_json()

        encoded = {
            "timestamp": datetime.utcnow().isoformat(),
            "branch": branch.to_dict(),
            "origin_id": branch.origin_id,
            "hash": self._hash_branch(branch)
        }

        # Prevent saving exact duplicate
        if payload and encoded["hash"] == payload[-1].get("hash"):
            print("⚠️ Duplicate branch detected, skipping save.")
            return

        payload.append(encoded)

        with open(SNAPSHOT_PATH, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"✅ ThoughtBranch saved to {SNAPSHOT_PATH}")

    def load_all_branches(self) -> List[ThoughtBranch]:
        try:
            raw = self._load_all_json()
            return [ThoughtBranch.from_dict(entry["branch"]) for entry in raw]
        except Exception as e:
            print(f"[⚠️] Failed to load branches: {e}")
            return []

    def load_tessaris_snapshot(self, thought_id: str) -> Optional[ThoughtBranch]:
        try:
            all_data = self._load_all_json()
            for entry in reversed(all_data):  # newest match first
                if entry.get("origin_id") == thought_id:
                    return ThoughtBranch.from_dict(entry["branch"])
        except Exception as e:
            print(f"[❌] Error loading snapshot for {thought_id}: {e}")
        return None

    def get_cache(self) -> List[ThoughtBranch]:
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
        try:
            return self._load_all_json()
        except:
            return []

    def export_latest_snapshot_to_context(self, context: dict):
        all_branches = self.load_all_branches()
        if not all_branches:
            print("⚠️ No branches available to export to context.")
            return
        latest = all_branches[-1]
        context["tessaris_snapshot"] = latest.root.to_dict()
        context["tessaris_codex_scroll"] = build_codex_scroll(latest.root.to_list(), include_coords=True)

    def save_direct_branchnode(self, node: BranchNode):
        payload = self._load_all_json()
        encoded = {
            "timestamp": datetime.utcnow().isoformat(),
            "branch": node.to_dict(),
            "origin_id": getattr(node, "id", None),
            "hash": self._hash_dict(node.to_dict())
        }
        payload.append(encoded)
        with open(SNAPSHOT_PATH, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"✅ Direct BranchNode saved to {SNAPSHOT_PATH}")

    def save_snapshot(self, snapshot: dict, name: Optional[str] = None):
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

    def _hash_branch(self, branch: ThoughtBranch) -> str:
        return self._hash_dict(branch.to_dict())

    def _hash_dict(self, data: Dict[str, Any]) -> str:
        raw = json.dumps(data, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()


# ✅ Singleton
TESSARIS_STORE = TessarisStore()

# 🔁 Exports
def load_tessaris_snapshot(thought_id: str) -> Optional[ThoughtBranch]:
    return TESSARIS_STORE.load_tessaris_snapshot(thought_id)

def save_snapshot(snapshot: dict, name: Optional[str] = None):
    TESSARIS_STORE.save_snapshot(snapshot, name)

if __name__ == "__main__":
    print("🧠 Saved Tessaris Thought Branches:")
    for entry in TESSARIS_STORE.list_snapshots():
        glyphs = entry["branch"].get("glyphs", [])
        print(f" - {entry.get('timestamp')}: {glyphs}")