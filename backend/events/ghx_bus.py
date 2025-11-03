from typing import Dict, Set
from starlette.websockets import WebSocket

_connections: Dict[str, Set[WebSocket]] = {}

def attach(container_id: str, ws: WebSocket) -> None:
    _connections.setdefault(container_id, set()).add(ws)

def detach(container_id: str, ws: WebSocket) -> None:
    _connections.get(container_id, set()).discard(ws)

async def broadcast(container_id: str, message: dict) -> None:
    dead = []
    for ws in list(_connections.get(container_id, set())):
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        detach(container_id, ws)