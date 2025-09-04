# backend/modules/glyphwave/qkd/qkd_logger.py

import datetime
from typing import Optional, Dict

# ✅ Import hooks for logging and KG writing
from backend.modules.dimensions.ucs.zones.experiments.hyperdrive.hyperdrive_control_panel.modules.sqi_reasoning_module import log_sqi_event
from backend.modules.knowledge_graph.kg_writer_singleton import write_glyph_event

# Optional future import for GHX replay hooks or CodexMetrics
# from backend.modules.codex.metrics.codex_metrics import record_metric


def _now_iso():
    return datetime.datetime.now(datetime.UTC).isoformat()


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
    log_sqi_event(event)

    # ✅ Log to Knowledge Graph as symbolic triple
    # Format: [QKDExchange] --[status]--> [Receiver]
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

    # ✅ Use correct writer function from kg_writer_singleton
    write_glyph_event(
        event_type="qkd_event",
        event=triple,
        container_id=None  # You can optionally pass a container_id if context is available
    )

    # ✅ Optionally broadcast to HUDs, replay, metrics (future)
    # if status == "tamper":
    #     record_metric("qkd_tamper_detected", wave_id=wave_id)

    return event  # For tracing/debugging