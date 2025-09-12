import asyncio
import inspect
from typing import Dict, Any, List, Union
from fastapi import WebSocket
from backend.modules.websocket_manager import websocket_manager

# 🌐 Track container-specific sockets (live sync)
active_qfc_sockets: Dict[str, WebSocket] = {}

# 🔐 Safe coercion for hashable/loggable source values
def coerce_source(value: Any) -> str:
    try:
        if isinstance(value, (dict, list)):
            return f"invalid_source_{hash(str(value))}"
        return str(value)
    except Exception:
        return f"invalid_source_{id(value)}"

# 📡 Broadcast QFC update to all connected clients (via websocket_manager)
async def send_qfc_update(render_packet: Dict[str, Any]) -> None:
    """
    Send a symbolic update to all connected QFC WebSocket clients.

    Args:
        render_packet (Dict[str, Any]): Data payload containing QWave beams, glyphs, etc.
    """
    try:
        source = coerce_source(render_packet.get("source", "unknown"))

        await websocket_manager.broadcast("qfc_update", {
            "type": "qfc_update",
            "source": source,
            "payload": render_packet.get("payload", {}),
        })
        print("🚀 QFC WebSocket update broadcasted.")
    except Exception as e:
        print(f"❌ Failed to broadcast QFC update: {e}")

# 🧠 Register live QFC sync socket for a specific container
async def register_qfc_socket(container_id: str, websocket: WebSocket):
    await websocket.accept()
    active_qfc_sockets[container_id] = websocket
    print(f"🔌 WebSocket registered for QFC container: {container_id}")

# ❌ Unregister QFC sync socket
async def unregister_qfc_socket(container_id: str):
    if container_id in active_qfc_sockets:
        del active_qfc_sockets[container_id]
        print(f"🛑 WebSocket unregistered for QFC container: {container_id}")

# 🛰️ Targeted container sync broadcast
async def broadcast_qfc_update(container_id: str, payload: Dict[str, Any]):
    """
    Send live QFC sync update to a specific container WebSocket.
    """
    socket = active_qfc_sockets.get(container_id)
    if socket:
        try:
            await socket.send_json({
                "type": "qfc_update",
                "source": "container_sync",
                "payload": payload,
            })
            print(f"📡 Live sync update sent to container: {container_id}")
        except Exception as e:
            print(f"❌ Failed to send live QFC sync: {e}")

# ───────────────────────────────────────────────
# ✅ Async-compatible fire-and-forget dispatcher
# ───────────────────────────────────────────────

def _is_coroutine_fn(fn):
    return inspect.iscoroutinefunction(fn)

def safe_fire_and_forget(coro_or_fn, *args, **kwargs):
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
    This bypasses container-specific WebSocket and goes to all clients via `send_qfc_update`.
    """
    if not isinstance(payload, list):
        payload = [payload]

    message = {
        "source": f"container::{container_id}",
        "payload": {
            "updates": payload,
            "type": "qfc_stream"
        }
    }

    safe_fire_and_forget(send_qfc_update, message)