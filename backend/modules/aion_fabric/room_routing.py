from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso


class TelevisionRoomRouter:
    """Mother-local registry and fail-closed plans for multiple television surfaces."""

    _lock = threading.RLock()

    def __init__(self, runtime_dir: str | Path) -> None:
        self.root = Path(runtime_dir) / "rooms"
        self.path = self.root / "televisions.json"
        self.handoff_path = self.root / "handoffs.json"
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _room_name(value: str) -> str:
        name = " ".join(str(value).split()).strip()[:60]
        if not name or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 '&-]*", name):
            raise ValueError("Enter a simple household room name")
        return name

    def _read(self, path: Path) -> list[Dict[str, Any]]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return [dict(item) for item in value if isinstance(item, dict)] if isinstance(value, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    @staticmethod
    def _write(path: Path, value: list[Dict[str, Any]]) -> None:
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(value))
        os.replace(temporary, path)

    def register(self, *, node_id: str, device_name: str, room_name: str = "Primary TV", endpoint: str = "", make_default: bool = False) -> Dict[str, Any]:
        if not str(node_id).startswith("node_"):
            raise ValueError("A Fabric television node is required")
        room = self._room_name(room_name)
        endpoint = str(endpoint).strip()[:255]
        with self._lock:
            televisions = self._read(self.path)
            duplicate = next((item for item in televisions if item.get("node_id") != node_id and str(item.get("room_name") or "").casefold() == room.casefold()), None)
            if duplicate:
                raise ValueError("That room already has a registered television")
            existing = next((item for item in televisions if item.get("node_id") == node_id), None)
            record = existing or {"registered_at": utc_now_iso()}
            record.update({
                "node_id": node_id,
                "device_name": " ".join(str(device_name).split())[:120],
                "room_name": room,
                "endpoint": endpoint,
                "default": bool(make_default or not televisions),
                "updated_at": utc_now_iso(),
            })
            if record["default"]:
                for item in televisions:
                    item["default"] = False
            televisions = [item for item in televisions if item.get("node_id") != node_id] + [record]
            self._write(self.path, televisions)
        return dict(record)

    def resolve(self, target: str, *, current_node_id: str | None = None) -> Dict[str, Any]:
        televisions = self._read(self.path)
        if not televisions:
            raise LookupError("No television rooms are registered")
        normalized = re.sub(r"[^a-z0-9 ]+", " ", str(target).lower()).strip()
        if normalized in {"this", "this tv", "this television", "here"}:
            match = next((item for item in televisions if item.get("node_id") == current_node_id), None)
            if not match:
                raise LookupError("Pilot cannot establish which television is in this room")
            return match
        matches = [item for item in televisions if str(item.get("room_name") or "").casefold() == normalized.casefold()]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise LookupError("More than one television matches that room")
        if not normalized:
            defaults = [item for item in televisions if item.get("default")]
            if len(defaults) == 1:
                return defaults[0]
            if len(televisions) == 1:
                return televisions[0]
        raise LookupError("Pilot could not resolve that television room")

    def prepare_handoff(self, *, source_node_id: str, destination_room: str, persona_id: str, playback: Dict[str, Any]) -> Dict[str, Any]:
        source = self.resolve("this tv", current_node_id=source_node_id)
        destination = self.resolve(destination_room)
        if source["node_id"] == destination["node_id"]:
            raise ValueError("The destination must be a different television")
        if not playback.get("playback_verified") or not str(playback.get("title") or "").strip():
            raise PermissionError("A handoff requires verified title and playback evidence")
        record: Dict[str, Any] = {
            "schema_version": "pilot.tv-handoff.v1",
            "handoff_id": f"handoff_{uuid4().hex}",
            "persona_id": str(persona_id)[:120],
            "source_node_id": source["node_id"],
            "destination_node_id": destination["node_id"],
            "destination_room": destination["room_name"],
            "provider": str(playback.get("provider") or "")[:80],
            "title": " ".join(str(playback.get("title") or "").split())[:200],
            "content_id": str(playback.get("content_id") or "")[:200],
            "position_seconds": max(0, int(playback.get("position_seconds") or 0)),
            "status": "awaiting_private_confirmation",
            "created_at": utc_now_iso(),
            "credentials_projected": False,
            "playback_claimed_on_destination": False,
        }
        record["confirmation_hash"] = canonical_hash(record)
        with self._lock:
            handoffs = self._read(self.handoff_path)
            self._write(self.handoff_path, (handoffs + [record])[-50:])
        return record

    def confirm_handoff(self, handoff_id: str, *, persona_id: str, confirmation_hash: str) -> Dict[str, Any]:
        with self._lock:
            handoffs = self._read(self.handoff_path)
            record = next((item for item in handoffs if item.get("handoff_id") == handoff_id), None)
            if not record or record.get("persona_id") != persona_id:
                raise LookupError("That private handoff is unavailable")
            if record.get("status") != "awaiting_private_confirmation" or record.get("confirmation_hash") != confirmation_hash:
                raise PermissionError("The handoff confirmation is stale or invalid")
            record["status"] = "approved_pending_destination_adapter"
            record["confirmed_at"] = utc_now_iso()
            record["playback_claimed_on_destination"] = False
            self._write(self.handoff_path, handoffs)
            return dict(record)

    def snapshot(self) -> Dict[str, Any]:
        televisions = self._read(self.path)
        handoffs = self._read(self.handoff_path)
        return {
            "schema_version": "pilot.tv-room-registry.v1",
            "televisions": televisions,
            "room_count": len(televisions),
            "latest_handoff": handoffs[-1] if handoffs else None,
            "credentials_projected": False,
        }
