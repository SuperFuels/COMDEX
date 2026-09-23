from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def _block():
    text = APP.read_text()
    start = text.index("AION-GOAL-ENGINE-VARIANT-COMPARISON-VIEWER-V1:START")
    end = text.index("AION-GOAL-ENGINE-VARIANT-COMPARISON-VIEWER-V1:END")
    return text[start:end]

def test_variant_viewer_has_two_clear_subsections():
    block = _block()
    assert "Experiment evidence" in block
    assert "Variant rankings" in block
    assert "Manual decision required" in block

def test_variant_viewer_does_not_auto_choose_winner():
    block = _block()
    assert "winner declared: false" in block
    assert "does not auto-select winners" in block
    assert "no experiment mutation performed" in block

def test_variant_viewer_uses_one_container_not_duplicate_cards():
    block = _block()
    assert block.count('data-aion-goal-engine-variant-comparison="v1"') == 2
    assert "experimentHtml" in block
    assert "rankingsHtml" in block
    assert "rankedVariants" in block

def test_variant_viewer_recovers_scores_from_ranked_variants():
    block = _block()
    assert "ranked_variants" in block
    assert "variant_scores" in block
    assert "outcome_score" in block
    assert "quality_score" in block
    assert "evidence_count" in block
