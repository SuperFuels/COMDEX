# File: backend/modules/sci/qfc_ws_broadcaster.py

import time
import logging
from typing import Dict, Any, Optional

from backend.modules.codex.codex_websocket_interface import send_codex_ws_event

logger = logging.getLogger(__name__)

DEFAULT_QFC_BROADCAST_EVENT = "qfc_field_update"


def _safe_list(v: Any) -> list:
    return v if isinstance(v, list) else []


def _safe_dict(v: Any) -> dict:
    return v if isinstance(v, dict) else {}


def _extract_container_id(field_state: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Try multiple common shapes:
      - metadata.container_id
      - field_state.container_id
      - field_state.context.container_id
      - field_state.metadata.context.container_id
    """
    if isinstance(metadata, dict):
        cid = metadata.get("container_id")
        if isinstance(cid, str) and cid:
            return cid

    cid2 = field_state.get("container_id")
    if isinstance(cid2, str) and cid2:
        return cid2

    ctx = field_state.get("context")
    if isinstance(ctx, dict):
        cid3 = ctx.get("container_id")
        if isinstance(cid3, str) and cid3:
            return cid3

    meta = field_state.get("metadata")
    if isinstance(meta, dict) and isinstance(meta.get("context"), dict):
        cid4 = meta["context"].get("container_id")
        if isinstance(cid4, str) and cid4:
            return cid4

    return None


async def broadcast_qfc_state(
    field_state: Dict[str, Any],
    observer_id: Optional[str] = None,
    event_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    container_id: Optional[str] = None,
) -> None:
    """
    Broadcast QFC state over Codex websocket.

    IMPORTANT:
      send_codex_ws_event signature is:
        send_codex_ws_event(event_type: str, payload: dict)
      so we must pass TWO args.
    """
    event = event_type or DEFAULT_QFC_BROADCAST_EVENT
    obs = observer_id or "anonymous"
    cid = container_id or _extract_container_id(field_state, metadata) or "unknown"

    # Canonical UI payload
    data: Dict[str, Any] = {
        "observer_id": obs,
        "nodes": _safe_list(field_state.get("nodes")),
        "links": _safe_list(field_state.get("links")),
        "glyphs": _safe_list(field_state.get("glyphs")),
        "scrolls": _safe_list(field_state.get("scrolls")),
        "qwaveBeams": _safe_list(field_state.get("qwaveBeams")),
        "entanglement": _safe_dict(field_state.get("entanglement")),
        "sqi_metrics": _safe_dict(field_state.get("sqi_metrics")),
        "camera": _safe_dict(field_state.get("camera")),
        "tags": _safe_list(field_state.get("reflection_tags")),
    }

    if isinstance(metadata, dict) and metadata:
        data["metadata"] = dict(metadata)

    # Packet wrapper (routing + backwards compatibility)
    packet: Dict[str, Any] = {
        "event": event,
        "container_id": cid,
        "observer_id": obs,
        "data": data,
        "timestamp": time.time(),
    }

    try:
        await send_codex_ws_event(event, packet)
        if getattr(logger, "debug", None):
            logger.debug(f"[QFC] broadcast event={event} observer={obs} container={cid}")
        else:
            print(f"📡 Broadcasted QFC '{event}' for observer: {obs} | container: {cid}")
    except Exception as e:
        logger.warning(f"[QFC] broadcast failed event={event} container={cid}: {e}")


async def broadcast_qfc_tick_update(
    tick_id: int,
    frame_state: Dict[str, Any],
    observer_id: Optional[str] = None,
    total_ticks: Optional[int] = None,
    source: Optional[str] = None,
    container_id: Optional[str] = None,
) -> None:
    """
    Broadcast a single QFC tick/frame update during replay/execution.
    """
    meta: Dict[str, Any] = {
        "tick": tick_id,
        "total_ticks": total_ticks,
        "source": source or "replay",
        "timestamp": time.time(),
    }

    await broadcast_qfc_state(
        field_state=frame_state,
        observer_id=observer_id,
        event_type="qfc_sync_tick",
        metadata=meta,
        container_id=container_id,
    )