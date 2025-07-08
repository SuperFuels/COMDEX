# File: backend/api/ws.py
from fastapi import APIRouter, WebSocket
from backend.modules.consciousness.state_manager import StateManager
import json
import asyncio

router = APIRouter()

clients = []

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
        clients.remove(websocket)