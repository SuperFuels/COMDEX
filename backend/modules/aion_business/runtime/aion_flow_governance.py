from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Mapping

from backend.modules.aion_fabric.canonical import canonical_hash, utc_now_iso


_CLASS_LEVEL = {"public": 0, "internal": 1, "confidential": 2, "restricted": 3}
_LOCATION_COLOUR = {
    "local": "green", "household": "teal", "organisation": "blue",
    "customer_cloud": "indigo", "external_api": "orange",
}


class AionFlowGovernancePlanner:
    """Pre-execution policy and disclosure plan for visual intelligence graphs."""

    def preflight(
        self,
        *,
        graph: Mapping[str, Any],
        actor: Mapping[str, Any],
        policy: Mapping[str, Any],
        approvals: Iterable[Mapping[str, Any]] = (),
        now: datetime | None = None,
    ) -> Dict[str, Any]:
        instant = now or datetime.now(timezone.utc)
        nodes = {str(item.get("id") or ""): dict(item) for item in graph.get("nodes") or []}
        approval_by_id = {str(item.get("approval_id") or ""): dict(item) for item in approvals}
        errors, edge_plan, approval_plan = [], [], []
        required_actor = ("person_id", "organisation_id", "workspace_id", "role", "purpose")
        missing_actor = [key for key in required_actor if not str(actor.get(key) or "").strip()]
        if missing_actor:
            errors.append(f"active_authority_incomplete:{','.join(missing_actor)}")
        allowed_roles = set(policy.get("allowed_roles") or [])
        if allowed_roles and actor.get("role") not in allowed_roles:
            errors.append("actor_role_not_allowed_for_purpose")
        allowed_purposes = set(policy.get("allowed_purposes") or [])
        if allowed_purposes and actor.get("purpose") not in allowed_purposes:
            errors.append("actor_purpose_not_allowed")
        membership_expiry = self._instant(actor.get("membership_expires_at"))
        if membership_expiry and membership_expiry <= instant:
            errors.append("membership_expired")
        if actor.get("revoked") is True:
            errors.append("actor_authority_revoked")

        for edge in graph.get("edges") or []:
            source = nodes.get(str(edge.get("source") or ""), {})
            target = nodes.get(str(edge.get("target") or ""), {})
            location = str(target.get("location") or "local")
            data_class = str(edge.get("data_classification") or target.get("data_classification") or "internal")
            fields = sorted(set(str(item) for item in edge.get("fields") or []))
            destination = str(edge.get("destination") or target.get("destination") or location)
            item_errors = []
            if data_class not in _CLASS_LEVEL:
                item_errors.append("data_classification_invalid")
            maximum = str(policy.get("maximum_external_classification") or "public")
            crossing = location in {"customer_cloud", "external_api"}
            if crossing and _CLASS_LEVEL.get(data_class, 99) > _CLASS_LEVEL.get(maximum, -1):
                item_errors.append("data_classification_exceeds_external_policy")
            allowed_destinations = set(policy.get("allowed_destinations") or [])
            if crossing and destination not in allowed_destinations:
                item_errors.append("destination_not_allowed")
            residency = str(target.get("residency") or "")
            allowed_residencies = set(policy.get("allowed_residencies") or [])
            if crossing and allowed_residencies and residency not in allowed_residencies:
                item_errors.append("residency_not_allowed")
            if crossing and edge.get("encrypted") is not True:
                item_errors.append("boundary_crossing_requires_encryption")
            if crossing and not fields:
                item_errors.append("boundary_crossing_fields_must_be_declared")
            if edge.get("fallback") is True:
                original = dict(edge.get("original_policy") or {})
                if _CLASS_LEVEL.get(data_class, 99) > _CLASS_LEVEL.get(str(original.get("maximum_classification") or data_class), 99):
                    item_errors.append("fallback_expands_data_classification")
                if original.get("destinations") and destination not in set(original["destinations"]):
                    item_errors.append("fallback_expands_destination")
                if float(edge.get("estimated_cost", 0) or 0) > float(original.get("maximum_cost", edge.get("estimated_cost", 0)) or 0):
                    item_errors.append("fallback_expands_cost")
            edge_plan.append({
                "edge_id": str(edge.get("id") or f"{edge.get('source')}->{edge.get('target')}"),
                "source": str(edge.get("source") or ""), "target": str(edge.get("target") or ""),
                "location": location, "colour": _LOCATION_COLOUR.get(location, "grey"),
                "destination": destination, "data_classification": data_class, "fields": fields,
                "redactions": sorted(set(edge.get("redactions") or [])), "residency": residency,
                "encrypted": bool(edge.get("encrypted")), "consent_required": bool(edge.get("consent_required")),
                "allowed": not item_errors, "block_reasons": item_errors,
            })
            errors.extend(f"edge:{edge_plan[-1]['edge_id']}:{reason}" for reason in item_errors)

        for node in nodes.values():
            if not node.get("requires_approval"):
                continue
            approval_id = str(node.get("approval_id") or "")
            approval = approval_by_id.get(approval_id) or {}
            expiry = self._instant(approval.get("expires_at"))
            exact_hash = str(node.get("exact_scope_hash") or "")
            valid = bool(
                approval_id and approval.get("approved") is True and approval.get("scope_hash") == exact_hash
                and approval.get("revoked") is not True and (not expiry or expiry > instant)
            )
            if node.get("separation_of_duty") is True and approval.get("approver_person_id") == actor.get("person_id"):
                valid = False
                reason = "separation_of_duty_requires_different_approver"
            elif not approval:
                reason = "private_approval_missing"
            elif approval.get("revoked") is True:
                reason = "private_approval_revoked"
            elif expiry and expiry <= instant:
                reason = "private_approval_expired"
            elif approval.get("scope_hash") != exact_hash:
                reason = "approved_scope_changed"
            else:
                reason = "" if valid else "private_approval_invalid"
            approval_plan.append({"node_id": node["id"], "approval_id": approval_id, "valid": valid, "reason": reason})
            if not valid:
                errors.append(f"node:{node['id']}:{reason}")

        result = {
            "schema_version": "aion.flow.policy_disclosure_plan.v1",
            "flow_id": str(graph.get("flow_id") or ""),
            "aion_boundary": {"ingress_required": True, "return_receipt_required": True},
            "actor": {key: actor.get(key) for key in required_actor},
            "edges": edge_plan,
            "approvals": approval_plan,
            "allowed": not errors,
            "blocked_explanations": [self._plain(error) for error in sorted(set(errors))],
            "restricted_content_exposed_in_explanations": False,
            "generated_at": utc_now_iso(),
        }
        result["plan_hash"] = canonical_hash(result)
        return result

    @staticmethod
    def _plain(error: str) -> str:
        reason = error.split(":")[-1]
        messages = {
            "active_authority_incomplete": "Pilot cannot identify the active person and workspace.",
            "actor_role_not_allowed_for_purpose": "Your current role does not permit this purpose.",
            "actor_purpose_not_allowed": "This use is outside the approved purpose.",
            "membership_expired": "Your workspace authority has expired.",
            "actor_authority_revoked": "This device or person no longer has authority.",
            "data_classification_exceeds_external_policy": "This information is too sensitive for the selected destination.",
            "destination_not_allowed": "The selected destination is not approved by the customer.",
            "residency_not_allowed": "The selected data region is not approved.",
            "boundary_crossing_requires_encryption": "Information cannot leave the brain without encryption.",
            "boundary_crossing_fields_must_be_declared": "Pilot must list the exact fields before they leave the brain.",
            "fallback_expands_data_classification": "The fallback would expose more sensitive information.",
            "fallback_expands_destination": "The fallback would send information somewhere new.",
            "fallback_expands_cost": "The fallback exceeds the approved cost.",
            "separation_of_duty_requires_different_approver": "A different authorized person must approve this action.",
            "private_approval_missing": "Private approval is required on an authorized phone.",
            "private_approval_revoked": "The approval was revoked.",
            "private_approval_expired": "The approval expired.",
            "approved_scope_changed": "The action changed after approval and must be reviewed again.",
            "private_approval_invalid": "The private approval is not valid.",
        }
        return messages.get(reason, "A customer policy requirement blocked this route.")

    @staticmethod
    def _instant(value: Any) -> datetime | None:
        if not value:
            return None
        try:
            instant = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return instant if instant.tzinfo else instant.replace(tzinfo=timezone.utc)
        except ValueError:
            return datetime.min.replace(tzinfo=timezone.utc)
