from __future__ import annotations

from backend.modules.workflow_capsules.glyph_store.workflow_glyph_schema import WorkflowGlyph
from backend.modules.workflow_capsules.glyph_store.workflow_glyph_repository import WorkflowGlyphRepository


UNIVERSAL_GLYPHS = [
    WorkflowGlyph(
        glyph_id="glyph.wd-1001.v1",
        glyph_code="WD-1001",
        name="Generic Lead Intake Workflow",
        workflow_id="universal.lead_intake.v1",
        workflow_version="v1",
        glyph_version="v1",
        scope="universal",
        callable=True,
        input_schema={
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "message": {"type": "string"},
                "customer_name": {"type": "string"},
                "email": {"type": "string"},
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "lead_received": {"type": "boolean"},
                "customer_name": {"type": "string"},
                "email": {"type": "string"},
                "enquiry": {"type": "string"},
            },
        },
        required_connectors=[],
        risk_tier="low",
        approval_policy={
            "dry_run_first": True,
            "approval_before_external_write": True,
            "live_send_enabled": False,
        },
        runtime_plan={
            "mode": "compiled_workflow_glyph_placeholder",
            "dry_run_only": True,
            "steps": [
                {"op": "aion.extract_lead_fields"},
                {"op": "aion.prepare_lead_summary"},
            ],
        },
        tags=["universal", "lead-intake", "starter"],
        description="Universal starter workflow for capturing and normalising inbound lead details.",
        source_glyph_code=None,
    ),
    WorkflowGlyph(
        glyph_id="glyph.gm-1001.v1",
        glyph_code="GM-1001",
        name="Gmail Customer Enquiry Reply",
        workflow_id="universal.gmail_customer_enquiry_reply.v1",
        workflow_version="v1",
        glyph_version="v1",
        scope="universal",
        callable=True,
        input_schema={
            "type": "object",
            "properties": {
                "gmail_message_id": {"type": "string"},
                "from": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "draft_created": {"type": "boolean"},
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
        },
        required_connectors=["gmail"],
        risk_tier="medium",
        approval_policy={
            "dry_run_first": True,
            "approval_before_external_write": True,
            "allowed_write_actions": ["gmail.create_draft"],
            "blocked_actions": [
                "gmail.send_email",
                "gmail.reply_email",
                "gmail.send_draft",
                "gmail.delete_email",
                "gmail.api_call",
            ],
            "live_send_enabled": False,
        },
        runtime_plan={
            "mode": "compiled_workflow_glyph_placeholder",
            "dry_run_only": True,
            "steps": [
                {"op": "gmail.watch_emails"},
                {"op": "aion.extract_fields"},
                {"op": "gmail.create_draft", "requires_approval": True},
            ],
        },
        tags=["universal", "gmail", "customer-enquiry", "draft-reply"],
        description="Universal Gmail workflow for reading a customer enquiry and preparing an approved draft reply. It does not send email.",
        source_glyph_code=None,
    ),
    WorkflowGlyph(
        glyph_id="glyph.el-1001.v1",
        glyph_code="EL-1001",
        name="Electrician Enquiry Setup",
        workflow_id="universal.electrician_enquiry_setup.v1",
        workflow_version="v1",
        glyph_version="v1",
        scope="universal",
        callable=True,
        input_schema={
            "type": "object",
            "properties": {
                "customer_message": {"type": "string"},
                "customer_name": {"type": "string"},
                "email": {"type": "string"},
                "job_type": {"type": "string"},
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "lead_type": {"type": "string"},
                "job_summary": {"type": "string"},
                "draft_reply": {"type": "string"},
                "requires_quote": {"type": "boolean"},
            },
        },
        required_connectors=["gmail"],
        risk_tier="medium",
        approval_policy={
            "dry_run_first": True,
            "approval_before_external_write": True,
            "allowed_write_actions": ["gmail.create_draft"],
            "live_send_enabled": False,
        },
        runtime_plan={
            "mode": "compiled_workflow_glyph_placeholder",
            "dry_run_only": True,
            "steps": [
                {"op": "aion.classify_electrician_enquiry"},
                {"op": "aion.extract_job_details"},
                {"op": "gmail.create_draft", "requires_approval": True},
            ],
        },
        tags=["universal", "electrician", "lead-intake", "quote"],
        description="Universal electrician enquiry workflow for classifying a job request and preparing a safe draft response.",
        source_glyph_code=None,
    ),
    WorkflowGlyph(
        glyph_id="glyph.mk-1001.v1",
        glyph_code="MK-1001",
        name="Marketing Campaign Draft Flow",
        workflow_id="universal.marketing_campaign_draft.v1",
        workflow_version="v1",
        glyph_version="v1",
        scope="universal",
        callable=True,
        input_schema={
            "type": "object",
            "properties": {
                "campaign_goal": {"type": "string"},
                "audience": {"type": "string"},
                "offer": {"type": "string"},
                "tone": {"type": "string"},
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "campaign_summary": {"type": "string"},
                "draft_copy": {"type": "string"},
                "approval_required": {"type": "boolean"},
            },
        },
        required_connectors=[],
        risk_tier="low",
        approval_policy={
            "dry_run_first": True,
            "approval_before_external_write": True,
            "live_send_enabled": False,
        },
        runtime_plan={
            "mode": "compiled_workflow_glyph_placeholder",
            "dry_run_only": True,
            "steps": [
                {"op": "aion.generate_campaign_brief"},
                {"op": "aion.draft_marketing_copy"},
                {"op": "approval.checkpoint"},
            ],
        },
        tags=["universal", "marketing", "campaign", "draft"],
        description="Universal marketing workflow for drafting campaign copy and stopping at approval.",
        source_glyph_code=None,
    ),
]


def seed_universal_glyphs() -> dict:
    repo = WorkflowGlyphRepository()
    saved = []

    for glyph in UNIVERSAL_GLYPHS:
        saved.append(repo.save(glyph))

    index = repo.rebuild_index()

    return {
        "ok": True,
        "count": len(saved),
        "saved": saved,
        "index": index,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(seed_universal_glyphs(), indent=2))
