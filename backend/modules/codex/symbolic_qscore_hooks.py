"""
symbolic_qscore_hooks.py

Applies symbolic quantum scoring (QScore) to beams and glyphs.
Supports plugin hook system and per-glyph evaluation.
"""

import logging
from typing import Dict, Any, Callable, List

from backend.modules.codex.symbolic_entropy import compute_entropy_metrics
from backend.modules.codex.symbolic_metadata import attach_symbolic_metadata
from backend.modules.sqi.sqi_scorer import score_electron_glyph

logger = logging.getLogger(__name__)

# --- Plugin registry ---
QCORE_HOOKS: List[Callable[[Dict[str, Any]], Dict[str, Any]]] = []

def register_qcore_hook(hook_fn: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
    """
    Register a custom QScore plugin hook for beam post-processing.
    Each hook must accept and return a beam dictionary.
    """
    QCORE_HOOKS.append(hook_fn)
    logger.info(f"[QScoreHooks] Registered plugin hook: {hook_fn.__name__}")


def apply_qscore_hooks(beam_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main QScore pipeline. Applies symbolic metadata, computes QScore,
    evaluates per-glyph coherence, and attaches summary metrics.

    Args:
        beam_dict: Symbolic beam dictionary.

    Returns:
        Updated beam_dict with qscore_metrics and optional glyph annotations.
    """
    if not beam_dict.get("logic_tree"):
        logger.warning("[QScoreHooks] Beam missing logic_tree; skipping.")
        return beam_dict

    try:
        beam_dict = attach_symbolic_metadata(beam_dict)
    except Exception as e:
        logger.error(f"[QScoreHooks] Metadata attachment failed: {e}")
        return beam_dict

    meta = beam_dict.get("symbolic_metadata", {})
    entropy = float(meta.get("entropy", 0.0))
    trust = float(meta.get("trust_score", 0.0))
    emotion = meta.get("emotion_state", "🤖 neutral")
    depth = _get_tree_depth(beam_dict["logic_tree"])

    # --- Per-glyph evaluation ---
    glyphs = beam_dict.get("glyphs", [])
    scored = _score_relevant_glyphs(glyphs)
    average_sqi = sum(g["score"] for g in scored) / len(scored) if scored else 0.0

    # --- Main QScore calculation ---
    qscore = _calculate_qscore(entropy, trust, depth, average_sqi)

    beam_dict["qscore_metrics"] = {
        "entropy": entropy,
        "trust_score": trust,
        "tree_depth": depth,
        "emotion": emotion,
        "glyph_sqi_avg": average_sqi,
        "qscore": qscore,
        "rating": _rate_qscore(qscore),
        "evaluated_glyphs": scored,
    }

    # --- Plugin hooks ---
    for hook_fn in QCORE_HOOKS:
        try:
            beam_dict = hook_fn(beam_dict)
        except Exception as e:
            logger.warning(f"[QScoreHooks] Plugin hook {hook_fn.__name__} failed: {e}")

    logger.info(
        f"[QScoreHooks] Beam {beam_dict.get('id', '?')} QScore={qscore:.4f} "
        f"(GlyphSQI={average_sqi:.3f}, Entropy={entropy:.3f}, Trust={trust:.3f})"
    )
    return beam_dict


# --- Internals ---

def _calculate_qscore(entropy: float, trust: float, depth: int, glyph_sqi: float) -> float:
    """
    Heuristic scoring formula.
    """
    try:
        depth_score = min(depth / 12.0, 1.0)
        qscore = (entropy * 0.25) + (trust * 0.25) + (depth_score * 0.2) + (glyph_sqi * 0.3)
        return round(min(max(qscore, 0.0), 1.0), 4)
    except Exception as e:
        logger.error(f"[QScoreHooks] QScore computation failed: {e}")
        return 0.0


def _score_relevant_glyphs(glyphs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Score glyphs of interest (currently type='electron') using `sqi_scorer`.
    """
    scored = []
    for glyph in glyphs:
        if glyph.get("type") != "electron":
            continue
        try:
            score = score_electron_glyph(glyph)
            glyph["sqi_score"] = score
            scored.append({
                "id": glyph.get("id"),
                "label": glyph.get("label", ""),
                "score": score,
                "status": glyph.get("prediction", {}).get("status", "unknown")
            })
        except Exception as e:
            logger.warning(f"[QScoreHooks] Failed to score glyph {glyph.get('id')}: {e}")
    return scored


def _rate_qscore(score: float) -> str:
    """
    Symbolic tier rating for visualization.
    """
    if score >= 0.85:
        return "🌟 exceptional"
    elif score >= 0.65:
        return "✅ strong"
    elif score >= 0.45:
        return "🌀 moderate"
    elif score >= 0.25:
        return "⚠️ weak"
    else:
        return "❌ incoherent"


def _get_tree_depth(node: Dict[str, Any], current: int = 0) -> int:
    """
    Recursively calculate depth of symbolic logic tree.
    """
    try:
        children = node.get("children", [])
        if not children:
            return current
        return max(_get_tree_depth(c, current + 1) for c in children if isinstance(c, dict))
    except Exception as e:
        logger.warning(f"[QScoreHooks] Tree depth calc failed: {e}")
        return current