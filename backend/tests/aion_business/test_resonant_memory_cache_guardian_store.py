from __future__ import annotations

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_language.resonant_memory_cache import (
    RMC_ENTITY_ID,
    ResonantMemoryCache,
)
from backend.modules.aion_learning.vault_store import AionLearningVaultStore


def _learning_store(tmp_path):
    layout = provision_business_vault(
        tmp_path / "customer-vault",
        business_name="RMC Workshop",
        business_stable_id="rmc-workshop",
        application_root=tmp_path / "application",
        update_root=tmp_path / "updates",
    )
    domains = VaultDomainStore(
        VaultGuardian(
            layout,
            business_stable_id="rmc-workshop",
            encryption_key=b"r" * 32,
        ),
        actor_id="rmc-boundary-test",
    )
    return layout, AionLearningVaultStore(
        domain_store=domains,
        workspace_id="rmc-workshop",
    )


def test_default_rmc_is_memory_only_and_creates_no_cache(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cache_path = tmp_path / "data" / "memory" / "resonant_memory_cache.json"
    rmc = ResonantMemoryCache(
        vault_store=AionLearningVaultStore(auto_configure=False),
        cache_path=cache_path,
    )

    rmc.set("private", "PRIVATE-MEMORY-ONLY")

    assert rmc.get("private") == "PRIVATE-MEMORY-ONLY"
    assert rmc.save(force=True) is False
    assert not cache_path.exists()
    assert not (tmp_path / "data").exists()


def test_rmc_survives_restart_inside_guardian(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    layout, learning = _learning_store(tmp_path)
    rmc = ResonantMemoryCache(vault_store=learning)
    rmc.set("private-rule", "PRIVATE-CUSTOMER-RMC-VALUE")
    assert rmc.save(force=True) is True

    restarted = ResonantMemoryCache(vault_store=learning)

    assert restarted.get("private-rule") == "PRIVATE-CUSTOMER-RMC-VALUE"
    assert learning.get_state(RMC_ENTITY_ID, {})["cache"]["private-rule"] == (
        "PRIVATE-CUSTOMER-RMC-VALUE"
    )
    assert not (tmp_path / "data").exists()
    assert b"PRIVATE-CUSTOMER-RMC-VALUE" not in (
        layout.records / "guardian.sqlite3"
    ).read_bytes()


def test_rmc_legacy_cache_requires_explicit_switch(tmp_path):
    cache_path = tmp_path / "legacy" / "resonant_memory_cache.json"
    rmc = ResonantMemoryCache(
        vault_store=AionLearningVaultStore(auto_configure=False),
        allow_legacy_files=True,
        cache_path=cache_path,
    )
    rmc.set("compatibility", {"value": 1})
    assert rmc.save(force=True) is True

    restarted = ResonantMemoryCache(
        vault_store=AionLearningVaultStore(auto_configure=False),
        allow_legacy_files=True,
        cache_path=cache_path,
    )
    assert restarted.get("compatibility") == {"value": 1}
