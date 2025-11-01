"""
🌱 Wiki Capsule Schema - Phase 2
──────────────────────────────────────────────
Defines the canonical .wiki.phn capsule structure and dataclass model
for static knowledge units (lexicon, grammar, culture, science...).

Each capsule = one self-contained fact cluster:
lemma / concept + definitions + examples + entanglement metadata.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Union
from pathlib import Path
import json, yaml, hashlib, time, re, logging

log = logging.getLogger(__name__)

# ───────────────────────────────────────────────
# 📚 Core Dataclass
# ───────────────────────────────────────────────
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

    # ───────────────────────────────
    # Serialization
    # ───────────────────────────────
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        meta = data.setdefault("meta", {})
        meta.setdefault("timestamp", time.time())
        meta.setdefault("version", "1.0")
        return data

    def to_json(self, path: Union[str, Path] = None, indent: int = 2) -> str:
        js = json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
        if path:
            Path(path).write_text(js, encoding="utf-8")
        return js

    def checksum(self) -> str:
        return hashlib.sha3_256(
            json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()

    # ───────────────────────────────
    # Load / Parse Utilities
    # ───────────────────────────────
    @classmethod
    def from_text(cls, text: str) -> "WikiCapsule":
        """
        Parse .wiki.phn or .wiki.enriched.phn content into a WikiCapsule.
        Handles JSON, YAML, and Markdown-like fenced variants.
        """

        import yaml

        # ── Pre-clean phase ───────────────────────────────
        clean = []
        skip_block = False
        for line in text.splitlines():
            # Skip code fences
            if line.strip().startswith("```"):
                skip_block = not skip_block
                continue
            # Skip synthetic wrappers
            if line.strip().startswith("^wiki_capsule"):
                continue
            if line.strip() == "}":
                continue
            # Ignore YAML doc separators
            if line.strip() == "---":
                continue
            if not skip_block:
                clean.append(line)
        text = "\n".join(clean).strip()

        # ── Try JSON -> YAML ───────────────────────────────
        data = None
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            try:
                data = yaml.safe_load(text)
            except Exception as e:
                log.warning(f"[Parser-Fallback] Non-YAML capsule ({type(e).__name__}): {e}")

        # ── Normalize structured data ─────────────────────
        if isinstance(data, list) and data and isinstance(data[0], dict):
            data = data[0]

        if isinstance(data, dict):
            if "title" in data and "lemma" not in data:
                data["lemma"] = data.pop("title")
            if "part_of_speech" in data and "pos" not in data:
                data["pos"] = data.pop("part_of_speech")

            for key in ["definitions", "examples", "synonyms", "antonyms"]:
                data.setdefault(key, [])

            entangled = data.get("entangled_links") or {}
            if not isinstance(entangled, dict):
                entangled = {}
            meta = data.get("meta") or {}
            if not isinstance(meta, dict):
                meta = {}

            meta.setdefault("signed_by", "Tessaris-Core")
            meta.setdefault("timestamp", time.time())
            meta.setdefault("sqi_score", 0.0)
            meta.setdefault("ρ", 0.0)
            meta.setdefault("Ī", 0.0)
            meta.setdefault("version", "1.0")

            data["entangled_links"] = entangled
            data["meta"] = meta
            return cls(**data)

        # ── Plain-text fallback ───────────────────────────
        lemma_match = re.search(r"^#\s*(.+)$", text, re.MULTILINE)
        lemma = lemma_match.group(1).strip() if lemma_match else "unknown"
        defs = re.findall(r"^- (.+)$", text, re.MULTILINE)

        return cls(
            lemma=lemma,
            pos="unknown",
            definitions=defs or [text.strip()],
            examples=[],
            meta={
                "signed_by": "Tessaris-Core",
                "timestamp": time.time(),
                "sqi_score": 0.0,
                "ρ": 0.0,
                "Ī": 0.0,
                "version": "1.0",
            },
        )

    @classmethod
    def load(cls, path: Union[str, Path]) -> "WikiCapsule":
        """Load a WikiCapsule from disk (.wiki.phn / .wiki.enriched.phn)."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Capsule file not found: {path}")
        text = path.read_text(encoding="utf-8")
        capsule = cls.from_text(text)
        capsule.meta.setdefault("checksum", capsule.checksum())
        return capsule


# ───────────────────────────────────────────────
# 🧩 Factory Utility
# ───────────────────────────────────────────────
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