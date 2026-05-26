from backend.modules.aion_business.providers.router import ProviderRouter


def test_provider_router_audit_includes_runtime_metric_fields():
    router = ProviderRouter()

    result = router.generate(
        prompt="Draft a short test message.",
        preferred_provider="local",
        capability="drafting",
        metadata={"workspace_id": "test_workspace"},
        max_tokens=256,
    )

    audit = (result.raw or {}).get("provider_audit")
    assert isinstance(audit, dict)

    assert "provider" in audit
    assert "capability" in audit
    assert "fallback_used" in audit
    assert "latency_ms" in audit

    assert "token_count" in audit
    assert "prompt_tokens" in audit
    assert "completion_tokens" in audit
    assert "total_tokens" in audit
    assert "cost_estimate" in audit
    assert "runtime_duration_ms" in audit
    assert "degradation_mode" in audit
    assert "degradation_event" in audit


def test_provider_router_audit_keeps_local_provider_safe():
    router = ProviderRouter()

    result = router.generate(
        prompt="Summarise this safely.",
        preferred_provider="local",
        capability="summarization",
        max_tokens=128,
    )

    audit = (result.raw or {}).get("provider_audit")
    assert audit["external_writes"] == "blocked"
    assert audit["business_state_mutation"] == "human_review_guarded"
    assert audit["would_grant_permission"] is False


def test_provider_runtime_metrics_are_numbers_or_safe_defaults():
    router = ProviderRouter()

    result = router.generate(
        prompt="Classify this: test",
        preferred_provider="local",
        capability="classification",
        max_tokens=64,
    )

    audit = (result.raw or {}).get("provider_audit")

    assert isinstance(audit["latency_ms"], int)
    assert isinstance(audit["runtime_duration_ms"], int)
    assert isinstance(audit["token_count"], int)
    assert isinstance(audit["prompt_tokens"], int)
    assert isinstance(audit["completion_tokens"], int)
    assert isinstance(audit["total_tokens"], int)
    assert isinstance(audit["cost_estimate"], float)
    assert audit["cost_estimate"] >= 0.0


def test_provider_runtime_metrics_surface_fallback_or_degradation_state():
    router = ProviderRouter()

    result = router.generate(
        prompt="Test unsupported capability.",
        preferred_provider="local",
        capability="reasoning",
        metadata={"fallback_provider": "local"},
        max_tokens=64,
    )

    audit = (result.raw or {}).get("provider_audit")
    assert isinstance(audit, dict)
    assert "degradation_event" in audit
    assert "degradation_mode" in audit
    assert audit["failed_closed"] in {True, False}
