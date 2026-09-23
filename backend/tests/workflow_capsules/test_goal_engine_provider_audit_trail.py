from backend.modules.aion_business.providers.local_adapter import LocalAdapter
from backend.modules.aion_business.providers.router import ProviderRouter


class FakeLocalTasks:
    def generate(self, prompt):
        return "drafted:" + prompt

    def summarize(self, prompt):
        return "summary:" + prompt

    def classify(self, prompt):
        return "classification:lead"

    def rewrite(self, prompt):
        return "rewrite:" + prompt


def test_provider_router_records_audit_trail_for_successful_local_call():
    router = ProviderRouter(local_adapter=LocalAdapter(tasks=FakeLocalTasks()))

    result = router.generate(
        prompt="Draft a safe reply.",
        preferred_provider="local",
        capability="drafting",
        metadata={"workspace_id": "costa-conexion", "task_id": "task_001"},
    )

    assert result.ok is True
    assert result.provider == "local"
    assert result.raw["provider_audit"]["provider"] == "local"
    assert result.raw["provider_audit"]["capability"] == "drafting"
    assert result.raw["provider_audit"]["local_only"] is True
    assert result.raw["provider_audit"]["external_writes"] == "blocked"
    assert result.raw["provider_audit"]["business_state_mutation"] == "human_review_guarded"
    assert result.raw["provider_audit"]["legacy_business_state_mutation"] == "blocked"


def test_provider_router_records_audit_trail_for_rejected_capability():
    router = ProviderRouter(local_adapter=LocalAdapter(tasks=FakeLocalTasks()))

    result = router.generate(
        prompt="Send an email directly.",
        preferred_provider="resend",
        capability="reasoning",
        metadata={"workspace_id": "costa-conexion"},
    )

    assert result.ok is False
    assert result.error_code == "provider_capability_not_supported:resend:reasoning"
    assert result.raw["provider_audit"]["provider"] == "resend"
    assert result.raw["provider_audit"]["capability"] == "reasoning"
    assert result.raw["provider_audit"]["capability_manifest_checked"] is True
    assert result.raw["provider_audit"]["failed_closed"] is True


def test_provider_router_audit_trail_preserves_fallback_used():
    router = ProviderRouter(local_adapter=LocalAdapter(tasks=FakeLocalTasks()))

    result = router.generate(
        prompt="Draft a fallback reply.",
        preferred_provider="openai",
        capability="drafting",
        metadata={"fallback_provider": "local"},
    )

    assert result.ok is True
    assert result.provider == "local"
    assert result.fallback_used is True
    assert result.raw["provider_audit"]["fallback_used"] is True
    assert result.raw["provider_audit"]["provider"] == "local"


def test_provider_router_source_contains_audit_builder():
    text = open("backend/modules/aion_business/providers/router.py").read()

    assert "_build_provider_audit" in text
    assert "provider_audit" in text
    assert "external_writes" in text
    assert "business_state_mutation" in text
