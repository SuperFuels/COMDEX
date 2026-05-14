from __future__ import annotations

from backend.modules.workflow_capsules.execution.workflow_capsule_runner import (
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
from backend.modules.workflow_capsules.registry.workflow_glyph_registry import (
    WorkflowGlyphRegistry,
)
from backend.modules.workflow_capsules.repository.workflow_capsule_repository import (
    WorkflowCapsuleRepository,
)


def _build_runner_with_materialized_electrician_capsule(tmp_path) -> WorkflowCapsuleRunner:
    repo = WorkflowCapsuleRepository(root=tmp_path / "workflow_capsules")

    pack = make_electrician_gmail_pack()
    binding = make_electrician_gmail_local_binding(
        workspace_id="costa-conexion",
        business_id="electrician-demo",
    )
    capsule = materialize_global_pattern_to_capsule(pack=pack, binding=binding)

    repo.save(
        capsule,
        scope="workspace",
        workspace_id="costa-conexion",
        overwrite=True,
    )

    registry = WorkflowGlyphRegistry(
        repository=repo,
        registry_path=tmp_path / "workflow_glyph_registry.json",
    )
    registry.rebuild_and_save()

    return WorkflowCapsuleRunner(registry=registry)


def test_materialized_global_pattern_runs_through_standard_dry_runner(tmp_path) -> None:
    runner = _build_runner_with_materialized_electrician_capsule(tmp_path)

    result = runner.run_dry(
        "workflow:electrician.gmail_receptionist.v1",
        inputs={
            "gmail_message_id": "msg-electrician-demo-001",
        },
        available_vault_requirements=[
            "vault.gmail.credentials",
        ],
        create_approval=True,
        rebuild_registry=False,
    ).to_dict()

    assert result["ok"] is True
    assert result["mode"] == "dry_run"
    assert result["canonical_key"] == "workflow:electrician.gmail_receptionist.v1"
    assert result["display_name"] == "Electrician Gmail Receptionist"
    assert result["capsule"]["display_glyph"] == "EL-001"
    assert result["capsule"]["vault_requirements"] == ["vault.gmail.credentials"]
    assert result["run"]["ok"] is True


def test_materialized_global_pattern_dry_run_requires_approval_but_does_not_live_execute(tmp_path) -> None:
    runner = _build_runner_with_materialized_electrician_capsule(tmp_path)

    result = runner.run_dry(
        "workflow:electrician.gmail_receptionist.v1",
        inputs={
            "gmail_message_id": "msg-electrician-demo-001",
        },
        available_vault_requirements=[
            "vault.gmail.credentials",
        ],
        create_approval=True,
        rebuild_registry=False,
    ).to_dict()

    assert result["ok"] is True
    assert result["run"]["approval_required"] is True
    assert result["approval"]["ok"] is True
    assert result["approval"]["status"] == "pending"
    assert result["approval"]["canonical_key"] == "workflow:electrician.gmail_receptionist.v1"

    run_text = str(result["run"]).lower()
    connector_text = str(result).lower()

    assert "live_execute" not in run_text
    assert "blocked_live_env_guard" not in connector_text
    assert "gmail_live_send_not_implemented" not in connector_text
    assert "external_write_ready" not in connector_text


def test_materialized_global_pattern_dry_run_blocks_without_vault_handle(tmp_path) -> None:
    runner = _build_runner_with_materialized_electrician_capsule(tmp_path)

    result = runner.run_dry(
        "workflow:electrician.gmail_receptionist.v1",
        inputs={
            "gmail_message_id": "msg-electrician-demo-001",
        },
        available_vault_requirements=[],
        create_approval=True,
        rebuild_registry=False,
    ).to_dict()

    assert result["canonical_key"] == "workflow:electrician.gmail_receptionist.v1"

    combined = str(result).lower()
    assert "vault.gmail.credentials" in combined
    assert "live_execute" not in combined
    assert "external_write_ready" not in combined


def test_materialized_global_pattern_can_resume_only_as_connector_ready_after_approval(tmp_path) -> None:
    runner = _build_runner_with_materialized_electrician_capsule(tmp_path)

    dry = runner.run_dry(
        "workflow:electrician.gmail_receptionist.v1",
        inputs={
            "gmail_message_id": "msg-electrician-demo-001",
        },
        available_vault_requirements=[
            "vault.gmail.credentials",
        ],
        create_approval=True,
        rebuild_registry=False,
    ).to_dict()

    approval_id = dry["approval"]["approval_id"]
    approved = runner.approve(approval_id, decided_by="pytest", reason="test approval")

    assert approved["ok"] is True
    assert approved["status"] == "approved"

    resumed = runner.resume_after_approval(
        approval_id,
        available_vault_requirements=[
            "vault.gmail.credentials",
        ],
        rebuild_registry=False,
        execution_mode="connector_ready",
    )

    assert resumed["ok"] is True
    assert resumed["execution_mode"] == "connector_ready"
    assert resumed["status"] == "simulated_external_write_ready"
    assert resumed["connector_result"]["payload"]["ready"] is True

    resumed_text = str(resumed).lower()
    assert "live_execute" not in resumed_text
    assert "blocked_live_env_guard" not in resumed_text
