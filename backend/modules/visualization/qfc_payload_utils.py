import logging
logger = logging.getLogger(__name__)

def serialize_beam_payload(beam):
    logger.debug("[qfc_payload_utils] Stubbed serialize_beam_payload() called.")
    return {
        "id": getattr(beam, "id", None),
        "status": getattr(beam, "status", "unknown")
    }

def to_qfc_payload(*args, **kwargs) -> dict:
    """Converts glyph or beam to QFC broadcast-friendly payload."""
    if len(args) == 1:
        glyph = args[0]
    elif len(args) >= 2:
        glyph = args[1]
    else:
        glyph = kwargs.get("glyph", {})

    if not isinstance(glyph, dict):
        logger.warning(f"[qfc_payload_utils] Expected dict, got {type(glyph)} — using empty payload.")
        glyph = {}

    return {
        "id": glyph.get("id"),
        "type": glyph.get("type", "glyph"),
        "tags": glyph.get("tags", []),
        "hash": glyph.get("hash"),
        "timestamp": glyph.get("timestamp"),
        "status": glyph.get("status", "ok"),
        "meta": glyph.get("meta", {})
    }