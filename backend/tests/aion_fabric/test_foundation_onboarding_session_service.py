from pathlib import Path
import subprocess
import textwrap

import pytest
from fastapi import HTTPException

from backend.modules.aion_business.api import business_twin_data_api as api
from backend.modules.aion_business.runtime.foundation_onboarding_session_service import (
    FoundationOnboardingSessionService,
    FoundationSessionRevisionConflict,
)


def packet(name: str = "Example Business") -> dict:
    return {
        "schema_version": "aion.business_foundation_discovery_packet.test",
        "status": "foundation_discovery_in_progress",
        "foundation_draft": {"business_name": name, "contact_name": "Owner"},
        "transcript": [{"speaker": "user", "text": name}],
        "readiness": {"readiness_score": 20},
        "next_question": {"target_field": "business_model", "text": "How does it work?"},
    }


def test_session_is_mother_authoritative_and_resumable_across_devices(tmp_path: Path):
    service = FoundationOnboardingSessionService(tmp_path)
    first = service.save(
        "example-business", packet=packet(), expected_revision=0,
        actor_id="owner.one", device_id="phone.one",
    )
    resumed = service.get("example-business")

    assert first["revision"] == 1
    assert resumed["packet"] == packet()
    assert resumed["last_device_id"] == "phone.one"
    assert resumed["authoritative_store"] == "mother_brain"
    assert resumed["browser_storage_role"] == "migration_cache_only"
    assert resumed["resume"]["next_question"]["target_field"] == "business_model"


def test_stale_device_cannot_overwrite_newer_progress(tmp_path: Path):
    service = FoundationOnboardingSessionService(tmp_path)
    service.save(
        "example-business", packet=packet(), expected_revision=0,
        actor_id="owner.one", device_id="desktop.one",
    )
    service.save(
        "example-business", packet=packet("Updated"), expected_revision=1,
        actor_id="owner.one", device_id="phone.one",
    )

    with pytest.raises(FoundationSessionRevisionConflict) as error:
        service.save(
            "example-business", packet=packet("Stale"), expected_revision=1,
            actor_id="owner.one", device_id="television.one",
        )
    assert error.value.current == 2
    assert service.get("example-business")["packet"]["foundation_draft"]["business_name"] == "Updated"


def test_completed_session_does_not_commit_or_mutate_business_map(tmp_path: Path):
    service = FoundationOnboardingSessionService(tmp_path / "sessions")
    complete_packet = packet()
    complete_packet.update({
        "status": "foundation_ready_for_finance_handoff",
        "next_question": {"reason": "finance_handoff_ready"},
    })
    result = service.save(
        "example-business", packet=complete_packet, expected_revision=0,
        actor_id="owner.one", device_id="desktop.one",
    )

    assert result["status"] == "completed_pending_commit"
    assert not (tmp_path / "business_containers" / "example-business" / "business_map.json").exists()
    receipt = (tmp_path / "sessions" / "example-business.receipts.jsonl").read_text(encoding="utf-8")
    assert '"canonical_business_map_mutated": false' in receipt


def test_session_rejects_secrets_and_oversized_transcripts(tmp_path: Path):
    service = FoundationOnboardingSessionService(tmp_path)
    unsafe = packet()
    unsafe["foundation_draft"]["api_key"] = "secret-value"
    with pytest.raises(ValueError, match="secret_not_allowed"):
        service.save(
            "example-business", packet=unsafe, expected_revision=0,
            actor_id="owner.one", device_id="desktop.one",
        )

    excessive = packet()
    excessive["transcript"] = [{}] * 501
    with pytest.raises(ValueError, match="transcript_too_long"):
        service.save(
            "example-business", packet=excessive, expected_revision=0,
            actor_id="owner.one", device_id="desktop.one",
        )


def test_reset_requires_confirmation_and_retains_audit_receipt(tmp_path: Path):
    service = FoundationOnboardingSessionService(tmp_path)
    service.save(
        "example-business", packet=packet(), expected_revision=0,
        actor_id="owner.one", device_id="desktop.one",
    )
    with pytest.raises(ValueError, match="confirmation_required"):
        service.reset(
            "example-business", expected_revision=1,
            actor_id="owner.one", confirm_reset=False,
        )
    reset = service.reset(
        "example-business", expected_revision=1,
        actor_id="owner.one", confirm_reset=True,
    )
    assert reset["revision"] == 2
    assert reset["packet"] is None
    assert "reset_progress" in (tmp_path / "example-business.receipts.jsonl").read_text(encoding="utf-8")


def test_api_exposes_session_lifecycle_and_revision_conflict(tmp_path: Path, monkeypatch):
    service = FoundationOnboardingSessionService(tmp_path)
    monkeypatch.setattr(api, "_foundation_sessions", lambda: service)

    created = api.put_foundation_session(
        "example-business",
        api.FoundationSessionWriteRequest(
            packet=packet(), expected_revision=0,
            actor_id="owner.one", device_id="phone.one",
        ),
    )
    assert created["session"]["revision"] == 1
    assert api.get_foundation_session("example-business")["session"]["packet"] == packet()

    with pytest.raises(HTTPException) as error:
        api.put_foundation_session(
            "example-business",
            api.FoundationSessionWriteRequest(
                packet=packet("Stale"), expected_revision=0,
                actor_id="owner.one", device_id="desktop.one",
            ),
        )
    assert error.value.status_code == 409
    assert error.value.detail["current"] == 1


def test_desktop_session_hydrates_and_saves_against_mother_authority():
    repository_root = Path(__file__).resolve().parents[3]
    module_path = repository_root / "desktop/mac/src/aion_development_business_session.js"
    script = textwrap.dedent(
        f"""
        const assert = require('assert');
        const store = new Map();
        global.localStorage = {{
          getItem: (key) => store.has(key) ? store.get(key) : null,
          setItem: (key, value) => store.set(key, String(value)),
          removeItem: (key) => store.delete(key),
          key: (index) => Array.from(store.keys())[index] || null,
          get length() {{ return store.size; }},
        }};
        global.sessionStorage = {{ clear() {{}} }};
        global.state = {{ workspaceId: 'example-business', apiBase: 'http://127.0.0.1:8080' }};
        global.location = {{ reload() {{}} }};
        const calls = [];
        global.fetch = async (url, options = {{}}) => {{
          calls.push({{ url, options }});
          if (!options.method || options.method === 'GET') {{
            return {{ ok: true, json: async () => ({{ ok: true, session: {{
              schema_version: 'aion.business_foundation_onboarding_session.v1',
              workspace_id: 'example-business', revision: 3, status: 'in_progress',
              packet: {{ foundation_draft: {{ business_name: 'Mother Copy' }}, transcript: [] }},
              updated_at: '2026-09-04T00:00:00Z',
            }} }}) }};
          }}
          const body = JSON.parse(options.body);
          assert.equal(body.expected_revision, 3);
          return {{ ok: true, json: async () => ({{ ok: true, session: {{
            workspace_id: 'example-business', revision: 4, status: 'in_progress',
            packet: body.packet, updated_at: '2026-09-04T00:01:00Z',
          }} }}) }};
        }};
        require({module_path.as_posix()!r});
        setTimeout(async () => {{
          assert.equal(global.AionDevelopmentBusinessSession.getFoundationPacket().foundation_draft.business_name, 'Mother Copy');
          global.AionDevelopmentBusinessSession.persistFoundationPacket({{
            foundation_draft: {{ business_name: 'Updated Copy' }}, transcript: []
          }});
          await new Promise((resolve) => setTimeout(resolve, 20));
          assert.equal(global.AionDevelopmentBusinessSession.getMotherSyncState().revision, 4);
          assert.equal(calls.filter((call) => call.options.method === 'PUT').length, 1);
          console.log('mother-authoritative desktop session verified');
        }}, 20);
        """
    )
    result = subprocess.run(
        ["node", "-e", script], cwd=repository_root,
        text=True, capture_output=True, check=True,
    )
    assert "mother-authoritative desktop session verified" in result.stdout


def test_desktop_session_does_not_apply_stale_response_after_workspace_switch():
    repository_root = Path(__file__).resolve().parents[3]
    module_path = repository_root / "desktop/mac/src/aion_development_business_session.js"
    script = textwrap.dedent(
        f"""
        const assert = require('assert');
        const store = new Map();
        global.localStorage = {{
          getItem: (key) => store.has(key) ? store.get(key) : null,
          setItem: (key, value) => store.set(key, String(value)),
          removeItem: (key) => store.delete(key),
          key: (index) => Array.from(store.keys())[index] || null,
          get length() {{ return store.size; }},
        }};
        global.sessionStorage = {{ clear() {{}} }};
        global.state = {{ workspaceId: 'legacy-business', apiBase: 'http://127.0.0.1:8080' }};
        global.location = {{ reload() {{}} }};
        const calls = [];
        global.fetch = async (url, options = {{}}) => {{
          calls.push({{ url, options }});
          const isNew = url.includes('qualification-workshop');
          if (!options.method || options.method === 'GET') {{
            await new Promise((resolve) => setTimeout(resolve, isNew ? 1 : 15));
            return {{ ok: true, json: async () => ({{ ok: true, session: {{
              workspace_id: isNew ? 'qualification-workshop' : 'legacy-business',
              revision: isNew ? 0 : 7, status: 'in_progress',
              packet: isNew ? null : {{ foundation_draft: {{ business_name: 'Legacy' }} }},
              updated_at: '2026-10-18T00:00:00Z',
            }} }}) }};
          }}
          const body = JSON.parse(options.body);
          assert.equal(body.expected_revision, 0);
          return {{ ok: true, json: async () => ({{ ok: true, session: {{
            workspace_id: 'qualification-workshop', revision: 1, status: 'in_progress',
            packet: body.packet, updated_at: '2026-10-18T00:01:00Z',
          }} }}) }};
        }};
        require({module_path.as_posix()!r});
        global.state.workspaceId = 'qualification-workshop';
        const activePacket = {{ foundation_draft: {{ business_name: 'Qualification Workshop Ltd' }} }};
        global.AionDevelopmentBusinessSession.persistFoundationPacket(activePacket);
        setTimeout(() => {{
          assert.equal(global.AionDevelopmentBusinessSession.getFoundationPacket().foundation_draft.business_name, 'Qualification Workshop Ltd');
          assert.equal(global.AionDevelopmentBusinessSession.getMotherSyncState().workspace_id, 'qualification-workshop');
          assert.equal(global.AionDevelopmentBusinessSession.getMotherSyncState().revision, 1);
          assert.equal(calls.filter((call) => call.options.method === 'PUT').length, 1);
          console.log('workspace switch stale response isolated');
        }}, 40);
        """
    )
    result = subprocess.run(
        ["node", "-e", script], cwd=repository_root,
        text=True, capture_output=True, check=True,
    )
    assert "workspace switch stale response isolated" in result.stdout


def test_desktop_session_retries_revision_conflict_without_dropping_latest_answer():
    repository_root = Path(__file__).resolve().parents[3]
    module_path = repository_root / "desktop/mac/src/aion_development_business_session.js"
    script = textwrap.dedent(
        f"""
        const assert = require('assert');
        const store = new Map();
        global.localStorage = {{
          getItem: (key) => store.has(key) ? store.get(key) : null,
          setItem: (key, value) => store.set(key, String(value)),
          removeItem: (key) => store.delete(key),
          key: (index) => Array.from(store.keys())[index] || null,
          get length() {{ return store.size; }},
        }};
        global.sessionStorage = {{ clear() {{}} }};
        global.state = {{ workspaceId: 'example-business', apiBase: 'http://127.0.0.1:8080' }};
        global.location = {{ reload() {{}} }};
        let revision = 3;
        let packet = {{ business_context_draft: {{ legal_name: 'Example Ltd' }} }};
        let putCount = 0;
        global.fetch = async (url, options = {{}}) => {{
          if (!options.method || options.method === 'GET') {{
            return {{ ok: true, json: async () => ({{ ok: true, session: {{
              workspace_id: 'example-business', revision, status: 'in_progress',
              packet, updated_at: '2026-10-18T00:00:00Z',
            }} }}) }};
          }}
          putCount += 1;
          const body = JSON.parse(options.body);
          if (putCount === 1) {{
            revision = 4;
            packet = {{ ...packet, voice_discovery: {{ status: 'draft' }} }};
            return {{ ok: false, status: 409, json: async () => ({{ detail: {{ current: 4 }} }}) }};
          }}
          assert.equal(body.expected_revision, 4);
          packet = body.packet;
          revision = 5;
          return {{ ok: true, json: async () => ({{ ok: true, session: {{
            workspace_id: 'example-business', revision, status: 'in_progress',
            packet, updated_at: '2026-10-18T00:01:00Z',
          }} }}) }};
        }};
        require({module_path.as_posix()!r});
        setTimeout(async () => {{
          global.AionDevelopmentBusinessSession.persistFoundationPacket({{
            foundation_draft: {{ business_name: 'Latest Founder Answer' }},
          }});
          await new Promise((resolve) => setTimeout(resolve, 40));
          assert.equal(putCount, 2);
          assert.equal(packet.foundation_draft.business_name, 'Latest Founder Answer');
          assert.equal(packet.business_context_draft.legal_name, 'Example Ltd');
          assert.equal(packet.voice_discovery.status, 'draft');
          assert.equal(global.AionDevelopmentBusinessSession.getMotherSyncState().revision, 5);
          console.log('foundation conflict retried without data loss');
        }}, 20);
        """
    )
    result = subprocess.run(
        ["node", "-e", script], cwd=repository_root,
        text=True, capture_output=True, check=True,
    )
    assert "foundation conflict retried without data loss" in result.stdout


def test_clean_desktop_does_not_read_or_write_a_placeholder_business():
    repository_root = Path(__file__).resolve().parents[3]
    module_path = repository_root / "desktop/mac/src/aion_development_business_session.js"
    script = textwrap.dedent(
        f"""
        const assert = require('assert');
        const store = new Map();
        global.localStorage = {{
          getItem: (key) => store.has(key) ? store.get(key) : null,
          setItem: (key, value) => store.set(key, String(value)),
          removeItem: (key) => store.delete(key),
          key: (index) => Array.from(store.keys())[index] || null,
          get length() {{ return store.size; }},
        }};
        global.sessionStorage = {{ clear() {{}} }};
        global.state = {{ workspaceId: 'business-not-registered', apiBase: 'http://127.0.0.1:8080' }};
        global.location = {{ reload() {{}} }};
        const calls = [];
        global.fetch = async (...args) => {{ calls.push(args); throw new Error('unexpected_network_call'); }};
        require({module_path.as_posix()!r});
        const packet = {{ foundation_draft: {{ founder_name: 'Alex Tester' }} }};
        global.AionDevelopmentBusinessSession.persistFoundationPacket(packet);
        setTimeout(() => {{
          assert.equal(calls.length, 0);
          assert.equal(global.AionDevelopmentBusinessSession.getFoundationPacket(), packet);
          assert.equal(global.AionDevelopmentBusinessSession.getMotherSyncState().status, 'awaiting_business_registration');
          console.log('unregistered desktop kept memory-only');
        }}, 20);
        """
    )
    result = subprocess.run(
        ["node", "-e", script], cwd=repository_root,
        text=True, capture_output=True, check=True,
    )
    assert "unregistered desktop kept memory-only" in result.stdout


def test_desktop_rehydrates_foundation_after_async_business_identity_restore():
    repository_root = Path(__file__).resolve().parents[3]
    module_path = repository_root / "desktop/mac/src/aion_development_business_session.js"
    script = textwrap.dedent(
        f"""
        const assert = require('assert');
        const store = new Map();
        const listeners = new Map();
        global.localStorage = {{
          getItem: (key) => store.has(key) ? store.get(key) : null,
          setItem: (key, value) => store.set(key, String(value)),
          removeItem: (key) => store.delete(key),
          key: (index) => Array.from(store.keys())[index] || null,
          get length() {{ return store.size; }},
        }};
        global.sessionStorage = {{ clear() {{}} }};
        global.state = {{ workspaceId: 'business-not-registered', apiBase: 'http://127.0.0.1:8080' }};
        global.location = {{ reload() {{}} }};
        global.addEventListener = (name, callback) => listeners.set(name, callback);
        const calls = [];
        global.fetch = async (url, options = {{}}) => {{
          calls.push({{ url, options }});
          return {{ ok: true, json: async () => ({{ ok: true, session: {{
            workspace_id: 'restored-business', revision: 8, status: 'completed_pending_commit',
            packet: {{ foundation_draft: {{ business_name: 'Restored Business Ltd' }} }},
            updated_at: '2026-10-18T01:00:00Z',
          }} }}) }};
        }};
        require({module_path.as_posix()!r});
        assert.equal(calls.length, 0);
        global.state.workspaceId = 'restored-business';
        listeners.get('aion:business-identity-established')();
        setTimeout(() => {{
          assert.equal(calls.length, 1);
          assert.equal(global.AionDevelopmentBusinessSession.getMotherSyncState().revision, 8);
          assert.equal(global.AionDevelopmentBusinessSession.getMotherSyncState().workspace_id, 'restored-business');
          assert.equal(global.AionDevelopmentBusinessSession.getFoundationPacket().foundation_draft.business_name, 'Restored Business Ltd');
          console.log('async business identity restored foundation authority');
        }}, 20);
        """
    )
    result = subprocess.run(
        ["node", "-e", script], cwd=repository_root,
        text=True, capture_output=True, check=True,
    )
    assert "async business identity restored foundation authority" in result.stdout
