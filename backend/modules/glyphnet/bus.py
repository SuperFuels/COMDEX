# backend/modules/glyphnet/bus.py
from __future__ import annotations
import asyncio, json, time, uuid, os
from typing import Any, Dict, Optional, Tuple, List

# Env-tunable per-subscriber queue size (defaults to 1024)
DEFAULT_QUEUE_MAXSIZE = int(os.getenv("GLYPHNET_QUEUE_MAX", "1024"))

class _GlyphBus:
    def __init__(self) -> None:
        # topic -> { sub_id -> asyncio.Queue }
        self._topics: Dict[str, Dict[str, asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, topic: str, maxsize: Optional[int] = None) -> Tuple[str, asyncio.Queue]:
        """Subscribe to a topic. Returns (sub_id, queue)."""
        q: asyncio.Queue = asyncio.Queue(maxsize=maxsize or DEFAULT_QUEUE_MAXSIZE)
        sub_id = str(uuid.uuid4())
        async with self._lock:
            self._topics.setdefault(topic, {})[sub_id] = q
        return sub_id, q

    async def unsubscribe(self, topic: str, sub_id: str) -> None:
        """Unsubscribe a previously registered sub_id from a topic."""
        async with self._lock:
            topic_map = self._topics.get(topic)
            if topic_map and sub_id in topic_map:
                del topic_map[sub_id]
                if not topic_map:
                    del self._topics[topic]

    async def publish(self, topic: str, msg: Dict[str, Any]) -> int:
        """
        Publish a message to a topic.
        Returns the number of subscribers that accepted the message.
        Drops on backpressure (QueueFull) — future: dead-letter channel.
        """
        # Ensure JSON-serializable so WS clients don't choke.
        try:
            json.dumps(msg, ensure_ascii=False)
        except Exception:
            msg = {"op": "error", "detail": "non-serializable message"}

        # Snapshot subscriber queues without holding the lock during puts.
        async with self._lock:
            subs = list(self._topics.get(topic, {}).values())

        delivered = 0
        for q in subs:
            try:
                q.put_nowait(msg)
                delivered += 1
            except asyncio.QueueFull:
                # Best-effort drop; consider logging/metrics if needed.
                pass
        return delivered

    # ---- optional introspection (useful in tests/health) ----
    async def list_topics(self) -> List[str]:
        async with self._lock:
            return list(self._topics.keys())

    async def subscriber_count(self, topic: str) -> int:
        async with self._lock:
            return len(self._topics.get(topic, {}))


glyph_bus = _GlyphBus()

def topic_for_recipient(recipient: str) -> str:
    """e.g. 'ucs://local/ucs_hub' -> 'gnet:ucs://local/ucs_hub'"""
    return f"gnet:{recipient}"

def envelope_capsule(
    recipient: str,
    capsule: Dict[str, Any],
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Standardize the bus envelope for Photon capsules."""
    return {
        "id": str(uuid.uuid4()),
        "ts": time.time(),
        "op": "capsule",
        "recipient": recipient,
        "capsule": capsule,
        "meta": dict(meta or {}),
    }