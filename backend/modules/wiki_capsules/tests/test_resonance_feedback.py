"""
Tests for resonance feedback and alignment.
"""
import pytest
from backend.modules.wiki_capsules.resonance_feedback import (
    resonance_alignment,
    wiki_resonance_sync
)

def test_align_resonance_basic():
    meta = {"ρ": 0.7, "Ī": 0.9, "sqi_score": 0.8}
    state = resonance_alignment.align_resonance(meta)
    assert isinstance(state, resonance_alignment.ResonanceState)
    assert 0 <= state.sqi_score <= 1
    assert round(state.rho, 2) > 0
    assert round(state.Ibar, 2) > 0

def test_sync_wiki_resonance_merges_feedback():
    wiki_meta = {"ρ": 0.6, "Ī": 0.8, "sqi_score": 0.7}
    feedback = {"ρ": 0.9, "Ī": 0.7, "sqi_score": 0.8}

    state = wiki_resonance_sync.sync_wiki_resonance(wiki_meta, feedback)
    # After sync, wiki_meta should be updated
    assert "ρ" in wiki_meta and "Ī" in wiki_meta
    assert abs(wiki_meta["ρ"] - state.rho) < 1e-6
    assert abs(wiki_meta["Ī"] - state.Ibar) < 1e-6
    assert 0 <= state.sqi_score <= 1.0