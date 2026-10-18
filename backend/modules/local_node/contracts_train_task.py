from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field


class GmailTriggerConfig(BaseModel):
    trigger_type: Literal["gmail_message_match"] = "gmail_message_match"
    account_id: str = "default"
    query: str = "is:unread"
    label: Optional[str] = None
    subject_contains: Optional[str] = None
    body_contains: Optional[str] = None
    from_contains: Optional[str] = None
    dedupe: bool = True
    max_results: int = 10


class ExtractFieldSpec(BaseModel):
    key: str
    label: str
    required: bool = False
    description: str = ""


class ExtractionStepConfig(BaseModel):
    step_type: Literal["extract_customer_details"] = "extract_customer_details"
    fields: List[ExtractFieldSpec] = Field(default_factory=list)


class HubSpotActionConfig(BaseModel):
    step_type: Literal["hubspot_create_or_update_contact"] = "hubspot_create_or_update_contact"
    account_id: str = "default"
    match_field: str = "email"
    field_mapping: Dict[str, str] = Field(default_factory=dict)
    dry_run: bool = True


class GmailDraftActionConfig(BaseModel):
    step_type: Literal["gmail_draft_welcome_email"] = "gmail_draft_welcome_email"
    account_id: str = "default"
    to_field: str = "email"
    subject_template: str = "Welcome — thanks for your enquiry"
    body_template: str = (
        "Hi {{name}},\n\n"
        "Thanks for getting in touch. We’ve received your enquiry and will come back to you shortly.\n\n"
        "Best,\n"
        "{{business_name}}"
    )


class ApprovalCheckpointConfig(BaseModel):
    step_type: Literal["approval_checkpoint"] = "approval_checkpoint"
    approval_mode: Literal[
        "draft_only",
        "ask_before_crm",
        "ask_before_email_send",
        "ask_before_external_action",
    ] = "ask_before_external_action"
    title: str = "Review new customer automation"
    require_human: bool = True


class TrainTaskWorkflowConfig(BaseModel):
    workflow_id: str
    name: str
    department_key: str = "operations"
    operator_id: str = "operator_customer_onboarding_v1"
    trigger: GmailTriggerConfig
    extraction: ExtractionStepConfig
    hubspot: HubSpotActionConfig
    email_draft: GmailDraftActionConfig
    approval: ApprovalCheckpointConfig
    enabled: bool = False
    version: int = 1
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TriggerMatch(BaseModel):
    trigger_id: str
    source: str
    source_item_id: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    dedupe_key: str
    matched_at: str


class TrainTaskRunResult(BaseModel):
    ok: bool
    workflow_id: str
    run_id: Optional[str] = None
    status: str = "unknown"
    trigger_match: Optional[Dict[str, Any]] = None
    extracted_fields: Dict[str, Any] = Field(default_factory=dict)
    hubspot_result: Dict[str, Any] = Field(default_factory=dict)
    email_draft_result: Dict[str, Any] = Field(default_factory=dict)
    approval_result: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    at: Optional[str] = None