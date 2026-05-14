import os
import json
import pytest
from backend.modules.holograms.ghx_continuity_ledger import GHXContinuityLedger
from backend.modules.holograms.ghx_ledger_vault_exporter import GHXVaultExporter


@pytest.fixture
def temp_vault(tmp_path):
    vault_path = tmp_path / "vault"
    vault_path.mkdir()
    return str(vault_path)


def test_export_and_load_snapshot(temp_vault):
    ledger = GHXContinuityLedger("NodeA")
    ledger.append_event("alpha", {"x": 1})
    ledger.append_event("beta", {"y": 2})

    exporter = GHXVaultExporter(vault_root=temp_vault)
    receipt = exporter.export_snapshot(ledger)

    assert os.path.exists(receipt["path"])
    assert receipt["entries"] == 2

    reloaded = exporter.load_latest()
    assert reloaded.verify_chain()["verified"] is True
    assert len(reloaded.chain) == 2


def test_export_empty_ledger_raises(temp_vault):
    ledger = GHXContinuityLedger("EmptyNode")
    exporter = GHXVaultExporter(vault_root=temp_vault)
    with pytest.raises(ValueError):
        exporter.export_snapshot(ledger)


def test_vault_rotation_keeps_limit(temp_vault):
    ledger = GHXContinuityLedger("RotateNode")
    exporter = GHXVaultExporter(vault_root=temp_vault, max_keep=3)

    for i in range(6):
        ledger.append_event(f"event{i}", {"i": i})
        exporter.export_snapshot(ledger)

    container_dir = os.path.join(temp_vault, "gcl")
    snapshots = [f for f in os.listdir(container_dir) if f.endswith(".json")]
    assert len(snapshots) <= 3