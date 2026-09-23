from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Dict, List, Sequence


SOCIAL_PROVIDER_VAULT_HANDLES = {
    "twitter_x": [
        "vault.twitter_x.oauth",
        "vault.twitter.credentials",
        "vault.x.credentials",
        "vault.twitter_x.credentials",
    ],
    "facebook": [
        "vault.facebook.oauth",
        "vault.meta.oauth",
        "vault.facebook.credentials",
        "vault.meta.credentials",
    ],
    "google_business": [
        "vault.google.oauth",
        "vault.google_business.credentials",
        "vault.google.credentials",
    ],
}


LIVE_APPROVAL_ACTIONS = {
    "publish_public_post",
    "send_external_message",
    "start_ad_campaign",
    "spend_money",
    "deploy_to_production",
    "buy_domain",
    "create_booking",
    "take_payment",
    "create_escrow",
    "mutate_reputation",
}


def canonical_hash(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _get_nested(data: Dict[str, Any], paths: Sequence[Sequence[str]], default: Any = "") -> Any:
    for path in paths:
        node: Any = data
        ok = True
        for key in path:
            if isinstance(node, dict) and key in node:
                node = node[key]
            else:
                ok = False
                break
        if ok and node not in (None, "", [], {}):
            return node
    return default


def _safe_string(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return str(value or "").strip()


def _normalise_available_vault(values: Sequence[Any] | None) -> set[str]:
    return {str(v).strip() for v in (values or []) if str(v).strip()}


def build_business_context_snapshot(
    *,
    business_id: str,
    brand_foundation_state: Dict[str, Any] | None = None,
    marketing_form: Dict[str, Any] | None = None,
    marketing_summary: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    brand = deepcopy(brand_foundation_state or {})
    marketing = deepcopy(marketing_form or {})
    summary = deepcopy(marketing_summary or {})

    brand_map = brand.get("brandMap") or brand.get("brand_map") or brand.get("brand_intelligence_map") or {}

    snapshot = {
        "business_id": business_id,
        "business_name": _safe_string(
            _get_nested(
                {"brand": brand, "brand_map": brand_map, "marketing": marketing},
                [
                    ["brand", "business_name"],
                    ["brand", "businessName"],
                    ["brand_map", "identity", "businessName"],
                    ["brand_map", "businessIdentity", "businessName"],
                    ["marketing", "business_name"],
                    ["marketing", "businessName"],
                ],
                business_id,
            )
        ),
        "brand_foundation_available": bool(brand),
        "marketing_form_available": bool(marketing),
        "marketing_summary_available": bool(summary),
        "tone_of_voice": _safe_string(
            _get_nested(
                {"brand_map": brand_map, "marketing": marketing},
                [
                    ["brand_map", "brandVoice", "toneOfVoice"],
                    ["brand_map", "brand_voice", "tone_of_voice"],
                    ["brand_map", "voice", "tone"],
                    ["marketing", "tone_of_voice"],
                    ["marketing", "toneOfVoice"],
                ],
                "",
            )
        ),
        "brand_story": _safe_string(
            _get_nested(
                {"brand_map": brand_map},
                [
                    ["brand_map", "brandStory"],
                    ["brand_map", "brand_story"],
                ],
                "",
            )
        ),
        "marketing_objective": _safe_string(
            _get_nested(
                {"marketing": marketing, "summary": summary, "brand_map": brand_map},
                [
                    ["marketing", "objective"],
                    ["marketing", "marketingObjective"],
                    ["summary", "objective"],
                    ["brand_map", "objective"],
                ],
                "",
            )
        ),
        "target_audience": _safe_string(
            _get_nested(
                {"marketing": marketing, "summary": summary, "brand_map": brand_map},
                [
                    ["marketing", "targetAudience"],
                    ["marketing", "target_audience"],
                    ["marketing", "audience"],
                    ["summary", "target_audience"],
                    ["brand_map", "targetAudience"],
                    ["brand_map", "target_audience"],
                ],
                "",
            )
        ),
        "offer": _safe_string(
            _get_nested(
                {"marketing": marketing, "summary": summary, "brand_map": brand_map},
                [
                    ["marketing", "offer"],
                    ["summary", "offer"],
                    ["brand_map", "offer"],
                ],
                "",
            )
        ),
        "channels": _safe_string(
            _get_nested(
                {"marketing": marketing, "summary": summary, "brand_map": brand_map},
                [
                    ["marketing", "channels"],
                    ["summary", "channels"],
                    ["brand_map", "channels"],
                ],
                "",
            )
        ),
        "hard_rules": _safe_string(
            _get_nested(
                {"marketing": marketing, "brand_map": brand_map},
                [
                    ["marketing", "hardRules"],
                    ["marketing", "hard_rules"],
                    ["brand_map", "hardRules"],
                    ["brand_map", "hard_rules"],
                ],
                "",
            )
        ),
        "raw_credentials_visible": False,
        "private_reasoning_visible": False,
    }

    snapshot["context_hash"] = canonical_hash(snapshot)
    return snapshot


def _text_mentions_twitter_x(*values: Any) -> bool:
    text = " ".join(_safe_string(v).lower() for v in values)
    return bool(
        re.search(r"\btwitter\b", text)
        or re.search(r"\bx\s*(channel|posts|setup|account|profile)\b", text)
        or re.search(r"\btwitter/x\b", text)
    )


def _text_mentions_facebook(*values: Any) -> bool:
    text = " ".join(_safe_string(v).lower() for v in values)
    return "facebook" in text or "meta" in text


def _text_mentions_google_business(*values: Any) -> bool:
    text = " ".join(_safe_string(v).lower() for v in values)
    return "google business" in text or "google business profile" in text


def _provider_access_decision(provider_key: str, available_vault_requirements: Sequence[Any] | None) -> Dict[str, Any]:
    available = _normalise_available_vault(available_vault_requirements)
    required = SOCIAL_PROVIDER_VAULT_HANDLES[provider_key]
    matched = sorted(available.intersection(required))
    missing = [] if matched else list(required)

    if matched:
        return {
            "provider_key": provider_key,
            "provider_access_state": "vault_reference_available",
            "decision": "staged_external",
            "required_vault_handles": required,
            "matched_vault_handles": matched,
            "missing_vault_requirements": [],
            "human_task_required": False,
            "credential_required": False,
            "live_action_allowed": False,
        }

    return {
        "provider_key": provider_key,
        "provider_access_state": "missing_provider_access",
        "decision": "human_task_required",
        "required_vault_handles": required,
        "matched_vault_handles": [],
        "missing_vault_requirements": missing,
        "human_task_required": True,
        "credential_required": True,
        "live_action_allowed": False,
    }


def _make_social_setup_node(
    *,
    provider_key: str,
    title: str,
    business_context: Dict[str, Any],
    available_vault_requirements: Sequence[Any] | None,
) -> Dict[str, Any]:
    access = _provider_access_decision(provider_key, available_vault_requirements)

    node = {
        "node_type": "mission_task_node",
        "title": title,
        "action_type": "setup_social_channel",
        "provider": provider_key,
        "required_context": [
            "brand_foundation",
            "tone_of_voice",
            "brand_story",
            "marketing_objective",
            "target_audience",
            "offer",
            "channels",
        ],
        "context_hash": business_context["context_hash"],
        "provider_access": access,
        "decision": access["decision"],
        "safe_draft_work_allowed": True,
        "staged_external_allowed": access["decision"] == "staged_external",
        "human_task_required": access["human_task_required"],
        "credential_required": access["credential_required"],
        "live_public_post_requires_exact_approval": True,
        "live_send_requires_exact_approval": True,
        "live_ad_spend_requires_exact_approval": True,
        "live_external_side_effects_allowed": False,
        "subtasks": [
            {
                "title": "Read business context and brand foundation",
                "decision": "safe_internal",
                "output": "context_summary",
            },
            {
                "title": f"Prepare {title} setup checklist",
                "decision": "safe_internal",
                "output": "setup_checklist",
            },
            {
                "title": f"Check {title} OAuth/credential vault access",
                "decision": access["decision"],
                "required_vault_handles": access["required_vault_handles"],
                "missing_vault_requirements": access["missing_vault_requirements"],
            },
            {
                "title": f"Prepare {title} profile/content draft",
                "decision": "safe_internal" if access["credential_required"] else "staged_external",
                "output": "draft_profile_payload",
            },
            {
                "title": f"Stop before publishing or sending anything on {title}",
                "decision": "human_approval_required",
                "approval_type": "exact_payload_approval",
            },
        ],
    }
    node["task_node_hash"] = canonical_hash(node)
    return node


def build_business_context_mission_map(
    *,
    business_id: str,
    mission_id: str,
    mission_run_id: str,
    user_goal: str,
    plan_steps: Sequence[Dict[str, Any]] | None = None,
    plan_text: str = "",
    brand_foundation_state: Dict[str, Any] | None = None,
    marketing_form: Dict[str, Any] | None = None,
    marketing_summary: Dict[str, Any] | None = None,
    available_vault_requirements: Sequence[Any] | None = None,
) -> Dict[str, Any]:
    business_context = build_business_context_snapshot(
        business_id=business_id,
        brand_foundation_state=brand_foundation_state,
        marketing_form=marketing_form,
        marketing_summary=marketing_summary,
    )

    steps = list(plan_steps or [])
    # Provider-access task nodes must come from the active mission request or
    # edited/approved plan text, not from broad default brand/marketing context.
    # Otherwise a generic marketing plan with "Facebook" in the business context
    # jumps straight to provider login work before the user has approved that
    # channel as the next execution node.
    explicit_execution_blob = " ".join([
        user_goal,
        plan_text,
        " ".join(
            _safe_string(step)
            for step in steps
            if str(step.get("decision") or "") not in {"safe_autonomous"}
        ),
    ])

    task_nodes: List[Dict[str, Any]] = []

    if _text_mentions_twitter_x(explicit_execution_blob):
        task_nodes.append(
            _make_social_setup_node(
                provider_key="twitter_x",
                title="Twitter/X channel setup",
                business_context=business_context,
                available_vault_requirements=available_vault_requirements,
            )
        )

    if _text_mentions_facebook(explicit_execution_blob):
        task_nodes.append(
            _make_social_setup_node(
                provider_key="facebook",
                title="Facebook channel setup",
                business_context=business_context,
                available_vault_requirements=available_vault_requirements,
            )
        )

    if _text_mentions_google_business(explicit_execution_blob):
        task_nodes.append(
            _make_social_setup_node(
                provider_key="google_business",
                title="Google Business Profile setup",
                business_context=business_context,
                available_vault_requirements=available_vault_requirements,
            )
        )

    human_task_cards = []
    credential_required_cards = []

    for node in task_nodes:
        access = node["provider_access"]
        if access["human_task_required"]:
            card = {
                "card_type": "human_task_card",
                "title": f"Connect provider access for {node['title']}",
                "reason": "Provider login/OAuth/credential vault access is required before this task can continue.",
                "required_evidence_type": "credential_ref",
                "required_vault_handles": access["required_vault_handles"],
                "missing_vault_requirements": access["missing_vault_requirements"],
                "resume_condition": "OAuth connected or credential_ref added to vault",
                "live_external_side_effects_allowed": False,
            }
            card["human_task_hash"] = canonical_hash(card)
            human_task_cards.append(card)

            credential_card = {
                "card_type": "credential_required_card",
                "provider": node["provider"],
                "title": node["title"],
                "missing_vault_requirements": access["missing_vault_requirements"],
                "credential_ref_only": True,
                "raw_credentials_visible": False,
            }
            credential_card["credential_card_hash"] = canonical_hash(credential_card)
            credential_required_cards.append(credential_card)

    task_loop_map = {
        "loop_type": "business_context_task_execution_loop",
        "business_context_hash": business_context["context_hash"],
        "top_level_task_count": len(task_nodes),
        "loop_steps": [
            "read_business_context",
            "read_brand_foundation",
            "read_marketing_context",
            "select_next_task_node",
            "check_required_context",
            "check_provider_access_or_create_human_task",
            "execute_safe_internal_or_staged_work",
            "save_output_to_business_container",
            "update_mission_timeline",
            "pause_for_exact_approval_or_human_task_when_required",
        ],
        "live_external_side_effects_allowed": False,
    }
    task_loop_map["task_loop_hash"] = canonical_hash(task_loop_map)

    result = {
        "payload_type": "aion_business_context_mission_map",
        "business_id": business_id,
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "user_goal": user_goal,
        "business_context": business_context,
        "task_nodes": task_nodes,
        "human_task_cards": human_task_cards,
        "credential_required_cards": credential_required_cards,
        "task_loop_map": task_loop_map,
        "safety": {
            "preview_only": True,
            "raw_credentials_visible": False,
            "private_reasoning_visible": False,
            "live_external_side_effects_enabled": False,
            "public_post_requires_exact_approval": True,
            "external_message_requires_exact_approval": True,
            "ad_spend_requires_exact_approval": True,
            "provider_login_requires_vault_or_human_task": True,
        },
    }
    result["business_context_mission_map_hash"] = canonical_hash(result)
    return result
