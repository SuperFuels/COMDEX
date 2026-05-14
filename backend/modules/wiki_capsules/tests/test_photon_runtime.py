"""
✅ Photon Runtime Tests
-----------------------
Unit tests for the Photon runtime + Wiki import bridge.
"""

import pytest
from pathlib import Path
from backend.modules.wiki_capsules.photon_runtime.photon_executor_extension import run_photon_file, simulate_photon_runtime
from backend.modules.wiki_capsules.integration.kg_query_extensions import add_capsule_to_kg
from backend.modules.wiki_capsules.foundations.wiki_capsule_schema import make_capsule


def test_run_photon_file_with_import(tmp_path):
    cap = make_capsule("Nova", "noun", ["a sudden bright star"], [])
    add_capsule_to_kg(cap, "Lexicon", tmp_path / "Nova.wiki.phn")
    phn_file = tmp_path / "nova_test.phn"
    phn_file.write_text("📚Lexicon>Nova\n⊕ combine {a,b}", encoding="utf-8")
    result = run_photon_file(str(phn_file))
    assert result["status"] == "executed"
    assert any(i["lemma"] == "Nova" for i in result["imports"])

def test_simulate_photon_runtime(tmp_path):
    cap = make_capsule("Photon", "noun", ["a particle of light"], [])
    add_capsule_to_kg(cap, "Lexicon", tmp_path / "Photon.wiki.phn")
    content = "main { 📚Lexicon>Photon }"
    result = simulate_photon_runtime(content)
    assert result["status"] == "ok"
    assert any(i["lemma"] == "Photon" for i in result["imports"])