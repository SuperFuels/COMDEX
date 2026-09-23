from pathlib import Path

APP = Path("desktop/mac/src/app.js")
CSS = Path("desktop/mac/src/styles.css")

def test_visibility_polish_override_installed():
    text = APP.read_text()
    assert "AION-GOAL-ENGINE-BOARDROOM-VISIBILITY-POLISH-V1:START" in text
    assert "installAionGoalEngineBoardroomVisibilityPolishV1" in text
    assert "window.renderAionGoalEngineVariantComparisonViewerV1" in text
    assert "window.renderAionGoalEngineMemoryRuntimePanelV1" in text

def test_variant_comparison_recovers_variant_rows():
    text = APP.read_text()
    assert "variantEvidence" in text
    assert "rankedVariants" in text
    assert "aion-boardroom-variant-detail-list" in text
    assert "variantRows.length" in text
    assert "evidence_count" in text

def test_memory_runtime_reads_tier_counts():
    text = APP.read_text()
    assert "item.tier_counts" in text
    assert "item.memory_tier_counts" in text
    assert "item.tiers" in text
    assert "item.tier_summary" in text
    assert "long_term_advisory" in text or "tier_counts" in text

def test_visibility_polish_css_installed():
    text = CSS.read_text()
    assert "AION-GOAL-ENGINE-BOARDROOM-VISIBILITY-POLISH-CSS-V1:START" in text
    assert ".aion-boardroom-goal-engine-visibility-audit" in text
    assert ".aion-boardroom-variant-detail-row" in text
    assert ".aion-boardroom-goal-engine-visibility-audit .aion-goal-engine-container-projection" in text
