"""
Phase 41B - Thesaurus Linker + Language Resonance Matrix (LRM)
----------------------------------------------------------------
Builds a resonance-weighted graph linking lexical atoms in the
Meaning Field Engine (MFG) by synonym/antonym relations.
"""

import json, math, time, logging
from pathlib import Path
from itertools import combinations
from backend.modules.aion_language.meaning_field_engine import MFG

logger = logging.getLogger(__name__)
LRM_PATH = Path("data/lexicons/language_resonance_matrix.json")


class ThesaurusLinker:
    def __init__(self):
        self.matrix = {}        # word -> {other_word: resonance_strength}
        self.last_update = None

    # ─────────────────────────────────────────
    def _resonance_score(self, rel_type: str) -> float:
        """Assign resonance polarity by relation type."""
        if rel_type == "synonym":
            return round(0.8 + 0.2 * math.sin(time.time()), 3)
        elif rel_type == "antonym":
            return round(-0.8 - 0.2 * math.sin(time.time()), 3)
        return 0.0

    # ─────────────────────────────────────────
    def build_from_MFG(self):
        """Scan Meaning Field clusters -> build resonance matrix."""
        clusters = getattr(MFG, "field", {}).get("clusters", [])
        if not clusters:
            logger.warning("[ThesaurusLinker] No clusters found in MFG.")
            return

        for c in clusters:
            word = c["center"]
            self.matrix.setdefault(word, {})

            for s in c.get("synonyms", []):
                self.matrix[word][s] = self._resonance_score("synonym")
            for a in c.get("antonyms", []):
                self.matrix[word][a] = self._resonance_score("antonym")

        self.last_update = time.time()
        logger.info(f"[ThesaurusLinker] Built LRM for {len(clusters)} concepts.")

    # ─────────────────────────────────────────
    def export(self):
        """Save Language Resonance Matrix to disk."""
        LRM_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LRM_PATH, "w") as f:
            json.dump({
                "timestamp": self.last_update,
                "matrix": self.matrix
            }, f, indent=2)
        logger.info(f"[ThesaurusLinker] Exported LRM -> {LRM_PATH}")

    # ─────────────────────────────────────────
    def link_strength(self, w1: str, w2: str) -> float:
        """Get resonance link strength between two words."""
        if w1 in self.matrix and w2 in self.matrix[w1]:
            return self.matrix[w1][w2]
        if w2 in self.matrix and w1 in self.matrix[w2]:
            return self.matrix[w2][w1]
        return 0.0


# Global Instance
try:
    LRM
except NameError:
    LRM = ThesaurusLinker()
    print("🔗 ThesaurusLinker global instance initialized as LRM")

if __name__ == "__main__":
    from backend.modules.aion_language.meaning_field_engine import MFG
    print("🔗 Building Language Resonance Matrix (LRM)...")
    LRM.build_from_MFG()
    LRM.export()
    print("✅ ThesaurusLinker completed and exported successfully.")