from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping

from .reasoning_replay_trace import build_default_home_fixed_reasoning_replay_trace

REASONING_REPLAY_BOARDROOM_VERSION = "aion.lrm.reasoning_replay_boardroom.v0.1"


_MUTABLE_HASH_FIELDS = {
    "boardroom_hash",
    "summary_hash",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(prefix: str, value: Any) -> str:
    return f"{prefix}_{hashlib.sha256(_canonical_json(value).encode('utf-8')).hexdigest()[:32]}"


def _redact_private_fields(value: Any) -> Any:
    if isinstance(value, Mapping):
        redacted = {}
        for key, inner in value.items():
            key_lower = str(key).lower()
            if key_lower in {
                "chain_of_thought",
                "private_chain_of_thought",
                "hidden_reasoning",
                "private_reasoning",
                "secret",
                "secrets",
                "access_token",
                "refresh_token",
                "api_key",
                "password",
                "credential",
                "credentials",
            }:
                continue
            redacted[key] = _redact_private_fields(inner)
        return redacted
    if isinstance(value, list):
        return [_redact_private_fields(item) for item in value]
    return value


def build_reasoning_replay_boardroom_panel(
    replay_trace: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build a Boardroom-safe visibility payload for a reasoning replay trace.

    This is a read-only projection. It must not expose private chain-of-thought,
    credentials, hidden reasoning, or live execution authority.
    """

    trace = _redact_private_fields(
        dict(replay_trace or build_default_home_fixed_reasoning_replay_trace())
    )

    reasoning_summary = {
        "recommendation": trace.get("recommendation", "human_review_required"),
        "decision_basis": trace.get("decision_basis", []),
        "evidence_hashes": trace.get("evidence_hashes", []),
        "proof_hashes": trace.get("proof_hashes", []),
        "context_hashes": trace.get("context_hashes", {}),
        "memory_snapshot_hash": trace.get("memory_snapshot_hash"),
        "reasoning_packet_hash": trace.get("reasoning_packet_hash"),
        "replay_trace_hash": trace.get("replay_trace_hash"),
    }

    safety = {
        "preview_only": True,
        "human_review_required": True,
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

    panel = {
        "boardroom_panel_version": REASONING_REPLAY_BOARDROOM_VERSION,
        "panel_title": "Reasoning Replay Trace",
        "panel_status": "preview_only",
        "operator_message": (
            "AION can replay why it reached this recommendation using governed "
            "packet, memory snapshot, evidence/proof hashes, and context hashes "
            "without exposing private chain-of-thought."
        ),
        "reasoning_summary": reasoning_summary,
        "replay_trace": trace,
        "safety": safety,
    }

    hash_payload = {
        key: value
        for key, value in panel.items()
        if key not in _MUTABLE_HASH_FIELDS
    }

    panel["boardroom_hash"] = _hash("reasoning_replay_boardroom", hash_payload)
    panel["summary"] = {
        "boardroom_panel_version": REASONING_REPLAY_BOARDROOM_VERSION,
        "panel_title": panel["panel_title"],
        "panel_status": panel["panel_status"],
        "recommendation": reasoning_summary["recommendation"],
        "human_review_required": True,
        "preview_only": True,
        "boardroom_hash": panel["boardroom_hash"],
    }
    panel["summary_hash"] = _hash("reasoning_replay_boardroom_summary", panel["summary"])

    return panel


def build_default_home_fixed_reasoning_replay_boardroom_panel() -> Dict[str, Any]:
    return build_reasoning_replay_boardroom_panel()
