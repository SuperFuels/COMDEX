from __future__ import annotations

from backend.modules.workflow_capsules.global_registry.global_registry_store import (
    GlobalWorkflowRegistryStore,
)
from backend.modules.workflow_capsules.global_registry.industry_pack_schema import (
    make_electrician_gmail_pack,
)
from backend.modules.workflow_capsules.global_registry.local_binding_schema import (
    make_electrician_gmail_local_binding,
)


def test_global_registry_store_saves_and_loads_industry_pack(tmp_path) -> None:
    store = GlobalWorkflowRegistryStore(
        global_root=tmp_path / "global",
        local_root=tmp_path / "local",
    )

    pack = make_electrician_gmail_pack()
    saved = store.save_industry_pack(pack)

    assert saved["ok"] is True
    assert saved["pack_key"] == "industry.electrician.core.v1"
    assert saved["checksum"]

    loaded = store.require_industry_pack("industry.electrician.core.v1")
    assert loaded.pack_key == "industry.electrician.core.v1"
    assert loaded.patterns[0].pattern_key == "global.workflow.electrician.gmail_receptionist.v1"

    rows = store.list_industry_packs()
    assert len(rows) == 1
    assert rows[0]["pack_key"] == "industry.electrician.core.v1"


def test_global_registry_store_saves_and_loads_local_binding(tmp_path) -> None:
    store = GlobalWorkflowRegistryStore(
        global_root=tmp_path / "global",
        local_root=tmp_path / "local",
    )

    binding = make_electrician_gmail_local_binding(
        workspace_id="costa-conexion",
        business_id="electrician-demo",
    )
    saved = store.save_local_binding(binding)

    assert saved["ok"] is True
    assert saved["binding_key"] == "binding.costa-conexion.electrician.gmail_receptionist.v1"
    assert saved["checksum"]

    loaded = store.require_local_binding("binding.costa-conexion.electrician.gmail_receptionist.v1")
    assert loaded.workspace_id == "costa-conexion"
    assert loaded.business_id == "electrician-demo"
    assert loaded.vault_bindings["gmail_credentials"] == "vault.gmail.credentials"

    rows = store.list_local_bindings(workspace_id="costa-conexion")
    assert len(rows) == 1
    assert rows[0]["workflow_canonical_key"] == "workflow:electrician.gmail_receptionist.v1"


def test_global_registry_store_keeps_global_and_local_separate(tmp_path) -> None:
    store = GlobalWorkflowRegistryStore(
        global_root=tmp_path / "global",
        local_root=tmp_path / "local",
    )

    pack = make_electrician_gmail_pack()
    binding = make_electrician_gmail_local_binding(
        workspace_id="costa-conexion",
        business_id="electrician-demo",
    )

    pack_saved = store.save_industry_pack(pack)
    binding_saved = store.save_local_binding(binding)

    assert "/global/" in pack_saved["path"].replace("\\", "/")
    assert "/local/" in binding_saved["path"].replace("\\", "/")

    pack_text = (tmp_path / "global").read_text(encoding="utf-8") if (tmp_path / "global").is_file() else ""
    assert pack_text == ""

    all_pack_rows = store.list_industry_packs()
    all_binding_rows = store.list_local_bindings()

    assert len(all_pack_rows) == 1
    assert len(all_binding_rows) == 1
    assert all_pack_rows[0]["pack_key"] != all_binding_rows[0]["binding_key"]


def test_global_registry_store_persisted_files_do_not_expose_credentials(tmp_path) -> None:
    store = GlobalWorkflowRegistryStore(
        global_root=tmp_path / "global",
        local_root=tmp_path / "local",
    )

    store.save_industry_pack(make_electrician_gmail_pack())
    store.save_local_binding(
        make_electrician_gmail_local_binding(
            workspace_id="costa-conexion",
            business_id="electrician-demo",
        )
    )

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(tmp_path.glob("**/*.json"))
    ).lower()

    assert "vault.gmail.credentials" in combined
    assert "access_token" not in combined
    assert "refresh_token" not in combined
    assert "client_secret" not in combined
    assert "password" not in combined
