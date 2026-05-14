from __future__ import annotations

from pathlib import Path

from backend.modules.workflow_capsules.global_registry.global_pattern_materializer import (
    materialize_global_pattern_to_capsule,
)
from backend.modules.workflow_capsules.global_registry.industry_pack_schema import (
    make_electrician_gmail_pack,
)
from backend.modules.workflow_capsules.global_registry.local_binding_schema import (
    make_electrician_gmail_local_binding,
)
from backend.modules.workflow_capsules.repository.workflow_capsule_repository import (
    WorkflowCapsuleRepository,
)


def test_materialized_capsule_saves_to_workspace_path(tmp_path) -> None:
    repo = WorkflowCapsuleRepository(root=tmp_path / "workflow_capsules")

    pack = make_electrician_gmail_pack()
    binding = make_electrician_gmail_local_binding(
        workspace_id="costa-conexion",
        business_id="electrician-demo",
    )
    capsule = materialize_global_pattern_to_capsule(pack=pack, binding=binding)

    saved = repo.save(
        capsule,
        scope="workspace",
        workspace_id="costa-conexion",
        overwrite=True,
    )

    assert saved["ok"] is True
    assert saved["canonical_key"] == "workflow:electrician.gmail_receptionist.v1"
    assert saved["scope"] == "workspace"
    assert saved["workspace_id"] == "costa-conexion"
    assert saved["checksum"]

    path = Path(str(saved["path"]))
    assert path.exists()
    assert path.name == "workflow_electrician.gmail_receptionist.v1.workflow.wiki.phn"
    assert "workspace/costa-conexion" in path.as_posix()


def test_saved_materialized_capsule_loads_back_from_workspace(tmp_path) -> None:
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

    loaded = repo.require(
        "workflow:electrician.gmail_receptionist.v1",
        workspace_id="costa-conexion",
        prefer_workspace=True,
    )

    assert loaded.canonical_key == "workflow:electrician.gmail_receptionist.v1"
    assert loaded.display_glyph == "EL-001"
    assert loaded.workflow_graph["workspace_id"] == "costa-conexion"
    assert loaded.workflow_graph["business_id"] == "electrician-demo"
    assert loaded.workflow_graph["vault_bindings"]["gmail_credentials"] == "vault.gmail.credentials"
    assert loaded.meta["source_pack_key"] == "industry.electrician.core.v1"
    assert loaded.meta["source_pattern_key"] == "global.workflow.electrician.gmail_receptionist.v1"
    assert loaded.meta["source_binding_key"] == "binding.costa-conexion.electrician.gmail_receptionist.v1"


def test_saved_materialized_capsule_file_contains_no_credentials(tmp_path) -> None:
    repo = WorkflowCapsuleRepository(root=tmp_path / "workflow_capsules")

    pack = make_electrician_gmail_pack()
    binding = make_electrician_gmail_local_binding(
        workspace_id="costa-conexion",
        business_id="electrician-demo",
    )
    capsule = materialize_global_pattern_to_capsule(pack=pack, binding=binding)

    saved = repo.save(
        capsule,
        scope="workspace",
        workspace_id="costa-conexion",
        overwrite=True,
    )

    text = Path(str(saved["path"])).read_text(encoding="utf-8").lower()

    assert "vault.gmail.credentials" in text
    assert "connector.gmail.default" in text

    assert "access_token" not in text
    assert "refresh_token" not in text
    assert "client_secret" not in text
    assert "password" not in text
    assert "api_key" not in text
    assert "private_key" not in text
