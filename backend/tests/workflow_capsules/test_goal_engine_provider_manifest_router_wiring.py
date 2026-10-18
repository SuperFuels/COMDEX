from backend.modules.aion_business.providers.router import ProviderRouter


def test_provider_router_exposes_capability_manifest():
    router = ProviderRouter()
    payload = router.capability_manifest()

    assert payload["trace_type"] == "provider_capability_manifest"
    assert "providers" in payload
    assert "local" in payload["providers"]
    assert "openai" in payload["providers"]
    assert "anthropic" in payload["providers"]


def test_provider_router_manifest_marks_local_available_without_api_key():
    router = ProviderRouter()
    payload = router.capability_manifest()

    local = payload["providers"]["local"]

    assert local["configured"] is True
    assert local["default_model"] == "gemma"
    assert local["runtime_limits"]["network"] == "local_only"
    assert local["runtime_limits"]["external_writes"] == "blocked"


def test_provider_router_manifest_discloses_cloud_key_status():
    router = ProviderRouter()
    payload = router.capability_manifest()

    openai = payload["providers"]["openai"]
    anthropic = payload["providers"]["anthropic"]

    assert "configured" in openai
    assert "configured" in anthropic
    assert openai["runtime_limits"]["network"] == "cloud"
    assert anthropic["runtime_limits"]["network"] == "cloud"


def test_provider_router_manifest_preserves_safe_defaults():
    router = ProviderRouter()
    payload = router.capability_manifest()

    safe = payload["safe_defaults"]

    assert safe["external_writes_require_approval"] is True
    assert safe["business_state_mutations_require_human_review"] is True
    assert safe["local_provider_does_not_grant_permission"] is True
    assert safe["provider_disclosure_required_in_ui"] is True
