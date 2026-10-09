from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
STATE_CONTRACTS = (ROOT / "desktop/mac/src/lib/desktop-state-contracts.js").read_text(encoding="utf-8")
BUSINESS_CONTAINERS = (
    ROOT / "backend/modules/aion_business/runtime/business_container_service.py"
).read_text(encoding="utf-8")


def test_new_desktop_marketing_form_contains_no_demo_customer_or_campaign():
    start = STATE_CONTRACTS.index("function buildDefaultMarketingForm()")
    end = STATE_CONTRACTS.index("function normalizeMarketingForm", start)
    defaults = STATE_CONTRACTS[start:end]

    assert 'brief: ""' in defaults
    assert 'targetAudience: ""' in defaults
    assert 'persona: ""' in defaults
    assert 'offer: ""' in defaults
    assert "spring telecom" not in defaults.lower()
    assert "core service towns" not in defaults.lower()


def test_marketing_template_and_library_state_survive_startup_normalization():
    start = STATE_CONTRACTS.index("function normalizeMarketingForm(value)")
    end = STATE_CONTRACTS.index("function buildDefaultBrandIntelligenceMap", start)
    normalizer = STATE_CONTRACTS[start:end]

    assert "brandedTemplates:" in normalizer
    assert "selectedBrandedTemplateId:" in normalizer
    assert "templateOverrides:" in normalizer
    assert "savedLibraryItems:" in normalizer
    assert "aionCampaignLatestRun:" in normalizer
    assert "aionCampaignCanvasCleared:" in normalizer
    assert "selectedPersonaIds:" in normalizer


def test_new_backend_brand_foundation_contains_no_invented_business_facts():
    start = BUSINESS_CONTAINERS.index("def _default_brand_foundation_model")
    end = BUSINESS_CONTAINERS.index("def _build_default_brand_intelligence_map", start)
    defaults = BUSINESS_CONTAINERS[start:end]

    assert 'target_audience=""' in defaults
    assert 'persona=""' in defaults
    assert 'offer=""' in defaults
    assert 'or "Costa Conexion"' not in defaults
    assert "Local homeowners" not in defaults
