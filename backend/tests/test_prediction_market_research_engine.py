import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.modules.hexcore.prediction_market_research_engine import run


def _snapshot(path: Path) -> Path:
    now = datetime.now(timezone.utc)
    market = {
        "platform": "polymarket", "market_id": "market-1",
        "title": "Will Alpha defeat Beta?", "event_title": "Alpha vs Beta",
        "market_description": "YES only if Alpha wins.", "market_type": "moneyline",
        "event_start_time": (now + timedelta(hours=2)).isoformat(),
        "close_time": (now + timedelta(hours=4)).isoformat(),
        "event_live": False, "event_ended": False,
        "yes_probability": .42, "yes_bid": .40, "yes_ask": .44,
        "resolution_ready": True, "resolution_source": "Official league",
        "research_priority_score": 10,
    }
    path.write_text(json.dumps({
        "market_snapshot": [market],
        "source_receipt": {"snapshot_sha256": "f" * 64},
    }), encoding="utf-8")
    return path


def _forecast(_: object):
    return {
        "forecast": {
            "domain": "sport", "probability_yes": .58, "uncertainty": .08,
            "confidence": "medium", "base_rate": "Comparable fixtures favour Alpha.",
            "evidence_for": ["Alpha has stronger recent form."],
            "evidence_against": ["Beta has home advantage."],
            "key_variables": ["lineup", "form"], "missing_information": ["late injuries"],
            "reasoning_summary": "Base rate adjusted for current evidence.",
            "abstain": False, "abstain_reason": "",
        },
        "sources": [
            {"url": "https://league.example/form", "domain": "league.example", "title": "Form",
             "source_type": "primary_official", "claim": "Official form"},
            {"url": "https://news.example/lineups", "domain": "news.example", "title": "Lineups",
             "source_type": "independent_reporting", "claim": "Lineup reporting"},
            {"url": "https://stats.example/history", "domain": "stats.example", "title": "History",
             "source_type": "statistics_database", "claim": "Historical rate"},
        ],
        "provider": "test", "model": "test", "response_id": "response-1", "usage": {},
    }


def test_source_backed_packet_is_frozen_and_market_blind(tmp_path: Path) -> None:
    result = run(
        market_snapshot_path=_snapshot(tmp_path / "markets.json"),
        state_path=tmp_path / "state.json", result_path=tmp_path / "result.json",
        forecaster=_forecast,
    )
    assert result["passed"]
    assert result["summary"]["usable_packets"] == 1
    packet = result["research_packets"][0]
    assert packet["probability_yes"] == .58
    assert packet["uncertainty"] == .08
    assert packet["independent_from_market_price"]
    assert not packet["market_price_disclosed_to_researcher"]
    assert len(packet["research_packet_sha256"]) == 64
    assert "yes_probability" not in packet


def test_weak_or_one_sided_research_is_blocked(tmp_path: Path) -> None:
    weak = _forecast(None)
    weak["sources"] = weak["sources"][:1]
    weak["forecast"]["evidence_against"] = []
    result = run(
        market_snapshot_path=_snapshot(tmp_path / "markets.json"),
        state_path=tmp_path / "state.json", result_path=tmp_path / "result.json",
        forecaster=lambda _: weak,
    )
    assert result["summary"]["usable_packets"] == 0
    created = result["created_packets"][0]
    assert "fewer_than_three_independent_sources" in created["blockers"]
    assert "one_sided_analysis" in created["blockers"]
