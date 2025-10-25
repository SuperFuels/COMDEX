from backend.modules.wiki_capsules.integration.kg_integration import add_capsule_to_kg, get_capsule
from backend.modules.wiki_capsules.foundations.wiki_capsule_schema import make_capsule

def test_add_and_get_capsule(tmp_path):
    capsule = make_capsule("apple", "noun", ["A fruit"], ["He ate it."])
    add_capsule_to_kg(capsule, "Lexicon")
    entry = get_capsule("Lexicon", "apple")
    assert "path" in entry
    assert entry["meta"]["signed_by"] == "Tessaris-Core"