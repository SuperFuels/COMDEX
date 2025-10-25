"""
🧪 Test — Wiki Importer (Phase 2)
--------------------------------
Validates that JSON data is converted into .wiki.phn capsules,
saved to disk, and registered in the Knowledge Graph registry.
"""

import json
from pathlib import Path
from backend.modules.wiki_capsules.integration import wiki_importer
from backend.modules.wiki_capsules.integration.kg_query_extensions import get_wiki

def test_importer_creates_capsules(tmp_path, monkeypatch):
    # Prepare a temporary dataset
    src = tmp_path / "sample_dict.json"
    data = {
        "apple": {
            "pos": "noun",
            "definitions": ["A round fruit of a tree of the rose family."],
            "examples": ["He ate a red apple."],
            "synonyms": ["pome"]
        },
        "banana": {
            "pos": "noun",
            "definitions": ["An elongated curved tropical fruit."],
            "examples": ["Bananas grow in warm regions."],
            "synonyms": ["plantain"]
        }
    }
    src.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # Redirect DATA_PATH to temporary directory
    target_dir = tmp_path / "lexicon"
    monkeypatch.setattr(wiki_importer, "DATA_PATH", target_dir)

    # Run importer
    wiki_importer.load_source(str(src), capsule_domain="Lexicon")

    # Ensure capsule files exist
    apple_file = target_dir / "Apple.wiki.phn"
    banana_file = target_dir / "Banana.wiki.phn"
    assert apple_file.exists()
    assert banana_file.exists()

    # Ensure KG has corresponding entries
    apple_entry = get_wiki("apple", "Lexicon")
    assert apple_entry["lemma"] == "apple"
    assert "capsule" in apple_entry
    assert "meta" in apple_entry
    assert apple_entry["meta"].get("signed_by") == "Tessaris-Core"