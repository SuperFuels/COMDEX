# backend/modules/aion_cognition/akg_triplets.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Tuple, List, Optional
import json, os, time, math

Triplet = Tuple[str, str, str]

@dataclass
class Edge:
    s: str
    r: str
    o: str
    count: int = 0
    strength: float = 0.0   # bounded [0,1]
    last_ts: float = 0.0

class AKGTripletStore:
    """
    Persisted edge store with:
      - reinforce(s,r,o,hit) => EMA toward hit (usually 1.0)
      - optional half-life decay applied on access/update
    """

    def __init__(
        self,
        path: str = "data/knowledge/akg_triplets.json",
        alpha: float = 0.35,
        half_life_s: float = 0.0,
    ):
        self.path = path
        self.alpha = float(alpha)
        self.half_life_s = float(half_life_s)
        self.edges: Dict[Triplet, Edge] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for e in raw.get("edges", []):
                t = (e["s"], e["r"], e["o"])
                self.edges[t] = Edge(**e)
        except Exception:
            # never hard-fail on a corrupted store; start clean
            self.edges = {}

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        payload = {
            "version": 1,
            "saved_ts": time.time(),
            "alpha": self.alpha,
            "half_life_s": self.half_life_s,
            "edges": [asdict(e) for e in self.edges.values()],
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def clear(self) -> None:
        self.edges = {}
        self.save()

    def _apply_half_life_decay(self, e: Edge, now: Optional[float] = None) -> None:
        if self.half_life_s <= 0:
            return
        now = time.time() if now is None else float(now)
        if e.last_ts <= 0:
            e.last_ts = now
            return
        dt = max(0.0, now - e.last_ts)
        if dt <= 0:
            return
        # exp(-ln2 * dt / half_life)
        decay = math.exp(-math.log(2.0) * dt / self.half_life_s)
        e.strength = max(0.0, min(1.0, e.strength * decay))
        e.last_ts = now

    def reinforce(self, s: str, r: str, o: str, hit: float = 1.0) -> Edge:
        s = (s or "").strip()
        r = (r or "").strip()
        o = (o or "").strip()
        if not s or not r or not o:
            raise ValueError("Triplet components must be non-empty")

        t = (s, r, o)
        e = self.edges.get(t)
        now = time.time()
        if e is None:
            e = Edge(s=s, r=r, o=o, count=0, strength=0.0, last_ts=now)
            self.edges[t] = e
        else:
            self._apply_half_life_decay(e, now=now)

        e.count += 1
        # EMA toward hit, bounded
        h = max(0.0, min(1.0, float(hit)))
        e.strength = max(0.0, min(1.0, (1.0 - self.alpha) * e.strength + self.alpha * h))
        e.last_ts = now
        return e

    def top_edges(self, k: int = 20) -> List[Edge]:
        # apply decay lazily so reads reflect “now”
        now = time.time()
        if self.half_life_s > 0:
            for e in self.edges.values():
                self._apply_half_life_decay(e, now=now)

        return sorted(
            self.edges.values(),
            key=lambda e: (e.strength, e.count, e.last_ts),
            reverse=True,
        )[: max(0, int(k))]

    def snapshot(self, k: int = 20) -> dict:
        top = self.top_edges(k=k)
        return {
            "ts": time.time(),
            "path": self.path,
            "alpha": self.alpha,
            "half_life_s": self.half_life_s,
            "edges_total": len(self.edges),
            "top_edges": [
                {"s": e.s, "r": e.r, "o": e.o, "strength": e.strength, "count": e.count, "last_ts": e.last_ts}
                for e in top
            ],
        }