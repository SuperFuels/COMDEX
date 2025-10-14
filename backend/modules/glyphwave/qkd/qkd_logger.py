# backend/modules/glyphwave/qkd/qkd_logger.py

import datetime
from typing import Optional, Dict

# ────────────────────────────────────────────────────────────────
# ✅ Safe import hooks with graceful fallbacks for testing
# ----------------------------------------------------------------
try:
    from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.sqi_reasoning_module import log_sqi_event
except ImportError:
    def log_sqi_event(event):
        """Fallback SQI logger for test environments."""
        print(f"[MOCK:SQI] QKD Event → {event}")

try:
    from backend.modules.knowledge_graph.kg_writer_singleton import write_glyph_event
except ImportError:
    def write_glyph_event(event_type, event, container_id=None):
        """Fallback KG writer for test environments."""
        print(f"[MOCK:KG] {event_type} :: {event}")
        return {"mocked": True, "event": event}

# Optional future import for GHX replay hooks or CodexMetrics
# from backend.modules.codex.metrics.codex_metrics import record_metric


# ────────────────────────────────────────────────────────────────
def _now_iso() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.datetime.now(datetime.UTC).isoformat()


# ────────────────────────────────────────────────────────────────
def log_qkd_event(
    sender_id: str,
    receiver_id: str,
    wave_id: str,
    status: str,  # e.g. 'success', 'tamper', 'timeout', 'fingerprint_mismatch'
    detail: Optional[str] = None,
    collapse_hash: Optional[str] = None,
    fingerprint: Optional[str] = None,
) -> Dict:
    """
    Log a QKD event to SQI and the Knowledge Graph.

    • Always writes to SQI reasoning pipeline if available.
    • Gracefully degrades to stdout during isolated tests.
    • Produces a structured triple for KG ingestion.
    """

    # ✅ Compose log payload
    event = {
        "type": "qkd_event",
        "timestamp": _now_iso(),
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "wave_id": wave_id,
        "status": status,
        "detail": detail,
        "collapse_hash": collapse_hash,
        "fingerprint": fingerprint,
    }

    # ✅ Log to SQI Reasoning Engine
    try:
        log_sqi_event(event)
    except Exception as e:
        print(f"[QKD_LOGGER] ⚠ Failed SQI log: {e}")

    # ✅ Build symbolic triple for KG integration
    triple = {
        "subject": f"QKDExchange:{wave_id}",
        "predicate": f"qkd:{status}",
        "object": f"Agent:{receiver_id}",
        "metadata": {
            "sender": sender_id,
            "timestamp": event["timestamp"],
            "collapse_hash": collapse_hash,
            "fingerprint": fingerprint,
            "detail": detail,
        },
    }

    # ✅ Attempt to write to Knowledge Graph (safe fail)
    try:
        write_glyph_event(
            event_type="qkd_event",
            event=triple,
            container_id=None  # Optional context container
        )
    except Exception as e:
        print(f"[QKD_LOGGER] ⚠ KG write failed: {e}")

    # ✅ Return structured event for debugging or audit trails
    return event