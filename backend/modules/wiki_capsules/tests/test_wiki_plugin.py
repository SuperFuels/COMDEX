import json
from pathlib import Path

from backend.modules.wiki_capsules.foundations.wiki_capsule_schema import make_capsule
from backend.modules.wiki_capsules.foundations.wiki_serializer import save_wiki_capsule
from backend.modules.wiki_capsules.integration.kg_query_extensions import (
    add_capsule_to_kg,
    _load_registry,
    _save_registry,
)
from backend.modules.wiki_capsules.photon_hooks.wiki_plugin import handle_wiki


def test_wiki_plugin_resolves_capsule(tmp_path: Path, monkeypatch):
    """
    Ensure 📚 glyph resolves a stored Wiki capsule via KG.
    """
    # --- Arrange: create a capsule + save to a temp .wiki.phn
    cap = make_capsule(
        lemma="orange",
        pos="noun",
        definitions=["A round juicy citrus fruit with a tough bright reddish-yellow rind."],
        examples=["She peeled an orange for breakfast."],
        synonyms=["citrus"],
        entangled_links={"Fruits": ["Apple", "Banana"]},
    )

    cap_dir = tmp_path / "Lexicon"
    cap_dir.mkdir(parents=True, exist_ok=True)
    cap_path = cap_dir / "Orange.wiki.phn"
    save_wiki_capsule(cap, cap_path)

    # --- Arrange: register in KG with explicit capsule_path
    add_capsule_to_kg(cap, domain="Lexicon", capsule_path=cap_path)

    # --- Act: resolve via 📚 glyph
    result = handle_wiki("📚Lexicon>Orange")

    # --- Assert: structure & content
    assert isinstance(result, dict)
    assert result.get("lemma") == "orange"
    assert result.get("domain") == "Lexicon"
    meta = result.get("meta", {})
    assert meta.get("signed_by") == "Tessaris-Core"
    assert "orange" in result.get("capsule", "").lower()


def test_wiki_plugin_missing_capsule_returns_error(tmp_path: Path):
    """
    📚 glyph should return an error payload when the capsule is not in KG.
    """
    result = handle_wiki("📚Lexicon>DoesNotExist")
    assert isinstance(result, dict)
    assert "error" in result
    assert "DoesNotExist" in result.get("instruction", "")