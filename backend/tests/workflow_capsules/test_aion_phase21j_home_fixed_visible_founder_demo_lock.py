from backend.services.aion_mission_mode.home_fixed_visible_founder_demo import (
    HomeFixedVisibleFounderDemo,
)


def test_phase21j_demo_builds_for_home_fixed():
    demo = HomeFixedVisibleFounderDemo.build_demo()
    assert demo["schema_version"] == "aion.home_fixed.visible_founder_demo.v1"
    assert demo["business_id"] == "home-fixed"
    assert demo["cockpit_surface"] == "aion_pilot"
    assert demo["demo_hash"].startswith("sha256:")


def test_phase21j_demo_contains_safe_autonomous_outputs():
    demo = HomeFixedVisibleFounderDemo.build_demo()
    assert "draft brand copy" in demo["safe_autonomous_work"]
    assert "draft website preview" in demo["safe_autonomous_work"]
    assert "draft social post" in demo["safe_autonomous_work"]
    assert "draft local SEO plan" in demo["safe_autonomous_work"]


def test_phase21j_artifacts_saved_inside_home_fixed_container():
    demo = HomeFixedVisibleFounderDemo.build_demo()
    assert demo["artifacts"]
    for artifact in demo["artifacts"]:
        assert artifact["container_path"].startswith("business/home-fixed/")
        assert artifact["status"] == "draft_preview"
        assert artifact["artifact_hash"].startswith("sha256:")


def test_phase21j_blocks_domain_deploy_post_and_ad_spend():
    demo = HomeFixedVisibleFounderDemo.build_demo()
    blocked = {item["action_type"] for item in demo["blocked_actions"]}
    assert "domain_purchase" in blocked
    assert "production_deploy" in blocked
    assert "facebook_post_publish" in blocked
    assert "google_ad_spend" in blocked


def test_phase21j_blocked_actions_have_exact_approval_payload_hashes():
    demo = HomeFixedVisibleFounderDemo.build_demo()
    for item in demo["blocked_actions"]:
        assert item["required_approval"] == "exact_payload_approval"
        assert item["expected_payload_hash"].startswith("sha256:")


def test_phase21j_proof_receipt_replay_ets_and_timeline_visible():
    demo = HomeFixedVisibleFounderDemo.build_demo()
    assert demo["proof_hash"].startswith("sha256:")
    assert demo["replay_hash"].startswith("sha256:")
    assert demo["receipt_hash"].startswith("sha256:")
    assert demo["ets_preview_hash"].startswith("sha256:")
    assert demo["timeline_hash"].startswith("sha256:")


def test_phase21j_safety_message_visible():
    demo = HomeFixedVisibleFounderDemo.build_demo()
    assert demo["safety_message"] == "AION stopped itself before doing anything risky."


def test_phase21j_no_unapproved_live_side_effects():
    demo = HomeFixedVisibleFounderDemo.build_demo()
    assert demo["live_side_effects_allowed"] is False
    assert demo["payments_created"] is False
    assert demo["bookings_created"] is False
    assert demo["escrow_created"] is False
    assert demo["external_messages_sent"] is False
    assert demo["public_posts_published"] is False
    assert demo["production_deploys_created"] is False
    assert demo["reputation_mutated"] is False


def test_phase21j_verification_passes():
    demo = HomeFixedVisibleFounderDemo.build_demo()
    verification = HomeFixedVisibleFounderDemo.verify_demo(demo)
    assert verification["verified"] is True
    assert verification["failure_reasons"] == ["home_fixed_visible_founder_demo_valid"]
    assert verification["verification_hash"].startswith("sha256:")


def test_phase21j_verification_fails_if_artifact_escapes_container():
    demo = HomeFixedVisibleFounderDemo.build_demo()
    demo["artifacts"][0]["container_path"] = "tmp/leaked.pdf"
    verification = HomeFixedVisibleFounderDemo.verify_demo(demo)
    assert verification["verified"] is False
    assert "artifact_outside_home_fixed_business_container" in verification["failure_reasons"]
