# File: backend/tests/test_score_sqi.py

import pytest
from backend.modules.symbolic_spreadsheet.scoring.sqi_scorer import score_sqi
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell

# Fixture: cell logic expected to match known pattern
@pytest.fixture
def pattern_match_cell():
    return GlyphCell(
        id="test-001",
        logic="⊕(x, y) ⊗ sin(z) ≡ result",
        trace=["init", "exec1"],
        emotion="inspired",
        prediction="The output converges to result",
        position=[0, 0, 0, 0],
    )

# Fixture: cell with generic logic that shouldn't match any pattern
@pytest.fixture
def non_pattern_cell():
    return GlyphCell(
        id="test-002",
        logic="a + b - c",
        trace=[],
        emotion="neutral",
        prediction="",
        position=[1, 0, 0, 0],
    )

def test_score_sqi_with_pattern_match(pattern_match_cell):
    score = score_sqi(pattern_match_cell)
    print(f"🔬 SQI with pattern match: {score}")
    # Expecting a high score due to emotion, trace, logic, prediction, and pattern match
    assert 0.85 <= score <= 1.0

def test_score_sqi_without_pattern(non_pattern_cell):
    score = score_sqi(non_pattern_cell)
    print(f"🔬 SQI without pattern match: {score}")
    # Expecting a lower score due to missing factors
    assert 0.7 <= score <= 0.8