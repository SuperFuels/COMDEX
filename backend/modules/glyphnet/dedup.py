# backend/modules/glyphnet/dedup.py
import time, hashlib
from collections import deque

DEDUP_TTL = 15.0  # seconds
_seen_ids: dict[str, float] = {}
_seen_order: deque[tuple[str, float]] = deque()

def _prune_seen(now: float):
    while _seen_order and _seen_order[0][1] <= now:
        mid, _ = _seen_order.popleft()
        _seen_ids.pop(mid, None)

def already_seen(mid: str) -> bool:
    now = time.time()
    _prune_seen(now)
    return mid in _seen_ids

def mark_seen(mid: str):
    now = time.time()
    _prune_seen(now)
    _seen_ids[mid] = now + DEDUP_TTL
    _seen_order.append((mid, now + DEDUP_TTL))

def canon_id_for_capsule(topic: str, capsule: dict) -> str:
    """Stable ids:
       - voice_frame → vf:<topic>:<channel>:<seq>
       - glyphs (text) → txt:<sha1(topic|text)[:16]>
       - fallback hash of capsule
    """
    vf = capsule.get("voice_frame")
    if vf:
        ch  = str(vf.get("channel", "ch"))
        seq = str(vf.get("seq", 0))
        return f"vf:{topic}:{ch}:{seq}"

    glyphs = capsule.get("glyphs")
    if glyphs:
        s = f"{topic}|{''.join(map(str, glyphs))}"
        h = hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]
        return f"txt:{h}"

    raw = hashlib.sha1(repr(capsule).encode("utf-8")).hexdigest()[:16]
    return f"cap:{raw}"