from __future__ import annotations

import pytest
import urllib.parse
import urllib.request

from backend.modules.aion_fabric.agent import AionTVAgent
from backend.modules.aion_fabric import companion
from backend.modules.aion_fabric.companion import _companion_html
from backend.modules.aion_fabric.voice import parse_voice_intent


@pytest.mark.parametrize(
    ("phrase", "route"),
    [
        ("compare family hotels in Granada", "research"),
        ("book the best one for Saturday", "booking"),
        ("buy the safest ladder", "shopping"),
        ("email the shortlist to Mia", "communication"),
        ("put the appointment in my calendar", "calendar"),
        ("help me think through tonight", "conversation"),
    ],
)
def test_agent_routes_open_ended_outcomes(phrase, route):
    assert AionTVAgent.classify(phrase) == route


def test_consequential_plan_stops_at_private_approval(tmp_path):
    agent = AionTVAgent(tmp_path)
    task = agent.create_plan(
        "book a locksmith for tomorrow",
        perception={"summary": "Foreground app Netflix; TV volume 20", "verified": True},
        companion_url="http://192.168.1.20:8767/companion/token",
    )
    assert task["status"] == "waiting_for_approval"
    assert task["approval"]["state"] == "pending"
    assert task["steps"][-1]["status"] == "blocked"
    assert agent.snapshot()["policy"]["model_output_executes_directly"] is False


def test_owner_cancel_closes_active_plan_and_pending_approval(tmp_path):
    agent = AionTVAgent(tmp_path)
    task = agent.create_plan("book a locksmith for tomorrow")

    cancelled = agent.cancel_active(reason="voice_emergency_stop")

    assert cancelled["task_id"] == task["task_id"]
    assert cancelled["status"] == "cancelled"
    assert cancelled["approval"]["state"] == "cancelled"
    assert agent.snapshot()["active_task"] is None


def test_private_decision_never_claims_external_execution(tmp_path):
    agent = AionTVAgent(tmp_path)
    task = agent.create_plan("buy the first ladder")
    decided = agent.decide(task["approval"]["approval_id"], approved=True)
    assert decided["status"] == "approved_pending_adapter"
    assert decided["steps"][-1]["status"] == "ready"
    assert "awaiting" in decided["steps"][-1]["evidence"].lower()


def test_research_plan_can_complete_without_approval(tmp_path):
    agent = AionTVAgent(tmp_path)
    task = agent.create_plan("compare three ladders")
    completed = agent.mark_prepared(task["task_id"], evidence="Three sourced results")
    assert completed["status"] == "completed"
    assert completed["approval"] is None


def test_companion_renders_only_task_scope_and_decision(tmp_path):
    agent = AionTVAgent(tmp_path)
    agent.create_plan("reserve a table for two")
    page = _companion_html("safe-token", "csrf-token", agent.snapshot()).decode("utf-8")
    assert "reserve a table for two" in page
    assert "Prepare privately as this identity" in page
    assert "pairing key" in page
    assert "client_key" not in page


def test_companion_games_surface_keeps_credentials_private(tmp_path):
    agent = AionTVAgent(tmp_path)
    page = _companion_html("safe-token", "csrf-token", agent.snapshot()).decode("utf-8")
    assert 'data-command="games"' in page
    assert 'type="password"' in page
    assert "/private-text" in page
    assert "does not retain or audit its value" in page
    assert 'id="touchpad"' in page
    assert "pointer_move" in page
    assert "pointer_click" in page
    assert "Pilot Learning Centre" in page
    assert "education_answer" in page
    assert "visibilitychange" in page
    assert "Reconnecting" in page
    assert "Hold to speak privately" in page
    assert "Programme cast" in page
    assert "does not use face recognition" in page
    assert "'/voice'" in page
    assert "Transcribing locally" in page
    assert "Start visible Observer" in page
    assert 'id="observer-profile"' in page
    assert "battery_saver" in page
    assert "observer_resource_state" in page
    assert "observer_pause" in page


def test_companion_renders_private_source_labelled_live_fact_check(tmp_path):
    agent = AionTVAgent(tmp_path)
    snapshot = agent.snapshot()
    snapshot["live_news"] = {
        "statement": "A current claim",
        "summary": "The claim omits relevant context.",
        "verdict": "Misleading",
        "confidence": 0.81,
        "claims": [{
            "claim": "The first checkable claim",
            "verdict": "Misleading",
            "explanation": "The dates differ.",
        }],
        "sources": [{
            "index": 1,
            "title": "Official evidence",
            "url": "https://example.gov/evidence",
            "source_class": "government_or_intergovernmental",
            "quality_score": 0.95,
            "quality_basis": "Primary government source",
        }],
        "performance": {"latency_ms": 740, "mean_source_quality": 0.95},
        "contradiction_analysis": {"contradictions_detected": 0},
        "correction_timeline": [{"event": "evidence_researched", "detail": "1 source"}],
    }
    page = _companion_html("safe-token", "csrf-token", snapshot).decode("utf-8")

    assert "Live fact-check" in page
    assert "Misleading · confidence 81%" in page
    assert "The first checkable claim" in page
    assert "Official evidence" in page
    assert "government_or_intergovernmental" in page
    assert "mean source quality 95%" in page
    assert "740 ms" in page
    assert "who disagrees" in page
    assert "show me the evidence" in page


def test_companion_shows_exact_service_scope_before_approval(tmp_path):
    agent = AionTVAgent(tmp_path)
    task = agent.create_plan("reserve a table for two")
    snapshot = agent.snapshot()
    snapshot["service_proposal"] = {
        "proposal_id": "service_proposal_test",
        "parameters": {"what": "Restaurant Example", "date": "2026-09-12", "party_size": 2},
        "status": "awaiting_private_approval",
    }
    page = _companion_html("safe-token", "csrf-token", snapshot).decode("utf-8")
    assert "Approve this exact action" in page
    assert "party_size" in page
    assert task["approval"]["approval_id"] in page


def test_companion_collects_missing_private_details_before_showing_approval(tmp_path):
    agent = AionTVAgent(tmp_path)
    agent.create_plan("put the Granada weekend in my calendar")
    snapshot = agent.snapshot()
    snapshot["service_proposal"] = {
        "proposal_id": "service_proposal_calendar",
        "parameters": {"title": "Granada weekend"},
        "missing_fields": ["start", "end"],
        "status": "needs_details",
    }
    page = _companion_html("safe-token", "csrf-token", snapshot).decode("utf-8")
    assert 'data-service-field="start"' in page
    assert 'data-service-field="end"' in page
    assert 'id="save-service-details"' in page
    assert "command('service_details'" in page
    assert "Approve this exact action" not in page


def test_unmapped_voice_request_routes_to_agent_instead_of_phrase_failure():
    intent = parse_voice_intent("Pilot plan a weekend in Granada for us")
    assert intent is not None
    assert intent.action == "agent_request"
    assert intent.arguments == {"request": "plan a weekend in granada for us"}

    refinement = parse_voice_intent("Pilot update the plan with a mid-range budget")
    assert refinement is not None
    assert refinement.action == "agent_request"
    assert refinement.arguments == {"refinement": "a mid range budget"}


def test_private_controller_has_fabric_native_god_view_controls(tmp_path):
    agent = AionTVAgent(tmp_path)
    page = _companion_html("safe-token", "csrf-token", agent.snapshot()).decode("utf-8")
    assert "God View controller" in page
    assert 'data-command="god_pilot"' in page
    assert 'data-command="god_select"' in page
    assert 'data-command="god_track_iss"' in page
    assert "Live View from Space" in page
    assert 'data-command="god_lapland"' in page


def test_pairing_page_explains_explicit_tls_trust_and_public_fingerprint():
    page = companion._entry_html(
        "123456",
        secure_url="https://192.168.1.10:8769/companion/token",
        ca_available=True,
        ca_fingerprint="ab" * 32,
    ).decode("utf-8")
    assert "Download public trust certificate" in page
    assert "enable full trust" in page.lower()
    assert "No private key is downloaded" in page
    assert "ab" * 32 in page


def test_private_companion_applies_one_scoped_decision(tmp_path, monkeypatch):
    monkeypatch.setattr(companion, "_lan_address", lambda preferred_peer=None: "127.0.0.1")
    agent = AionTVAgent(tmp_path)
    task = agent.create_plan("book a table for two")
    service = companion.CompanionService(
        agent.snapshot,
        lambda approval_id, approved: agent.decide(approval_id, approved=approved),
        port=0,
        token="companion-test-token",
    )
    service.start()
    try:
        with urllib.request.urlopen(service.public_url, timeout=2) as response:
            assert "Private approval" in response.read().decode("utf-8")
        body = urllib.parse.urlencode({
            "approval_id": task["approval"]["approval_id"],
            "decision": "approve",
        }).encode()
        request = urllib.request.Request(
            f"{service.public_url}/decision",
            data=body,
            method="POST",
            headers={"X-AION-CSRF": service.csrf_token},
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            assert "approved" in response.read().decode("utf-8")
        assert agent.latest()["status"] == "approved_pending_adapter"
    finally:
        service.stop()


def test_private_companion_routes_bounded_controller_command(tmp_path, monkeypatch):
    monkeypatch.setattr(companion, "_lan_address", lambda preferred_peer=None: "127.0.0.1")
    received = []
    service = companion.CompanionService(
        lambda: {"controller": {"tv_name": "Test TV", "volume": 20}},
        lambda approval_id, approved: {},
        command_handler=lambda command, arguments: received.append((command, arguments)) or {"accepted": True},
        port=0,
        token="controller-test-token",
        csrf_token="controller-csrf-token",
    )
    service.start()
    try:
        body = urllib.parse.urlencode({"command": "left", "arguments": "{}"}).encode()
        request = urllib.request.Request(
            f"{service.public_url}/command",
            data=body,
            method="POST",
            headers={"X-AION-CSRF": service.csrf_token},
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            assert urllib.request.urlopen(f"{service.public_url}/manifest.webmanifest", timeout=2).status == 200
            assert response.status == 200
        assert received == [("left", {})]
    finally:
        service.stop()


def test_private_companion_delivers_sensitive_text_without_echo(tmp_path, monkeypatch):
    monkeypatch.setattr(companion, "_lan_address", lambda preferred_peer=None: "127.0.0.1")
    received = []
    service = companion.CompanionService(
        lambda: {"controller": {"tv_name": "Test TV", "volume": 20}},
        lambda approval_id, approved: {},
        private_text_handler=lambda value, purpose: received.append((value, purpose)) or {
            "accepted": True,
            "retained": False,
        },
        port=0,
        token="private-text-test-token",
        csrf_token="private-text-csrf-token",
    )
    service.start()
    try:
        secret = "test-password-never-echo"
        body = urllib.parse.urlencode({"purpose": "password", "value": secret}).encode()
        request = urllib.request.Request(
            f"{service.public_url}/private-text",
            data=body,
            method="POST",
            headers={"X-AION-CSRF": service.csrf_token},
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            payload = response.read().decode("utf-8")
        assert secret not in payload
        assert received == [(secret, "password")]
    finally:
        service.stop()
