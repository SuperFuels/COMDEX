"""Provider-neutral creative planning and evidence-governed experiment learning."""

from __future__ import annotations

import hashlib
import json
import os
import re
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any


PLATFORM_PROFILES: dict[str, dict[str, Any]] = {
    "instagram_feed": {"label": "Instagram feed", "ratio": "4:5", "width": 1080, "height": 1350, "formats": ["image", "video", "carousel"], "preferred_seconds": [6, 30]},
    "instagram_reels": {"label": "Instagram Reels", "ratio": "9:16", "width": 1080, "height": 1920, "formats": ["video", "clip"], "preferred_seconds": [15, 30]},
    "instagram_stories": {"label": "Instagram Stories", "ratio": "9:16", "width": 1080, "height": 1920, "formats": ["image", "video", "clip"], "preferred_seconds": [6, 15]},
    "facebook_feed": {"label": "Facebook feed", "ratio": "4:5", "width": 1080, "height": 1350, "formats": ["image", "video", "carousel"], "preferred_seconds": [6, 30]},
    "facebook_reels": {"label": "Facebook Reels", "ratio": "9:16", "width": 1080, "height": 1920, "formats": ["video", "clip"], "preferred_seconds": [15, 30]},
    "tiktok": {"label": "TikTok", "ratio": "9:16", "width": 1080, "height": 1920, "formats": ["video", "clip"], "preferred_seconds": [21, 30], "source": "https://ads.tiktok.com/help/article/global-app-bundle-video-ad-specifications"},
    "youtube_shorts": {"label": "YouTube Shorts", "ratio": "9:16", "width": 1080, "height": 1920, "formats": ["video", "clip"], "preferred_seconds": [15, 45], "maximum_seconds": 180, "source": "https://support.google.com/youtube/answer/15424877"},
    "linkedin_feed": {"label": "LinkedIn feed", "ratio": "4:5", "width": 1080, "height": 1350, "formats": ["image", "carousel"], "preferred_seconds": [3, 30]},
    "linkedin_video": {"label": "LinkedIn video", "ratio": "4:5", "width": 1080, "height": 1350, "formats": ["video", "clip"], "preferred_seconds": [15, 30], "source": "https://business.linkedin.com/advertise/ads/sponsored-content/video-ads/specs"},
}

PROVIDER_CAPABILITIES: dict[str, dict[str, Any]] = {
    "openai": {"label": "OpenAI", "image": True, "video": True, "models": ["gpt-image-1", "sora-2", "sora-2-pro"], "direct": True, "docs": "https://platform.openai.com/docs/api-reference/videos"},
    "gemini": {"label": "Google Gemini", "image": True, "video": True, "models": ["Imagen", "Veo 3.1"], "direct": True, "docs": "https://ai.google.dev/gemini-api/docs/veo"},
    "runway": {"label": "Runway", "image": True, "video": True, "models": ["Gen-4.5", "Veo 3.1", "Seedance"], "direct": False, "docs": "https://docs.dev.runwayml.com/api/"},
    "luma": {"label": "Luma", "image": True, "video": True, "models": ["Ray 2", "Ray 2 Flash"], "direct": False, "docs": "https://docs.lumalabs.ai/docs/video-generation"},
    "fal": {"label": "fal", "image": True, "video": True, "models": ["Model marketplace"], "direct": False, "docs": "https://fal.ai/docs/documentation/model-apis/overview"},
    "tessaris_native": {"label": "Tessaris native", "image": False, "video": False, "clipping": True, "subtitles": True, "renditions": True, "experiments": True, "direct": True},
}


def _hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _connected(provider: str) -> bool:
    env_names = {
        "openai": ("OPENAI_API_KEY",),
        "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        "runway": ("RUNWAYML_API_SECRET", "RUNWAY_API_KEY"),
        "luma": ("LUMA_API_KEY",),
        "fal": ("FAL_KEY", "FAL_API_KEY"),
    }
    return provider == "tessaris_native" or any(os.getenv(name) for name in env_names.get(provider, ()))


class MarketingCreativeEngine:
    """Owns the campaign contract; external models are replaceable renderers."""

    def capabilities(self) -> dict[str, Any]:
        providers = []
        for key, value in PROVIDER_CAPABILITIES.items():
            providers.append({"key": key, **deepcopy(value), "connected": _connected(key)})
        return {
            "providers": providers,
            "owned_capabilities": [
                "brand-grounded creative briefs", "storyboards and shot lists",
                "platform-safe renditions", "clip decision lists", "caption and subtitle contracts",
                "single-variable experiments", "evidence-gated winner iteration",
            ],
            "autonomous_publish": False,
            "autonomous_spend": False,
        }

    def platforms(self) -> list[dict[str, Any]]:
        return [{"key": key, **deepcopy(value)} for key, value in PLATFORM_PROFILES.items()]

    def build_plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        brief = str(payload.get("brief") or "Create useful, credible content for the target customer.").strip()
        objective = str(payload.get("objective") or "Generate qualified interest").strip()
        audience = str(payload.get("audience") or "The business's priority customer").strip()
        offer = str(payload.get("offer") or "The approved business offer").strip()
        tone = str(payload.get("tone") or "Clear, credible and human").strip()
        requested_platforms = payload.get("platforms") or ["instagram_feed", "facebook_feed", "tiktok"]
        requested_formats = [str(item).lower() for item in (payload.get("formats") or ["image", "video", "clip"])]
        variant_count = max(2, min(int(payload.get("variant_count") or 3), 4))
        platforms = [key for key in requested_platforms if key in PLATFORM_PROFILES]
        if not platforms:
            raise ValueError("at_least_one_supported_platform_required")

        concept = {
            "campaign_promise": offer,
            "audience": audience,
            "objective": objective,
            "creative_thesis": brief,
            "tone": tone,
            "proof_rule": "Use verified business evidence only; never invent outcomes, reviews or claims.",
            "call_to_action": str(payload.get("call_to_action") or "Take the next approved step").strip(),
        }
        duration_match = re.search(r"\b(\d+)\s*(day|week|month)s?\b", brief, re.IGNORECASE)
        duration_days = 7
        if duration_match:
            amount = max(1, int(duration_match.group(1)))
            unit = duration_match.group(2).lower()
            duration_days = amount * {"day": 1, "week": 7, "month": 30}[unit]
        duration_days = min(duration_days, 30)
        scenes = [
            {"scene": 1, "role": "hook", "duration_seconds": 3, "direction": f"Open on the customer's most recognisable problem: {brief}"},
            {"scene": 2, "role": "context", "duration_seconds": 5, "direction": f"Show the situation from the perspective of {audience}."},
            {"scene": 3, "role": "solution", "duration_seconds": 8, "direction": f"Demonstrate the approved offer clearly: {offer}."},
            {"scene": 4, "role": "proof", "duration_seconds": 6, "direction": "Use a real process, product detail, demonstration or verified result."},
            {"scene": 5, "role": "cta", "duration_seconds": 4, "direction": concept["call_to_action"]},
        ]
        renditions = []
        jobs = []
        for platform in platforms:
            profile = PLATFORM_PROFILES[platform]
            compatible = [item for item in requested_formats if item in profile["formats"]]
            for content_format in compatible:
                rendition_id = f"rend_{_hash([platform, content_format, concept])[:12]}"
                rendition = {
                    "id": rendition_id, "platform": platform, "platform_label": profile["label"],
                    "format": content_format, "ratio": profile["ratio"],
                    "width": profile["width"], "height": profile["height"],
                    "duration_seconds": profile.get("preferred_seconds", [0, 0]),
                    "safe_zone": "Keep essential text, faces, logos and CTA inside the central 80% frame.",
                    "caption_contract": "Hook first; one clear message; platform-native CTA; substantiated claims only.",
                    "subtitle_contract": "Burned-in captions plus editable subtitle track for spoken video.",
                }
                renditions.append(rendition)
                render_type = "image" if content_format in {"image", "carousel"} else "video"
                jobs.append({
                    "id": f"job_{_hash([rendition_id, render_type])[:12]}",
                    "rendition_id": rendition_id, "render_type": render_type,
                    "status": "planned", "requires_approval": True,
                    "provider_strategy": "best connected direct provider, then approved optional provider",
                    "prompt": f"{tone}. {brief}. Audience: {audience}. Offer: {offer}. {profile['ratio']} composition. No invented text or claims.",
                })

        variables = [
            ("hook", "Lead with the costly consequence instead of the general problem."),
            ("opening_visual", "Open with a close-up human or product proof instead of a wide establishing view."),
            ("call_to_action", "Use a lower-friction next step while preserving the same offer."),
        ]
        variants = [{
            "id": "A", "name": "Control", "controlled_variable": "control",
            "change": "Approved master concept", "hypothesis": "Baseline performance",
        }]
        for index in range(variant_count - 1):
            variable, change = variables[index]
            variants.append({
                "id": chr(ord("B") + index), "name": f"Challenger {chr(ord('B') + index)}",
                "controlled_variable": variable, "change": change,
                "hypothesis": f"Changing only {variable.replace('_', ' ')} will improve the primary outcome.",
            })

        experiment = {
            "id": f"exp_{_hash([concept, platforms, variants])[:16]}",
            "primary_metric": str(payload.get("primary_metric") or "qualified_action_rate"),
            "variants": variants, "minimum_sample_per_variant": 100,
            "minimum_relative_improvement": 0.15,
            "challenger_traffic_cap": 0.20,
            "guardrails": ["complaint_rate", "unsubscribe_rate", "unsafe_or_false_claims"],
            "winner_requires_approval": True,
            "rule": "Change one variable at a time; do not call a winner without the frozen evidence threshold.",
        }
        themes = [
            ("Problem and recognition", "Open with the customer's real situation and make the relevance immediate."),
            ("Education", "Explain one useful fact or decision criterion without overstating the offer."),
            ("Proof", "Show a real project, process, product detail or verified result."),
            ("How it works", "Make the next steps simple, concrete and low-friction."),
            ("Objection handling", "Answer one common concern using approved business evidence."),
            ("Offer", "Present the approved offer and who it is suitable for."),
            ("Action", "Invite the customer to take the approved next step."),
        ]
        created = datetime.now(timezone.utc)
        schedule = []
        for day_index in range(duration_days):
            theme, direction = themes[day_index % len(themes)]
            platform = platforms[day_index % len(platforms)]
            platform_renditions = [item for item in renditions if item["platform"] == platform]
            chosen = platform_renditions[day_index % len(platform_renditions)] if platform_renditions else None
            schedule.append({
                "day": day_index + 1,
                "scheduled_for": (created + timedelta(days=day_index)).date().isoformat(),
                "theme": theme,
                "direction": direction,
                "platform": platform,
                "platform_label": PLATFORM_PROFILES[platform]["label"],
                "format": chosen["format"] if chosen else requested_formats[0],
                "rendition_id": chosen["id"] if chosen else None,
                "status": "planned",
                "requires_approval": True,
            })
        plan_core = {
            "concept": concept, "storyboard": scenes, "renditions": renditions,
            "generation_jobs": jobs, "campaign_schedule": schedule,
            "duration_days": duration_days, "experiment": experiment,
        }
        return {
            "id": f"creative_{_hash(plan_core)[:16]}", "status": "ready_for_review",
            "created_at": datetime.now(timezone.utc).isoformat(), **plan_core,
            "plan_hash": _hash(plan_core), "requires_approval": True,
            "auto_publish": False, "auto_spend": False,
        }

    def evaluate_experiment(self, payload: dict[str, Any]) -> dict[str, Any]:
        rows = payload.get("variants") or []
        if len(rows) < 2:
            raise ValueError("at_least_two_variants_required")
        minimum_sample = max(1, int(payload.get("minimum_sample_per_variant") or 100))
        threshold = max(0.0, float(payload.get("minimum_relative_improvement") or 0.15))
        clean = []
        for row in rows:
            clean.append({
                "id": str(row.get("id") or "").strip(),
                "sample_size": max(0, int(row.get("sample_size") or 0)),
                "primary_metric": max(0.0, float(row.get("primary_metric") or 0.0)),
                "complaint_rate": max(0.0, float(row.get("complaint_rate") or 0.0)),
                "unsafe_or_false_claims": max(0, int(row.get("unsafe_or_false_claims") or 0)),
            })
        if any(row["sample_size"] < minimum_sample for row in clean):
            return self._evaluation("collect_more_evidence", clean, None, "Minimum sample has not been reached for every variant.")
        if any(row["unsafe_or_false_claims"] > 0 for row in clean):
            return self._evaluation("stop_and_review", clean, None, "A safety or truthfulness guardrail was breached.")
        baseline = clean[0]
        candidates = sorted(clean[1:], key=lambda row: row["primary_metric"], reverse=True)
        best = candidates[0]
        relative = (best["primary_metric"] - baseline["primary_metric"]) / max(baseline["primary_metric"], 1e-9)
        if best["complaint_rate"] > baseline["complaint_rate"]:
            return self._evaluation("keep_control", clean, baseline["id"], "The challenger improved the main metric but worsened complaints.")
        if relative < threshold:
            return self._evaluation("keep_control", clean, baseline["id"], "No challenger cleared the frozen improvement threshold.")
        result = self._evaluation("winner_candidate", clean, best["id"], f"Candidate improved the primary metric by {relative:.1%} without breaching guardrails.")
        result["next_iteration"] = {"base_variant": best["id"], "change_exactly_one_new_variable": True, "challenger_traffic_cap": 0.20}
        return result

    @staticmethod
    def _evaluation(status: str, variants: list[dict[str, Any]], winner: str | None, reason: str) -> dict[str, Any]:
        return {
            "status": status, "winner_candidate": winner, "reason": reason,
            "variants": variants, "auto_apply": False, "requires_approval": True,
            "auto_publish": False, "auto_spend": False,
            "evidence_hash": _hash(variants),
        }
