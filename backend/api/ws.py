# File: backend/api/ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.modules.consciousness.state_manager import StateManager
import json
import asyncio
from typing import Set, Any, Dict

router = APIRouter()

# -----------------------------
# Existing: container WS clients
# -----------------------------
clients = []  # keep name to avoid breaking any imports elsewhere


@router.websocket("/ws/containers")
async def container_ws(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            state = StateManager()
            containers = state.list_containers_with_status()
            await websocket.send_text(json.dumps({"containers": containers}))
            await asyncio.sleep(10)
    except Exception:
        # preserve existing behavior (broad catch) but avoid crash on double-remove
        try:
            clients.remove(websocket)
        except ValueError:
            pass


# -----------------------------
# New: QFC WS clients + helpers
# -----------------------------
QFC_CLIENTS: Set[WebSocket] = set()


@router.websocket("/ws/qfc")
async def qfc_ws(websocket: WebSocket):
    """
    Frontend connects here: ws(s)://<host>/ws/qfc

    We keep the socket open and optionally accept inbound messages (hello/prefs),
    but we don't require the client to continuously send anything.
    """
    await websocket.accept()
    QFC_CLIENTS.add(websocket)

    try:
        while True:
            # If the client sends messages (e.g. "hello"), we can read them.
            # If it doesn't, this will just wait, keeping the socket open.
            _msg = await websocket.receive_text()
            # Optional: you can parse/handle hello/prefs here later
            # try:
            #     data = json.loads(_msg)
            # except Exception:
            #     data = None

    except WebSocketDisconnect:
        pass
    except Exception:
        # keep robust; don't kill server if a client is weird
        pass
    finally:
        QFC_CLIENTS.discard(websocket)


async def broadcast_qfc(payload: Dict[str, Any]) -> None:
    """
    Call this from anywhere (async context) to push a frame/meta to all QFC HUD clients.

    Example payload:
      {"t": 1, "kappa": 0.1, "chi": 0.2, ...}
    """
    if not QFC_CLIENTS:
        return

    msg = json.dumps(payload, default=str)
    dead = []

    for ws in list(QFC_CLIENTS):
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)

    for ws in dead:
        QFC_CLIENTS.discard(ws)


def broadcast_qfc_sync(payload: Dict[str, Any]) -> None:
    """
    Convenience wrapper if you’re in non-async code.
    Schedules the async broadcast on the running event loop.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(broadcast_qfc(payload))