from __future__ import annotations

import pytest

from backend.modules.aion_business.runtime.legacy_runtime_data_root import (
    LEGACY_RUNTIME_DIRECTORIES,
    LegacyRuntimeDataRootError,
    ensure_legacy_runtime_data_root,
    resolve_legacy_runtime_data_root,
    _supported_system,
)


def test_explicit_external_root_is_created_with_required_scaffolding(tmp_path):
    application = tmp_path / "application"
    runtime = tmp_path / "node-state" / "legacy"
    root = ensure_legacy_runtime_data_root(
        application_root=application,
        environment={"TESSARIS_DATA_ROOT": str(runtime)},
        system="linux",
    )
    assert root == runtime.resolve()
    assert all((root / name).is_dir() for name in LEGACY_RUNTIME_DIRECTORIES)


@pytest.mark.parametrize("variable", ["TESSARIS_DATA_ROOT", "DATA_ROOT"])
def test_application_tree_root_fails_closed(tmp_path, variable):
    application = tmp_path / "application"
    with pytest.raises(
        LegacyRuntimeDataRootError,
        match="overlaps_application",
    ):
        resolve_legacy_runtime_data_root(
            application_root=application,
            environment={variable: str(application / "data")},
            system="linux",
        )


@pytest.mark.parametrize(
    ("protected_name", "error_name"),
    [
        ("TESSARIS_UPDATE_ROOT", "overlaps_update"),
        ("TESSARIS_BUSINESS_VAULT_ROOT", "overlaps_vault"),
    ],
)
def test_update_and_vault_overlap_fail_closed(tmp_path, protected_name, error_name):
    protected = tmp_path / "protected"
    with pytest.raises(LegacyRuntimeDataRootError, match=error_name):
        resolve_legacy_runtime_data_root(
            application_root=tmp_path / "application",
            environment={
                "TESSARIS_DATA_ROOT": str(protected / "legacy"),
                protected_name: str(protected),
            },
            system="linux",
        )


def test_default_uses_external_node_state_and_leaves_old_source_untouched(tmp_path):
    application = tmp_path / "application"
    old_source = application / "data" / "customer-memory.json"
    old_source.parent.mkdir(parents=True)
    old_source.write_text('{"retained":true}', encoding="utf-8")
    node_state = tmp_path / "node-state"
    root = ensure_legacy_runtime_data_root(
        application_root=application,
        environment={
            "HOME": str(tmp_path / "home"),
            "TESSARIS_NODE_STATE_ROOT": str(node_state),
            "TESSARIS_UPDATE_ROOT": str(tmp_path / "updates"),
            "TESSARIS_BUSINESS_VAULT_ROOT": str(tmp_path / "vaults"),
        },
        system="linux",
    )
    assert root == (node_state / "legacy-runtime-data").resolve()
    assert old_source.read_text(encoding="utf-8") == '{"retained":true}'


@pytest.mark.parametrize("reported", ["win32", "cygwin", "msys", "windows"])
def test_python_windows_platform_names_use_windows_layout(reported):
    assert _supported_system(reported) == "windows"
