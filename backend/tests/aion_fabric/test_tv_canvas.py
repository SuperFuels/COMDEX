from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

import pytest

from backend.modules.aion_fabric import tv_canvas


def test_learning_voice_uses_bounded_multilingual_natural_speech(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit):
            captured["limit"] = limit
            return b"ID3" + (b"natural-audio" * 100)

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-natural-voice-key")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "test-spanish-teacher")
    monkeypatch.setattr(tv_canvas, "urlopen", fake_urlopen)
    tv_canvas._local_spanish_speech.cache_clear()
    audio = tv_canvas._local_spanish_speech("hola")
    assert audio.startswith(b"ID3")
    assert captured["payload"]["model_id"] == "eleven_multilingual_v2"
    assert captured["payload"]["voice_settings"]["use_speaker_boost"] is True
    assert captured["limit"] == 2_000_001


def test_tv_canvas_is_token_protected_and_read_only(monkeypatch):
    monkeypatch.setattr(tv_canvas, "_lan_address", lambda preferred_peer=None: "127.0.0.1")
    status = {
        "nodes": [
            {
                "enrollment": "enrolled",
                "profile": {
                    "name": "Living Room TV",
                    "metadata": {"webos_pairing": "paired", "webos_latest_state": {"volume": {"volume": 23}}},
                },
            }
        ],
        "ledger": {"webos_action_receipts": 7},
        "audit_chain_valid": True,
        "tv_autopilot": {"belief": {"surface": "aion_canvas", "confidence": 0.99}},
    }
    surface_manifest = {
        "payload_hash": "surface-manifest-1",
        "tiles": [
            {"tile_id": "games", "label": "Games", "privacy": "public", "authority_domain": "public"},
            {"tile_id": "tasks", "label": "Tasks", "privacy": "private", "authority_domain": "personal", "role": "owner"},
            {"tile_id": "boardroom.acme", "label": "Acme Boardroom", "privacy": "organisation", "authority_domain": "boardroom", "role": "reviewer"},
        ],
    }
    presentation = {
        "presentation_id": "surface-presentation-1", "content_kind": "briefing",
        "authority_domain": "personal", "title": "Today", "content": {"tasks": 3},
    }
    service = tv_canvas.TVCanvasService(
        lambda: status,
        port=0,
        token="test-session-token",
        surface_manifest_provider=lambda: surface_manifest,
        presentation_provider=lambda: presentation,
    )
    service.start()
    try:
        with urllib.request.urlopen(service.public_url, timeout=2) as response:
            page = response.read().decode("utf-8")
            assert "Pilot TV" in page
            assert "What would you like to do?" in page
            assert "God View" in page
            assert "Private areas are locked" in page
            assert "workspace.classList.toggle('locked'" in page
            assert "renderSurfaceTiles" in page
            assert "renderPresentation" in page
            assert "closes automatically when authority expires" in page
            assert "authority_domain" in page
            assert "five minutes without activity" in page
            assert "#f7f9fc" in page
        with urllib.request.urlopen(f"{service.public_url}/education", timeout=2) as response:
            education_page = response.read().decode("utf-8")
        assert "Spanish Learning Centre" in education_page
        assert "Use the LG remote arrows" in education_page
        assert "/education/action" in education_page
        assert "lesson-voice" in education_page
        assert "Correct!" not in education_page
        assert "expected_round:lesson.round_number" in education_page
        with urllib.request.urlopen(f"{service.public_url}/god-view", timeout=2) as response:
            god_view_page = response.read().decode("utf-8")
            assert response.headers["Content-Security-Policy"].find("https://cesium.com") >= 0
            assert response.headers["Content-Security-Policy"].find("https://www.youtube-nocookie.com") >= 0
        assert "Pilot God View" in god_view_page
        assert "Live aircraft" in god_view_page
        assert "Pilot Mode" in god_view_page
        assert "VIEWING CAMERA" in god_view_page
        assert "Live View from Space" in god_view_page
        assert "/control" in god_view_page
        sent = service.send_god_control("right")
        with urllib.request.urlopen(f"{service.public_url}/god-view/control", timeout=2) as response:
            control = json.loads(response.read())
        assert control["sequence"] == sent["sequence"]
        assert control["command"] == "right"
        with urllib.request.urlopen(f"{service.public_url}/state", timeout=2) as response:
            snapshot = json.loads(response.read())
        assert snapshot["tv_name"] == "Living Room TV"
        assert snapshot["tv_volume"] == 23
        assert snapshot["verified_actions"] == 7
        assert snapshot["autopilot_belief"]["surface"] == "aion_canvas"
        assert snapshot["surface_manifest"] == surface_manifest
        assert snapshot["presentation"] == presentation
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(service.public_url.replace("test-session-token", "wrong"), timeout=2)
        assert error.value.code == 404
        request = urllib.request.Request(f"{service.public_url}/state", method="POST")
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request, timeout=2)
        assert error.value.code == 405
    finally:
        service.stop()


def test_tv_canvas_only_exposes_sanitized_state(monkeypatch):
    monkeypatch.setattr(tv_canvas, "_lan_address", lambda preferred_peer=None: "127.0.0.1")
    service = tv_canvas.TVCanvasService(
        lambda: {
            "nodes": [],
            "ledger": {},
            "audit_chain_valid": True,
            "private_key": "must-not-escape",
            "credentials": {"token": "must-not-escape"},
        },
        port=0,
    )
    snapshot = service.snapshot()
    assert "private_key" not in snapshot
    assert "credentials" not in snapshot


def test_tv_canvas_exposes_only_active_person_workspace_tasks(monkeypatch):
    monkeypatch.setattr(tv_canvas, "_lan_address", lambda preferred_peer=None: "127.0.0.1")
    status = {
        "nodes": [], "ledger": {}, "audit_chain_valid": True,
        "private_identity": {
            "active_shared_identity": {
                "persona_id": "persona_kevin", "display_name": "Kevin",
            }
        },
        "pilot_inbox_shared_summary": {"open_tasks": 1},
    }
    seen = []
    service = tv_canvas.TVCanvasService(
        lambda: status,
        private_workspace_provider=lambda persona_id: seen.append(persona_id) or {
            "tasks": [{"title": "Buy milk", "status": "open", "assigned_to_me": True}],
            "reminders": [],
        },
        port=0,
    )
    service.set_view("tasks")
    snapshot = service.snapshot()
    assert snapshot["view"] == "tasks"
    assert snapshot["private_workspace"]["tasks"][0]["title"] == "Buy milk"
    assert seen == ["persona_kevin"]


def test_dedicated_education_page_accepts_only_scoped_remote_actions(monkeypatch):
    monkeypatch.setattr(tv_canvas, "_lan_address", lambda preferred_peer=None: "127.0.0.1")
    state = {"education": {"session": None}, "nodes": [], "ledger": {}}
    calls = []
    service = tv_canvas.TVCanvasService(
        lambda: state,
        education_handler=lambda command, arguments: calls.append((command, arguments)) or {"accepted": True, "education": state["education"]},
        port=0,
        token="education-session-token",
    )
    service.start()
    try:
        body = urllib.parse.urlencode({"command": "start", "arguments": '{"profile_id":"explorer_a"}'}).encode()
        request = urllib.request.Request(
            f"{service.public_url}/education/action",
            data=body,
            method="POST",
            headers={"X-AION-Education": service.education_action_token},
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            assert json.loads(response.read())["accepted"] is True
        assert calls == [("start", {"profile_id": "explorer_a"})]
    finally:
        service.stop()
