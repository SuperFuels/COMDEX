"""
🧪 Test - KG Query Extensions (Phase 2)
--------------------------------------
Ensures capsule addition, retrieval, and domain listing work as expected.
"""

from pathlib import Path
import json
from backend.modules.wiki_capsules.foundations.wiki_capsule_schema import make_capsule
from backend.modules.wiki_capsules.integration.kg_query_extensions import (
    add_capsule_to_kg,
    get_wiki,
    list_domain,
)

def test_add_and_retrieve_capsule(tmp_path, monkeypatch):
    # Redirect registry to temp directory
    from backend.modules.wiki_capsules import integration
    reg_path = tmp_path / "kg_registry.json"
    monkeypatch.setattr(integration.kg_query_extensions, "KG_PATH", reg_path)

    # Create capsule
    cap = make_capsule(
        "pear",
        "noun",
        ["A sweet fruit with a rounded base and tapering top."],
        ["She picked a ripe pear."],
    )

    # Save capsule file to match KG reference
    domain_dir = tmp_path / "Lexicon"
    domain_dir.mkdir(parents=True, exist_ok=True)
    cap_path = domain_dir / "Pear.wiki.phn"
    cap.to_json(cap_path)

    # Add to KG and verify
    add_capsule_to_kg(cap, "Lexicon")
    assert "pear" in list_domain("Lexicon")

    # Read capsule back
    entry = get_wiki("pear", "Lexicon")
    assert entry["lemma"] == "pear"
    assert "capsule" in entry
    assert entry["meta"].get("signed_by") == "Tessaris-Core"
    assert "Pear.wiki.phn" in entry["capsule"] or "pear" in entry["capsule"].lower()