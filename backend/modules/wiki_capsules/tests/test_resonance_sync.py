import pytest
from backend.AION.resonance.resonance_engine import update_resonance, get_resonance
from backend.modules.wiki_capsules.resonance_feedback.wiki_resonance_sync import sync_resonance_with_kg

def test_resonance_update_and_sync(tmp_path, monkeypatch):
    update_resonance("light", ["wave","energy"])
    assert get_resonance("light")["SQI"] > 0
    sync_resonance_with_kg("Lexicon")