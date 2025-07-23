# backend/modules/glyphnet/glyph_signal_reconstructor.py

import logging
from typing import Dict, Any, Optional

from backend.modules.glyphos.codexlang_translator import parse_codexlang_string
from backend.modules.codex.codex_trace import CodexTrace
from backend.modules.glyphos.glyph_synthesis_engine import suggest_repair_candidates

logger = logging.getLogger(__name__)


def reconstruct_gip_signal(packet: Dict[str, Any]) -> Dict[str, Any]:
    """
    Attempts to rebuild the symbolic signal logic from a partial or damaged .gip packet.
    """
    raw_content = packet.get("payload", "")
    sender = packet.get("sender", "unknown")

    if not raw_content:
        return {"status": "error", "message": "Missing payload for reconstruction"}

    try:
        # Try direct parse
        parsed = parse_codexlang_string(raw_content)
        return {
            "status": "ok",
            "reconstructed": parsed,
            "method": "direct",
            "confidence": 1.0,
        }
    except Exception:
        logger.info(f"[Reconstructor] Direct parse failed, running heuristic repair…")

    try:
        suggestions = suggest_repair_candidates(raw_content, max_attempts=5)
        if not suggestions:
            return {"status": "error", "message": "No repair path found"}

        best = suggestions[0]
        CodexTrace.log_event("reconstructed_signal", {
            "sender": sender,
            "original_fragment": raw_content,
            "reconstructed": best,
            "confidence": best.get("score", 0.0)
        })

        return {
            "status": "ok",
            "reconstructed": best.get("logic"),
            "method": "heuristic",
            "confidence": best.get("score", 0.0),
        }

    except Exception as e:
        logger.exception("[Reconstructor] Heuristic repair failed")
        return {"status": "error", "message": str(e)}