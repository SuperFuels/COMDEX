from types import SimpleNamespace

from backend.api import local_node_router


def test_brand_template_generation_uses_selected_model_and_returns_structured_template(monkeypatch):
    captured = {}

    class DraftSkill:
        def run(self, request):
            captured["request"] = request
            return SimpleNamespace(
                ok=True,
                error_code=None,
                output_payload={
                    "draft": """{
                      "name_suggestion": "Coastal Product",
                      "design_summary": "Clean product-led layout",
                      "primary_color": "#14213d",
                      "secondary_color": "#f8fafc",
                      "accent_color": "#2563eb",
                      "headline_font": "Inter",
                      "body_font": "Inter",
                      "shapes": "Rounded cards",
                      "image_treatment": "Full bleed product image",
                      "text_layout": "Bottom-left text panel",
                      "logo_position": "Top right",
                      "cta_style": "Rounded blue button",
                      "sample_headline": "Built for everyday life",
                      "sample_body": "A concise supporting line"
                    }""",
                    "provider": "openai",
                    "model": "gpt-test",
                },
            )

    runtime = SimpleNamespace(
        config=SimpleNamespace(workspace_id="workspace-test"),
        workflow_execution_runtime=SimpleNamespace(draft_content_skill=DraftSkill()),
    )
    monkeypatch.setattr(local_node_router, "get_runtime", lambda workspace_id=None: runtime)

    request = local_node_router.GenerateMarketingBrandTemplateRequest(
        workspace_id="workspace-test",
        selected_provider="openai",
        selected_model="gpt-test",
        platform_template="instagram_feed",
        platform_label="Instagram",
        format_label="Single image post",
        canvas_size="1080 × 1350 px",
        aspect_ratio="4:5 portrait",
        description="Clean coastal product layout",
    )
    result = local_node_router.generate_marketing_brand_template(request)

    assert result["ok"] is True
    assert result["template"]["name_suggestion"] == "Coastal Product"
    assert captured["request"].input_payload["provider"] == "openai"
    assert captured["request"].input_payload["preferred_model"] == "gpt-test"
    assert "strict JSON" in captured["request"].input_payload["prompt"]


def test_brand_template_generation_recovers_from_non_json_model_output(monkeypatch):
    class DraftSkill:
        def run(self, request):
            return SimpleNamespace(
                ok=True,
                error_code=None,
                output_payload={
                    "draft": """Here is the reusable template:\n"
                    "name_suggestion: Coastal Trust\n"
                    "design_summary: Clean image-led layout with restrained text\n"
                    "primary_color: #14213d\n"
                    "accent_color: #0f8b8d\n"
                    "sample_headline: Built for the coast""",
                    "provider": "local_model",
                    "model": "qwen-test",
                },
            )

    runtime = SimpleNamespace(
        config=SimpleNamespace(workspace_id="workspace-test"),
        workflow_execution_runtime=SimpleNamespace(draft_content_skill=DraftSkill()),
    )
    monkeypatch.setattr(local_node_router, "get_runtime", lambda workspace_id=None: runtime)

    request = local_node_router.GenerateMarketingBrandTemplateRequest(
        workspace_id="workspace-test",
        selected_provider="local_model",
        selected_model="qwen-test",
        platform_template="facebook_reel",
        platform_label="Facebook",
        format_label="Reel / video",
        canvas_size="1080 × 1920 px",
        aspect_ratio="9:16 vertical",
        description="Premium architectural promotion",
        brand_foundation={"secondary_color": "#ffffff", "primary_font": "Manrope"},
    )

    result = local_node_router.generate_marketing_brand_template(request)

    assert result["ok"] is True
    assert result["template"]["name_suggestion"] == "Coastal Trust"
    assert result["template"]["accent_color"] == "#0f8b8d"
    assert result["template"]["secondary_color"] == "#ffffff"
    assert result["template"]["headline_font"] == "Manrope"


def test_brand_template_regeneration_forces_a_new_visible_layout(monkeypatch):
    class DraftSkill:
        def run(self, request):
            return SimpleNamespace(
                ok=True,
                error_code=None,
                output_payload={"draft": "name_suggestion: Repeated local result", "provider": "local_model", "model": "qwen-test"},
            )

    runtime = SimpleNamespace(
        config=SimpleNamespace(workspace_id="workspace-test"),
        workflow_execution_runtime=SimpleNamespace(draft_content_skill=DraftSkill()),
    )
    monkeypatch.setattr(local_node_router, "get_runtime", lambda workspace_id=None: runtime)
    previous = {"layout_variant": "full_bleed", "sample_headline": "A clear benefit-led headline"}
    request = local_node_router.GenerateMarketingBrandTemplateRequest(
        workspace_id="workspace-test",
        selected_provider="local_model",
        selected_model="qwen-test",
        platform_template="facebook_reel",
        platform_label="Facebook",
        format_label="Reel / video",
        canvas_size="1080 × 1920 px",
        aspect_ratio="9:16 vertical",
        description="Premium architectural promotion",
        previous_template=previous,
        generation_index=1,
    )

    result = local_node_router.generate_marketing_brand_template(request)

    assert result["template"]["layout_variant"] == "framed"
    assert result["template"]["sample_headline"] != previous["sample_headline"]
