from __future__ import annotations

import json

import pytest

from backend.modules.aion_fabric.live_events import LiveEventIntelligence
from backend.modules.aion_fabric.voice import parse_voice_intent


class _Response:
    def __init__(self, payload):
        self.body = json.dumps(payload).encode() if not isinstance(payload, bytes) else payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit=-1):
        return self.body


def _local_score():
    return {
        "answer": "The captured scoreboard shows Real Madrid 2, Barcelona 1.",
        "confidence": 0.92,
        "scoreboard": {
            "detected": True,
            "score_text": "REAL MADRID 2 - 1 BARCELONA",
            "confidence": 0.92,
            "structured": {"left": "REAL MADRID", "left_score": 2, "right": "BARCELONA", "right_score": 1},
        },
        "rule_key": None,
        "rule_explanation": "",
    }


def test_authenticated_football_feed_is_fused_with_screen_evidence(tmp_path):
    seen = {}

    def opener(request, timeout):
        seen["request"] = request
        seen["timeout"] = timeout
        return _Response(
            {
                "matches": [
                    {
                        "id": 42,
                        "competition": {"name": "Champions League"},
                        "homeTeam": {"name": "Real Madrid CF"},
                        "awayTeam": {"name": "FC Barcelona"},
                        "status": "IN_PLAY",
                        "minute": 78,
                        "lastUpdated": "2026-08-30T00:10:00Z",
                        "score": {"fullTime": {"home": 2, "away": 1}},
                    }
                ]
            }
        )

    service = LiveEventIntelligence(tmp_path, urlopen=opener, secret_resolver=lambda provider: "owner-token-123" if provider == "football_data" else "")
    result = service.query(question_kind="score", question="what is the score", local_interpretation=_local_score())

    assert result["reconciliation"] == "screen_and_provider_agree"
    assert result["authenticated_provider_fact"]["provider_match_id"] == "42"
    assert "authenticated feed shows" in result["answer"]
    assert result["provenance"]["provider_secret_projected_to_tv_or_phone"] is False
    assert "owner-token-123" not in result["provider"]["request_url"]
    assert seen["request"].get_header("X-auth-token") == "owner-token-123"
    assert seen["timeout"] == 12


def test_scorer_is_reported_only_when_authenticated_feed_supplies_it(tmp_path):
    def opener(_request, timeout):
        assert timeout == 12
        return _Response(
            {
                "matches": [
                    {
                        "id": 7,
                        "homeTeam": {"name": "Real Madrid"},
                        "awayTeam": {"name": "Barcelona"},
                        "status": "IN_PLAY",
                        "score": {"fullTime": {"home": 2, "away": 1}},
                        "goals": [{"minute": 77, "scorer": {"name": "Alex Example"}, "team": {"name": "Real Madrid"}}],
                    }
                ]
            }
        )

    result = LiveEventIntelligence(tmp_path, urlopen=opener, secret_resolver=lambda _provider: "valid-key-123").query(
        question_kind="scorer", question="who scored", local_interpretation=_local_score()
    )

    assert "Alex Example" in result["answer"]
    assert result["confidence"] == 0.93


def test_missing_provider_falls_back_to_labelled_screen_evidence(tmp_path):
    result = LiveEventIntelligence(tmp_path, secret_resolver=lambda _provider: "").query(
        question_kind="score", question="what is the score", local_interpretation=_local_score()
    )

    assert result["reconciliation"] == "screen_only"
    assert "captured scoreboard" in result["answer"]
    assert "No authenticated live-event provider" in result["answer"]
    assert result["provider"]["connected"] is False


def test_conflicting_provider_and_screen_scores_are_never_silently_merged(tmp_path):
    def opener(_request, timeout):
        assert timeout == 12
        return _Response({"matches": [{"id": 8, "homeTeam": {"name": "Real Madrid"}, "awayTeam": {"name": "Barcelona"}, "score": {"fullTime": {"home": 1, "away": 2}}}]})

    result = LiveEventIntelligence(tmp_path, urlopen=opener, secret_resolver=lambda _provider: "valid-key-123").query(
        question_kind="score", question="what is the score", local_interpretation=_local_score()
    )

    assert result["reconciliation"] == "screen_provider_conflict"
    assert result["authenticated_provider_fact"]["home_score"] == 1
    assert result["screen_observation"]["structured"]["left_score"] == 2


def test_provider_response_size_is_bounded(tmp_path):
    service = LiveEventIntelligence(tmp_path)
    with pytest.raises(RuntimeError):
        service._read_json_response(_Response(b"x" * (service.MAX_RESPONSE_BYTES + 1)))


def test_status_never_returns_provider_secrets(tmp_path):
    status = LiveEventIntelligence(tmp_path, secret_resolver=lambda _provider: "private-secret-value").status()

    assert status["football_data"] == {"connected": True, "secret_exposed": False}
    assert "private-secret-value" not in json.dumps(status)


def test_live_event_voice_intents_route_separately_from_rule_explanation():
    assert parse_voice_intent("Pilot who scored the last goal").arguments["kind"] == "scorer"
    assert parse_voice_intent("Pilot show the statistics").arguments["kind"] == "statistics"
    assert parse_voice_intent("Pilot what is the score").action == "live_event"
    assert parse_voice_intent("Pilot why was that offside").action == "live_sports"
    assert parse_voice_intent("Pilot show upcoming concerts").arguments["kind"] == "concerts"
    assert parse_voice_intent("Pilot show the incident timeline").arguments["kind"] == "timeline"
    historical = parse_voice_intent("Pilot compare Real Madrid over the last 30 days")
    assert historical.arguments == {"kind": "historical_statistics", "question": "compare real madrid over the last 30 days", "history_days": 30}


def test_authenticated_incident_timeline_and_lineups_are_bounded(tmp_path):
    def opener(_request, timeout):
        assert timeout == 12
        return _Response({"matches": [{
            "id": 10,
            "homeTeam": {"name": "Real Madrid", "lineup": [{"name": "A Player", "position": "Forward", "shirtNumber": 9}]},
            "awayTeam": {"name": "Barcelona", "lineup": [{"name": "B Player", "position": "Goalkeeper", "shirtNumber": 1}]},
            "score": {"fullTime": {"home": 2, "away": 1}},
            "goals": [{"minute": 12, "scorer": {"name": "A Player"}, "team": {"name": "Real Madrid"}}],
            "bookings": [{"minute": 40, "player": {"name": "B Player"}, "team": {"name": "Barcelona"}, "card": "YELLOW_CARD"}],
            "substitutions": [{"minute": 70, "team": {"name": "Real Madrid"}, "playerOut": {"name": "A Player"}, "playerIn": {"name": "C Player"}}],
        }]})

    service = LiveEventIntelligence(tmp_path, urlopen=opener, secret_resolver=lambda _provider: "valid-key-123")
    timeline = service.query(question_kind="timeline", question="show incident timeline", local_interpretation=_local_score())
    statistics = service.query(question_kind="statistics", question="show stats", local_interpretation=_local_score())

    assert "goal by A Player" in timeline["answer"]
    assert "YELLOW_CARD for B Player" in timeline["answer"]
    assert "2 lineup entries" in statistics["answer"]


def test_historical_statistics_require_explicit_range_and_exact_team_evidence(tmp_path):
    def opener(request, timeout):
        assert timeout == 12
        assert "dateFrom=" in request.full_url and "dateTo=" in request.full_url
        return _Response({"matches": [
            {"id": 11, "homeTeam": {"name": "Real Madrid CF"}, "awayTeam": {"name": "Barcelona"}, "score": {"fullTime": {"home": 2, "away": 1}}},
            {"id": 12, "homeTeam": {"name": "Valencia"}, "awayTeam": {"name": "Real Madrid CF"}, "score": {"fullTime": {"home": 1, "away": 1}}},
        ]})

    service = LiveEventIntelligence(tmp_path, urlopen=opener, secret_resolver=lambda _provider: "valid-key-123")
    result = service.query(question_kind="historical_statistics", question="compare Real Madrid over the last 30 days", local_interpretation=None, history_days=30)
    missing = service.query(question_kind="historical_statistics", question="compare Real Madrid", local_interpretation=None)

    assert result["historical_statistics"] == {"team": "Real Madrid CF", "range_days": 30, "played": 2, "wins": 1, "draws": 1, "losses": 0, "goals_for": 3, "goals_against": 2}
    assert "explicitly selected last 30 days" in result["answer"]
    assert missing["confidence"] == 0
