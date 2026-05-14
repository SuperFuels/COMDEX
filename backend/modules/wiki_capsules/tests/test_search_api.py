import json
from pathlib import Path
from backend.modules.wiki_capsules.devtools_search.search_api import search_kg

TEST_KG_PATH = Path("data/knowledge/kg_registry.json")

def setup_module(module):
    TEST_KG_PATH.parent.mkdir(parents=True, exist_ok=True)
    sample_data = {
        "Lexicon": {
            "apple": {"meta": {"signed_by": "Tessaris-Core"}, "path": "Apple.wiki.phn"},
            "banana": {"meta": {"signed_by": "Tessaris-Core"}, "path": "Banana.wiki.phn"},
            "pear": {"meta": {"signed_by": "Tessaris-Core"}, "path": "Pear.wiki.phn"},
        }
    }
    json.dump(sample_data, open(TEST_KG_PATH, "w", encoding="utf-8"), indent=2)

def teardown_module(module):
    if TEST_KG_PATH.exists():
        TEST_KG_PATH.unlink()

def test_keyword_search_exact():
    results = search_kg("apple", domain="Lexicon")
    assert any(r["lemma"] == "apple" for r in results)
    assert results[0]["score"] >= 3

def test_keyword_search_fuzzy():
    results = search_kg("appl", domain="Lexicon", fuzzy=True)
    assert any("apple" in r["lemma"] for r in results)