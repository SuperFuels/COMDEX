import json
import os
import uuid
import asyncio
from datetime import datetime
# 🔌 GHX Broadcast Hook for A8c Symbolic Ingestion
from backend.modules.qfield.qfc_utils import build_qfc_payload
from backend.modules.visualization.broadcast_qfc_update import broadcast_qfc_update


# Optional in-memory log (can be exposed for HUD, dev tools, etc.)
RECENT_BEAM_LOGS = []

# Path to the persistent trace log
BEAM_LOG_PATH = "logs/beam_traces.jsonl"  # Ensure this folder exists

def log_beam_prediction(beam_data: dict):
    """
    Log a QWave beam event for collapse trace, replay, or audit purposes.
    Appends to persistent .jsonl file and in-memory queue.

    Expected beam_data keys:
    - source (glyph or string)
    - target (glyph or string)
    - sqi_score (float)
    - innovation_score (float)
    - container_id (str)
    - tags (list)
    """

    log_entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": serialize_glyph(beam_data.get("source")),
        "target": serialize_glyph(beam_data.get("target")),
        "sqi_score": beam_data.get("sqi_score"),
        "innovation_score": beam_data.get("innovation_score"),
        "container_id": beam_data.get("container_id"),
        "tags": beam_data.get("tags", []),
        "type": "qwave_beam"
    }

    # 1. Add to in-memory buffer
    RECENT_BEAM_LOGS.append(log_entry)
    if len(RECENT_BEAM_LOGS) > 1000:
        RECENT_BEAM_LOGS.pop(0)

    # 2. Append to persistent log file
    os.makedirs(os.path.dirname(BEAM_LOG_PATH), exist_ok=True)
    with open(BEAM_LOG_PATH, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    # 3. Optional: Future WebSocket or GHX broadcast (not implemented here)
    # broadcast_beam_event(log_entry)

    return log_entry


def serialize_glyph(glyph):
    """
    Serialize a glyph object or ID into a dict for logging.
    """
    if glyph is None:
        return None
    if isinstance(glyph, str):
        return {"id": glyph}
    if isinstance(glyph, dict):
        return glyph
    if hasattr(glyph, "to_dict"):
        return glyph.to_dict()
    if hasattr(glyph, "id"):
        return {"id": glyph.id}
    return str(glyph)

def emit_qwave_beam(
    glyph_id: str,
    result: dict,
    source: str,
    context: dict,
    state: str = "ingested",
    metadata: dict = None
):
    """
    Emit a QWave beam (A8c telemetry) after symbolic ingestion or mutation.
    """

    packet = {
        "id": str(uuid.uuid4()),
        "type": "qwave_beam",
        "glyph_id": glyph_id,
        "source": source,
        "state": state,
        "timestamp": datetime.utcnow().isoformat(),
        "codex_lang": result.get("codex_lang"),
        "raw": result.get("raw"),
        "context": context or {},
        "metadata": metadata or {}
    }

    container_id = context.get("container_id", "unknown.dc")

    # Format into QFC payload
    qfc_payload = build_qfc_payload(
        {
            "glyph": "📡",
            "op": "emit_beam",
            "metadata": packet
        },
        context={"container_id": container_id}
    )

    try:
        asyncio.create_task(broadcast_qfc_update(container_id, qfc_payload))
    except RuntimeError:
        asyncio.run(broadcast_qfc_update(container_id, qfc_payload))