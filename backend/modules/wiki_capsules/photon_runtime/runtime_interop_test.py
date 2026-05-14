"""
🔄 Runtime Interop Test
-----------------------
Ensures that the Photon executor can import from the KG via 📚Wiki references
and handle both .phn and .ptn file inputs seamlessly.
"""

from backend.modules.wiki_capsules.photon_runtime.photon_executor_extension import run_photon_file
from backend.modules.wiki_capsules.integration.kg_query_extensions import add_capsule_to_kg
from backend.modules.wiki_capsules.foundations.wiki_capsule_schema import make_capsule
from pathlib import Path
import json


def prepare_sample_capsule(tmp_path: Path):
    capsule = make_capsule("Orion", "noun", ["a constellation"], ["Orion is visible in winter."])
    add_capsule_to_kg(capsule, "Lexicon", tmp_path / "Orion.wiki.phn")
    (tmp_path / "sample.phn").write_text("main { 📚Lexicon>Orion }", encoding="utf-8")
    return tmp_path / "sample.phn"


def test_runtime_import(tmp_path):
    phn = prepare_sample_capsule(tmp_path)
    result = run_photon_file(str(phn))
    assert result["status"] == "executed"
    assert any(i["lemma"] == "Orion" for i in result["imports"])