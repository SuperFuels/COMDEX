from __future__ import annotations

from backend.modules.workflow_capsules.execution.workflow_capsule_expander import (
    WorkflowCapsuleExpander,
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


def test_materializer_creates_local_workflow_capsule_from_global_pattern() -> None:
    pack = make_electrician_gmail_pack()
    binding = make_electrician_gmail_local_binding(
        workspace_id="costa-conexion",
        business_id="electrician-demo",
    )

    capsule = materialize_global_pattern_to_capsule(pack=pack, binding=binding)

    assert capsule.canonical_key == "workflow:electrician.gmail_receptionist.v1"
    assert capsule.display_name == "Electrician Gmail Receptionist"
    assert capsule.display_glyph == "EL-001"
    assert "vault.gmail.credentials" in capsule.vault_requirements
    assert capsule.policy.dry_run_first is True
    assert capsule.policy.external_writes_allowed is False
    assert capsule.workflow_graph["workspace_id"] == "costa-conexion"
    assert capsule.workflow_graph["connector_bindings"]["gmail"] == "connector.gmail.default"
    assert capsule.workflow_graph["vault_bindings"]["gmail_credentials"] == "vault.gmail.credentials"


def test_materialized_capsule_expands_with_existing_expander() -> None:
    pack = make_electrician_gmail_pack()
    binding = make_electrician_gmail_local_binding(
        workspace_id="costa-conexion",
        business_id="electrician-demo",
    )

    capsule = materialize_global_pattern_to_capsule(pack=pack, binding=binding)
    expansion = WorkflowCapsuleExpander().expand(capsule)

    assert expansion.ok is True
    assert len(expansion.steps) == 4
    assert expansion.steps[0].kind == "read_email"
    assert expansion.steps[1].kind == "draft_content"
    assert expansion.steps[2].kind == "approval_checkpoint"
    assert expansion.steps[2].requires_approval is True
    assert expansion.steps[3].kind == "send_email"
    assert expansion.steps[3].external_write is True
    assert expansion.steps[3].requires_approval is True


def test_materialized_capsule_contains_vault_handles_not_credentials() -> None:
    pack = make_electrician_gmail_pack()
    binding = make_electrician_gmail_local_binding(
        workspace_id="costa-conexion",
        business_id="electrician-demo",
    )

    capsule = materialize_global_pattern_to_capsule(pack=pack, binding=binding)
    data = str(capsule.to_dict()).lower()

    assert "vault.gmail.credentials" in data
    assert "connector.gmail.default" in data

    assert "access_token" not in data
    assert "refresh_token" not in data
    assert "client_secret" not in data
    assert "password" not in data
    assert "api_key" not in data
    assert "private_key" not in data
