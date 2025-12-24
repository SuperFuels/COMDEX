# File: backend/modules/visualization/qfc_websocket_bridge.py

import asyncio
import inspect
from typing import Any, Dict, List, Optional, Union

from fastapi import WebSocket

from backend.modules.websocket_manager import websocket_manager

# 🌐 Track container-specific sockets (live sync)
active_qfc_sockets: Dict[str, WebSocket] = {}


# 🔐 Safe coercion for hashable/loggable source values
def coerce_source(value: Any) -> str:
    """
    Convert any value to a string suitable for source tagging.
    Falls back to hash/id for non-serializable objects.
    """
    try:
        if isinstance(value, (dict, list)):
            return f"invalid_source_{hash(str(value))}"
        return str(value)
    except Exception:
        return f"invalid_source_{id(value)}"


def _safe_dict(v: Any) -> Dict[str, Any]:
    return v if isinstance(v, dict) else {}


def _extract_container_id(field_state: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Best-effort container_id extraction, matching the shapes seen in QQC logs + field packets.
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


# 📡 Broadcast QFC update to all connected clients (via websocket_manager)
async def send_qfc_update(render_packet: Dict[str, Any]) -> None:
    """
    Send a symbolic update to all connected QFC WebSocket clients.

    Args:
        render_packet (Dict[str, Any]): Data payload containing QWave beams, glyphs, etc.
    """
    try:
        source = coerce_source(render_packet.get("source", "unknown"))

        payload = {
            "type": "qfc_update",
            "source": source,
            "payload": _safe_dict(render_packet.get("payload", {})),
        }

        # ✅ Correct argument order: message first, then tag via keyword
        await websocket_manager.broadcast(payload, tag="qfc_update")
        # keep print for existing dev logs
        print("🚀 QFC WebSocket update broadcasted.")
    except Exception as e:
        print(f"❌ Failed to broadcast QFC update: {e}")


# 🧠 Register live QFC sync socket for a specific container
async def register_qfc_socket(container_id: str, websocket: WebSocket):
    """
    Accepts a WebSocket and registers it to a specific container ID.
    """
    await websocket.accept()
    active_qfc_sockets[container_id] = websocket
    print(f"🔌 WebSocket registered for QFC container: {container_id}")


# ❌ Unregister QFC sync socket
async def unregister_qfc_socket(container_id: str):
    if container_id in active_qfc_sockets:
        del active_qfc_sockets[container_id]
        print(f"🛑 WebSocket unregistered for QFC container: {container_id}")


async def _broadcast_container_sync(
    container_id: str,
    payload: Dict[str, Any],
    observer_id: Optional[str] = None,
    source: Optional[str] = None,
    **_kwargs: Any,
) -> None:
    """
    Internal: Send live QFC sync update to a specific container WebSocket.

    Compatible with callers that pass extra kwargs (e.g. observer_id/source).
    """
    socket = active_qfc_sockets.get(container_id)
    if not socket:
        return

    try:
        await socket.send_json(
            {
                "type": "qfc_update",
                # preserve old default ("container_sync"), but allow caller override
                "source": source or (observer_id or "container_sync"),
                "payload": _safe_dict(payload),
            }
        )
        print(f"📡 Live sync update sent to container: {container_id}")
    except Exception as e:
        print(f"❌ Failed to send live QFC sync: {e}")


def _is_coroutine_fn(fn: Any) -> bool:
    return inspect.iscoroutinefunction(fn)


def safe_fire_and_forget(coro_or_fn, *args, **kwargs):
    """
    Execute a coroutine or function safely without awaiting.
    Falls back to asyncio.run if no running loop exists.
    """
    try:
        if _is_coroutine_fn(coro_or_fn):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(coro_or_fn(*args, **kwargs))
            except RuntimeError:
                asyncio.run(coro_or_fn(*args, **kwargs))
        else:
            coro_or_fn(*args, **kwargs)
    except Exception as e:
        print(f"⚠️ QFC Bridge fallback dispatch failed: {e}")


# 🌈 Stream symbolic beam updates to all clients (non-container specific)
def broadcast_qfc_beams(container_id: str, payload: Union[Dict[str, Any], List[Dict[str, Any]]]):
    """
    Broadcast multi-packet QFC visual data (e.g. QWave beams, traces) to the frontend.
    Bypasses container-specific WebSocket and goes to all clients via `send_qfc_update`.
    """
    if not isinstance(payload, list):
        payload = [payload]

    message = {
        "source": f"container::{container_id}",
        "payload": {
            "updates": payload,
            "type": "qfc_stream",
        },
    }

    safe_fire_and_forget(send_qfc_update, message)


# ───────────────────────────────────────────────
# 🛠 Optional helper: broadcast QPU / CPU metrics live
# ───────────────────────────────────────────────
def broadcast_cpu_qpu_metrics(container_id: str, metrics: Dict[str, Any], cpu: bool = False):
    """
    Send CPU or QPU benchmark / execution metrics to frontend.
    """
    metric_type = "cpu_metrics" if cpu else "qpu_metrics"
    payload = {
        "type": metric_type,
        "metrics": metrics,
    }
    safe_fire_and_forget(broadcast_qfc_beams, container_id, payload)


# ───────────────────────────────────────────────
# ✅ Main bridge entrypoint (BACKWARD + FORWARD compatible)
# ───────────────────────────────────────────────
async def broadcast_qfc_update(*args: Any, **kwargs: Any):
    """
    Backward compatible AND forward compatible entrypoint.

    Supports legacy live-sync:
        await broadcast_qfc_update(container_id: str, payload: Dict[str, Any])

    Supports newer callers (Codex hooks):
        await broadcast_qfc_update(
            field_state=Dict[str, Any],
            observer_id=str,
            event_type=str,
            metadata=Dict[str, Any],
            container_id=str,
        )

    New-style routes to backend.modules.sci.qfc_ws_broadcaster.broadcast_qfc_state
    so you keep the Codex WS event pipeline consistent.
    """

    # -----------------------------
    # New-style detection
    # -----------------------------
    field_state = kwargs.get("field_state")
    if field_state is None and len(args) >= 1 and isinstance(args[0], dict):
        # allow: broadcast_qfc_update(field_state_dict, observer_id="x", ...)
        field_state = args[0]

    if isinstance(field_state, dict):
        observer_id = kwargs.get("observer_id")
        event_type = kwargs.get("event_type")
        metadata = kwargs.get("metadata")
        container_id = kwargs.get("container_id")

        if not isinstance(observer_id, str) or not observer_id:
            observer_id = None
        if not isinstance(event_type, str) or not event_type:
            event_type = None
        if not isinstance(metadata, dict):
            metadata = None
        if not isinstance(container_id, str) or not container_id:
            container_id = _extract_container_id(field_state, metadata)

        # Prefer the canonical broadcaster (Codex WS event pipeline)
        try:
            from backend.modules.sci.qfc_ws_broadcaster import broadcast_qfc_state  # lazy import
            await broadcast_qfc_state(
                field_state=field_state,
                observer_id=observer_id,
                event_type=event_type,
                metadata=metadata,
                container_id=container_id,
            )
            return
        except Exception as e:
            # Fallback: still get *something* to the UI if sci module isn't available
            try:
                cid = container_id or "unknown"
                broadcast_qfc_beams(
                    cid,
                    {
                        "type": "qfc_field_update",
                        "observer_id": observer_id or "anonymous",
                        "event_type": event_type or "qfc_field_update",
                        "metadata": metadata or {},
                        "field_state": field_state,
                    },
                )
            except Exception:
                pass
            print(f"⚠️ QFC bridge: broadcast_qfc_state failed (fallback used): {e}")
            return

    # -----------------------------
    # Legacy live-sync path
    # -----------------------------
    container_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    observer_id: Optional[str] = None
    source: Optional[str] = None

    if len(args) >= 2 and isinstance(args[0], str) and isinstance(args[1], dict):
        container_id, payload = args[0], args[1]
        # tolerate legacy callers passing (container_id, payload, observer_id=?)
        if len(args) >= 3 and isinstance(args[2], str):
            observer_id = args[2]
    else:
        cid = kwargs.get("container_id")
        pl = kwargs.get("payload")
        if isinstance(cid, str) and isinstance(pl, dict):
            container_id, payload = cid, pl

    if isinstance(kwargs.get("observer_id"), str):
        observer_id = kwargs["observer_id"]
    if isinstance(kwargs.get("source"), str):
        source = kwargs["source"]

    if container_id and isinstance(payload, dict):
        await _broadcast_container_sync(
            container_id,
            payload,
            observer_id=observer_id,
            source=source,
            **kwargs,
        )
        return

    # If we got called with something weird, just no-op (this should never crash callers).
    return