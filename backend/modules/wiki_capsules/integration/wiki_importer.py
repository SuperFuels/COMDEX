"""
🧠 Wiki Importer - Phase 2
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

    # 🔧 Ensure correct target directory
    domain_path = Path("data/knowledge") / capsule_domain
    domain_path.mkdir(parents=True, exist_ok=True)

    imported = 0

    for entry in entries:
        lemma = entry.get("lemma")
        if not lemma:
            print("⚠️ Skipping entry with no lemma.")
            continue

        capsule = make_capsule(
            lemma=lemma,
            pos=entry.get("pos", "noun"),
            definitions=entry.get("definitions", []),
            examples=entry.get("examples", []),
            synonyms=entry.get("synonyms", []),
            antonyms=entry.get("antonyms", []),
            entangled_links=entry.get("entangled_links", {}),
        )

        # ✅ Save under domain folder, e.g. data/knowledge/Lexicon/apple.wiki.phn
        target_path = domain_path / f"{lemma.lower()}.wiki.phn"
        save_wiki_capsule(capsule, target_path)

        # ✅ Register in the KG
        add_capsule_to_kg(capsule, capsule_domain, target_path)

        imported += 1

    print(f"✅ [WikiImporter] Imported {imported} entries -> data/knowledge/{capsule_domain}/")


# ──────────────────────────────────────────────
# CLI Entrypoint
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Import Wiki Capsules into Tessaris KG")
    parser.add_argument("source", help="Path to JSON file containing entries")
    parser.add_argument("domain", nargs="?", default="Lexicon", help="Target KG domain")
    parser.add_argument("--validate", "-v", action="store_true", help="Run linter after import")
    parser.add_argument("--summary", "-s", action="store_true", help="Print summary report")

    args = parser.parse_args()
    load_source(args.source, args.domain)

    if args.validate:
        from backend.modules.wiki_capsules.validation_maintenance.wiki_linter import lint_directory
        results = lint_directory(f"data/knowledge/{args.domain}")
        if args.summary:
            import json as _json
            print(_json.dumps(results, indent=2, ensure_ascii=False))