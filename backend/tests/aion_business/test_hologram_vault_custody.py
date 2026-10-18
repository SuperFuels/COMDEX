from __future__ import annotations

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_learning.vault_store import AionLearningVaultStore
from backend.modules.holograms.hqce_telemetry_db import HQCETelemetryDB
from backend.modules.holograms.morphic_ledger import MorphicLedger


def _learning_store(tmp_path):
    layout = provision_business_vault(
        tmp_path / "customer.business-vault",
        business_name="Private Workshop",
        business_stable_id="private-workshop",
        application_root=tmp_path / "application",
        update_root=tmp_path / "updates",
    )
    domains = VaultDomainStore(
        VaultGuardian(
            layout,
            business_stable_id="private-workshop",
            encryption_key=b"h" * 32,
        ),
        actor_id="hologram-custody-test",
    )
    return layout, domains, AionLearningVaultStore(
        domain_store=domains,
        workspace_id="private-workshop",
    )


def test_hologram_telemetry_restarts_from_guardian_without_raw_files(tmp_path):
    layout, domains, store = _learning_store(tmp_path)
    raw_root = tmp_path / "application" / "data" / "ledger"
    ledger = MorphicLedger(base_path=str(raw_root), vault_store=store)
    ledger.append(
        {
            "psi": 0.2,
            "kappa": 0.3,
            "T": 0.4,
            "coherence": 0.9,
            "stability": 0.8,
            "phi": 0.7,
            "metadata": {"customer": "Private Client"},
        },
        observer="custody-test",
    )
    latest = ledger.query_latest()
    assert latest is not None

    restarted = MorphicLedger(
        base_path=str(tmp_path / "different-application" / "data"),
        vault_store=store,
    )
    assert restarted.query_latest()["meta"]["customer"] == "Private Client"

    telemetry = HQCETelemetryDB(
        db_path=str(tmp_path / "application" / "hqce.sqlite3"),
        vault_store=store,
    )
    telemetry.ingest_record(latest, "private-session")
    restarted_telemetry = HQCETelemetryDB(vault_store=store)
    assert restarted_telemetry.latest_values(1)[0]["session_id"] == "private-session"

    assert not raw_root.exists()
    assert not (tmp_path / "application" / "hqce.sqlite3").exists()
    database_bytes = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"Private Client" not in database_bytes
    assert b"private-session" not in database_bytes
    assert domains.guardian.verify_audit_chain()["healthy"] is True


def test_hologram_local_experiment_is_memory_only(tmp_path):
    ledger = MorphicLedger(
        base_path=str(tmp_path / "must-not-exist"),
        vault_store=AionLearningVaultStore(auto_configure=False),
    )
    ledger.append({"psi": 0.1, "coherence": 0.8})
    assert ledger.query_latest()["tensor"]["coherence"] == 0.8
    assert not (tmp_path / "must-not-exist").exists()

    telemetry = HQCETelemetryDB(
        db_path=str(tmp_path / "must-not-exist.sqlite3"),
        vault_store=AionLearningVaultStore(auto_configure=False),
    )
    telemetry.ingest_record(ledger.query_latest(), "experiment")
    assert telemetry.latest_values(1)[0]["session_id"] == "experiment"
    assert not (tmp_path / "must-not-exist.sqlite3").exists()
