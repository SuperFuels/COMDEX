from backend.modules.aion_business.runtime.creative_provider_adapters import (
    gemini_veo_request,
    openai_video_request,
)
from backend.modules.aion_business.runtime.marketing_creative_engine import MarketingCreativeEngine
from backend.modules.aion_business.skills.draft_content import DraftContentSkill
from backend.modules.aion_business.contracts.skills import SkillRunRequest


def test_plan_builds_platform_renditions_and_controlled_experiment():
    plan = MarketingCreativeEngine().build_plan({
        "brief": "Show how a homeowner gets a repair reviewed",
        "audience": "Homeowners in Almeria",
        "offer": "Human-reviewed repair request",
        "platforms": ["instagram_feed", "tiktok", "youtube_shorts"],
        "formats": ["image", "video", "clip"],
        "variant_count": 4,
    })
    assert plan["status"] == "ready_for_review"
    assert plan["auto_publish"] is False
    assert plan["auto_spend"] is False
    assert {item["ratio"] for item in plan["renditions"]} == {"4:5", "9:16"}
    variants = plan["experiment"]["variants"]
    assert [item["controlled_variable"] for item in variants] == [
        "control", "hook", "opening_visual", "call_to_action"
    ]
    assert all(job["requires_approval"] for job in plan["generation_jobs"])


def test_experiment_does_not_declare_winner_without_enough_evidence():
    result = MarketingCreativeEngine().evaluate_experiment({
        "variants": [
            {"id": "A", "sample_size": 20, "primary_metric": 0.1},
            {"id": "B", "sample_size": 20, "primary_metric": 0.2},
        ]
    })
    assert result["status"] == "collect_more_evidence"
    assert result["winner_candidate"] is None
    assert result["auto_apply"] is False


def test_experiment_marks_only_guardrail_safe_winner_candidate():
    result = MarketingCreativeEngine().evaluate_experiment({
        "variants": [
            {"id": "A", "sample_size": 200, "primary_metric": 0.10, "complaint_rate": 0.01},
            {"id": "B", "sample_size": 200, "primary_metric": 0.13, "complaint_rate": 0.01},
        ]
    })
    assert result["status"] == "winner_candidate"
    assert result["winner_candidate"] == "B"
    assert result["requires_approval"] is True


def test_provider_request_builders_obey_supported_dimensions_and_durations():
    openai = openai_video_request("A repair story", "9:16", 9)
    assert openai["size"] == "720x1280"
    assert openai["seconds"] == "8"
    gemini = gemini_veo_request("A repair story", "16:9", 20)
    assert gemini["config"]["durationSeconds"] == 8


def test_one_week_instruction_builds_seven_day_approval_gated_calendar():
    plan = MarketingCreativeEngine().build_plan({
        "brief": "Create a 1 week Facebook campaign for car ports in Almeria",
        "audience": "Homeowners in Almeria",
        "offer": "Car port installation",
        "platforms": ["facebook_feed", "facebook_reels"],
        "formats": ["image", "video"],
    })
    assert plan["duration_days"] == 7
    assert len(plan["campaign_schedule"]) == 7
    assert {item["platform"] for item in plan["campaign_schedule"]} == {
        "facebook_feed", "facebook_reels"
    }
    assert all(item["requires_approval"] for item in plan["campaign_schedule"])


def test_safe_fallback_copy_uses_business_name_and_human_review_boundary():
    request = SkillRunRequest(
        skill_id="draft_content",
        agent_id="marketing_test_agent",
        objective="Generate qualified enquiries",
        input_payload={"prompt": "Draft a campaign", "workspace_id": "home-fixed"},
    )
    copy = DraftContentSkill._build_fallback_content(
        prompt="Draft a campaign",
        title="HomeFixed campaign",
        metadata={
            "workspace_id": "home-fixed",
            "offer": "a car port installation project",
            "target_audience": "homeowners in Almeria",
        },
        request=request,
    )
    assert "Home Fixed" in copy
    assert "price, booking or work is confirmed" in copy
    assert "Now promoting" not in copy
