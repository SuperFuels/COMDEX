import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.modules.hexcore.prediction_market_paper_game import _default_settlement_fetcher, run


def _snapshot(path: Path, *, count: int = 6, close_hours: float = 1) -> Path:
    close_time = (datetime.now(timezone.utc) + timedelta(hours=close_hours)).isoformat()
    markets = []
    for index in range(count):
        markets.append({
            "platform": "kalshi",
            "market_id": f"FAST-{index}",
            "title": f"Will event {index} happen?",
            "yes_probability": .20,
            "yes_bid": .19,
            "yes_ask": .21,
            "resolution_ready": True,
            "restricted": False,
            "close_time": close_time,
            "event_start_time": close_time,
            "event_live": False,
            "event_ended": False,
        })
    path.write_text(json.dumps({
        "market_snapshot": markets,
        "source_receipt": {"snapshot_sha256": "a" * 64, "observed_at": datetime.now(timezone.utc).isoformat()},
    }), encoding="utf-8")
    return path


def _research(path: Path, *, count: int = 6) -> Path:
    path.write_text(json.dumps({
        "research_packets": [{
            "platform": "kalshi", "market_id": f"FAST-{index}",
            "usable_for_paper_decision": True,
            "independent_from_market_price": True,
            "market_price_disclosed_to_researcher": False,
            "research_quality_version": 2,
            "researched_at": datetime.now(timezone.utc).isoformat(),
            "probability_yes": .50, "uncertainty": .05,
            "research_packet_sha256": str(index) * 64,
            "sources": [{"url": "https://official.example/a"}] * 3,
            "source_domains": ["official.example", "news.example"],
            "model": "test-researcher",
        } for index in range(count)],
    }), encoding="utf-8")
    return path


def test_game_opens_bounded_fast_positions_and_persists(tmp_path: Path) -> None:
    market_path = _snapshot(tmp_path / "markets.json")
    state_path = tmp_path / "state.json"
    result_path = tmp_path / "result.json"
    research_path = _research(tmp_path / "research.json")
    result = run(market_snapshot_path=market_path, research_path=research_path,
                 state_path=state_path, result_path=result_path)
    assert result["gate"]["paper_only"]
    assert result["gate"]["maximum_time_to_close_hours"] == 24
    assert result["gate"]["orders_submitted"] == 0
    assert result["gate"]["live_capital_at_risk"] == 0
    assert result["gate"]["max_daily_risk"] == 100
    assert result["tally"]["open_positions"] == 5
    assert result["tally"]["cash"] == 949.5
    assert result["tally"]["account_value"] == 999.5
    assert all(row["stake"] == 10 for row in result["open_positions"])
    assert all(row["edge_basis"] == "market_blind_source_backed_domain_research"
               for row in result["open_positions"])
    repeated = run(market_snapshot_path=market_path, research_path=research_path,
                   state_path=state_path, result_path=result_path)
    assert repeated["tally"]["total_bets"] == 5
    assert repeated["new_positions"] == []


def test_game_rejects_markets_closing_after_24_hours(tmp_path: Path) -> None:
    result = run(
        market_snapshot_path=_snapshot(tmp_path / "markets.json", close_hours=25),
        research_path=_research(tmp_path / "research.json"),
        state_path=tmp_path / "state.json",
        result_path=tmp_path / "result.json",
    )
    assert result["tally"]["total_bets"] == 0
    assert result["tally"]["account_value"] == 1000


def test_game_rejects_started_event_and_stale_research(tmp_path: Path) -> None:
    market_path = _snapshot(tmp_path / "markets.json", count=1)
    snapshot = json.loads(market_path.read_text(encoding="utf-8"))
    snapshot["market_snapshot"][0]["event_start_time"] = (
        datetime.now(timezone.utc) - timedelta(minutes=1)
    ).isoformat()
    market_path.write_text(json.dumps(snapshot), encoding="utf-8")
    result = run(
        market_snapshot_path=market_path,
        research_path=_research(tmp_path / "research.json", count=1),
        state_path=tmp_path / "state.json",
        result_path=tmp_path / "result.json",
    )
    assert result["tally"]["total_bets"] == 0

    snapshot["market_snapshot"][0]["event_start_time"] = (
        datetime.now(timezone.utc) + timedelta(hours=1)
    ).isoformat()
    market_path.write_text(json.dumps(snapshot), encoding="utf-8")
    research_path = _research(tmp_path / "stale-research.json", count=1)
    research = json.loads(research_path.read_text(encoding="utf-8"))
    research["research_packets"][0]["researched_at"] = (
        datetime.now(timezone.utc) - timedelta(hours=7)
    ).isoformat()
    research_path.write_text(json.dumps(research), encoding="utf-8")
    result = run(
        market_snapshot_path=market_path,
        research_path=research_path,
        state_path=tmp_path / "state-2.json",
        result_path=tmp_path / "result-2.json",
    )
    assert result["tally"]["total_bets"] == 0


def test_game_scores_only_later_official_settlement(tmp_path: Path) -> None:
    market_path = _snapshot(tmp_path / "markets.json", count=1)
    state_path = tmp_path / "state.json"
    result_path = tmp_path / "result.json"
    research_path = _research(tmp_path / "research.json", count=1)
    opened = run(market_snapshot_path=market_path, research_path=research_path,
                 state_path=state_path, result_path=result_path)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["positions"][0]["close_epoch"] = 0
    state_path.write_text(json.dumps(state), encoding="utf-8")
    settled = run(
        market_snapshot_path=market_path,
        research_path=research_path,
        state_path=state_path,
        result_path=result_path,
        settlement_fetcher=lambda platform, market_id: {
            "settled": True, "outcome": 0, "source": f"official:{platform}:{market_id}",
        },
    )
    assert opened["open_positions"][0]["side"] == "yes"
    assert settled["tally"]["settled_bets"] == 1
    assert settled["tally"]["losses"] == 1
    assert settled["tally"]["win_rate"] == 0
    assert settled["recent_settlements"][0]["settlement_source"].startswith("official:")
    assert len(settled["recent_settlements"][0]["receipt_sha256"]) == 64


def test_polymarket_settlement_queries_the_closed_archive(monkeypatch) -> None:
    observed = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps([{
                "closed": True,
                "outcomePrices": '["1", "0"]',
                "umaResolutionStatus": "resolved",
            }]).encode()

    def fake_open(request, timeout):
        observed["url"] = request.full_url
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_open)
    receipt = _default_settlement_fetcher("polymarket", "condition-1")
    assert "closed=true" in observed["url"]
    assert "condition_ids=condition-1" in observed["url"]
    assert receipt["settled"] and receipt["outcome"] == 1
