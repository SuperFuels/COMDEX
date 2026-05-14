"""
Query Resonance API - Phase 41C
--------------------------------
Enables semantic querying and similarity computation
over the Language Resonance Matrix (LRM).

Author: Tessaris Research Group
Date: Phase 41C - October 2025
"""

import json
from pathlib import Path
from backend.modules.aion_language.thesaurus_linker import LRM

# Updated path to match where LRM exports
MATRIX_PATH = Path("data/semantic/language_resonance_matrix.json")

class QueryResonanceAPI:
    def __init__(self):
        self.matrix = getattr(LRM, "matrix", {})
        if not self.matrix:
            self._load_matrix()

    def _load_matrix(self):
        """Load the stored resonance matrix from disk."""
        if not MATRIX_PATH.exists():
            print(f"[QRA] ⚠️ No resonance matrix found at {MATRIX_PATH}")
            self.matrix = {}
            return
        try:
            with open(MATRIX_PATH) as f:
                self.matrix = json.load(f)
            print(f"[QRA] Loaded {len(self.matrix)} word nodes from {MATRIX_PATH}")
        except Exception as e:
            print(f"[QRA] ❌ Failed to load resonance matrix: {e}")
            self.matrix = {}

    def query_related(self, word, top_n=5):
        """Return top related terms by absolute resonance value."""
        if word not in self.matrix:
            return []
        related = sorted(
            self.matrix[word].items(),
            key=lambda kv: abs(kv[1]),
            reverse=True
        )
        return related[:top_n]

    def semantic_distance(self, word1, word2):
        """Compute distance = 1 - |resonance| (lower means closer)."""
        if word1 not in self.matrix:
            return None
        val = self.matrix[word1].get(word2)
        if val is None:
            return None
        return round(1 - abs(val), 3)

    def resonance_field_summary(self):
        """Provide a quick summary of the matrix (robust to malformed entries)."""
        total_links = 0
        all_vals = []
        for v in self.matrix.values():
            if isinstance(v, dict):
                total_links += len(v)
                all_vals.extend(abs(x) for x in v.values() if isinstance(x, (int, float)))
        avg_strength = round(sum(all_vals) / len(all_vals), 3) if all_vals else 0.0
        return {
            "total_words": len(self.matrix),
            "total_links": total_links,
            "mean_resonance_strength": avg_strength
        }

# Global instance
try:
    QRA
except NameError:
    QRA = QueryResonanceAPI()
    print("🧭 QueryResonanceAPI global instance initialized as QRA")