import json
from pathlib import Path
from backend.modules.wiki_capsules.photon_page.photon_page_spec import make_photon_page
from backend.modules.wiki_capsules.photon_page.converter_tools import (
    save_page, load_page, page_to_json, json_to_page
)
from backend.modules.wiki_capsules.photon_page.photon_page_validator import validate_page

def test_page_creation_and_save(tmp_path):
    page = make_photon_page("TestPage", imports=["Apple"], body="⊕ combine { a, b }")
    path = tmp_path / "TestPage.ptn.json"
    save_page(page, path)
    loaded = load_page(path)
    assert loaded.name == "TestPage"
    assert "⊕" in loaded.body

def test_page_validation_with_existing_import(tmp_path):
    wiki_root = tmp_path / "Lexicon"
    wiki_root.mkdir(parents=True)
    (wiki_root / "Apple.wiki.phn").write_text("dummy", encoding="utf-8")

    page = make_photon_page("FruitLogic", imports=["Apple"], body="↔ connect { X, Y }")
    assert validate_page(page, wiki_root) is True

def test_entanglement_error(tmp_path):
    page = make_photon_page("SelfRef", imports=["SelfRef"], body="⊕ combine {}")
    try:
        validate_page(page, tmp_path)
    except ValueError as e:
        assert "cannot import itself" in str(e)