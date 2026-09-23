from __future__ import annotations

from backend.modules.workflow_capsules.connectors.providers.gmail_connector import (
    GMAIL_VAULT_HANDLE,
    GmailWorkflowConnector,
)
from backend.modules.workflow_capsules.connectors.providers.gmail_local_node_bridge import (
    LocalNodeGmailClientBridge,
)
from backend.modules.workflow_capsules.connectors.workflow_connector_adapter import (
    WorkflowConnectorAdapter,
)
from backend.modules.workflow_capsules.execution.workflow_capsule_runner import (
    EXECUTION_MODE_LIVE_EXECUTE,
    WorkflowCapsuleRunner,
)


class FakeLocalNodeRuntime:
    def _create_gmail_draft(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        cc: str = "",
        bcc: str = "",
        thread_id: str = "",
    ):
        return {
            "ok": True,
            "created": True,
            "sent": False,
            "draft_id": "draft-phase6-001",
            "message_id": "message-phase6-001",
            "thread_id": thread_id or "thread-phase6-001",
            "to": to,
            "subject": subject,
            "raw": "must-not-leak",
            "access_token": "must-not-leak",
        }


class FakeApprovalStore:
    def __init__(self, approval):
        self.approval = approval

    def get(self, approval_id):
        if approval_id == self.approval["approval_id"]:
            return self.approval
        return None


class FakeRegistry:
    def __init__(self, capsule):
        self.capsule = capsule

    def rebuild_and_save(self):
        return None

    def require(self, value):
        return self.capsule


class FakeCapsule:
    canonical_key = "workflow:test.gmail_draft.v1"
    display_name = "Test Gmail Draft"
    workflow_id = "workflow:test.gmail_draft.v1"
    vault_requirements = [GMAIL_VAULT_HANDLE]
    meta = {"permission_mode": "review"}
    workflow_graph = {}
    compiled_glyph = {}


class FakeStep:
    step_id = "create_gmail_draft"
    kind = "create_draft"
    external_write = True
    raw = {
        "step_id": "create_gmail_draft",
        "kind": "create_draft",
        "connector": "gmail",
        "to": "customer@example.com",
        "subject": "Re: Quote",
        "body": "Draft body",
        "output_ref": "gmail_draft.output",
        "permission": {
            "action": "gmail.create_draft",
            "risk_tier": "medium",
        },
    }


class FakeExpansion:
    ok = True
    errors = []
    warnings = []
    steps = [FakeStep()]


class FakeExpander:
    def expand(self, capsule):
        return FakeExpansion()


def _runner(approval):
    gmail_connector = GmailWorkflowConnector(
        gmail_client=LocalNodeGmailClientBridge(FakeLocalNodeRuntime())
    )

    return WorkflowCapsuleRunner(
        registry=FakeRegistry(FakeCapsule()),
        expander=FakeExpander(),
        approval_store=FakeApprovalStore(approval),
        connector_adapter=WorkflowConnectorAdapter(gmail_connector=gmail_connector),
    )


def _approval(**overrides):
    base = {
        "approval_id": "approval_gmail_draft_001",
        "status": "approved",
        "canonical_key": "workflow:test.gmail_draft.v1",
        "run_id": "run_001",
        "external_write_step_id": "create_gmail_draft",
        "payload": {
            "run": {
                "schema_version": "aion.workflow_capsule_dry_run_result.v1",
                "mode": "dry_run",
                "run_id": "run_001",
            }
        },
    }
    base.update(overrides)
    return base


def test_resume_real_gmail_draft_requires_vault() -> None:
    runner = _runner(_approval())

    result = runner.resume_after_approval(
        "approval_gmail_draft_001",
        available_vault_requirements=[],
        execution_mode=EXECUTION_MODE_LIVE_EXECUTE,
        extra={"allow_real_gmail_draft": True},
        rebuild_registry=False,
    )

    assert result["ok"] is False
    assert result["error"] == "missing_vault_requirements"
    assert GMAIL_VAULT_HANDLE in result["missing_vault_requirements"]


def test_resume_real_gmail_draft_requires_explicit_request() -> None:
    runner = _runner(_approval())

    result = runner.resume_after_approval(
        "approval_gmail_draft_001",
        available_vault_requirements=[GMAIL_VAULT_HANDLE],
        execution_mode=EXECUTION_MODE_LIVE_EXECUTE,
        rebuild_registry=False,
    )

    assert result["ok"] is False
    assert result["error"] == "real_gmail_draft_requires_explicit_request"


def test_resume_real_gmail_draft_requires_prior_dry_run_payload() -> None:
    approval = _approval(payload={})
    runner = _runner(approval)

    result = runner.resume_after_approval(
        "approval_gmail_draft_001",
        available_vault_requirements=[GMAIL_VAULT_HANDLE],
        execution_mode=EXECUTION_MODE_LIVE_EXECUTE,
        extra={"allow_real_gmail_draft": True},
        rebuild_registry=False,
    )

    assert result["ok"] is False
    assert result["error"] == "dry_run_required_before_real_gmail_draft"


def test_resume_real_gmail_draft_creates_draft_and_never_sends() -> None:
    runner = _runner(_approval())

    result = runner.resume_after_approval(
        "approval_gmail_draft_001",
        available_vault_requirements=[GMAIL_VAULT_HANDLE],
        execution_mode=EXECUTION_MODE_LIVE_EXECUTE,
        extra={"allow_real_gmail_draft": True},
        rebuild_registry=False,
    )

    assert result["ok"] is True
    assert result["status"] == "gmail_draft_created"
    assert result["message"] == "Draft created in Gmail. No email was sent."

    payload = result["connector_result"]["payload"]
    assert payload["sent"] is False
    assert payload["must_not_send"] is True
    assert payload["live_send_enabled"] is False
    assert payload["bridge_result"]["payload"]["draft_id"] == "draft-phase6-001"
    assert payload["bridge_result"]["payload"]["raw"] == "<redacted>"
    assert payload["bridge_result"]["payload"]["access_token"] == "<redacted>"

    audit = result["audit_event"]
    assert audit["connector"] == "gmail"
    assert audit["action"] == "create_draft"
    assert audit["status"] == "gmail_draft_created"
    assert audit["sent"] is False
    assert audit["must_not_send"] is True
    assert audit["live_send_enabled"] is False
