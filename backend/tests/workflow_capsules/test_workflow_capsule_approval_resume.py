from backend.modules.workflow_capsules.execution.workflow_capsule_runner import WorkflowCapsuleRunner


def test_gmail_workflow_approval_resume_blocks_without_vault_and_passes_with_vault():
    runner = WorkflowCapsuleRunner()

    dry = runner.run_dry(
        "WG-001",
        inputs={"gmail_message_id": "demo-message-001"},
        available_vault_requirements=[],
        cau_state={
            "allow_learn": False,
            "adr_active": False,
            "deny_reason": "pytest_no_learning",
        },
        extra={"pytest": True, "stage": "approval_resume"},
    )

    assert dry.ok is True
    assert dry.canonical_key == "workflow:gmail.enquiry_reply.v1"
    assert dry.run_id
    assert dry.approval["ok"] is True
    assert dry.approval["status"] == "pending"

    approval_id = dry.approval["approval_id"]

    approved = runner.approve(
        approval_id,
        decided_by="pytest",
        reason="pytest approval resume validation",
    )

    assert approved["ok"] is True
    assert approved["status"] == "approved"
    assert approved["decision"] == "approved"

    blocked = runner.resume_after_approval(
        approval_id,
        available_vault_requirements=[],
        cau_state={"allow_learn": False},
    )

    assert blocked["ok"] is False
    assert blocked["error"] == "missing_vault_requirements"
    assert "vault.gmail.credentials" in blocked["missing_vault_requirements"]

    ready = runner.resume_after_approval(
        approval_id,
        available_vault_requirements=["vault.gmail.credentials"],
        cau_state={"allow_learn": False},
    )

    assert ready["ok"] is True
    assert ready["phase"] == "resume_after_approval"
    assert ready["canonical_key"] == "workflow:gmail.enquiry_reply.v1"
    assert ready["executed_external_step"] == "send_email_after_approval"
    assert ready["status"] == "simulated_external_write_ready"
    assert "not wired" in ready["message"]
