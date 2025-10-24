# ================================================================
# 📘 Phase 45F.5 — LangField → QLang + QTensor Integration
# ================================================================
"""
Combines all lexical–semantic resonance layers into a unified
QLang QTensor field for the AION cognitive substrate.

Inputs:
    data/lexicons/lexicore.lex.json
    data/lexicons/language_resonance_matrix.json
    data/lexicons/etymology_lineage.ety.json
    data/semantic/wikigraph.json

Output:
    data/qtensor/langfield_resonance.qdata.json
"""
import json, math, time, logging
from pathlib import Path
from typing import Any, Dict, List, Union

# Initialize logger
logger = logging.getLogger(__name__)

# Input paths
LEX_PATH   = Path("data/lexicons/lexicore.lex.json")
LRM_PATH   = Path("data/lexicons/language_resonance_matrix.json")
ETY_PATH   = Path("data/lexicons/etymology_lineage.ety.json")
WIKI_PATH  = Path("data/semantic/wikigraph.json")

# Output path
QDATA_PATH = Path("data/qtensor/langfield_resonance.qdata.json")


# ─────────────────────────────────────────
# Helper — Extract robust lexical ID
# ─────────────────────────────────────────
def _wid_from_entry(entry: Dict[str, Any]) -> str:
    """
    Robust word/lemma/id extractor.
    Supports {id, word, lemma, term, token}.
    """
    return (
        entry.get("id")
        or entry.get("word")
        or entry.get("lemma")
        or entry.get("term")
        or entry.get("token")
        or ""
    ).strip().lower()


# ================================================================
# 🧩 LangFieldResonanceConverter
# ================================================================
class LangFieldResonanceConverter:
    def __init__(self):
        self.tensor_field: Dict[str, Any] = {}
        self.timestamp: float | None = None

    # ─────────────────────────────────────────
    def _safe_load(self, path: Path) -> Union[Dict, List]:
        """Gracefully load JSON data, returning empty if missing or invalid."""
        try:
            if not path.exists():
                logger.warning(f"[LangField] Missing source: {path}")
                return []
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception as e:
            logger.warning(f"[LangField] Failed to load {path}: {e}")
            return []

    # ─────────────────────────────────────────
    def _combine_resonances(self, sem, lex, ety, wiki) -> Dict[str, float]:
        """
        Merge resonance values into Φ–ψ–η–Λ tensor.
        Weighting emphasizes etymic depth and lexical correlation.
        """
        Φ = sem.get("semantic_score", 1.0)
        ψ = lex.get("correlation", 1.0)
        η = ety.get("depth_weight", 1.0)
        Λ = len(wiki.get("links", [])) if isinstance(wiki, dict) and "links" in wiki else 1.0

        q_val = round((Φ * ψ * η * math.log(Λ + 1)) ** 0.25, 6)
        phase = round(math.atan2(ψ, Φ), 3)
        return {"Φ": Φ, "ψ": ψ, "η": η, "Λ": Λ, "q_val": q_val, "phase": phase}

    # ─────────────────────────────────────────
    # ─────────────────────────────────────────
    def integrate(self):
        logger.info("🧬 Integrating LangField resonance layers …")

        # Load inputs
        lex  = self._safe_load(LEX_PATH)
        lrm  = self._safe_load(LRM_PATH)
        ety  = self._safe_load(ETY_PATH)
        wiki = self._safe_load(WIKI_PATH)

        # Defensive typing
        if not isinstance(lrm, dict):  lrm = {}
        if not isinstance(ety, dict):  ety = {}
        if not isinstance(wiki, dict): wiki = {}

        # Accept both list or dict for LexiCore
        if isinstance(lex, dict):
            entries: List[Dict[str, Any]] = list(lex.get("lexicon", []))
        else:
            entries = list(lex)  # assume already a list

        lrm_matrix  = lrm.get("matrix", {})
        ety_lineage = ety.get("lineage", [])
        wiki_nodes  = wiki.get("wikigraph", {}).get("nodes", {})

        count = 0
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            wid = _wid_from_entry(entry)
            if not wid:
                continue

            sem = {"semantic_score": entry.get("weight", 1.0)}

            # Thesaurus correlation
            lex_rel = {"correlation": 1.0}
            if wid in lrm_matrix and isinstance(lrm_matrix[wid], dict) and wid in lrm_matrix[wid]:
                lex_rel["correlation"] = lrm_matrix[wid][wid]

            # Etymology depth — supports list of dicts *or* list of strings
            ety_rel = {"depth_weight": 1.0}
            for e in ety_lineage:
                if isinstance(e, dict):
                    e_word = e.get("word", "").strip().lower()
                    if e_word == wid:
                        ety_rel["depth_weight"] = float(e.get("depth", 1.0))
                        break
                elif isinstance(e, str):
                    if e.strip().lower() == wid:
                        ety_rel["depth_weight"] = 1.0
                        break

            # Wikigraph node
            wiki_node = wiki_nodes.get(wid, {})

            # Combine all resonance values
            self.tensor_field[wid] = self._combine_resonances(sem, lex_rel, ety_rel, wiki_node)
            count += 1

        self.timestamp = time.time()
        logger.info(f"[LangField] Built tensor field for {count} lexical atoms.")

    # ─────────────────────────────────────────
    def export(self):
        """Write unified QTensor field to disk."""
        QDATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(QDATA_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": self.timestamp,
                "tensor_field": self.tensor_field,
                "meta": {
                    "schema": "LangFieldResonance.v1",
                    "desc": "Unified Φ–ψ–η–Λ QTensor field",
                    "ready_for_QLang": True
                }
            }, f, indent=2)
        logger.info(f"[LangField] Exported unified QTensor → {QDATA_PATH}")


# ================================================================
# 🧠 CLI Entry Point
# ================================================================
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    conv = LangFieldResonanceConverter()
    conv.integrate()
    conv.export()
    print("✅ LangField Resonance → QLang QTensor integration complete.")