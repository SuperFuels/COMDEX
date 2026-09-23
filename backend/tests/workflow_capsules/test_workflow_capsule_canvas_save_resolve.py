from __future__ import annotations

from backend.modules.workflow_capsules.canvas.canvas_workflow_compiler import (
    CanvasWorkflowCompiler,
)
from backend.modules.workflow_capsules.repository.workflow_capsule_repository import (
    WorkflowCapsuleRepository,
)
from backend.modules.workflow_capsules.registry.workflow_glyph_registry import (
    WorkflowGlyphRegistry,
    WorkflowGlyphRegistryEntry,
)
from backend.modules.workflow_capsules.execution.workflow_capsule_runner import (
    WorkflowCapsuleRunner,
)


def _sample_canvas():
    return {
        "canonical_key": "workflow:canvas.saved_demo.v1",
        "display_name": "Canvas Saved Demo Workflow",
        "meaning": "Saved canvas-built demo workflow.",
        "display_glyph": "WG-CANVAS-DEMO-001",
        "tags": ["canvas", "demo", "saved"],
        "allowed_use_cases": ["Run a canvas-built demo workflow."],
        "vault_requirements": ["vault.gmail.credentials"],
        "policy": {
            "dry_run_first": True,
            "approval_before_external_write": True,
            "external_writes_allowed": False,
            "allow_autonomous_execution": False,
        },
        "nodes": [
            {
                "id": "read",
                "type": "read_email",
                "data": {
                    "step_id": "read_email",
                    "kind": "read_email",
                    "label": "Read Gmail message",
                    "connector": "gmail",
                    "requires": ["vault.gmail.credentials"],
                    "output_ref": "gmail.message",
                },
            },
            {
                "id": "draft",
                "type": "draft_reply",
                "data": {
                    "step_id": "draft_reply",
                    "kind": "draft_content",
                    "label": "Draft reply",
                    "output_ref": "gmail.reply_draft",
                },
            },
            {
                "id": "approval",
                "type": "approval_checkpoint",
                "data": {
                    "step_id": "approval",
                    "kind": "external_write",
                    "label": "Create Gmail draft after approval",
                    "connector": "gmail",
                    "requires": ["vault.gmail.credentials"],
                    "requires_approval": True,
                    "external_write": True,
                    "guard": {
                        "requires_approval_ref": "approval.result",
                        "reason": "Human approval required before Gmail draft creation.",
                    },
                    "output_ref": "gmail.draft.created",
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "read", "target": "draft"},
            {"id": "e2", "source": "draft", "target": "approval"},
        ],
    }


def test_canvas_compiled_capsule_can_be_saved_and_resolved(tmp_path) -> None:
    repo = WorkflowCapsuleRepository(root=tmp_path / "workflow_capsules")
    registry = WorkflowGlyphRegistry(
        repository=repo,
        registry_path=tmp_path / "workflow_glyph_registry.json",
    )

    compiled = CanvasWorkflowCompiler().compile(_sample_canvas())
    assert compiled.ok is True
    assert compiled.capsule is not None

    saved = repo.save(
        compiled.capsule,
        scope="core",
    )

    assert saved["ok"] is True
    assert str(saved["path"]).endswith(".workflow.wiki.phn")

    registry.entries[compiled.capsule.canonical_key] = WorkflowGlyphRegistryEntry.from_capsule(
        compiled.capsule,
        capsule_path=str(saved["path"]),
    )
    registry.save()

    by_key = registry.require("workflow:canvas.saved_demo.v1")
    by_glyph = registry.require("WG-CANVAS-DEMO-001")

    assert by_key.canonical_key == "workflow:canvas.saved_demo.v1"
    assert by_glyph.canonical_key == "workflow:canvas.saved_demo.v1"


def test_canvas_saved_capsule_runs_dry_through_standard_runner(tmp_path) -> None:
    repo = WorkflowCapsuleRepository(root=tmp_path / "workflow_capsules")
    registry = WorkflowGlyphRegistry(
        repository=repo,
        registry_path=tmp_path / "workflow_glyph_registry.json",
    )

    compiled = CanvasWorkflowCompiler().compile(_sample_canvas())
    saved = repo.save(
        compiled.capsule,
        scope="core",
    )
    registry.entries[compiled.capsule.canonical_key] = WorkflowGlyphRegistryEntry.from_capsule(
        compiled.capsule,
        capsule_path=str(saved["path"]),
    )
    registry.save()

    runner = WorkflowCapsuleRunner(registry=registry)

    result = runner.run_dry(
        "WG-CANVAS-DEMO-001",
        inputs={"gmail_message_id": "msg-canvas-001"},
        available_vault_requirements=["vault.gmail.credentials"],
        cau_state={
            "allow_learn": False,
            "adr_active": False,
            "deny_reason": "test_default_no_learning",
        },
        rebuild_registry=False,
    ).to_dict()

    assert result["canonical_key"] == "workflow:canvas.saved_demo.v1"
    assert result["ok"] is True
    assert result["run"]["approval_required"] is True
    assert result["approval"]["status"] == "pending"
    assert result["feedback"]["mutation_allowed"] is False
