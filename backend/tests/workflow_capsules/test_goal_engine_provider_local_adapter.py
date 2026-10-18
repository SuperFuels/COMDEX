from backend.modules.aion_business.providers.local_adapter import LocalAdapter
from backend.modules.aion_business.providers.router import ProviderRouter


class FakeLocalTasks:
    def generate(self, prompt: str) -> str:
        return f"generated:{prompt}"

    def summarize(self, prompt: str) -> str:
        return f"summary:{prompt}"

    def classify(self, prompt: str) -> str:
        return "class:lead"

    def rewrite(self, prompt: str) -> str:
        return f"rewrite:{prompt}"


def test_local_adapter_generates_with_safe_usage_metadata():
    adapter = LocalAdapter(tasks=FakeLocalTasks())

    result = adapter.generate(prompt="Draft this", capability="drafting")

    assert result.ok is True
    assert result.provider == "local"
    assert result.content == "generated:Draft this"
    assert result.usage["local_only"] is True
    assert result.usage["external_writes"] == "blocked"
    assert result.usage["business_state_mutation"] == "blocked"


def test_local_adapter_routes_task_level_methods():
    adapter = LocalAdapter(tasks=FakeLocalTasks())

    assert adapter.generate(prompt="Summarize this", capability="summarization").content.startswith("summary:")
    assert adapter.generate(prompt="Classify this", capability="classification").content == "class:lead"
    assert adapter.generate(prompt="Rewrite this", capability="rewrite").content.startswith("rewrite:")


def test_local_adapter_fails_closed_for_unsupported_capability():
    adapter = LocalAdapter(tasks=FakeLocalTasks())

    result = adapter.generate(prompt="Plan", capability="multi_agent_orchestration")

    assert result.ok is False
    assert result.error_code == "local_capability_not_supported:multi_agent_orchestration"
    assert result.usage["external_writes"] == "blocked"


def test_provider_router_calls_local_adapter_when_local_selected():
    router = ProviderRouter(local_adapter=LocalAdapter(tasks=FakeLocalTasks()))

    result = router.generate(
        prompt="Summarize local",
        preferred_provider="local",
        capability="summarization",
        metadata={"capability": "summarization"},
    )

    assert result.ok is True
    assert result.provider == "local"
    assert result.content.startswith("summary:")
    assert result.usage["local_only"] is True


def test_provider_router_local_no_longer_returns_not_implemented():
    router = ProviderRouter(local_adapter=LocalAdapter(tasks=FakeLocalTasks()))

    result = router.generate(
        prompt="Draft local",
        preferred_provider="local",
        capability="drafting",
        metadata={"capability": "drafting"},
    )

    assert result.error_code != "local_provider_not_implemented"
