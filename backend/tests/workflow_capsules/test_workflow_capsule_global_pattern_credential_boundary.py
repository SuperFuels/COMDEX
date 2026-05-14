from __future__ import annotations

import json
from pathlib import Path

import pytest

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


FORBIDDEN_SECRET_TERMS = [
    "access_token",
    "refresh_token",
    "client_secret",
    "password",
    "api_key",
    "private_key",
]


def test_materialized_capsule_allows_handles_but_not_raw_credentials() -> None:
    pack = make_electrician_gmail_pack()
    binding = make_electrician_gmail_local_binding(
        workspace_id="costa-conexion",
        business_id="electrician-demo",
    )

    capsule = materialize_global_pattern_to_capsule(pack=pack, binding=binding)
    payload = json.dumps(capsule.to_dict(), sort_keys=True).lower()

    assert "vault.gmail.credentials" in payload
    assert "connector.gmail.default" in payload

    for term in FORBIDDEN_SECRET_TERMS:
        assert term not in payload


def test_saved_materialized_capsule_file_allows_handles_but_not_raw_credentials(tmp_path) -> None:
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

    for term in FORBIDDEN_SECRET_TERMS:
        assert term not in text


@pytest.mark.parametrize("secret_key", FORBIDDEN_SECRET_TERMS)
def test_materializer_rejects_secret_fields_in_local_binding(secret_key: str) -> None:
    pack = make_electrician_gmail_pack()
    binding = make_electrician_gmail_local_binding(
        workspace_id="costa-conexion",
        business_id="electrician-demo",
    )

    binding.business_context[secret_key] = "must-not-enter-capsule"

    with pytest.raises(ValueError, match="secret_fields"):
        materialize_global_pattern_to_capsule(pack=pack, binding=binding)


@pytest.mark.parametrize("secret_key", FORBIDDEN_SECRET_TERMS)
def test_materializer_rejects_secret_fields_in_global_pack_template(secret_key: str) -> None:
    pack = make_electrician_gmail_pack()
    binding = make_electrician_gmail_local_binding(
        workspace_id="costa-conexion",
        business_id="electrician-demo",
    )

    pack.patterns[0].template[secret_key] = "must-not-enter-capsule"

    with pytest.raises(ValueError, match="secret_fields"):
        materialize_global_pattern_to_capsule(pack=pack, binding=binding)
