# ✅ File: backend/tests/test_innovation_scorer.py

import pytest
from typing import Dict, Any
from backend.modules.creative.innovation_scorer import compute_innovation_score

def test_baseline_score():
    idea = {
        "novelty": 0.5,
        "coherence": 0.5,
        "entropy": 0.5,
        "impact": 0.5,
        "alignment": 0.5
    }
    score = compute_innovation_score(idea, mutated=False)
    assert 0 <= score <= 1

def test_missing_fields_fallback():
    idea = {
        "novelty": 0.8,
        "impact": 0.6
    }
    score = compute_innovation_score(idea, mutated=True)
    assert isinstance(score, float)

def test_high_entropy_penalty():
    idea_low_entropy = {
        "novelty": 0.9,
        "coherence": 0.8,
        "entropy": 0.1,
        "impact": 0.9,
        "alignment": 0.9
    }
    idea_high_entropy = {
        "novelty": 0.9,
        "coherence": 0.8,
        "entropy": 0.95,
        "impact": 0.9,
        "alignment": 0.9
    }
    score_low = compute_innovation_score(idea_low_entropy, mutated=True)
    score_high = compute_innovation_score(idea_high_entropy, mutated=True)
    assert score_high < score_low  # High entropy should lower score

def test_perfect_alignment_boost():
    idea = {
        "novelty": 0.6,
        "coherence": 0.7,
        "entropy": 0.3,
        "impact": 0.8,
        "alignment": 1.0
    }
    boosted = compute_innovation_score(idea, mutated=True)
    assert boosted > 0.6

def test_mutated_boost():
    idea = {
        "novelty": 0.6,
        "coherence": 0.7,
        "entropy": 0.3,
        "impact": 0.8,
        "alignment": 0.9
    }
    original = compute_innovation_score(idea, mutated=False)
    mutated = compute_innovation_score(idea, mutated=True)
    assert mutated > original
