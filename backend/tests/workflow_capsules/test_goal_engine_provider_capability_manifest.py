from backend.modules.aion_business.providers.capability_manifest import (
    PROVIDER_CAPABILITY_MANIFEST_SCHEMA_VERSION,
    build_provider_capability_manifest,
    provider_manifest_for_ui,
)


def test_provider_capability_manifest_names_core_providers():
    manifest = build_provider_capability_manifest(
        provider_status={"local": True, "openai": False, "anthropic": False}
    )

    assert set(manifest) >= {"local", "openai", "anthropic"}

    assert manifest["local"]["default_model"] == "gemma"
    assert manifest["openai"]["default_model"] == "gpt-4.1-mini"
    assert manifest["anthropic"]["default_model"] == "claude-sonnet-4-20250514"


def test_provider_capability_manifest_exposes_required_capability_flags():
    manifest = build_provider_capability_manifest(provider_status={"local": True})
    local = manifest["local"]
    anthropic = manifest["anthropic"]

    for key in [
        "supports_long_running_sessions",
        "supports_checkpoint_resume",
        "supports_sandboxed_execution",
        "supports_outcome_evaluation",
        "supports_memory_dreaming",
        "supports_multi_agent_orchestration",
        "supports_mcp_private_connectors",
        "max_tokens",
        "max_cost_per_task",
        "runtime_limits",
        "fallback_provider",
        "degradation_mode",
        "disclosure",
    ]:
        assert key in local

    assert local["supports_sandboxed_execution"] is True
    assert local["supports_memory_dreaming"] is True
    assert anthropic["enhanced_mode"] is True


def test_provider_capability_manifest_safe_defaults_for_business_state():
    payload = provider_manifest_for_ui(provider_status={"local": True})

    assert payload["schema_version"] == PROVIDER_CAPABILITY_MANIFEST_SCHEMA_VERSION
    assert payload["trace_type"] == "provider_capability_manifest"

    safe = payload["safe_defaults"]
    assert safe["external_writes_require_approval"] is True
    assert safe["business_state_mutations_require_human_review"] is True
    assert safe["local_provider_does_not_grant_permission"] is True
    assert safe["provider_disclosure_required_in_ui"] is True


def test_provider_capability_manifest_has_ui_disclosure_for_each_provider():
    payload = provider_manifest_for_ui(provider_status={"local": True})
    providers = payload["providers"]

    for provider in ["local", "openai", "anthropic"]:
        assert providers[provider]["disclosure"]
        assert providers[provider]["degradation_mode"]
        assert "capabilities" in providers[provider]
