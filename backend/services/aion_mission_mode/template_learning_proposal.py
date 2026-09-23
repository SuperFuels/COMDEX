from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List


class TemplateProposalError(ValueError):
    pass


class TemplateApprovalRequired(TemplateProposalError):
    pass


def canonical_hash(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _safe_copy(payload: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(json.dumps(payload, sort_keys=True, ensure_ascii=False))


def generate_template_diff(
    current_template: Dict[str, Any],
    proposed_template: Dict[str, Any],
) -> Dict[str, Any]:
    current = _safe_copy(current_template or {})
    proposed = _safe_copy(proposed_template or {})

    added: List[str] = []
    removed: List[str] = []
    changed: List[str] = []

    keys = sorted(set(current.keys()) | set(proposed.keys()))
    for key in keys:
        if key not in current:
            added.append(key)
        elif key not in proposed:
            removed.append(key)
        elif current[key] != proposed[key]:
            changed.append(key)

    diff = {
        "added_fields": added,
        "removed_fields": removed,
        "changed_fields": changed,
        "current_template_hash": canonical_hash(current),
        "proposed_template_hash": canonical_hash(proposed),
    }
    diff["proposed_template_diff_hash"] = canonical_hash(diff)
    return diff


def create_template_improvement_proposal(
    *,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
    source_template_id: str,
    proposed_template_id: str,
    source_mission_receipt_hash: str,
    ets_preview_hash: str,
    current_template: Dict[str, Any],
    proposed_template: Dict[str, Any],
    reason: str,
) -> Dict[str, Any]:
    if not mission_id or not mission_run_id or not business_id:
        raise TemplateProposalError("mission_id, mission_run_id and business_id are required")

    diff = generate_template_diff(current_template, proposed_template)

    proposal = {
        "proposal_type": "template_improvement_proposal",
        "proposal_state": "waiting_human_approval",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "source_template_id": source_template_id,
        "proposed_template_id": proposed_template_id,
        "source_mission_receipt_hash": source_mission_receipt_hash,
        "ets_preview_hash": ets_preview_hash,
        "reason": reason,
        "current_template_hash": diff["current_template_hash"],
        "proposed_template_hash": diff["proposed_template_hash"],
        "proposed_template_diff": diff,
        "live_template_mutation_allowed": False,
        "requires_human_approval": True,
        "approved": False,
        "approval_hash": "none",
    }
    proposal["template_improvement_proposal_hash"] = canonical_hash(proposal)
    return proposal


def approve_template_proposal(
    proposal: Dict[str, Any],
    *,
    approver_id: str,
    approval_note: str,
) -> Dict[str, Any]:
    if proposal.get("proposal_type") != "template_improvement_proposal":
        raise TemplateProposalError("invalid proposal type")

    approved = _safe_copy(proposal)
    approved["proposal_state"] = "approved_for_template_save"
    approved["approved"] = True
    approved["approved_by"] = approver_id
    approved["approval_note"] = approval_note
    approved["live_template_mutation_allowed"] = False

    approval_payload = {
        "template_improvement_proposal_hash": proposal["template_improvement_proposal_hash"],
        "approver_id": approver_id,
        "approval_note": approval_note,
        "approved_proposed_template_hash": proposal["proposed_template_hash"],
    }
    approved["approval_hash"] = canonical_hash(approval_payload)
    approved["approved_proposal_hash"] = canonical_hash(approved)
    return approved


def assert_template_save_allowed(proposal: Dict[str, Any], proposed_template: Dict[str, Any]) -> Dict[str, Any]:
    reasons: List[str] = []

    if proposal.get("proposal_type") != "template_improvement_proposal":
        reasons.append("invalid_proposal_type")

    if not proposal.get("approved"):
        reasons.append("human_approval_required")

    if proposal.get("proposal_state") != "approved_for_template_save":
        reasons.append("proposal_not_in_approved_save_state")

    if proposal.get("approval_hash") in {None, "", "none"}:
        reasons.append("missing_approval_hash")

    current_proposed_hash = canonical_hash(_safe_copy(proposed_template or {}))
    if current_proposed_hash != proposal.get("proposed_template_hash"):
        reasons.append("proposed_template_hash_mismatch")

    allowed = len(reasons) == 0
    assertion = {
        "template_save_allowed": allowed,
        "reasons": reasons if reasons else ["template_save_approved_and_hash_bound"],
        "proposal_hash": proposal.get("template_improvement_proposal_hash"),
        "approval_hash": proposal.get("approval_hash"),
        "proposed_template_hash": current_proposed_hash,
        "live_template_mutation_allowed": False,
    }
    assertion["template_save_assertion_hash"] = canonical_hash(assertion)
    return assertion


def save_approved_template(
    *,
    business_container_root: str,
    proposal: Dict[str, Any],
    proposed_template: Dict[str, Any],
) -> Dict[str, Any]:
    assertion = assert_template_save_allowed(proposal, proposed_template)
    if not assertion["template_save_allowed"]:
        raise TemplateApprovalRequired(",".join(assertion["reasons"]))

    root = Path(business_container_root).resolve()
    template_id = proposal["proposed_template_id"].replace("/", "_")
    relative_path = Path("templates") / "approved" / f"{template_id}.json"
    target = (root / relative_path).resolve()

    if os.path.commonpath([str(root), str(target)]) != str(root):
        raise TemplateProposalError("template output path escapes business container")

    record = {
        "business_id": proposal["business_id"],
        "mission_id": proposal["mission_id"],
        "mission_run_id": proposal["mission_run_id"],
        "source_template_id": proposal["source_template_id"],
        "proposed_template_id": proposal["proposed_template_id"],
        "template_save_assertion_hash": assertion["template_save_assertion_hash"],
        "approval_hash": proposal["approval_hash"],
        "template_hash": canonical_hash(_safe_copy(proposed_template)),
        "relative_template_path": str(relative_path),
        "contained_template_path": str(target),
        "template_state": "approved_template_ready_to_persist",
    }
    record["template_save_record_hash"] = canonical_hash(record)
    return record
