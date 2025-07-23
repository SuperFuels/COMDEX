# File: backend/modules/websocket_manager.py

from fastapi import WebSocket
from typing import List, Dict, Any, Optional
from collections import defaultdict
import asyncio
import json

class WebSocketClient:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.tags: set[str] = set()
        self.extra_filters: Dict[str, Any] = {}

class WebSocketManager:
    def __init__(self):
        self.clients: List[WebSocketClient] = []
        self.tag_map: Dict[str, List[WebSocketClient]] = defaultdict(list)

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        client = WebSocketClient(websocket)
        self.clients.append(client)
        print(f"[🔌] WebSocket connected: {len(self.clients)} clients")

    def disconnect(self, websocket: WebSocket):
        client = next((c for c in self.clients if c.websocket == websocket), None)
        if client:
            self.clients.remove(client)
            for tag in client.tags:
                if client in self.tag_map[tag]:
                    self.tag_map[tag].remove(client)
            print(f"[⚡] WebSocket disconnected: {len(self.clients)} clients")

    async def subscribe(self, websocket: WebSocket, tag: str, filters: Optional[Dict[str, Any]] = None):
        client = next((c for c in self.clients if c.websocket == websocket), None)
        if client:
            client.tags.add(tag)
            self.tag_map[tag].append(client)
            if filters:
                client.extra_filters = filters
            print(f"[📡] Subscribed client to tag: {tag} with filters: {filters or '{}'}")

    async def unsubscribe(self, websocket: WebSocket, tag: str):
        client = next((c for c in self.clients if c.websocket == websocket), None)
        if client and tag in client.tags:
            client.tags.remove(tag)
            if client in self.tag_map[tag]:
                self.tag_map[tag].remove(client)
            print(f"[❌] Unsubscribed client from tag: {tag}")

    async def broadcast(self, message: Dict[str, Any], tag: Optional[str] = None, origin_id: Optional[str] = None):
        """
        Send a message to all clients or to a subset based on tag and filter.
        """
        target_clients = self.tag_map[tag] if tag else self.clients
        print(f"[📣] Broadcasting to {len(target_clients)} clients {'on tag: ' + tag if tag else '(global)'}")

        for client in target_clients:
            try:
                # Filter matching logic
                filters = client.extra_filters
                if filters:
                    if "symbol" in filters and filters["symbol"] != message.get("symbol"):
                        continue
                    if "target" in filters and filters["target"] != message.get("meta", {}).get("container"):
                        continue

                enriched_msg = message.copy()
                if origin_id:
                    enriched_msg["origin"] = origin_id
                await client.websocket.send_text(json.dumps(enriched_msg))
            except Exception as e:
                print(f"[⚠️] Failed to send WebSocket message: {e}")

# ✅ Singleton instance for global use
websocket_manager = WebSocketManager()