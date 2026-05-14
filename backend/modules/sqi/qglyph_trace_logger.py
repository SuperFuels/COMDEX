# File: backend/modules/sqi/qglyph_trace_logger.py

import time
import logging
from typing import Optional, Dict

from ..hexcore.memory_engine import store_memory

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Optional config + safe GHX logging (won't fail if unavailable)
# ─────────────────────────────────────────────────────────────────────────────
try:
    from backend.config import ENABLE_GLYPH_LOGGING
except Exception:
    ENABLE_GLYPH_LOGGING = True

try:
    from backend.modules.hologram.ghx_logging import safe_ghx_log
except Exception:
    def safe_ghx_log(ghx, evt):
        try:
            import logging as _logging
            _logging.debug("[GHX][safe_ghx_log-fallback] %s", evt)
        except Exception:
            pass

# Lazy import helpers to avoid circular deps
def _get_broadcast_event():
    try:
        from backend.routes.ws.glyphnet_ws import broadcast_event
        return broadcast_event
    except Exception:
        return None

def _ingest_kg_event(payload: dict) -> None:
    try:
        from backend.modules.knowledge_graph.knowledge_bus_adapter import ingest_bus_event
        ingest_bus_event(payload)
    except Exception:
        # Knowledge bus not wired yet - ignore silently
        pass


def log_qglyph_resolution(
    qglyph_id: str,
    observer_id: Optional[str],
    bias_score_left: float,
    bias_score_right: float,
    chosen_path: str,
    reason: Optional[str] = None,
    meta: Optional[Dict] = None
):
    """
    Logs a QGlyph collapse decision with observer bias and reasoning.
    Stores to memory engine and console log.

    Upgrades:
      * Adds iso_time
      * Best-effort broadcast over glyphnet_ws (if available)
      * Writes a normalized KnowledgeIndex event (if adapter available)
      * Safe GHX trace hook (guarded by ENABLE_GLYPH_LOGGING)
    """
    timestamp = int(time.time())
    iso_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    trace = {
        "type": "qglyph_collapse_trace",
        "timestamp": timestamp,
        "iso_time": iso_time,  # ✅ new, non-breaking
        "qglyph_id": qglyph_id,
        "observer_id": observer_id,
        "bias_left": bias_score_left,
        "bias_right": bias_score_right,
        "chosen_path": chosen_path,
        "reason": reason or "",
        "meta": meta or {},
    }

    # Store in memory system for retrieval or review (original behavior)
    store_memory(trace)

    # Console log for monitoring (original behavior)
    logger.info(
        f"[QGlyph Collapse] ID: {qglyph_id} by {observer_id or 'Unknown'} -> {chosen_path} "
        f"(L:{bias_score_left:.2f}, R:{bias_score_right:.2f}) Reason: {reason}"
    )

    # 🔎 Safe GHX log hook (optional, never raises)
    if ENABLE_GLYPH_LOGGING:
        safe_ghx_log(
            ghx=None,
            evt={
                "event": "qglyph_collapse",
                "qglyph_id": qglyph_id,
                "observer_id": observer_id,
                "chosen_path": chosen_path,
                "bias_left": bias_score_left,
                "bias_right": bias_score_right,
                "iso_time": iso_time,
            },
        )

    # 🛰️ Optional: broadcast to WS subscribers (if glyphnet_ws is wired)
    try:
        broadcast_event = _get_broadcast_event()
        if broadcast_event:
            payload = {
                "type": "qglyph_collapse_trace",
                "qglyph_id": qglyph_id,
                "observer_id": observer_id,
                "chosen_path": chosen_path,
                "bias_left": bias_score_left,
                "bias_right": bias_score_right,
                "iso_time": iso_time,
                "meta": meta or {},
            }
            # fire-and-forget (caller context may be sync)
            try:
                # If in async loop, caller can schedule; if not, just call
                broadcast_event(payload)  # function itself can be async-aware
            except TypeError:
                # If coroutine, ignore here; upstream may wrap with create_task
                pass
    except Exception as _e:
        logger.debug(f"[qglyph_trace_logger] Broadcast skipped: {_e}")

    # 📦 Optional: normalize into KnowledgeIndex via bus adapter
    try:
        container_id = (meta or {}).get("container_id", "ucs_ephemeral")
        external_hash = (meta or {}).get("hash")  # if you already carry a content hash
        kg_payload = {
            "container_id": container_id,
            "entry": {
                "id": qglyph_id,
                "hash": external_hash,  # can be None; adapter will fall back
                "type": "qglyph_collapse",
                "timestamp": iso_time,
                "tags": ["⧖", "collapse", "qglyph"],
                "plugin": (meta or {}).get("plugin"),
            },
        }
        _ingest_kg_event(kg_payload)
    except Exception as _e:
        logger.debug(f"[qglyph_trace_logger] KG ingest skipped: {_e}")

    return trace