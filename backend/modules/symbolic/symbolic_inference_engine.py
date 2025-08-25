from typing import Dict, Any, List
from backend.modules.consciousness.prediction_engine import suggest_simplifications
from backend.modules.symbolic.symbolic_broadcast import broadcast_glyph_event
from backend.modules.consciousness.logic_prediction_utils import detect_contradictions
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
from backend.modules.codex.codex_metrics import score_glyph_tree

# Optional import if Lean proof support is present
try:
    from backend.modules.lean.lean_proofverifier import verify_container
    LEAN_SUPPORT = True
except ImportError:
    LEAN_SUPPORT = False


class SymbolicInferenceEngine:
    """
    Central symbolic reasoning system.

    Detects contradictions, suggests rewrites, scores logic,
    and syncs symbolic events to WebSocket and Knowledge Graph.
    """

    def __init__(self):
        self.writer = get_kg_writer()

    def analyze_container(self, container: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a .dc.json container for symbolic logic issues.

        Args:
            container (dict): The symbolic container

        Returns:
            dict: Inference result with status, rewrites, contradictions, scores
        """
        container_id = container.get("id", "unknown")
        trace = container.get("trace", [])
        contradiction_entries = []
        suggestions = []

        for i, entry in enumerate(trace):
            glyph = entry.get("glyph")
            coord = entry.get("coord", f"step_{i}")

            if not glyph:
                continue

            # Check for contradiction
            if self._is_contradiction_heuristic(glyph) or detect_contradictions(glyph):
                contradiction_entries.append({
                    "glyph": glyph,
                    "coord": coord
                })

                broadcast_glyph_event(
                    event_type="contradiction",
                    glyph=glyph,
                    container_id=container_id,
                    coord=coord,
                    extra={"confidence": 0.95}
                )

                self.writer.inject_glyph(
                    content=glyph,
                    glyph_type="contradiction",
                    metadata={"container_id": container_id, "coord": coord}
                )

        if contradiction_entries:
            suggestions = suggest_simplifications(container)
            container["traceMetadata"] = container.get("traceMetadata", {})
            container["traceMetadata"]["rewriteSuggestions"] = suggestions

        # SQI scoring
        score_result = score_glyph_tree(trace)
        container["traceMetadata"] = container.get("traceMetadata", {})
        container["traceMetadata"]["sqiScore"] = score_result

        # Optional Lean verification
        if LEAN_SUPPORT:
            try:
                proof_result = verify_container(container)
                container["traceMetadata"]["leanProof"] = proof_result
            except Exception as e:
                container["traceMetadata"]["leanProofError"] = str(e)

        return {
            "status": "contradiction" if contradiction_entries else "ok",
            "contradictions": contradiction_entries,
            "rewrites": suggestions,
            "score": score_result,
            "lean_verified": container["traceMetadata"].get("leanProof", None)
        }

    def _is_contradiction_heuristic(self, glyph: str) -> bool:
        """
        Basic textual contradiction heuristic.

        Returns True if the glyph includes classical contradiction forms.
        """
        return any([
            "⊥" in glyph,
            "→ ⊥" in glyph,
            "¬" in glyph and "→" in glyph,
            "False" in glyph and "implies" in glyph
        ])


# ✅ Add this global wrapper to allow external imports
_engine = SymbolicInferenceEngine()

def run_symbolic_inference(container: Dict[str, Any]) -> Dict[str, Any]:
    """
    Global function wrapper to run symbolic inference on a container.
    This is used by external modules to trigger contradiction/rewrite detection.
    """
    return _engine.analyze_container(container)