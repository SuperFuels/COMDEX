import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.modules.hexcore import prediction_market_research_engine as research_engine
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


def test_default_provider_is_local_qwen_and_needs_no_openai_key(
    tmp_path: Path, monkeypatch,
) -> None:
    calls = []
    monkeypatch.delenv("AION_PREDICTION_RESEARCH_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        research_engine,
        "_local_qwen_forecast",
        lambda market: calls.append(market["market_id"]) or _forecast(market),
    )
    result = run(
        market_snapshot_path=_snapshot(tmp_path / "markets.json"),
        state_path=tmp_path / "state.json", result_path=tmp_path / "result.json",
    )
    assert result["passed"]
    assert calls == ["market-1"]
    assert result["summary"]["research_provider"] == "local_qwen"


def test_local_qwen_can_only_cite_retrieved_source_ids(monkeypatch) -> None:
    evidence = [
        {"source_id": f"source-{index}", "url": f"https://source{index}.example/item",
         "domain": f"source{index}.example", "title": f"Source {index}",
         "source_type": "primary_official" if index == 1 else "independent_reporting",
         "excerpt": "Verified evidence excerpt."}
        for index in range(1, 4)
    ]
    content = json.dumps({
        "probability_yes": .55, "uncertainty": .1, "confidence": "medium",
        "base_rate": "balanced", "evidence_for": ["support"],
        "evidence_against": ["counter"], "key_variables": ["lineup"],
        "missing_information": [], "reasoning_summary": "mixed evidence",
        "source_claims": {**{row["source_id"]: "used" for row in evidence},
                          "invented-source": "must be dropped"},
        "abstain": False, "abstain_reason": "",
    })
    monkeypatch.setattr(research_engine, "_governed_web_evidence", lambda _: evidence)
    monkeypatch.setattr(research_engine, "_local_qwen_runtime_profile", lambda: {"profile": True})
    monkeypatch.setattr(
        "backend.services.aion_mission_mode.pilot_local_model_runtime.run_selected_local_chat",
        lambda **_: {"content": content, "model": "qwen3-8b-fast-local-q4"},
    )
    result = research_engine._local_qwen_forecast({"title": "Alpha?"})
    assert [row["domain"] for row in result["sources"]] == [
        "source1.example", "source2.example", "source3.example",
    ]
    assert result["provider"] == "local_qwen_governed_web_retrieval"
