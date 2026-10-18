from backend.modules.aion_business.providers.router import ProviderRouter


def test_provider_router_checks_manifest_before_provider_call():
    text = open("backend/modules/aion_business/providers/router.py").read()

    assert "_provider_supports_capability" in text
    assert "provider_capability_not_supported" in text
    assert "capability_manifest_checked" in text


def test_provider_router_fails_closed_for_unsupported_resend_reasoning():
    router = ProviderRouter()

    result = router.generate(
        prompt="Think deeply about this plan.",
        preferred_provider="resend",
        capability="reasoning",
        metadata={"fallback_provider": "resend"},
    )

    assert result.ok is False
    assert result.error_code == "provider_capability_not_supported:resend:reasoning"


def test_provider_router_allows_local_supported_drafting():
    router = ProviderRouter()
    result = router.generate(
        prompt="Draft a safe customer reply.",
        preferred_provider="local",
        capability="drafting",
        metadata={"fallback_provider": "local"},
    )

    assert result.provider == "local"
    assert result.ok is True
    assert result.error_code is None
    assert result.content

def test_provider_router_support_aliases_match_existing_capability_names():
    router = ProviderRouter()

    assert router._provider_supports_capability("local", "drafting") is True
    assert router._provider_supports_capability("local", "summarization") is True
    assert router._provider_supports_capability("local", "classification") is True
