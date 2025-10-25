"""
Knowledge Graph Integration for Wiki Capsules
---------------------------------------------
Maintains persistent registry of all loaded capsules.
"""

import json
from pathlib import Path
from dataclasses import asdict
from backend.modules.wiki_capsules.foundations.wiki_capsule_schema import WikiCapsule

KG_PATH = Path("data/knowledge/kg_registry.json")


def _load_registry():
    if not KG_PATH.exists():
        return {}
    with open(KG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_registry(registry):
    KG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(KG_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)


def add_capsule_to_kg(capsule, domain: str):
    """
    Add a WikiCapsule (dataclass or dict) into the Knowledge Graph registry.
    """
    # 🧠 Normalize capsule
    if isinstance(capsule, WikiCapsule):
        capsule_dict = asdict(capsule)
    elif isinstance(capsule, dict):
        capsule_dict = capsule
    else:
        raise TypeError("Expected WikiCapsule or dict")

    lemma = capsule_dict["lemma"]
    path = f"data/knowledge/{domain}/{lemma.title()}.wiki.phn"

    registry = _load_registry()
    if domain not in registry:
        registry[domain] = {}

    registry[domain][lemma] = {
        "path": path,
        "meta": capsule_dict.get("meta", {}),
        "entangled_links": capsule_dict.get("entangled_links", {}),
    }

    _save_registry(registry)
    return registry


def get_capsule(domain: str, lemma: str):
    registry = _load_registry()
    entry = registry.get(domain, {}).get(lemma)
    if not entry:
        raise KeyError(f"No capsule found for {domain}:{lemma}")
    return entry