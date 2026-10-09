from types import SimpleNamespace
from pathlib import Path

from backend.modules.aion_business.runtime.department_pilot_conversation_service import (
    DepartmentPilotConversationService,
)


class MemoryContainers:
    def __init__(self):
        self.records = {
            "business_identity": {"name": "Example Co", "revision": 2},
            "brand_foundation": {"tone": "clear", "revision": 3},
            "operational_runtime_summary": {},
        }

    def load_optional_dict(self, _workspace_id, kind):
        return self.records.get(kind)

    def save_dict(self, _workspace_id, kind, payload):
        self.records[kind] = payload
        return "memory"


class ModelRouter:
    def __init__(self, payload):
        self.payload = payload
        self.request = None

    def generate(self, **kwargs):
        self.request = kwargs
        return SimpleNamespace(
            ok=True, content=self.payload, provider="local_model", model="qwen-test",
            fallback_used=False, error_code=None,
        )


def test_marketing_conversation_lets_model_select_safe_content_tool():
    containers = MemoryContainers()
    router = ModelRouter(
        '{"message":"I will create three useful posts.","intent":"create",'
        '"tool_calls":[{"name":"marketing.create_content_plan","arguments":'
        '{"brief":"Three proof-led posts","content_count":3,'
        '"platforms":["facebook_feed"],"formats":["image"]}}]}'
    )
    service = DepartmentPilotConversationService(
        container_repository=containers, provider_router=router,
    )

    result = service.answer(
        "example", "marketing", "Produce three pieces of content for me",
        preferred_provider="local_model", preferred_model="qwen-test",
    )

    assert result["provider"]["model"] == "qwen-test"
    assert result["external_writes_performed"] is False
    assert result["tool_results"][0]["status"] == "completed"
    plan = result["tool_results"][0]["artifact"]["payload"]
    assert plan["requested_content_count"] == 3
    assert len(plan["campaign_schedule"]) == 3
    assert containers.records["operational_runtime_summary"]["department_pilot_artifacts"]
    assert "available_tools" in router.request["prompt"]


def test_external_tool_is_staged_for_approval_and_never_executed():
    router = ModelRouter(
        '{"message":"I prepared the publication.","intent":"schedule",'
        '"tool_calls":[{"name":"marketing.prepare_publication",'
        '"arguments":{"channel":"facebook"}}]}'
    )
    service = DepartmentPilotConversationService(
        container_repository=MemoryContainers(), provider_router=router,
    )

    result = service.answer("example", "marketing", "Post this on Facebook")

    assert result["tool_results"] == []
    assert result["approval_requests"] == [{
        "tool": "marketing.prepare_publication",
        "arguments": {"channel": "facebook"},
        "status": "awaiting_approval",
    }]
    assert result["external_writes_performed"] is False
    assert "Nothing has been published" in result["turn"]["content"]


def test_unregistered_tool_is_ignored():
    router = ModelRouter(
        '{"message":"I can help with that.","intent":"answer",'
        '"tool_calls":[{"name":"shell.delete_everything","arguments":{}}]}'
    )
    service = DepartmentPilotConversationService(
        container_repository=MemoryContainers(), provider_router=router,
    )

    result = service.answer("example", "support", "Help me")

    assert result["tool_results"] == []
    assert result["approval_requests"] == []
    assert result["turn"]["content"] == "I can help with that."


def test_marketing_workspace_uses_governed_conversation_instead_of_fixed_campaign_action():
    source = (Path(__file__).parents[3] / "desktop/mac/src/app.js").read_text(encoding="utf-8")

    assert 'data-aion-marketing-pilot-form="true"' in source
    assert 'department_id: "marketing", user_text: text' in source
    assert "getAionDepartmentPilotModelPreference()" in source
    assert 'item?.tool === "marketing.create_content_plan"' in source
