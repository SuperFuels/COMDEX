"""
🔍 KG Query Extensions — Phase 2
--------------------------------
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

#───────────────────────────────────────────────
# 📘 Registry Helpers
#───────────────────────────────────────────────
def _load_registry() -> Dict[str, Any]:
    """Load the global Knowledge Graph registry."""
    if not KG_PATH.exists():
        return {}
    return json.load(open(KG_PATH, "r", encoding="utf-8"))


def _save_registry(reg: Dict[str, Any]) -> None:
    """Persist registry to disk."""
    json.dump(reg, open(KG_PATH, "w", encoding="utf-8"), indent=2)


#───────────────────────────────────────────────
# 🧩 CRUD Operations
#───────────────────────────────────────────────
def add_capsule_to_kg(capsule: WikiCapsule, domain: str, capsule_path: Path = None) -> None:
    """Register a capsule inside the Knowledge Graph registry."""
    reg = _load_registry()
    dom = reg.setdefault(domain, {})
    capsule_dict = capsule.to_dict() if hasattr(capsule, "to_dict") else capsule

    # Determine actual file path
    if capsule_path is None:
        capsule_path = Path(f"data/knowledge/{domain}/{capsule_dict.get('lemma','').title()}.wiki.phn")
    capsule_path = Path(capsule_path).resolve()

    # Ensure metadata integrity
    meta = capsule_dict.get("metadata", {}) or {}
    meta.setdefault("signed_by", "Tessaris-Core")
    meta.setdefault("version", "1.0")
    meta.setdefault("timestamp", time.time())

    dom[capsule_dict["lemma"]] = {
        "path": str(capsule_path),
        "meta": meta,
    }

    _save_registry(reg)
    print(f"[KG] Added {domain}>{capsule_dict['lemma']} @ {capsule_path}")


def get_wiki(lemma: str, domain: str = "Lexicon") -> Dict[str, Any]:
    """Retrieve capsule data for a given lemma from the KG registry (case-insensitive)."""
    reg = _load_registry()
    dom = reg.get(domain, {})

    # normalize lookup — match lowercase or titlecase
    entry = dom.get(lemma) or dom.get(lemma.lower()) or dom.get(lemma.title())

    if not entry:
        raise KeyError(f"Capsule not found in KG: {domain}>{lemma}")

    capsule_path = Path(entry.get("path", "")).expanduser()

    if not capsule_path.exists():
        tmp_dir = Path("/tmp")
        matches = list(tmp_dir.rglob(f"{lemma.title()}.wiki.phn"))
        if matches:
            capsule_path = matches[0]
            print(f"[KG] Self-healed capsule path → {capsule_path}")
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