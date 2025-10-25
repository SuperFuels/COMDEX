"""
🧠 Wiki Importer — Phase 2
--------------------------
Converts external dictionary / thesaurus JSON into .wiki.phn capsules
and writes them into the Knowledge Graph container.
"""

import json
from pathlib import Path
from typing import Any, Dict
from backend.modules.wiki_capsules.foundations.wiki_capsule_schema import make_capsule
from backend.modules.wiki_capsules.foundations.wiki_serializer import save_wiki_capsule
from backend.modules.wiki_capsules.integration.kg_query_extensions import add_capsule_to_kg

DATA_PATH = Path("data/knowledge/lexicon")
DATA_PATH.mkdir(parents=True, exist_ok=True)


def load_source(source_path: str, capsule_domain: str = "Lexicon") -> None:
    """
    Load a JSON source (either list or dict) and convert its entries into Wiki capsules.
    Each capsule is saved as a .wiki.phn file and registered in the Knowledge Graph.
    """
    path = Path(source_path)
    if not path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Handle both list-based and dict-based input formats
    if isinstance(data, dict):
        entries = [{"lemma": k, **v} for k, v in data.items()]
    elif isinstance(data, list):
        entries = data
    else:
        raise ValueError("Unsupported data format. Expected list or dict of entries.")

    for entry in entries:
        lemma = entry.get("lemma")
        pos = entry.get("pos", "noun")
        definitions = entry.get("definitions", [])
        examples = entry.get("examples", [])
        synonyms = entry.get("synonyms", [])
        antonyms = entry.get("antonyms", [])
        entangled_links = entry.get("entangled_links", {})

        capsule = make_capsule(
            lemma=lemma,
            pos=pos,
            definitions=definitions,
            examples=examples,
            synonyms=synonyms,
            antonyms=antonyms,
            entangled_links=entangled_links,
        )

        # Save capsule to disk
        target_path = DATA_PATH / f"{lemma.title()}.wiki.phn"
        save_wiki_capsule(capsule, target_path)

        # Register capsule in the KG
        add_capsule_to_kg(capsule, capsule_domain)

    print(f"✅ [WikiImporter] Imported {len(entries)} entries → KG domain: {capsule_domain}")