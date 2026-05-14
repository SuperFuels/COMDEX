"""
🔍 KG Query Extensions - Phase 2
──────────────────────────────────────────────
Adds capsule CRUD helpers for the Knowledge Graph and enables
querying Wiki Capsules with file + metadata access.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any
from backend.modules.wiki_capsules.foundations.wiki_capsule_schema import WikiCapsule

KG_PATH = Path("data/knowledge/kg_registry.json")
KG_PATH.parent.mkdir(parents=True, exist_ok=True)


# ───────────────────────────────────────────────
# 📘 Registry Helpers
# ───────────────────────────────────────────────
def _load_registry() -> Dict[str, Any]:
    """Load the global Knowledge Graph registry."""
    if not KG_PATH.exists():
        return {}
    try:
        return json.load(open(KG_PATH, "r", encoding="utf-8"))
    except json.JSONDecodeError:
        print("[KG] Registry JSON corrupted - resetting empty registry.")
        return {}


def _save_registry(reg: Dict[str, Any]) -> None:
    """Persist registry to disk safely."""
    tmp = KG_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=2, ensure_ascii=False)
    tmp.replace(KG_PATH)


# ───────────────────────────────────────────────
# 🧩 CRUD Operations
# ───────────────────────────────────────────────
def add_capsule_to_kg(capsule: WikiCapsule, domain: str, capsule_path: Path = None) -> None:
    """Register a capsule inside the Knowledge Graph registry."""
    reg = _load_registry()
    dom = reg.setdefault(domain, {})

    capsule_dict = capsule.to_dict() if hasattr(capsule, "to_dict") else capsule

    # Determine actual file path
    lemma = capsule_dict.get("lemma", "").strip()
    if not lemma:
        raise ValueError("Cannot add capsule without lemma")

    if capsule_path is None:
        capsule_path = Path(f"data/knowledge/{domain}/{lemma}.wiki.phn")
    capsule_path = Path(capsule_path).resolve()

    # Ensure metadata integrity
    meta = capsule_dict.get("meta", {}) or {}
    meta.setdefault("signed_by", "Tessaris-Core")
    meta.setdefault("version", "1.0")
    meta.setdefault("timestamp", time.time())

    dom[lemma] = {
        "path": str(capsule_path),
        "meta": meta,
    }

    _save_registry(reg)
    print(f"[KG] Added {domain}>{lemma} @ {capsule_path}")


def get_wiki(lemma: str, domain: str = "Lexicon") -> Dict[str, Any]:
    """Retrieve capsule data for a given lemma from the KG registry (case-insensitive)."""
    reg = _load_registry()
    dom = reg.get(domain, {})

    # normalize lookup - match lowercase or titlecase
    entry = dom.get(lemma) or dom.get(lemma.lower()) or dom.get(lemma.title())

    if not entry:
        raise KeyError(f"Capsule not found in KG: {domain}>{lemma}")

    capsule_path = Path(entry.get("path", "")).expanduser()

    if not capsule_path.exists():
        tmp_dir = Path("/tmp")
        matches = list(tmp_dir.rglob(f"{lemma}.wiki.phn"))
        if matches:
            capsule_path = matches[0]
            print(f"[KG] Self-healed capsule path -> {capsule_path}")
        else:
            raise FileNotFoundError(f"Capsule file missing: {capsule_path}")

    with open(capsule_path, "r", encoding="utf-8") as f:
        capsule_data = f.read()

    return {
        "lemma": lemma.lower(),
        "domain": domain,
        "meta": entry.get("meta", {}),
        "capsule": capsule_data,
        "path": str(capsule_path),
    }


def list_domain(domain: str = "Lexicon") -> list[str]:
    """List all capsule lemmas under a domain."""
    reg = _load_registry()
    return list(reg.get(domain, {}).keys())


# ───────────────────────────────────────────────
# 🔗 Unified KG Registration Entry Point
# ───────────────────────────────────────────────
def register_kg_entry(title: str, content: str, domain: str = "Lexicon") -> None:
    """
    Lightweight registration helper used by AION ingestion.
    Creates or updates a KG entry for a given title/content pair.
    Ensures backward compatibility with legacy `title` key capsules.
    """
    try:
        # Normalize title -> lemma
        lemma = title.strip()
        definitions = [content.strip()] if content.strip() else []

        capsule = WikiCapsule(
            lemma=lemma,
            pos="unknown",
            definitions=definitions,
            examples=[],
            synonyms=[],
            antonyms=[],
            entangled_links={},
            meta={"source": "wiki_ingest", "timestamp": time.time()},
        )

        add_capsule_to_kg(capsule, domain=domain)
        print(f"[KG] Registered entry: {domain}>{lemma}")

    except Exception as e:
        print(f"[KG] Failed to register entry '{title}': {e}")


# ───────────────────────────────────────────────
# 🧭 Metadata Update Utility
# ───────────────────────────────────────────────
def update_capsule_meta(lemma: str, domain: str, meta: dict):
    """
    Update metadata for a capsule in the KG registry.
    Phase 11: also embed resonance energy E (if provided) into the KG node.
    """
    import json
    from pathlib import Path

    REGISTRY_PATH = Path("data/kg_registry.json")
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Load existing registry
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            registry = json.load(f)
    else:
        registry = {}

    node_key = f"{domain}>{lemma}"
    node = registry.get(node_key, {})

    # Merge or create meta
    node_meta = node.get("meta", {})
    node_meta.update(meta)

    # ⬡ Phase 11 - embed symbolic resonance energy if present
    if "E" in meta:
        node_meta["E"] = meta["E"]

    node["meta"] = node_meta
    registry[node_key] = node

    # Save
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)

    print(f"[KG] Updated meta for {node_key} -> E={meta.get('E')}")