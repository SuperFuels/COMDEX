# ================================================================
# 📖 RuleBookIndex - persistent .dc container registry
# ================================================================
import json, logging, time
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)
STORE = Path("data/rulebooks/rulebook_index.json")
EXPORT_DIR = Path("data/rulebooks/exports")

class RuleBookIndex:
    """
    Maintains registry of all known rulebooks.
    Each entry includes metadata, entanglement, usage stats, and mutation history.
    """

    def __init__(self):
        self.rulebooks: Dict[str, Dict[str, Any]] = self._load_all()

    def _load_all(self) -> Dict[str, Dict[str, Any]]:
        if STORE.exists():
            return json.load(open(STORE))
        return {}

    def save(self):
        STORE.parent.mkdir(parents=True, exist_ok=True)
        with open(STORE, "w") as f:
            json.dump(self.rulebooks, f, indent=2)

    def register(self, rulebook_id: str, metadata: Dict[str, Any]):
        entry = self.rulebooks.get(rulebook_id, {})
        entry.update(metadata)
        entry.setdefault("created_at", time.time())
        entry["updated_at"] = time.time()
        entry.setdefault("usage_count", 0)
        entry.setdefault("mutations", [])
        self.rulebooks[rulebook_id] = entry
        self.save()
        logger.info(f"[RuleBookIndex] Registered {rulebook_id}")

    def increment_usage(self, rulebook_id: str):
        if rulebook_id in self.rulebooks:
            self.rulebooks[rulebook_id]["usage_count"] += 1
            self.rulebooks[rulebook_id]["last_used"] = time.time()
            self.save()

    def record_mutation(self, rulebook_id: str, mutation: Dict[str, Any]):
        if rulebook_id not in self.rulebooks:
            return
        self.rulebooks[rulebook_id].setdefault("mutations", []).append({
            "timestamp": time.time(),
            **mutation
        })
        self.save()

    def export_all(self):
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = EXPORT_DIR / f"rulebooks_{int(time.time())}.dc.json"
        with open(out_path, "w") as f:
            json.dump(self.rulebooks, f, indent=2)
        logger.info(f"[RuleBookIndex] Exported {len(self.rulebooks)} rulebooks -> {out_path}")
        return out_path