"""Canonical contracts for the AION Department Pilot lifecycle.

This schema family is the durable boundary between the Boardroom, Central Pilot,
specialist Department Pilots, tools, the Business Container and the next Boardroom
meeting.  It deliberately does not execute work.  Runtime services persist and
advance these records while the existing mission/tool gateways enforce execution.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


DepartmentId = Literal[
    "marketing",
    "sales",
    "finance",
    "operations",
    "support",
    "hr",
    "pilot",
    "builder",
]

VerificationState = Literal[
    "unverified",
    "founder_supplied",
    "source_backed",
    "reconciled",
    "conflicted",
    "stale",
]

PackageStatus = Literal["draft", "awaiting_approval", "approved", "routed", "closed", "cancelled"]
TaskStatus = Literal[
    "queued",
    "claimed",
    "running",
    "waiting_approval",
    "blocked",
    "retry_scheduled",
    "completed",
    "failed",
    "cancelled",
]
TaskPriority = Literal["low", "medium", "high", "critical"]
ToolMode = Literal[
    "safe_internal",
    "read_only_external",
    "staged_external",
    "approved_live_external",
    "human_only",
    "unsupported",
]
ApprovalStatus = Literal["requested", "approved", "rejected", "expired", "invalidated"]
ArtifactStatus = Literal["draft", "staged", "accepted", "superseded", "rejected"]
ReceiptOutcome = Literal["succeeded", "failed", "blocked", "cancelled", "partial"]
HandbackStatus = Literal["draft", "ready_for_boardroom", "accepted", "superseded"]


def canonical_contract_hash(value: Any) -> str:
    """Return the common deterministic hash used across this contract family."""

    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + sha256(raw.encode("utf-8")).hexdigest()


def _record_hash(model: BaseModel, *excluded: str) -> str:
    payload = model.model_dump(mode="json")
    for key in excluded:
        payload.pop(key, None)
    return canonical_contract_hash(payload)


class CanonicalContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ContractProvenance(CanonicalContract):
    schema_version: Literal["aion.department_pilot.provenance.v1"] = (
        "aion.department_pilot.provenance.v1"
    )
    created_by: str
    created_at: str
    source_system: str = "aion"
    source_record_id: Optional[str] = None
    source_hash: Optional[str] = None
    correlation_id: Optional[str] = None


class ContextReference(CanonicalContract):
    schema_version: Literal["aion.department_pilot.context_reference.v1"] = (
        "aion.department_pilot.context_reference.v1"
    )
    reference_id: str
    workspace_id: str
    container_kind: str
    container_id: str
    json_pointer: Optional[str] = None
    revision: Optional[int] = None
    content_hash: str
    verification_state: VerificationState = "unverified"
    summary: Optional[str] = None
    evidence_refs: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_hash(self) -> "ContextReference":
        if not self.content_hash.startswith("sha256:"):
            raise ValueError("context_reference_requires_sha256_content_hash")
        return self


class RetrievedEvidence(CanonicalContract):
    schema_version: Literal["aion.department_pilot.retrieved_evidence.v1"] = (
        "aion.department_pilot.retrieved_evidence.v1"
    )
    evidence_id: str
    task_id: str
    department_id: DepartmentId
    reference_id: str
    retrieval_status: Literal["retrieved", "missing", "hash_mismatch", "access_denied"]
    expected_content_hash: str
    source_content_hash: Optional[str] = None
    verification_state: VerificationState = "unverified"
    retrieved_at: str
    retrieved_by: str
    data: Dict[str, Any] = Field(default_factory=dict)
    issue: Optional[str] = None
    retrieval_hash: str

    @model_validator(mode="after")
    def validate_retrieval(self) -> "RetrievedEvidence":
        hashes = [self.expected_content_hash, self.retrieval_hash]
        if self.source_content_hash:
            hashes.append(self.source_content_hash)
        if any(not value.startswith("sha256:") for value in hashes):
            raise ValueError("retrieved_evidence_requires_sha256_hashes")
        if self.retrieval_status == "retrieved":
            if self.source_content_hash != self.expected_content_hash:
                raise ValueError("retrieved_evidence_source_hash_mismatch")
            if self.issue:
                raise ValueError("successfully_retrieved_evidence_cannot_have_issue")
        elif not self.issue:
            raise ValueError("unsuccessful_evidence_retrieval_requires_issue")
        if self.retrieval_hash != _record_hash(self, "retrieval_hash"):
            raise ValueError("retrieved_evidence_hash_mismatch")
        return self


class BoardroomPackageApproval(CanonicalContract):
    schema_version: Literal["aion.department_pilot.package_approval.v1"] = (
        "aion.department_pilot.package_approval.v1"
    )
    approval_id: str
    package_id: str
    approved: bool
    approved_by: str
    approved_at: str
    approved_package_hash: str
    approval_scope: Literal["boardroom_assignment_boundary"] = "boardroom_assignment_boundary"
    notes: Optional[str] = None
    approval_hash: str

    @model_validator(mode="after")
    def validate_hashes(self) -> "BoardroomPackageApproval":
        for value in (self.approved_package_hash, self.approval_hash):
            if not value.startswith("sha256:"):
                raise ValueError("package_approval_requires_sha256_hashes")
        if self.approval_hash != _record_hash(self, "approval_hash"):
            raise ValueError("boardroom_package_approval_hash_mismatch")
        return self


class BoardroomAssignmentAction(CanonicalContract):
    schema_version: Literal["aion.department_pilot.assignment_action.v1"] = (
        "aion.department_pilot.assignment_action.v1"
    )
    action_id: str
    title: str
    objective: str
    department_id: DepartmentId
    capability: str
    priority: TaskPriority = "medium"
    acceptance_criteria: List[str] = Field(default_factory=list)
    dependency_action_ids: List[str] = Field(default_factory=list)
    requested_artifact_types: List[str] = Field(default_factory=list)
    due_at: Optional[str] = None


class BoardroomAssignmentPackage(CanonicalContract):
    schema_version: Literal["aion.department_pilot.boardroom_assignment_package.v1"] = (
        "aion.department_pilot.boardroom_assignment_package.v1"
    )
    package_id: str
    workspace_id: str
    business_id: str
    boardroom_session_id: str
    boardroom_decision_id: str
    title: str
    objective: str
    department_id: DepartmentId
    status: PackageStatus = "draft"
    actions: List[BoardroomAssignmentAction]
    context_refs: List[ContextReference] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    provenance: ContractProvenance
    package_hash: str
    approval: Optional[BoardroomPackageApproval] = None

    @model_validator(mode="after")
    def validate_package(self) -> "BoardroomAssignmentPackage":
        if not self.actions:
            raise ValueError("boardroom_assignment_package_requires_actions")
        if any(action.department_id != self.department_id for action in self.actions):
            raise ValueError("boardroom_assignment_action_department_mismatch")
        if not self.package_hash.startswith("sha256:"):
            raise ValueError("boardroom_assignment_package_requires_sha256_hash")
        if self.package_hash != _record_hash(self, "package_hash", "approval"):
            raise ValueError("boardroom_assignment_package_hash_mismatch")
        if self.status in {"approved", "routed", "closed"}:
            if not self.approval or self.approval.approved is not True:
                raise ValueError("approved_package_requires_positive_approval")
            if self.approval.approved_package_hash != self.package_hash:
                raise ValueError("package_changed_after_approval")
        return self


class DepartmentPilotTask(CanonicalContract):
    schema_version: Literal["aion.department_pilot.task.v1"] = "aion.department_pilot.task.v1"
    task_id: str
    workspace_id: str
    business_id: str
    package_id: str
    package_hash: str
    action_id: str
    department_id: DepartmentId
    pilot_id: str
    title: str
    objective: str
    capability: str
    status: TaskStatus = "queued"
    priority: TaskPriority = "medium"
    acceptance_criteria: List[str] = Field(default_factory=list)
    dependency_task_ids: List[str] = Field(default_factory=list)
    context_refs: List[ContextReference] = Field(default_factory=list)
    approval_required: bool = False
    assigned_at: Optional[str] = None
    claimed_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    provenance: ContractProvenance
    task_hash: str

    @model_validator(mode="after")
    def validate_task(self) -> "DepartmentPilotTask":
        if not self.package_hash.startswith("sha256:") or not self.task_hash.startswith("sha256:"):
            raise ValueError("department_task_requires_sha256_hashes")
        if self.task_hash != _record_hash(self, "task_hash"):
            raise ValueError("department_task_hash_mismatch")
        if self.retry_count < 0 or self.max_retries < 0 or self.retry_count > self.max_retries:
            raise ValueError("invalid_department_task_retry_state")
        if self.status == "completed" and not self.completed_at:
            raise ValueError("completed_department_task_requires_completed_at")
        return self


class DepartmentTaskEvent(CanonicalContract):
    schema_version: Literal["aion.department_pilot.task_event.v1"] = (
        "aion.department_pilot.task_event.v1"
    )
    event_id: str
    task_id: str
    department_id: DepartmentId
    event_type: Literal[
        "created",
        "claimed",
        "started",
        "progress",
        "approval_requested",
        "approval_resolved",
        "blocked",
        "retry_scheduled",
        "artifact_created",
        "completed",
        "failed",
        "cancelled",
        "handed_back",
    ]
    occurred_at: str
    actor_id: str
    from_status: Optional[TaskStatus] = None
    to_status: Optional[TaskStatus] = None
    progress_percent: Optional[int] = None
    message: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    previous_event_hash: Optional[str] = None
    event_hash: str

    @model_validator(mode="after")
    def validate_event(self) -> "DepartmentTaskEvent":
        if self.progress_percent is not None and not 0 <= self.progress_percent <= 100:
            raise ValueError("task_event_progress_must_be_between_0_and_100")
        if not self.event_hash.startswith("sha256:"):
            raise ValueError("task_event_requires_sha256_hash")
        if self.event_hash != _record_hash(self, "event_hash"):
            raise ValueError("task_event_hash_mismatch")
        return self


class DepartmentConversationTurn(CanonicalContract):
    schema_version: Literal["aion.department_pilot.conversation_turn.v1"] = (
        "aion.department_pilot.conversation_turn.v1"
    )
    turn_id: str
    task_id: str
    department_id: DepartmentId
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    created_at: str
    actor_id: Optional[str] = None
    context_refs: List[ContextReference] = Field(default_factory=list)
    tool_call_id: Optional[str] = None
    previous_turn_hash: Optional[str] = None
    turn_hash: str

    @model_validator(mode="after")
    def validate_turn(self) -> "DepartmentConversationTurn":
        if not self.turn_hash.startswith("sha256:"):
            raise ValueError("conversation_turn_requires_sha256_hash")
        if self.turn_hash != _record_hash(self, "turn_hash"):
            raise ValueError("conversation_turn_hash_mismatch")
        return self


class ProposedToolCall(CanonicalContract):
    schema_version: Literal["aion.department_pilot.proposed_tool_call.v1"] = (
        "aion.department_pilot.proposed_tool_call.v1"
    )
    tool_call_id: str
    task_id: str
    department_id: DepartmentId
    capability: str
    tool_name: str
    provider: str
    tool_mode: ToolMode
    payload: Dict[str, Any] = Field(default_factory=dict)
    payload_hash: str
    rationale: str
    external_side_effect: bool = False
    approval_required: bool = False
    proposed_at: str
    proposed_by: str
    proposal_hash: str

    @model_validator(mode="after")
    def validate_tool_call(self) -> "ProposedToolCall":
        if self.payload_hash != canonical_contract_hash(self.payload):
            raise ValueError("proposed_tool_payload_hash_mismatch")
        if not self.proposal_hash.startswith("sha256:"):
            raise ValueError("proposed_tool_call_requires_sha256_proposal_hash")
        if self.proposal_hash != _record_hash(self, "proposal_hash"):
            raise ValueError("proposed_tool_call_hash_mismatch")
        if self.tool_mode == "approved_live_external":
            if self.approval_required is not True or self.external_side_effect is not True:
                raise ValueError("live_tool_call_requires_exact_payload_approval")
        return self


class DepartmentApprovalRecord(CanonicalContract):
    schema_version: Literal["aion.department_pilot.approval_record.v1"] = (
        "aion.department_pilot.approval_record.v1"
    )
    approval_id: str
    task_id: str
    tool_call_id: str
    department_id: DepartmentId
    status: ApprovalStatus
    approval_scope: Literal["exact_payload_only"] = "exact_payload_only"
    requested_payload_hash: str
    decided_payload_hash: Optional[str] = None
    requested_by: str
    requested_at: str
    decided_by: Optional[str] = None
    decided_at: Optional[str] = None
    expires_at: Optional[str] = None
    reason: Optional[str] = None
    approval_hash: str

    @model_validator(mode="after")
    def validate_approval(self) -> "DepartmentApprovalRecord":
        if not self.requested_payload_hash.startswith("sha256:"):
            raise ValueError("approval_requires_exact_sha256_payload_hash")
        if not self.approval_hash.startswith("sha256:"):
            raise ValueError("approval_requires_sha256_approval_hash")
        if self.approval_hash != _record_hash(self, "approval_hash"):
            raise ValueError("department_approval_hash_mismatch")
        if self.status == "approved":
            if not self.decided_by or not self.decided_at:
                raise ValueError("approved_tool_call_requires_decision_identity_and_time")
            if self.decided_payload_hash != self.requested_payload_hash:
                raise ValueError("approved_payload_hash_mismatch")
        return self


class DepartmentArtifact(CanonicalContract):
    schema_version: Literal["aion.department_pilot.artifact.v1"] = (
        "aion.department_pilot.artifact.v1"
    )
    artifact_id: str
    task_id: str
    department_id: DepartmentId
    artifact_type: str
    title: str
    status: ArtifactStatus = "draft"
    business_container_path: str
    file_cabinet_path: Optional[str] = None
    media_type: Optional[str] = None
    content_hash: str
    evidence_refs: List[str] = Field(default_factory=list)
    created_at: str
    created_by: str
    provenance: ContractProvenance

    @model_validator(mode="after")
    def validate_artifact(self) -> "DepartmentArtifact":
        if not self.content_hash.startswith("sha256:"):
            raise ValueError("department_artifact_requires_sha256_content_hash")
        if not self.business_container_path:
            raise ValueError("department_artifact_requires_business_container_path")
        return self


class DepartmentExecutionReceipt(CanonicalContract):
    schema_version: Literal["aion.department_pilot.execution_receipt.v1"] = (
        "aion.department_pilot.execution_receipt.v1"
    )
    receipt_id: str
    task_id: str
    department_id: DepartmentId
    outcome: ReceiptOutcome
    started_at: Optional[str] = None
    completed_at: str
    requested_payload_hash: Optional[str] = None
    executed_payload_hash: Optional[str] = None
    before_state_hash: Optional[str] = None
    after_state_hash: Optional[str] = None
    artifact_ids: List[str] = Field(default_factory=list)
    evidence_hashes: List[str] = Field(default_factory=list)
    approval_ids: List[str] = Field(default_factory=list)
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    rollback_available: bool = False
    rollback_instructions: Optional[str] = None
    legacy_receipt_hash: Optional[str] = None
    receipt_hash: str

    @model_validator(mode="after")
    def validate_receipt(self) -> "DepartmentExecutionReceipt":
        hash_values = [self.receipt_hash, *self.evidence_hashes]
        hash_values.extend(
            value
            for value in (
                self.requested_payload_hash,
                self.executed_payload_hash,
                self.before_state_hash,
                self.after_state_hash,
                self.legacy_receipt_hash,
            )
            if value is not None
        )
        if any(not value.startswith("sha256:") for value in hash_values):
            raise ValueError("execution_receipt_requires_sha256_hashes")
        if self.receipt_hash != _record_hash(self, "receipt_hash"):
            raise ValueError("department_execution_receipt_hash_mismatch")
        if self.rollback_available and not self.rollback_instructions:
            raise ValueError("rollback_instructions_required_when_available")
        if self.outcome == "failed" and not self.error_code:
            raise ValueError("failed_receipt_requires_error_code")
        return self


class DepartmentIntelligencePatch(CanonicalContract):
    schema_version: Literal["aion.department_pilot.intelligence_patch.v1"] = (
        "aion.department_pilot.intelligence_patch.v1"
    )
    patch_id: str
    task_id: str
    department_id: DepartmentId
    base_revision: int
    operations: List[Dict[str, Any]]
    evidence_refs: List[str] = Field(default_factory=list)
    verification_state: VerificationState = "unverified"
    created_at: str
    created_by: str
    patch_hash: str

    @model_validator(mode="after")
    def validate_patch(self) -> "DepartmentIntelligencePatch":
        if not self.operations:
            raise ValueError("department_intelligence_patch_requires_operations")
        for operation in self.operations:
            if operation.get("op") not in {"add", "replace", "remove", "test"}:
                raise ValueError("unsupported_department_intelligence_patch_operation")
            if not str(operation.get("path") or "").startswith("/"):
                raise ValueError("department_intelligence_patch_requires_json_pointer_path")
        if not self.patch_hash.startswith("sha256:"):
            raise ValueError("department_intelligence_patch_requires_sha256_hash")
        if self.patch_hash != _record_hash(self, "patch_hash"):
            raise ValueError("department_intelligence_patch_hash_mismatch")
        return self


class BoardroomHandbackSummary(CanonicalContract):
    schema_version: Literal["aion.department_pilot.boardroom_handback.v1"] = (
        "aion.department_pilot.boardroom_handback.v1"
    )
    handback_id: str
    package_id: str
    task_id: str
    department_id: DepartmentId
    status: HandbackStatus = "draft"
    outcome: ReceiptOutcome
    executive_summary: str
    completed_actions: List[str] = Field(default_factory=list)
    unresolved_items: List[str] = Field(default_factory=list)
    decisions_requested: List[str] = Field(default_factory=list)
    metric_changes: Dict[str, Any] = Field(default_factory=dict)
    artifact_ids: List[str] = Field(default_factory=list)
    receipt_ids: List[str] = Field(default_factory=list)
    intelligence_patch_ids: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    created_at: str
    created_by: str
    handback_hash: str

    @model_validator(mode="after")
    def validate_handback(self) -> "BoardroomHandbackSummary":
        if not self.handback_hash.startswith("sha256:"):
            raise ValueError("boardroom_handback_requires_sha256_hash")
        if self.handback_hash != _record_hash(self, "handback_hash"):
            raise ValueError("boardroom_handback_hash_mismatch")
        if self.status in {"ready_for_boardroom", "accepted"} and not self.receipt_ids:
            raise ValueError("ready_handback_requires_completion_receipt")
        return self


class DepartmentPilotWorkEnvelope(CanonicalContract):
    """The complete, portable record of one Boardroom action lifecycle."""

    schema_version: Literal["aion.department_pilot.work_envelope.v1"] = (
        "aion.department_pilot.work_envelope.v1"
    )
    package: BoardroomAssignmentPackage
    task: DepartmentPilotTask
    events: List[DepartmentTaskEvent] = Field(default_factory=list)
    conversation: List[DepartmentConversationTurn] = Field(default_factory=list)
    retrieved_evidence: List[RetrievedEvidence] = Field(default_factory=list)
    proposed_tool_calls: List[ProposedToolCall] = Field(default_factory=list)
    approvals: List[DepartmentApprovalRecord] = Field(default_factory=list)
    artifacts: List[DepartmentArtifact] = Field(default_factory=list)
    receipts: List[DepartmentExecutionReceipt] = Field(default_factory=list)
    intelligence_patches: List[DepartmentIntelligencePatch] = Field(default_factory=list)
    handback: Optional[BoardroomHandbackSummary] = None
    envelope_hash: str

    @model_validator(mode="after")
    def validate_lifecycle_links(self) -> "DepartmentPilotWorkEnvelope":
        if self.task.package_id != self.package.package_id:
            raise ValueError("task_package_id_mismatch")
        if self.task.package_hash != self.package.package_hash:
            raise ValueError("task_package_hash_mismatch")
        if self.task.department_id != self.package.department_id:
            raise ValueError("task_package_department_mismatch")

        linked_records: List[Any] = [
            *self.events,
            *self.conversation,
            *self.retrieved_evidence,
            *self.proposed_tool_calls,
            *self.approvals,
            *self.artifacts,
            *self.receipts,
            *self.intelligence_patches,
        ]
        for record in linked_records:
            if record.task_id != self.task.task_id:
                raise ValueError("work_envelope_task_link_mismatch")
            if record.department_id != self.task.department_id:
                raise ValueError("work_envelope_department_link_mismatch")

        tool_calls = {item.tool_call_id: item for item in self.proposed_tool_calls}
        for approval in self.approvals:
            tool_call = tool_calls.get(approval.tool_call_id)
            if tool_call is None:
                raise ValueError("approval_has_no_proposed_tool_call")
            if approval.requested_payload_hash != tool_call.payload_hash:
                raise ValueError("approval_tool_payload_hash_mismatch")

        artifact_ids = {item.artifact_id for item in self.artifacts}
        approval_ids = {item.approval_id for item in self.approvals}
        for receipt in self.receipts:
            if not set(receipt.artifact_ids).issubset(artifact_ids):
                raise ValueError("receipt_references_unknown_artifact")
            if not set(receipt.approval_ids).issubset(approval_ids):
                raise ValueError("receipt_references_unknown_approval")

        if self.handback:
            if self.handback.task_id != self.task.task_id:
                raise ValueError("handback_task_link_mismatch")
            if self.handback.package_id != self.package.package_id:
                raise ValueError("handback_package_link_mismatch")
            if self.handback.department_id != self.task.department_id:
                raise ValueError("handback_department_link_mismatch")
            receipt_ids = {item.receipt_id for item in self.receipts}
            patch_ids = {item.patch_id for item in self.intelligence_patches}
            if not set(self.handback.receipt_ids).issubset(receipt_ids):
                raise ValueError("handback_references_unknown_receipt")
            if not set(self.handback.artifact_ids).issubset(artifact_ids):
                raise ValueError("handback_references_unknown_artifact")
            if not set(self.handback.intelligence_patch_ids).issubset(patch_ids):
                raise ValueError("handback_references_unknown_intelligence_patch")
        if not self.envelope_hash.startswith("sha256:"):
            raise ValueError("work_envelope_requires_sha256_hash")
        if self.envelope_hash != _record_hash(self, "envelope_hash"):
            raise ValueError("work_envelope_hash_mismatch")
        return self
