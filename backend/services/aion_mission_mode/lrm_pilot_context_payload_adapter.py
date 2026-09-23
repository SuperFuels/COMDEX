from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Dict, Mapping, Optional

from backend.modules.aion_lrm.lrm_end_to_end_decision_loop import (
    build_default_home_fixed_lrm_end_to_end_decision_loop,
)


LRM_PILOT_CONTEXT_PAYLOAD_ADAPTER_VERSION = "aion.mission_mode.lrm_pilot_context_payload_adapter.v0.1"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(prefix: str, value: Any) -> str:
    return f"{prefix}_{hashlib.sha256(_canonical(value).encode('utf-8')).hexdigest()[:32]}"


def _redact(value: Any) -> Any:
    forbidden = {
        "private_chain_of_thought",
        "chain_of_thought",
        "hidden_reasoning",
        "private_reasoning",
        "secret",
        "secrets",
        "password",
        "api_key",
        "access_token",
        "refresh_token",
        "credential",
        "credentials",
    }

    if isinstance(value, Mapping):
        cleaned: Dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if key_text.lower() in forbidden:
                continue
            cleaned[key_text] = _redact(item)
        return cleaned

    if isinstance(value, list):
        return [_redact(item) for item in value]

    return deepcopy(value)


def _normalise_business_id(value: str) -> str:
    raw = str(value or "home-fixed").strip().lower().replace("_", "-")
    return raw or "home-fixed"


def _mission_container_root(
    *,
    business_id: str,
    mission_id: str,
    mission_run_id: str,
) -> str:
    return (
        f"business/{_normalise_business_id(business_id)}/"
        f"missions/{mission_id}/runs/{mission_run_id}"
    )


def _extract_lrm_state(loop: Mapping[str, Any]) -> Dict[str, Any]:
    recommendation = loop.get("reasoning_recommendation_card", {})
    human_decision = loop.get("human_review_decision_envelope", {})
    evidence_gap = loop.get("evidence_gap_envelope", {})
    evidence_satisfaction = loop.get("evidence_satisfaction_envelope", {})
    replay = loop.get("reasoning_replay_trace", {})
    boardroom = loop.get("boardroom_replay_panel", {})

    decision_state = (
        human_decision.get("decision_state", {})
        if isinstance(human_decision.get("decision_state", {}), Mapping)
        else {}
    )
    gap_state = (
        evidence_gap.get("gap_state", {})
        if isinstance(evidence_gap.get("gap_state", {}), Mapping)
        else {}
    )
    satisfaction_state = (
        evidence_satisfaction.get("satisfaction_state", {})
        if isinstance(evidence_satisfaction.get("satisfaction_state", {}), Mapping)
        else {}
    )

    return {
        "loop_hash": loop.get("loop_hash"),
        "loop_summary_hash": loop.get("summary_hash"),
        "loop_final_state": loop.get("final_state"),
        "replay_trace_hash": replay.get("replay_trace_hash"),
        "boardroom_replay_hash": boardroom.get("boardroom_hash"),
        "recommendation_card_hash": recommendation.get("card_hash"),
        "recommendation_summary_hash": recommendation.get("summary_hash"),
        "human_review_decision_hash": human_decision.get("envelope_hash"),
        "human_review_summary_hash": human_decision.get("summary_hash"),
        "human_review_decision": decision_state.get("decision"),
        "evidence_gap_hash": evidence_gap.get("evidence_gap_hash"),
        "evidence_gap_summary_hash": evidence_gap.get("summary_hash"),
        "evidence_gap_active": gap_state.get("evidence_gap_active"),
        "required_evidence": gap_state.get("required_evidence", []),
        "missing_evidence": gap_state.get("missing_evidence", []),
        "evidence_satisfaction_hash": evidence_satisfaction.get("satisfaction_hash"),
        "evidence_satisfaction_summary_hash": evidence_satisfaction.get("summary_hash"),
        "evidence_gap_satisfied": satisfaction_state.get("evidence_gap_satisfied"),
        "next_review_state": satisfaction_state.get("next_review_state"),
        "evidence_hashes": satisfaction_state.get("evidence_hashes", []),
    }


def build_lrm_pilot_context_payload(
    lrm_loop: Optional[Mapping[str, Any]] = None,
    *,
    business_id: str = "home-fixed",
    mission_id: str = "pilot_demo_pdf_mission",
    mission_run_id: str = "pilot_demo_run_preview",
    cockpit_surface: str = "aion_pilot_cockpit",
    boardroom_surface: str = "boardroom_dashboard",
) -> Dict[str, Any]:
    loop = _redact(dict(lrm_loop or build_default_home_fixed_lrm_end_to_end_decision_loop()))

    safe_business_id = _normalise_business_id(business_id or loop.get("business_id", "home-fixed"))
    safe_mission_id = str(mission_id or "pilot_demo_pdf_mission")
    safe_mission_run_id = str(mission_run_id or "pilot_demo_run_preview")
    container_root = _mission_container_root(
        business_id=safe_business_id,
        mission_id=safe_mission_id,
        mission_run_id=safe_mission_run_id,
    )

    lrm_state = _extract_lrm_state(loop)

    artifacts = [
        {
            "artifact_type": "lrm_loop_summary",
            "status": "preview_only",
            "path": f"{container_root}/artifacts/lrm-loop-summary.json",
            "artifact_hash": lrm_state.get("loop_hash"),
            "receipt_hash": lrm_state.get("loop_summary_hash"),
        },
        {
            "artifact_type": "lrm_replay_trace",
            "status": "preview_only",
            "path": f"{container_root}/artifacts/lrm-replay-trace.json",
            "artifact_hash": lrm_state.get("replay_trace_hash"),
            "receipt_hash": lrm_state.get("boardroom_replay_hash"),
        },
    ]

    visible_stream_events = [
        {
            "type": "lrm_loop_loaded",
            "label": "LRM loop loaded",
            "status": "preview_only",
            "detail": f"Loop state: {lrm_state.get('loop_final_state')}",
        },
        {
            "type": "lrm_human_review",
            "label": "Human review state",
            "status": "human_review_required",
            "detail": str(lrm_state.get("next_review_state") or "human_review_required"),
        },
        {
            "type": "lrm_evidence_state",
            "label": "Evidence state",
            "status": "preview_only",
            "detail": "Evidence gap satisfied" if lrm_state.get("evidence_gap_satisfied") else "Evidence still required",
        },
    ]

    safety = {
        "preview_only": True,
        "human_review_required": True,
        "pilot_context_payload_grants_live_permission": False,
        "boardroom_projection_only": True,
        "private_chain_of_thought_exposed": False,
        "hidden_reasoning_exposed": False,
        "credentials_exposed": False,
        "would_create_booking": False,
        "would_create_payment": False,
        "would_create_escrow": False,
        "would_send_external_message": False,
        "would_write_live_chain": False,
        "would_execute_workflow": False,
        "live_side_effects_enabled": False,
    }

    payload_core = {
        "payload_version": LRM_PILOT_CONTEXT_PAYLOAD_ADAPTER_VERSION,
        "payload_type": "aion_lrm_pilot_context_payload",
        "business_id": safe_business_id,
        "mission_id": safe_mission_id,
        "mission_run_id": safe_mission_run_id,
        "cockpit_surface": cockpit_surface,
        "boardroom_surface": boardroom_surface,
        "business_container_root": container_root,
        "source_lrm_loop_hash": lrm_state.get("loop_hash"),
        "source_lrm_loop_summary_hash": lrm_state.get("loop_summary_hash"),
        "lrm_state": lrm_state,
        "pilot_cockpit_projection": {
            "status": lrm_state.get("next_review_state") or lrm_state.get("loop_final_state") or "preview_only",
            "mode": "preview_only",
            "identity": "AION Pilot native runtime executor, not UI automation",
            "mission_id": safe_mission_id,
            "mission_run_id": safe_mission_run_id,
            "business_id": safe_business_id,
            "save_path": f"{container_root}/artifacts/lrm-loop-summary.json",
            "visible_stream_events": visible_stream_events,
            "artifacts": artifacts,
            "blocked_actions": [
                "booking",
                "payment",
                "escrow",
                "external_message",
                "live_chain_write",
                "workflow_execution",
            ],
        },
        "boardroom_projection": {
            "surface": boardroom_surface,
            "panel_type": "lrm_pilot_context",
            "status": "preview_only",
            "human_review_required": True,
            "loop_hash": lrm_state.get("loop_hash"),
            "recommendation_card_hash": lrm_state.get("recommendation_card_hash"),
            "human_review_decision_hash": lrm_state.get("human_review_decision_hash"),
            "evidence_gap_hash": lrm_state.get("evidence_gap_hash"),
            "evidence_satisfaction_hash": lrm_state.get("evidence_satisfaction_hash"),
            "next_review_state": lrm_state.get("next_review_state"),
        },
        "safety": safety,
    }

    payload_hash = _hash("lrm_pilot_context_payload", payload_core)

    summary = {
        "payload_version": LRM_PILOT_CONTEXT_PAYLOAD_ADAPTER_VERSION,
        "business_id": safe_business_id,
        "mission_id": safe_mission_id,
        "mission_run_id": safe_mission_run_id,
        "source_lrm_loop_hash": lrm_state.get("loop_hash"),
        "next_review_state": lrm_state.get("next_review_state"),
        "preview_only": True,
        "human_review_required": True,
        "payload_hash": payload_hash,
    }

    return {
        **payload_core,
        "payload_hash": payload_hash,
        "summary": summary,
        "summary_hash": _hash("lrm_pilot_context_payload_summary", summary),
    }


def build_default_home_fixed_lrm_pilot_context_payload() -> Dict[str, Any]:
    return build_lrm_pilot_context_payload()
