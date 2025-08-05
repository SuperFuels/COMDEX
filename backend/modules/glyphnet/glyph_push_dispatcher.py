import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# ✅ Glyph Push Dispatcher
def dispatch_glyph_push(event: Dict[str, Any]):
    """
    Handles dispatching glyph push packets to GlyphNet.
    This is a compatibility shim to satisfy legacy imports.
    """
    try:
        # Lazy import WebSocket broadcaster to avoid circular dependency
        from backend.routes.ws.glyphnet_ws import broadcast_event

        glyph_id = event.get("glyph", "unknown")
        logger.info(f"[GlyphPush] Dispatching glyph push: {glyph_id}")

        # Broadcast the event via GlyphNet WebSocket
        broadcast_event("glyph_push", event)

    except Exception as e:
        logger.error(f"[GlyphPushDispatcher] Failed to dispatch glyph push: {e}")