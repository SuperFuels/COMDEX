# 📄 symbolic_utils.py
#
# 🧩 Symbolic Utilities Module
# Core utilities for symbolic reasoning, glyph tracing, causal chain reconstruction,
# entropy scoring, and gradient feedback analysis for IGI/AION systems.
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ✅ Causal Chain Reconstruction for Glyph Failures (⮌)
# ✅ Glyph Event Normalization (Dict ↔ GlyphEvent)
# ✅ Entropy & Confidence Scoring Utilities
# ✅ Trace Linking for KG and Entanglement Feedback
# ✅ Vector Distance Metrics for Goal Drift Analysis
# ✅ Safe Fallbacks for Missing Metadata or Containers
# ✅ Logging Hooks for Debugging Symbolic Flows
# ✅ Future-ready for Holographic & QGlyph integrations
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import logging
from typing import List, Dict, Union, Any
from backend.modules.codex.codex_metrics import CodexMetrics

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# 🔄 Normalize GlyphEvent Input
# ──────────────────────────────────────────────
def normalize_glyph_event(glyph: Union["GlyphEvent", Dict[str, Any]]) -> Dict[str, Any]:
    """
    Normalize a GlyphEvent object or dict into a consistent dict format.
    Ensures compatibility with KG, gradient engine, and tracing utils.
    """
    if not glyph:
        return {}

    if hasattr(glyph, "__dict__"):  # Likely a GlyphEvent object
        glyph_dict = {k: v for k, v in glyph.__dict__.items()}
    elif isinstance(glyph, dict):
        glyph_dict = glyph.copy()
    else:
        logger.warning(f"[symbolic_utils] Unexpected glyph type: {type(glyph)}")
        return {}

    # Ensure mandatory fields exist
    glyph_dict.setdefault("id", glyph_dict.get("glyph_id", "unknown"))
    glyph_dict.setdefault("container_id", glyph_dict.get("container", "unknown"))
    glyph_dict.setdefault("entropy", glyph_dict.get("entropy", 0.0))
    glyph_dict.setdefault("confidence", glyph_dict.get("confidence", 0.5))
    glyph_dict.setdefault("operator", glyph_dict.get("operator", "?"))

    return glyph_dict


# ──────────────────────────────────────────────
# ⮌ Trace Back Causal Chain
# ──────────────────────────────────────────────
def trace_back_causal_chain(failed_glyph: Union["GlyphEvent", Dict[str, Any]], depth: int = 5) -> List[Dict[str, Any]]:
    """
    Trace backward through the glyph trace log to identify causal ancestry.
    Returns up to `depth` previous glyphs leading to this failure.
    """
    from backend.modules.glyphos.glyph_trace_logger import glyph_trace  # 🔁 Lazy import to avoid circular import

    normalized_failed = normalize_glyph_event(failed_glyph)
    container_id = normalized_failed.get("container_id", "unknown")
    glyph_id = normalized_failed.get("id", "unknown")

    logger.info(f"[symbolic_utils] Tracing causal chain for glyph {glyph_id} in container {container_id}")

    trace = glyph_trace.get_trace_for_container(container_id)
    if not trace:
        logger.warning(f"[symbolic_utils] No trace found for container {container_id}")
        return [normalized_failed]

    # Locate the index of the failed glyph in the trace
    index = next((i for i, g in enumerate(trace) if g.get("id") == glyph_id), None)
    if index is None:
        logger.warning(f"[symbolic_utils] Glyph {glyph_id} not found in trace for container {container_id}")
        return [normalized_failed]

    # Extract causal chain
    causal_chain = trace[max(0, index - depth): index]
    logger.debug(f"[symbolic_utils] Causal chain length: {len(causal_chain)}")

    # Normalize all glyphs
    return [normalize_glyph_event(g) for g in causal_chain]


# ──────────────────────────────────────────────
# 🎯 Entropy & Confidence Scoring
# ──────────────────────────────────────────────
def compute_entropy_confidence_score(glyph: Union["GlyphEvent", Dict[str, Any]]) -> float:
    """
    Computes a simple combined entropy-confidence score.
    Lower entropy and higher confidence yield higher positive scores.
    """
    g = normalize_glyph_event(glyph)
    entropy = g.get("entropy", 0.0)
    confidence = g.get("confidence", 0.5)
    return round((confidence - entropy), 4)


# ──────────────────────────────────────────────
# 🧭 Vector Distance Utility (Goal Drift)
# ──────────────────────────────────────────────
def compute_vector_distance(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Computes Euclidean distance between two symbolic vectors.
    """
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        logger.warning("[symbolic_utils] Invalid vectors for distance computation.")
        return 0.0
    return sum((a - b) ** 2 for a, b in zip(vec_a, vec_b)) ** 0.5


# ──────────────────────────────────────────────
# 🔬 Blindspot Logging Hook
# ──────────────────────────────────────────────
def log_blindspot_event(glyph: Union["GlyphEvent", Dict[str, Any]], reason: str = "Unknown"):
    """
    Logs a blindspot event to CodexMetrics for later analysis.
    """
    metrics = CodexMetrics()
    normalized = normalize_glyph_event(glyph)
    logger.warning(f"[symbolic_utils] Blindspot detected: Glyph {normalized.get('id')} | Reason: {reason}")
    metrics.record_blindspot_event(normalized)


# ──────────────────────────────────────────────
# 🌌 Debug Utility: Print Glyph Chain
# ──────────────────────────────────────────────
def debug_print_glyph_chain(chain: List[Dict[str, Any]]):
    """
    Prints a readable debug view of a causal glyph chain.
    """
    logger.info("=== Glyph Causal Chain ===")
    for i, g in enumerate(chain):
        logger.info(f"Step {i+1}: {g.get('operator')} | ID={g.get('id')} | Confidence={g.get('confidence')} | Entropy={g.get('entropy')}")
    logger.info("===========================")

# ──────────────────────────────────────────────
# 🔠 Logic Expression Parser (-> sympy)
# ──────────────────────────────────────────────
import re
from sympy import sympify, Symbol
from backend.quant.qpy.compat_sympy_logic import qand, qor, qnot, qimplies, qequiv

def parse_logical_operators(expr: str):
    """
    Parses a string containing symbolic logic operators into a sympy logic expression.
    Supports standard and symbolic forms:
    ∧, ∨, ¬, ->, ↔, ->, ⇔
    """
    if not expr or not isinstance(expr, str):
        raise ValueError("Expected string input for logical expression.")

    replacements = {
        "∧": "&",
        "∨": "|",
        "¬": "~",
        "->": ">>",
        "->": ">>",
        "↔": "<<>>",
        "⇔": "<<>>",
    }

    # Replace all symbolic operators
    for symbol, repl in replacements.items():
        expr = expr.replace(symbol, repl)

    # Normalize spacing and symbols
    expr = expr.replace(" and ", " & ").replace(" or ", " | ").replace(" not ", " ~ ")
    expr = expr.replace("==", "<<>>")

    # Replace equivalence with proper sympy call
    if "<<" in expr and ">>" in expr:
        expr = re.sub(r"(.*?)<<>>(.*)", r"Equivalent(\1, \2)", expr)

    # Sanitize leftover symbols
    expr = expr.strip()

    try:
        parsed = sympify(expr, evaluate=True)
        return parsed
    except Exception as e:
        raise ValueError(f"Could not parse expression '{expr}': {e}")