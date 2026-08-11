from pathlib import Path

import pytest

from backend.modules.aion_business.runtime.support_voice_service import SupportVoiceService
from backend.tests.test_finance_bookkeeping_service import configure


def test_support_voice_deployment_is_separate_governed_and_verified(monkeypatch, tmp_path: Path):
    repository, _ = configure(monkeypatch, tmp_path)
    service = SupportVoiceService()
    service.support.repository = repository
    service.support.authority.repository = repository
    service.authority.repository = repository
    monkeypatch.setattr("backend.modules.aion_business.runtime.support_voice_service.get_retell_api_key",
                        lambda workspace_id=None: "secret-test-key")
    calls = []
    def provider(url, key, payload, method="POST"):
        calls.append((url, payload, method))
        if "list-agents" in url: return []
        if "create-retell-llm" in url: return {"llm_id": "llm-support-1", "version": 0}
        if "create-agent" in url: return {"agent_id": "agent-support-1", "agent_name": "AION - Home Fixed Support v1", "version": 0}
        if "publish-agent" in url: return {"agent_id": "agent-support-1", "version": 1}
        if "get-agent-versions" in url: return [{"agent_id": "agent-support-1", "agent_name": "AION - Home Fixed Support v1", "voice_id": "retell-Cimo", "language": ["en-GB", "es-ES"], "is_published": True, "version": 1}]
        raise AssertionError(url)
    monkeypatch.setattr(service, "_request", provider)
    result = service.deploy("acme", deployed_by_person_id="person.owner")
    deployment = result["deployment"]
    assert deployment["agent_id"] == "agent-support-1"
    assert deployment["live_execution_enabled"] is False
    assert result["verified"]["is_published"] is True
    llm_payload = next(payload for url, payload, _ in calls if "create-retell-llm" in url)
    assert "Never admit legal liability" in llm_payload["general_prompt"]
    assert "You are not the Sales agent" in llm_payload["general_prompt"]
    assert llm_payload["model_temperature"] == 0
    again = service.deploy("acme", deployed_by_person_id="person.owner")
    assert again["created"] is False


def test_retell_webhook_rejects_invalid_signature(monkeypatch, tmp_path: Path):
    repository, _ = configure(monkeypatch, tmp_path)
    service = SupportVoiceService()
    service.support.repository = repository
    service.support.authority.repository = repository
    service.authority.repository = repository
    monkeypatch.setattr("backend.modules.aion_business.runtime.support_voice_service.get_retell_api_key",
                        lambda workspace_id=None: "secret-test-key")
    with pytest.raises(PermissionError, match="signature_invalid"):
        service.record_webhook("acme", raw_body=b'{}', signature="invalid")


def test_support_voice_recovers_existing_agent_without_duplicate(monkeypatch, tmp_path: Path):
    repository, _ = configure(monkeypatch, tmp_path)
    service = SupportVoiceService()
    service.support.repository = repository
    service.support.authority.repository = repository
    service.authority.repository = repository
    monkeypatch.setattr("backend.modules.aion_business.runtime.support_voice_service.get_retell_api_key",
                        lambda workspace_id=None: "secret-test-key")
    calls = []
    def provider(url, key, payload, method="POST"):
        calls.append(url)
        if "list-agents" in url:
            return [{"agent_id": "agent-existing", "agent_name": "AION - Home Fixed Support v1",
                     "voice_id": "retell-Cimo", "language": ["en-GB", "es-ES"], "version": 1,
                     "response_engine": {"type": "retell-llm", "llm_id": "llm-existing"}}]
        if "get-agent-versions" in url:
            return [{"agent_id": "agent-existing", "agent_name": "AION - Home Fixed Support v1",
                     "voice_id": "retell-Cimo", "language": ["en-GB", "es-ES"],
                     "is_published": True, "version": 1}]
        raise AssertionError(url)
    monkeypatch.setattr(service, "_request", provider)
    result = service.deploy("acme", deployed_by_person_id="person.owner")
    assert result["recovered"] is True
    assert result["deployment"]["llm_id"] == "llm-existing"
    assert not any("create-agent" in url for url in calls)
