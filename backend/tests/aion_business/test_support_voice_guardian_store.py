from __future__ import annotations

import hashlib
import hmac
import json
import time

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.support_case_service import SupportCaseService
from backend.modules.aion_business.runtime.support_voice_service import SupportVoiceService
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.tests.test_finance_bookkeeping_service import configure


def test_support_voice_deployment_and_events_restart_from_encrypted_vault(monkeypatch, tmp_path):
    repository, _authority = configure(monkeypatch, tmp_path)
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"v" * 32)
    domains = VaultDomainStore(guardian)
    support = SupportCaseService(repository, domain_store=domains)
    subject = SupportVoiceService(support, domain_store=domains)
    deployment = {
        "schema_version": "aion.support.retell_deployment.v1", "workspace_id": "acme",
        "status": "published_unbound_controlled_use", "agent_id": "agent-private",
        "agent_name": "Private Support Agent", "published": True,
    }
    subject._rehash(deployment)
    subject._write_deployment("acme", deployment)
    key = "private-webhook-key"
    monkeypatch.setattr(
        "backend.modules.aion_business.runtime.support_voice_service.get_retell_api_key",
        lambda workspace_id=None: key,
    )
    body = json.dumps({
        "event": "call_ended", "call": {"call_id": "private-call", "agent_id": "agent-private",
        "transcript_object": [{"role": "user", "content": "Private support problem"}]},
    }).encode()
    timestamp = str(int(time.time() * 1000))
    signature = "v=" + timestamp + ",d=" + hmac.new(
        key.encode(), body + timestamp.encode(), hashlib.sha256,
    ).hexdigest()
    subject.record_webhook("acme", raw_body=body, signature=signature)

    restarted = SupportVoiceService(
        SupportCaseService(repository, domain_store=domains), domain_store=domains,
    )
    assert restarted.status("acme")["agent_id"] == "agent-private"
    assert len([row for row in domains.list("support.records", workspace_id="acme")
                if str(row["entity_id"]).startswith("voice/events/")]) == 1
    assert not (repository.base_dir / "acme" / "support" / "voice").exists()
    assert b"Private support problem" not in guardian.database.read_bytes()
