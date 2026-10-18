from __future__ import annotations

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.workflow_capsules.glyph_store.workflow_glyph_repository import (
    WorkflowGlyphRepository,
)
from backend.modules.workflow_capsules.glyph_store.workflow_glyph_schema import (
    WorkflowGlyph,
)


def _glyph(code: str, *, scope: str, name: str) -> WorkflowGlyph:
    return WorkflowGlyph.from_dict({
        "glyph_id": f"glyph.{code.lower()}",
        "glyph_code": code,
        "name": name,
        "workflow_id": f"workflow:{code.lower()}.v1",
        "glyph_version": "v1",
        "scope": scope,
        "callable": True,
        "runtime_plan": {"mode": "dry_run", "customer_rule": name},
    })


def test_customer_glyphs_use_guardian_while_universal_templates_remain_product_content(
    tmp_path,
):
    layout = provision_business_vault(
        tmp_path / "customer-vault",
        business_name="Acme",
        business_stable_id="acme",
        application_root=tmp_path / "application",
        update_root=tmp_path / "updates",
    )
    store = VaultDomainStore(
        VaultGuardian(layout, business_stable_id="acme", encryption_key=b"g" * 32),
        actor_id="workflow-capsule-glyph-test",
    )
    product_glyphs = tmp_path / "application" / "universal-glyphs"
    derived_index = tmp_path / "application" / "derived-index.json"
    retained_legacy_customer = _glyph(
        "MY-OLD1", scope="my", name="Retained plaintext migration source"
    )
    retained_legacy_customer.save(product_glyphs / "MY-OLD1.v1.json")
    repository = WorkflowGlyphRepository(
        glyph_dir=product_glyphs,
        index_path=derived_index,
        domain_store=store,
        workspace_id="acme",
    )

    universal = _glyph(
        "UT-1001", scope="universal", name="Signed universal template"
    )
    customer = _glyph(
        "MY-9001", scope="my", name="Private Acme customer follow-up"
    )
    universal_saved = repository.save(universal)
    customer_saved = repository.save(customer)

    assert universal_saved["path"].endswith("UT-1001.v1.json")
    assert customer_saved["path"].startswith(
        "vault://train_agent.automations/workflow_capsule_glyphs/"
    )
    assert repository.rebuild_index()["derived_index_persisted"] is False
    assert not derived_index.exists()
    assert not (product_glyphs / "MY-9001.v1.json").exists()
    assert repository.load("MY-OLD1", "v1") is None
    assert all(g.glyph_code != "MY-OLD1" for g in repository.list())

    restarted = WorkflowGlyphRepository(
        glyph_dir=product_glyphs,
        index_path=derived_index,
        domain_store=store,
        workspace_id="acme",
    )
    assert restarted.require("UT-1001", "v1").scope == "universal"
    assert restarted.require("MY-9001", "v1").name == (
        "Private Acme customer follow-up"
    )
    assert [g.glyph_code for g in restarted.list(scope="my")] == ["MY-9001"]

    database_bytes = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"Private Acme customer follow-up" not in database_bytes
    assert b"Signed universal template" not in database_bytes
