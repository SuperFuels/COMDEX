from __future__ import annotations
import asyncio, json, time, uuid
from typing import Any, Dict, Optional, Tuple

class _GlyphBus:
    def __init__(self) -> None:
        self._topics: Dict[str, Dict[str, asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, topic: str) -> Tuple[str, asyncio.Queue]:
        q: asyncio.Queue = asyncio.Queue(maxsize=1024)
        sub_id = str(uuid.uuid4())
        async with self._lock:
            self._topics.setdefault(topic, {})[sub_id] = q
        return sub_id, q

    async def unsubscribe(self, topic: str, sub_id: str) -> None:
        async with self._lock:
            if topic in self._topics and sub_id in self._topics[topic]:
                del self._topics[topic][sub_id]
                if not self._topics[topic]:
                    del self._topics[topic]

    async def publish(self, topic: str, msg: Dict[str, Any]) -> int:
        # best-effort JSON sanity
        try:
            json.dumps(msg, ensure_ascii=False)
        except Exception:
            msg = {"op": "error", "detail": "non-serializable message"}
        delivered = 0
        async with self._lock:
            subs = list(self._topics.get(topic, {}).values())
        for q in subs:
            try:
                q.put_nowait(msg)
                delivered += 1
            except asyncio.QueueFull:
                # drop if backpressured; in future add dead-letter
                pass
        return delivered

glyph_bus = _GlyphBus()

def topic_for_recipient(recipient: str) -> str:
    # e.g. recipient="ucs://local/ucs_hub" -> "gnet:ucs://local/ucs_hub"
    return f"gnet:{recipient}"

def envelope_capsule(recipient: str, capsule: Dict[str, Any], meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "ts": time.time(),
        "op": "capsule",
        "recipient": recipient,
        "capsule": capsule,
        "meta": meta or {},
    }