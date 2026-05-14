from __future__ import annotations

from pathlib import Path

from backend.modules.aion_conversation.conversation_orchestrator import (
    ConversationOrchestrator,
)
from backend.modules.workflow_capsules.canvas.canvas_workflow_compiler import (
    CanvasWorkflowCompiler,
)
from backend.modules.workflow_capsules.execution.workflow_capsule_runner import (
    EXECUTION_MODE_CONNECTOR_READY,
    WorkflowCapsuleRunner,
)
from backend.modules.workflow_capsules.global_registry.global_pattern_materializer import (
    materialize_global_pattern_to_capsule,
)
from backend.modules.workflow_capsules.global_registry.industry_pack_schema import (
    make_electrician_gmail_pack,
)
from backend.modules.workflow_capsules.global_registry.local_binding_schema import (
    make_electrician_gmail_local_binding,
)


def test_final_production_lock_intent_to_guarded_resume_path() -> None:
    orch = ConversationOrchestrator()

    out = orch.handle_turn(
        session_id="pytest_final_production_lock_intent",
        user_text="Run WG-001 and draft a Gmail enquiry reply.",
        include_debug=True,
        include_metadata=True,
    )

    assert out["ok"] is True
    assert out["mode"] == "workflow_proposal"

    workflow = out["metadata"]["workflow_capsule"]
    full = out["metadata"]["workflow_capsule_result"]

    assert workflow["canonical_key"] == "workflow:gmail.enquiry_reply.v1"
    assert workflow["step_count"] == 5
    assert workflow["approval_required"] is True
    assert workflow["external_writes_blocked"] is True
    assert workflow["approval_id"]

    assert full["ok"] is True
    assert full["mode"] == "dry_run"
    assert full["run"]["approval_required"] is True
    assert full["run"]["external_writes_blocked"] is True
    assert full["approval"]["status"] == "pending"
    assert full["trace"]["ok"] is True
    assert full["feedback"]["ok"] is True
    assert full["feedback"]["mutation_applied"] is False

    combined = str(full).lower()
    assert "access_token" not in combined
    assert "refresh_token" not in combined
    assert "client_secret" not in combined
    assert "private_key" not in combined
    assert "live_execute" not in combined


def test_final_production_lock_approval_to_connector_ready_only() -> None:
    runner = WorkflowCapsuleRunner()

    dry = runner.run_dry(
        "WG-001",
        inputs={"gmail_message_id": "pytest-final-lock-msg-001"},
        available_vault_requirements=["vault.gmail.credentials"],
        cau_state={
            "allow_learn": False,
            "adr_active": False,
            "deny_reason": "pytest_final_lock_no_learning",
        },
        extra={"pytest": True, "lock": "final_production"},
    )

    assert dry.ok is True
    assert dry.mode == "dry_run"
    assert dry.approval["ok"] is True
    assert dry.approval["status"] == "pending"

    approval_id = dry.approval["approval_id"]

    approved = runner.approve(
        approval_id,
        decided_by="pytest",
        reason="Final production lock approval.",
    )

    assert approved["ok"] is True
    assert approved["status"] == "approved"

    resumed = runner.resume_after_approval(
        approval_id,
        available_vault_requirements=["vault.gmail.credentials"],
        cau_state={
            "allow_learn": False,
            "adr_active": False,
            "deny_reason": "pytest_final_lock_no_learning",
        },
        execution_mode=EXECUTION_MODE_CONNECTOR_READY,
    )

    assert resumed["ok"] is True
    assert resumed["phase"] == "resume_after_approval"
    assert resumed["execution_mode"] == "connector_ready"
    assert resumed["status"] == "simulated_external_write_ready"
    assert resumed["connector_result"]["action"] == "external_write_ready"
    assert resumed["connector_result"]["payload"]["ready"] is True
    assert resumed["permission"]["decision"] in {
        "request_approval",
        "auto_run",
        "draft_only",
        "block",
    }

    combined = str(resumed).lower()
    assert "live_execute" not in combined
    assert "gmail_live_send" not in combined
    assert "send_message" not in combined


def test_final_production_lock_canvas_compile_save_contract_still_present() -> None:
    canvas = {
        "canonical_key": "workflow:final_lock.canvas_demo.v1",
        "display_name": "Final Lock Canvas Demo",
        "meaning": "Canvas-built workflow capsule final lock demo.",
        "display_glyph": "WG-FINAL-CANVAS",
        "tags": ["final-lock", "canvas"],
        "vault_requirements": ["vault.gmail.credentials"],
        "permission_mode": "review",
        "nodes": [
            {
                "id": "draft",
                "type": "draft_content",
                "data": {
                    "step_id": "draft",
                    "kind": "draft_content",
                    "label": "Draft message",
                    "permission": {
                        "mode": "draft_auto",
                        "risk_tier": "low",
                        "decision": "draft_only",
                    },
                    "output_ref": "draft.output",
                },
            },
            {
                "id": "approval",
                "type": "approval_checkpoint",
                "data": {
                    "step_id": "approval",
                    "kind": "approval_checkpoint",
                    "label": "Approve draft",
                    "permission": {
                        "mode": "review",
                        "risk_tier": "medium",
                        "decision": "request_approval",
                    },
                    "requires_approval": True,
                    "output_ref": "approval.output",
                },
            },
        ],
        "edges": [
            {
                "id": "e1",
                "source": "draft",
                "target": "approval",
            }
        ],
    }

    compiled = CanvasWorkflowCompiler().compile(canvas)

    assert compiled.ok is True
    assert compiled.capsule is not None
    assert compiled.capsule.canonical_key == "workflow:final_lock.canvas_demo.v1"
    assert compiled.capsule.workflow_graph["permission_mode"] == "review"
    assert compiled.capsule.compiled_glyph["steps"][0]["permission"]["mode"] == "draft_auto"

    combined = str(compiled.capsule.to_dict()).lower()
    assert "vault.gmail.credentials" in combined
    assert "access_token" not in combined
    assert "refresh_token" not in combined
    assert "client_secret" not in combined
    assert "private_key" not in combined


def test_final_production_lock_global_industry_pack_materialisation_still_present() -> None:
    pack = make_electrician_gmail_pack()
    binding = make_electrician_gmail_local_binding(
        workspace_id="costa-conexion",
        business_id="electrician-demo",
    )

    capsule = materialize_global_pattern_to_capsule(pack=pack, binding=binding)

    assert capsule.canonical_key == "workflow:electrician.gmail_receptionist.v1"
    assert capsule.display_glyph == "EL-001"
    assert capsule.vault_requirements == ["vault.gmail.credentials"]

    steps = capsule.compiled_glyph["steps"]
    assert [step["id"] for step in steps] == [
        "read",
        "draft",
        "approval",
        "send",
    ]
    assert [step["kind"] for step in steps] == [
        "read_email",
        "draft_content",
        "approval_checkpoint",
        "send_email",
    ]
    assert steps[-1]["external_write"] is True
    assert steps[-1]["requires_approval"] is True

    combined = str(capsule.to_dict()).lower()
    assert "connector.gmail.default" in combined
    assert "vault.gmail.credentials" in combined
    assert "access_token" not in combined
    assert "refresh_token" not in combined
    assert "client_secret" not in combined
    assert "private_key" not in combined


def test_final_production_lock_static_ui_bridges_are_present() -> None:
    app = Path("desktop/mac/src/app.js")
    assert app.exists()

    text = app.read_text(encoding="utf-8")

    assert "AION_WORKFLOW_CAPSULE_BOARDROOM_APPROVAL_BRIDGE_V1" in text
    assert "AION_WORKFLOW_CAPSULE_AUTONOMY_UI_BRIDGE_V1" in text
    assert 'data-aion-workflow-save-capsule="true"' in text
    assert "/api/workflow-capsules/canvas/compile-save" in text
    assert "/api/workflow-capsules/approvals/" in text
    assert 'execution_mode: "connector_ready"' in text or '"execution_mode":"connector_ready"' in text

    marker = "AION_WORKFLOW_CAPSULE_BOARDROOM_APPROVAL_BRIDGE_V1"
    start = text.index(marker)
    window = text[max(0, start - 6000): start + 14000]

    assert "live_execute" not in window
    assert "gmail_live_send" not in window.lower()
    assert "send_message" not in window.lower()
