# ============================================================
# 🧩 test_reference_validator.py
# ============================================================
from backend.modules.wiki_capsules.validation_maintenance.reference_validator import validate_cross_references
from backend.modules.wiki_capsules.integration.kg_query_extensions import _save_registry

def test_reference_validator_detects_missing_ref(tmp_path, monkeypatch):
    reg = {
        "Lexicon": {
            "Apple": {"meta": {"entangled_links": {"related": "Lexicon>Banana"}}},
            "Banana": {},
        },
        "Fruits": {},
    }
    _save_registry(reg)
    result = validate_cross_references()
    assert result["checked_domains"]
    assert result["valid"]  # Banana exists

    # Now remove Banana
    reg["Lexicon"].pop("Banana")
    _save_registry(reg)
    result2 = validate_cross_references()
    assert not result2["valid"]
    assert result2["missing"]