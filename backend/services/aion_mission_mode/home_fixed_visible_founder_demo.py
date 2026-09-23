import hashlib
import json
from typing import Any, Dict, List


class HomeFixedVisibleFounderDemoError(Exception):
    pass


class HomeFixedVisibleFounderDemo:
    REQUIRED_SAFETY_MESSAGE = "AION stopped itself before doing anything risky."

    BLOCKED_LIVE_ACTIONS = {
        "domain_purchase",
        "production_deploy",
        "facebook_post_publish",
        "google_ad_spend",
        "payment_submit",
        "booking_create",
        "escrow_create",
        "external_message_send",
        "reputation_mutation",
    }

    @staticmethod
    def canonical_hash(payload: Dict[str, Any]) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()

    @classmethod
    def build_demo(cls) -> Dict[str, Any]:
        artifacts = [
            {
                "artifact_type": "brand_copy",
                "title": "Home Fixed service positioning draft",
                "status": "draft_preview",
                "container_path": "business/home-fixed/missions/home_fixed_founder_demo/runs/demo_run/artifacts/brand-copy.md",
                "artifact_hash": "sha256:home_fixed_brand_copy_preview",
            },
            {
                "artifact_type": "website_preview",
                "title": "Home Fixed website preview",
                "status": "draft_preview",
                "container_path": "business/home-fixed/missions/home_fixed_founder_demo/runs/demo_run/artifacts/website-preview/",
                "artifact_hash": "sha256:home_fixed_website_preview",
            },
            {
                "artifact_type": "social_post",
                "title": "Outdoor living Facebook post draft",
                "status": "draft_preview",
                "container_path": "business/home-fixed/missions/home_fixed_founder_demo/runs/demo_run/artifacts/facebook-post-draft.md",
                "artifact_hash": "sha256:home_fixed_social_post_preview",
            },
            {
                "artifact_type": "seo_plan",
                "title": "Local SEO plan draft",
                "status": "draft_preview",
                "container_path": "business/home-fixed/missions/home_fixed_founder_demo/runs/demo_run/artifacts/local-seo-plan.md",
                "artifact_hash": "sha256:home_fixed_seo_plan_preview",
            },
        ]

        blocked_actions = [
            {
                "action_type": "domain_purchase",
                "reason": "Domain purchase spends money and requires exact approval.",
                "safe_alternative": "Prepare checkout preview only.",
                "required_approval": "exact_payload_approval",
                "expected_payload_hash": "sha256:domain_checkout_preview_payload",
            },
            {
                "action_type": "production_deploy",
                "reason": "Production deployment mutates a live public surface.",
                "safe_alternative": "Prepare Vercel preview only.",
                "required_approval": "exact_payload_approval",
                "expected_payload_hash": "sha256:deployment_preview_payload",
            },
            {
                "action_type": "facebook_post_publish",
                "reason": "Public posting is an external live action.",
                "safe_alternative": "Create draft post only.",
                "required_approval": "exact_payload_approval",
                "expected_payload_hash": "sha256:facebook_post_payload",
            },
            {
                "action_type": "google_ad_spend",
                "reason": "Ad campaign activation spends money.",
                "safe_alternative": "Create ad preview and budget estimate only.",
                "required_approval": "exact_payload_approval",
                "expected_payload_hash": "sha256:google_ad_budget_payload",
            },
        ]

        demo = {
            "schema_version": "aion.home_fixed.visible_founder_demo.v1",
            "business_id": "home-fixed",
            "mission_id": "home_fixed_founder_demo",
            "mission_run_id": "demo_run",
            "cockpit_surface": "aion_pilot",
            "demo_state": "visible_preview_ready",
            "safe_autonomous_work": [
                "draft brand copy",
                "draft website preview",
                "draft social post",
                "draft local SEO plan",
                "prepare proof and replay",
            ],
            "approval_required_work": [
                "domain purchase",
                "production deploy",
                "public social post",
                "ad spend",
            ],
            "artifacts": artifacts,
            "blocked_actions": blocked_actions,
            "proof_hash": "sha256:home_fixed_demo_proof_preview",
            "replay_hash": "sha256:home_fixed_demo_replay_preview",
            "receipt_hash": "sha256:home_fixed_demo_receipt_preview",
            "ets_preview_hash": "sha256:home_fixed_demo_ets_preview",
            "timeline_hash": "sha256:home_fixed_demo_timeline",
            "safety_message": cls.REQUIRED_SAFETY_MESSAGE,
            "live_side_effects_allowed": False,
            "payments_created": False,
            "bookings_created": False,
            "escrow_created": False,
            "external_messages_sent": False,
            "public_posts_published": False,
            "production_deploys_created": False,
            "reputation_mutated": False,
        }
        demo["demo_hash"] = cls.canonical_hash(demo)
        return demo

    @classmethod
    def verify_demo(cls, demo: Dict[str, Any]) -> Dict[str, Any]:
        failures: List[str] = []

        if demo.get("business_id") != "home-fixed":
            failures.append("business_id_must_be_home_fixed")

        if demo.get("safety_message") != cls.REQUIRED_SAFETY_MESSAGE:
            failures.append("missing_required_safety_message")

        for field in [
            "live_side_effects_allowed",
            "payments_created",
            "bookings_created",
            "escrow_created",
            "external_messages_sent",
            "public_posts_published",
            "production_deploys_created",
            "reputation_mutated",
        ]:
            if demo.get(field) is not False:
                failures.append(f"{field}_must_be_false")

        for artifact in demo.get("artifacts", []):
            path = artifact.get("container_path", "")
            if not path.startswith("business/home-fixed/"):
                failures.append("artifact_outside_home_fixed_business_container")
            if artifact.get("status") != "draft_preview":
                failures.append("artifact_must_remain_draft_preview")

        blocked_types = {item.get("action_type") for item in demo.get("blocked_actions", [])}
        required = {
            "domain_purchase",
            "production_deploy",
            "facebook_post_publish",
            "google_ad_spend",
        }
        if not required.issubset(blocked_types):
            failures.append("required_risky_actions_not_blocked")

        result = {
            "verified": not failures,
            "failure_reasons": failures or ["home_fixed_visible_founder_demo_valid"],
            "demo_hash": demo.get("demo_hash"),
            "proof_hash": demo.get("proof_hash"),
            "replay_hash": demo.get("replay_hash"),
            "receipt_hash": demo.get("receipt_hash"),
            "ets_preview_hash": demo.get("ets_preview_hash"),
            "timeline_hash": demo.get("timeline_hash"),
        }
        result["verification_hash"] = cls.canonical_hash(result)
        return result
