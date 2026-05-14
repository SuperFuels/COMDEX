from __future__ import annotations

from dataclasses import dataclass
import hashlib
import random

from .stable_json import stable_stringify


def stable_hash(obj) -> str:
    """
    Deterministic SHA-256 over canonical JSON for any JSON-ish object.
    Uses stable_stringify() (sorted keys, stable separators).
    """
    blob = stable_stringify(obj).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


@dataclass(frozen=True)
class TickClock:
    """Deterministic tick clock for benchmark mode."""
    dt: float = 1.0 / 30.0
    t0: float = 0.0

    def t(self, tick: int) -> float:
        return self.t0 + self.dt * float(tick)


class SeededRNG:
    """
    Injectable RNG wrapper.
    Record `algo` + `seed` into replay bundles for audit/replay.
    """

    def __init__(self, seed: int, algo: str = "python.random.Random"):
        self.seed = int(seed)
        self.algo = str(algo)
        self._rng = random.Random(self.seed)

    def uniform(self, a: float, b: float) -> float:
        return self._rng.uniform(a, b)

    def random(self) -> float:
        return self._rng.random()

    def randint(self, a: int, b: int) -> int:
        return self._rng.randint(a, b)