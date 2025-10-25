"""
📦 Wiki Capsule Serializer — Phase 1
------------------------------------
Converts WikiCapsule objects ↔ .wiki.phn text format.
"""

from pathlib import Path
from backend.modules.wiki_capsules.foundations.wiki_capsule_schema import WikiCapsule
import yaml, json

#───────────────────────────────────────────────
# 🧠 Serializer
#───────────────────────────────────────────────
def serialize_to_phn(capsule: WikiCapsule) -> str:
    """Serialize a WikiCapsule object into Photon-compatible .wiki.phn format (YAML-based)."""

    # Support both dataclass and dict-based capsules
    if isinstance(capsule, dict):
        meta = capsule.get("metadata", {})
        lemma = capsule.get("lemma", "")
        pos = capsule.get("pos", "")
        definitions = capsule.get("definitions", [])
        examples = capsule.get("examples", [])
        synonyms = capsule.get("synonyms", [])
        antonyms = capsule.get("antonyms", [])
        entangled_links = capsule.get("entangled_links", {})
    else:
        meta = getattr(capsule, "metadata", {}) or {}
        meta["checksum"] = capsule.checksum() if hasattr(capsule, "checksum") else ""
        lemma = capsule.lemma
        pos = capsule.pos
        definitions = capsule.definitions
        examples = capsule.examples
        synonyms = capsule.synonyms
        antonyms = capsule.antonyms
        entangled_links = capsule.entangled_links

    # Construct YAML sections
    header = yaml.dump({"meta": meta}, sort_keys=False)
    body = {
        "lemma": lemma,
        "pos": pos,
        "definitions": definitions,
        "examples": examples,
        "synonyms": synonyms,
        "antonyms": antonyms,
        "entangled_links": entangled_links,
    }
    body_yaml = yaml.dump(body, sort_keys=False)

    return f"^wiki_capsule {{\n{header}\n{body_yaml}\n}}"


#───────────────────────────────────────────────
# 💾 Save helper
#───────────────────────────────────────────────
def save_wiki_capsule(capsule: WikiCapsule, out_path: Path):
    """Serialize and save a Wiki capsule to disk."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    phn_text = serialize_to_phn(capsule)
    out_path.write_text(phn_text, encoding="utf-8")
    print(f"[Serializer] Saved Wiki capsule → {out_path}")