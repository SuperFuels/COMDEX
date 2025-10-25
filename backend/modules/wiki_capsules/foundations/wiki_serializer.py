"""
📦 Wiki Capsule Serializer — Phase 3.1 (YAML-safe + Symbolic Unified)
--------------------------------------------------------------------
Preserves symbolic ^wiki_capsule framing while keeping YAML strictly single-document
for linter and importer validation.
"""

from pathlib import Path
from backend.modules.wiki_capsules.foundations.wiki_capsule_schema import WikiCapsule
import yaml


#───────────────────────────────────────────────
# 🧠 Serializer
#───────────────────────────────────────────────
def serialize_to_phn(capsule: WikiCapsule) -> str:
    """Serialize a WikiCapsule into a single YAML-valid .wiki.phn text block."""

    # Handle both dicts and dataclass objects
    if isinstance(capsule, dict):
        meta = capsule.get("metadata") or capsule.get("meta", {}) or {}
        lemma = capsule.get("lemma", "")
        pos = capsule.get("pos", "")
        definitions = capsule.get("definitions", [])
        examples = capsule.get("examples", [])
        synonyms = capsule.get("synonyms", [])
        antonyms = capsule.get("antonyms", [])
        entangled_links = capsule.get("entangled_links", {})
    else:
        meta = getattr(capsule, "metadata", {}) or getattr(capsule, "meta", {}) or {}
        if hasattr(capsule, "checksum"):
            meta["checksum"] = capsule.checksum()
        lemma = getattr(capsule, "lemma", "")
        pos = getattr(capsule, "pos", "")
        definitions = getattr(capsule, "definitions", [])
        examples = getattr(capsule, "examples", [])
        synonyms = getattr(capsule, "synonyms", [])
        antonyms = getattr(capsule, "antonyms", [])
        entangled_links = getattr(capsule, "entangled_links", {})

    # Merge meta + body into one YAML dict (single document)
    capsule_dict = {
        "meta": meta,
        "lemma": lemma,
        "pos": pos,
        "definitions": definitions,
        "examples": examples,
        "synonyms": synonyms,
        "antonyms": antonyms,
        "entangled_links": entangled_links,
    }

    yaml_text = yaml.safe_dump(capsule_dict, sort_keys=False, allow_unicode=True)

    # Symbolic framing kept as comments → YAML still valid
    return (
        "# ^wiki_capsule {\n"
        f"{yaml_text}"
        "# }\n"
    )


#───────────────────────────────────────────────
# 💾 Save helper
#───────────────────────────────────────────────
def save_wiki_capsule(capsule: WikiCapsule, out_path: Path):
    """Serialize and save a Wiki capsule to disk safely."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    phn_text = serialize_to_phn(capsule)
    out_path.write_text(phn_text, encoding="utf-8")
    print(f"[Serializer] Saved Wiki capsule → {out_path}")