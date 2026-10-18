from __future__ import annotations

import base64
import json

import pytest

from backend.modules.aion_business.api.browser_skills_api import (
    BrowserChainPayload,
    BrowserSkillPayload,
    delete_browser_skill,
    get_browser_chain,
    get_browser_skill,
    list_browser_chains,
    list_browser_skills,
    save_browser_chain,
    save_browser_skill,
)


def test_browser_skills_and_chains_restart_from_vault_and_import_legacy(tmp_path, monkeypatch):
    vault_root = tmp_path / "customer-vault"
    environment = {
        "TESSARIS_BUSINESS_CONTAINER_BACKEND": "guardian",
        "TESSARIS_BUSINESS_VAULT_PATH": str(vault_root),
        "TESSARIS_BUSINESS_NAME": "Acme",
        "TESSARIS_BUSINESS_STABLE_ID": "acme",
        "TESSARIS_BUSINESS_VAULT_KEY_B64": base64.urlsafe_b64encode(b"w" * 32).decode().rstrip("="),
        "TESSARIS_APPLICATION_ROOT": str(tmp_path / "application"),
        "TESSARIS_UPDATE_ROOT": str(tmp_path / "updates"),
    }
    for key, value in environment.items():
        monkeypatch.setenv(key, value)
    monkeypatch.chdir(tmp_path)
    legacy = tmp_path / ".runtime" / "AION_BUSINESS" / "browser_skills" / "acme"
    legacy.mkdir(parents=True)
    legacy_path = legacy / "legacy-skill.json"
    legacy_path.write_text(json.dumps({
        "skill_id": "legacy-skill", "steps": [{"instruction": "Private browser action"}],
    }))

    imported = list_browser_skills("acme")
    saved = save_browser_skill(
        "acme", BrowserSkillPayload(skill={"skill_id": "new-skill", "private": "Customer workflow"}),
    )
    chain = save_browser_chain(
        "acme", BrowserChainPayload(chain={"chain_id": "chain-1", "skills": ["new-skill"]}),
    )

    assert imported["items"][0]["legacy_source_retained"] is True
    assert saved["item"]["private"] == "Customer workflow"
    assert get_browser_skill("acme", "new-skill")["item"]["skill_id"] == "new-skill"
    assert get_browser_chain("acme", "chain-1")["item"] == chain["item"]
    assert list_browser_chains("acme")["count"] == 1
    delete_browser_skill("acme", "new-skill")
    with pytest.raises(Exception) as exc:
        get_browser_skill("acme", "new-skill")
    assert getattr(exc.value, "status_code", None) == 404
    assert legacy_path.is_file()
    database = (vault_root / "records" / "guardian.sqlite3").read_bytes()
    assert b"Private browser action" not in database
    assert b"Customer workflow" not in database
