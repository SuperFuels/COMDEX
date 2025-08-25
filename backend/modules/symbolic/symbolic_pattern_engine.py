# backend/modules/symbolic/symbolic_pattern_engine.py

from typing import List, Dict, Any, Optional, Tuple
import hashlib
import time
from backend.modules.codex.codexlang_rewriter import CodexLangRewriter
from backend.modules.codex.codex_ast_encoder import encode_codex_ast_to_glyphs
from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import LogicGlyph
from backend.modules.knowledge_graph.knowledge_graph_writer import KnowledgeGraphWriter
from backend.modules.dna_chain.dna_switch import add_dna_mutation
from backend.modules.codex.codex_metric import CodexMetrics

class SymbolicPatternEngine:
    """
    Symbolic recombination and pattern synthesis engine for glyph logic recovery,
    predictive fusion, and SQI-aligned mutation suggestion.
    """

    @classmethod
    def detect_pattern_overlap(cls, glyphs: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """
        Detect glyph pairs with overlapping symbolic structure, hinting at recombination potential.
        Returns list of tuples (glyph_a, glyph_b)
        """
        overlaps = []
        for i, glyph_a in enumerate(glyphs):
            for glyph_b in glyphs[i+1:]:
                if cls._symbolic_overlap(glyph_a, glyph_b) > 0.5:
                    overlaps.append((glyph_a, glyph_b))
        return overlaps

    @classmethod
    def _symbolic_overlap(cls, a: Dict[str, Any], b: Dict[str, Any]) -> float:
        """Naive overlap based on common tokens. Could be upgraded to embedding cosine similarity."""
        text_a = a.get("text", "").lower()
        text_b = b.get("text", "").lower()
        tokens_a = set(text_a.split())
        tokens_b = set(text_b.split())
        if not tokens_a or not tokens_b:
            return 0.0
        return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)

    @classmethod
    def recombine_all(cls, fragments: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Attempt to recombine symbolic fragments into a unified prediction or fused glyph.
        Stores into KG, emits DNA mutation, and returns result.
        """
        if not fragments:
            return None

        combined_text = " + ".join([f.get("text", "") for f in fragments if f.get("text")])
        origin_ids = [f.get("id") for f in fragments if "id" in f]

        fused_text = f"Fusion({combined_text})"

        fused_glyph = {
            "type": "symbol",
            "text": fused_text,
            "metadata": {
                "recombinedFrom": origin_ids,
                "confidence": 0.91,
                "fusionEngine": "SymbolicPatternEngine",
                "timestamp": time.time()
            }
        }

        # Inject into KG
        KnowledgeGraphWriter.store_symbolic_glyph(fused_glyph)

        # Log mutation
        add_dna_mutation(
            from_glyph=" + ".join(origin_ids),
            to_glyph=fused_text,
            reason="symbolic fragment fusion"
        )

        # Score it
        CodexMetrics.record_confidence_event(fused_glyph, fused_glyph["metadata"].get("confidence", 0.91))

        return fused_glyph

    @classmethod
    def fuse_predictive_paths(cls, container: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search predictive glyphs (e.g., from electrons) and try to fuse them into coherent paths.
        """
        fused = []
        electrons = container.get("electrons", [])
        predictive_glyphs = [e for e in electrons if any("Predicts" in g.get("text", "") for g in e.get("glyphs", []))]

        for electron in predictive_glyphs:
            glyphs = electron.get("glyphs", [])
            if len(glyphs) > 1:
                recombined = cls.recombine_all(glyphs)
                if recombined:
                    fused.append(recombined)
                    container.setdefault("trace", {}).setdefault("fused_predictions", []).append(recombined)
        return fused