from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict
from uuid import uuid4

from .canonical import canonical_hash, utc_now_iso
from .contracts import EnrollmentState
from .schema import DeviceSchema


@dataclass(slots=True)
class FieldActionProposal:
    proposal_id: str
    node_id: str
    action_id: str
    action_name: str
    arguments: Dict[str, Any]
    protocol: str
    endpoint: str
    risk: str
    requires_approval: bool
    state: str
    reason: str
    proposal_hash: str
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GovernedFieldOperator:
    """Prepare field actions but fail closed until a real adapter is authorized."""

    def propose(
        self,
        schema: DeviceSchema,
        *,
        action_id: str,
        arguments: Dict[str, Any],
        enrollment: EnrollmentState,
    ) -> FieldActionProposal:
        control = next((item for item in schema.controls if item.action_id == action_id), None)
        if control is None:
            raise KeyError(f"Action is not present in the evidenced device schema: {action_id}")
        state = "dry_run_ready" if enrollment is EnrollmentState.ENROLLED else "blocked_not_enrolled"
        reason = (
            "Schema-backed proposal is ready for an adapter dry run; live execution remains disabled."
            if state == "dry_run_ready"
            else "Discovery does not grant control. Enroll the device before testing an adapter."
        )
        payload = {
            "node_id": schema.node_id,
            "action_id": control.action_id,
            "arguments": arguments,
            "protocol": control.protocol,
            "endpoint": control.endpoint,
        }
        return FieldActionProposal(
            proposal_id=f"proposal_{uuid4().hex}",
            node_id=schema.node_id,
            action_id=control.action_id,
            action_name=control.name,
            arguments=arguments,
            protocol=control.protocol,
            endpoint=control.endpoint,
            risk=control.risk.value,
            requires_approval=control.requires_approval,
            state=state,
            reason=reason,
            proposal_hash=canonical_hash(payload),
        )

    def execute(self, proposal: FieldActionProposal) -> None:
        raise PermissionError(
            "No live device-control adapter is authorized in AION Fabric 0.2. "
            "Promote and test a protocol-specific adapter before execution."
        )
