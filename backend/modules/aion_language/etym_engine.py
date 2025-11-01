# ======================================================
# 📁 backend/modules/aion_language/etym_engine.py
# ======================================================
"""
Phase 45F.4 - EtymEngine (Root Lineage Tracker)
───────────────────────────────────────────────────────
Parses and links etymological roots across the LexiCore,
ThesauriNet, and Meaning Field Engine to generate Φ-ψ-η
resonance lineages.

Output:
    data/lexicons/etymology_lineage.ety.json
"""

import json, time, logging, math
from pathlib import Path
from backend.modules.aion_language.meaning_field_engine import MFG

logger = logging.getLogger(__name__)
ETY_PATH = Path("data/lexicons/etymology_lineage.ety.json")

class EtymEngine:
    def __init__(self):
        self.lineage = {}       # word -> {root, origin, resonance_score}
        self.last_update = None

    # ─────────────────────────────────────────
    def _resonance(self, depth: int) -> float:
        """Assign resonance weight by historical depth."""
        base = 1.0 / (1.0 + math.exp(depth - 2))
        return round(base + 0.05 * math.sin(time.time()), 4)

    # ─────────────────────────────────────────
    def add_entry(self, word: str, root: str, origin: str, depth: int = 1):
        """Register a single word -> root lineage mapping."""
        self.lineage[word] = {
            "root": root,
            "origin": origin,
            "depth": depth,
            "resonance": self._resonance(depth)
        }

    # ─────────────────────────────────────────
    def integrate_with_MFG(self):
        """Integrate etymic resonance into MFG clusters."""
        for w, info in self.lineage.items():
            if hasattr(MFG, "update_resonance"):
                MFG.update_resonance(w, info["resonance"])
        logger.info(f"[EtymEngine] Integrated {len(self.lineage)} roots into MFG resonance map.")

    # ─────────────────────────────────────────
    def export(self):
        """Export etymic lineage to disk."""
        ETY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(ETY_PATH, "w") as f:
            json.dump({
                "timestamp": time.time(),
                "lineage": self.lineage,
                "meta": {
                    "schema": "etym.v1",
                    "ready_for_resonance": True
                }
            }, f, indent=2)
        self.last_update = time.time()
        logger.info(f"[EtymEngine] Exported lineage -> {ETY_PATH}")

# ─────────────────────────────────────────
# Global instance
# ─────────────────────────────────────────
try:
    ETYM
except NameError:
    ETYM = EtymEngine()
    print("🌱 EtymEngine global instance initialized as ETYM")

# ─────────────────────────────────────────
# Optional CLI entry
# ─────────────────────────────────────────
if __name__ == "__main__":
    print("🌱 Building Etymology Lineage ...")
    ETYM.add_entry("photon", "phōs", "Greek φῶς (light)", depth=1)
    ETYM.add_entry("wave", "wafian", "Old English wafian (to move)", depth=2)
    ETYM.add_entry("light", "leuk", "Proto-Indo-European *leuk- (bright)", depth=3)
    ETYM.export()
    print("✅ EtymEngine completed successfully.")