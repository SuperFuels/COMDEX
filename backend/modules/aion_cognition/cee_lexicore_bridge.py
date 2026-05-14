# ================================================================
# 🧠 LexiCore + ThesauriNet Bridge - Cognitive Exercise Engine
# ================================================================
"""
Unified access to lexical data for CEE generators.

Goals:
  - Lazy load (no eager dataset load at import time).
  - Singleton bridge to avoid repeated "Missing data source" spam.
  - Safe fallbacks when datasets are absent.
  - Back-compat: `bridge`, `get_synonyms`, `get_antonyms`, `get_related`.
"""

from __future__ import annotations

import json
import random
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


def _data_root() -> Path:
    return Path(os.getenv("DATA_ROOT", "data"))


DATA_DIR = _data_root() / "lexicore"
LEXICORE_PATH = DATA_DIR / "lexicore_index.json"
THESAURI_PATH = DATA_DIR / "thesaurinet.json"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        logger.warning(f"[LexiCoreBridge] Missing data source: {path}")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        logger.error(f"[LexiCoreBridge] Failed to load JSON {path}: {e}")
        return {}


def _dedupe_clean(xs: List[Any]) -> List[str]:
    out: List[str] = []
    seen = set()
    for x in xs or []:
        s = str(x).strip()
        if not s:
            continue
        sl = s.lower()
        if sl in seen:
            continue
        seen.add(sl)
        out.append(s)
    return out


class LexiCoreBridge:
    """Bridge for lexical and semantic word relationships."""

    def __init__(self, lexicore_path: Path = LEXICORE_PATH, thesauri_path: Path = THESAURI_PATH):
        self.lexicore_path = lexicore_path
        self.thesauri_path = thesauri_path
        self.lexicore: Dict[str, Any] = {}
        self.thesauri: Dict[str, Any] = {}
        self._loaded = False

    def ensure_loaded(self) -> None:
        if self._loaded:
            return
        self.lexicore = _load_json(self.lexicore_path)
        self.thesauri = _load_json(self.thesauri_path)
        self._loaded = True
        logger.info(
            f"[LexiCoreBridge] Loaded {len(self.lexicore)} LexiCore entries, {len(self.thesauri)} ThesauriNet entries."
        )

    def get_synonyms(self, word: str) -> List[str]:
        self.ensure_loaded()
        w = (word or "").strip()
        if not w:
            return []
        synonyms: List[Any] = []
        if w in self.lexicore and isinstance(self.lexicore[w], dict):
            synonyms.extend(self.lexicore[w].get("synonyms", []) or [])
        if not synonyms and w in self.thesauri and isinstance(self.thesauri[w], dict):
            synonyms.extend(self.thesauri[w].get("synonyms", []) or [])
        if not synonyms:
            synonyms = self._approximate(negative=False)
        return _dedupe_clean(synonyms)

    def get_antonyms(self, word: str) -> List[str]:
        self.ensure_loaded()
        w = (word or "").strip()
        if not w:
            return []
        antonyms: List[Any] = []
        if w in self.lexicore and isinstance(self.lexicore[w], dict):
            antonyms.extend(self.lexicore[w].get("antonyms", []) or [])
        if not antonyms and w in self.thesauri and isinstance(self.thesauri[w], dict):
            antonyms.extend(self.thesauri[w].get("antonyms", []) or [])
        if not antonyms:
            antonyms = self._approximate(negative=True)
        return _dedupe_clean(antonyms)

    def get_related(self, word: str, depth: int = 1) -> List[str]:
        self.ensure_loaded()
        w = (word or "").strip()
        if not w:
            return []
        depth = max(1, int(depth or 1))

        related: set[str] = set()
        node = self.thesauri.get(w)
        if isinstance(node, dict):
            for x in (node.get("related", []) or []):
                if x:
                    related.add(str(x).strip())

        if depth > 1:
            # bounded recursion, avoids infinite fan-out
            frontier = list(related)
            for _ in range(depth - 1):
                if not frontier:
                    break
                nxt: List[str] = []
                for r in frontier:
                    node2 = self.thesauri.get(r)
                    if isinstance(node2, dict):
                        for x in (node2.get("related", []) or []):
                            s = str(x).strip()
                            if s and s not in related:
                                related.add(s)
                                nxt.append(s)
                frontier = nxt

        return _dedupe_clean(list(related))

    def _approximate(self, negative: bool = False) -> List[str]:
        # fallback pool when datasets are missing
        pool = list(self.lexicore.keys()) if self.lexicore else []
        if not pool:
            pool = ["bright", "dark", "fast", "slow", "light", "heavy", "hot", "cold", "calm", "angry"]
        k = 2 if negative else 3
        if len(pool) <= k:
            return pool
        return random.sample(pool, k=k)


# ---------------------------
# Singleton accessor (CEE uses this)
# ---------------------------
_BRIDGE: Optional[LexiCoreBridge] = None


def get_bridge() -> LexiCoreBridge:
    global _BRIDGE
    if _BRIDGE is None:
        _BRIDGE = LexiCoreBridge()
    return _BRIDGE


# ---------------------------
# Back-compat: `bridge` proxy + helper functions
# ---------------------------
class _BridgeProxy:
    def __getattr__(self, name: str):
        return getattr(get_bridge(), name)


bridge = _BridgeProxy()


_FALLBACK_SYNONYMS: Dict[str, List[str]] = {
    "happy": ["joyful", "content", "cheerful"],
    "bright": ["light", "vivid", "smart"],
    "fast": ["quick", "rapid", "swift"],
    "calm": ["peaceful", "serene", "still"],
}

_FALLBACK_ANTONYMS: Dict[str, List[str]] = {
    "happy": ["sad", "unhappy"],
    "bright": ["dim", "dull"],
    "fast": ["slow", "sluggish"],
    "calm": ["angry", "agitated"],
}


def get_synonyms(word: str) -> List[str]:
    w = (word or "").strip()
    if not w:
        return []
    try:
        syns = get_bridge().get_synonyms(w)
        if syns:
            return syns
    except Exception as e:
        logger.debug(f"[LexiCoreBridge] get_synonyms bridge failed: {e}")
    return _FALLBACK_SYNONYMS.get(w.lower(), ["neutral"])


def get_antonyms(word: str) -> List[str]:
    w = (word or "").strip()
    if not w:
        return []
    try:
        ants = get_bridge().get_antonyms(w)
        if ants:
            return ants
    except Exception as e:
        logger.debug(f"[LexiCoreBridge] get_antonyms bridge failed: {e}")
    return _FALLBACK_ANTONYMS.get(w.lower(), ["opposite"])


def get_related(word: str, depth: int = 1) -> List[str]:
    w = (word or "").strip()
    if not w:
        return []
    try:
        return get_bridge().get_related(w, depth=depth)
    except Exception as e:
        logger.debug(f"[LexiCoreBridge] get_related bridge failed: {e}")
        return []


__all__ = [
    "LexiCoreBridge",
    "get_bridge",
    "bridge",
    "get_synonyms",
    "get_antonyms",
    "get_related",
]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    w = "happy"
    print("Synonyms:", bridge.get_synonyms(w))
    print("Antonyms:", bridge.get_antonyms(w))
    print("Related:", bridge.get_related(w))
    print("get_synonyms('fast') ->", get_synonyms("fast"))
    print("get_antonyms('bright') ->", get_antonyms("bright"))
    print("get_related('calm', depth=2) ->", get_related("calm", depth=2))