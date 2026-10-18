from __future__ import annotations

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


def _save_materialized_capsule(tmp_path):
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

    return repo, capsule


def test_registry_resolves_materialized_workspace_capsule_by_canonical_key(tmp_path) -> None:
    repo, capsule = _save_materialized_capsule(tmp_path)

    registry = WorkflowGlyphRegistry(
        repository=repo,
        registry_path=tmp_path / "workflow_glyph_registry.json",
    )
    registry.rebuild_and_save()

    resolved = registry.require("workflow:electrician.gmail_receptionist.v1")

    assert resolved.canonical_key == "workflow:electrician.gmail_receptionist.v1"
    assert resolved.display_glyph == "EL-001"
    assert resolved.workflow_graph["workspace_id"] == "costa-conexion"
    assert resolved.workflow_graph["business_id"] == "electrician-demo"
    assert resolved.workflow_graph["vault_bindings"]["gmail_credentials"] == "vault.gmail.credentials"


def test_registry_resolves_materialized_workspace_capsule_by_display_glyph(tmp_path) -> None:
    repo, capsule = _save_materialized_capsule(tmp_path)

    registry = WorkflowGlyphRegistry(
        repository=repo,
        registry_path=tmp_path / "workflow_glyph_registry.json",
    )
    registry.rebuild_and_save()

    resolved = registry.require("EL-001")

    assert resolved.canonical_key == "workflow:electrician.gmail_receptionist.v1"
    assert resolved.display_name == "Electrician Gmail Receptionist"
    assert "electrician" in resolved.tags
    assert "global-pattern" in resolved.tags


def test_registry_materialized_entry_contains_workspace_capsule_path(tmp_path) -> None:
    repo, capsule = _save_materialized_capsule(tmp_path)

    registry = WorkflowGlyphRegistry(
        repository=repo,
        registry_path=tmp_path / "workflow_glyph_registry.json",
    )
    build = registry.rebuild_and_save()

    assert build["ok"] is True
    assert "workflow:electrician.gmail_receptionist.v1" in registry.entries

    entry = registry.entries["workflow:electrician.gmail_receptionist.v1"]
    assert "workspace/costa-conexion" in entry.capsule_path.replace("\\", "/")
    assert entry.checksum
