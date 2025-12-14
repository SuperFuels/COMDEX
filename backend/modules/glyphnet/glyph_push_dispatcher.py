# File: backend/modules/glyphnet/glyph_push_dispatcher.py
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _fire_and_forget(coro) -> None:
    """Schedule a coroutine without blocking (safe for sync call sites)."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        # No running loop in this thread; run best-effort without crashing caller
        try:
            asyncio.run(coro)
        except Exception:
            pass


# ✅ Glyph Push Dispatcher
def dispatch_glyph_push(event: Dict[str, Any]) -> None:
    """
    Dispatch glyph push packets to GlyphNet.

    IMPORTANT:
      `backend.routes.ws.glyphnet_ws.broadcast_event` is async in this codebase.
      This dispatcher is a sync compatibility shim, so we schedule it without blocking.
    """
    try:
        # Lazy import to avoid circular dependency
        from backend.routes.ws.glyphnet_ws import broadcast_event  # async

        glyph_id = event.get("glyph", "unknown")
        logger.info(f"[GlyphPush] Dispatching glyph push: {glyph_id}")

        _fire_and_forget(broadcast_event("glyph_push", event))

    except Exception as e:
        logger.error(f"[GlyphPushDispatcher] Failed to dispatch glyph push: {e}")