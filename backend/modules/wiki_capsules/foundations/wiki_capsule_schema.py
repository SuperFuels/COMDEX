"""
🌱 Wiki Capsule Schema — Phase 1
--------------------------------
Defines the canonical .wiki.phn capsule structure and dataclass model
for static knowledge units (lexicon, grammar, culture, science…).

Each capsule = one self-contained fact cluster:
lemma / concept + definitions + examples + entanglement metadata
"""

from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any
import json, hashlib, time

#───────────────────────────────────────────────
# 📚 Core Dataclass
#───────────────────────────────────────────────
@dataclass
class WikiCapsule:
    lemma: str
    pos: str
    definitions: List[str]
    examples: List[str] = field(default_factory=list)
    synonyms: List[str] = field(default_factory=list)
    antonyms: List[str] = field(default_factory=list)
    entangled_links: Dict[str, List[str]] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["meta"].setdefault("timestamp", time.time())
        data["meta"].setdefault("version", "1.0")
        return data

    def to_json(self, path=None, indent=2):
        js = json.dumps(self.to_dict(), indent=indent)
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(js)
        return js

    def checksum(self) -> str:
        return hashlib.sha3_256(
            json.dumps(self.to_dict(), sort_keys=True).encode()
        ).hexdigest()

#───────────────────────────────────────────────
# 🧩 Factory Utility
#───────────────────────────────────────────────
def make_capsule(
    lemma: str,
    pos: str,
    definitions: List[str],
    examples: List[str] = None,
    synonyms: List[str] = None,
    antonyms: List[str] = None,
    entangled_links: Dict[str, List[str]] = None,
) -> WikiCapsule:
    """Helper to quickly create a capsule with prefilled metadata."""
    capsule = WikiCapsule(
        lemma=lemma,
        pos=pos,
        definitions=definitions,
        examples=examples or [],
        synonyms=synonyms or [],
        antonyms=antonyms or [],
        entangled_links=entangled_links or {},
        meta={
            "signed_by": "Tessaris-Core",
            "timestamp": time.time(),
            "sqi_score": 0.0,
            "ρ": 0.0,
            "Ī": 0.0,
            "version": "1.0",
        },
    )
    capsule.meta["checksum"] = capsule.checksum()
    return capsule