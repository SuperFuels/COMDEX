from pathlib import Path

from backend.modules.hexcore.prediction_market_intelligence_arena import (
    KALSHI_MARKETS,
    POLYMARKET_GEOBLOCK,
    POLYMARKET_MARKETS,
    assess_live_capital_gate,
    commit_paper_forecast,
    market_proposal_draft,
    paper_decision,
    run,
    score_paper_settlement,
)


def _fetch(url: str, **_: object):
    if url == POLYMARKET_GEOBLOCK:
        return {"blocked": False, "country": "ES", "region": "MD"}
    if url == POLYMARKET_MARKETS:
        return [{
            "conditionId": "poly-1", "slug": "event-one", "question": "Will event one occur?",
            "outcomes": '["Yes","No"]', "outcomePrices": '["0.42","0.58"]',
            "bestBid": 0.40, "bestAsk": 0.44, "liquidityNum": 10_000,
            "volume24hr": 2_000, "resolutionSource": "Official agency",
            "endDateIso": "2099-01-01", "endDate": "2099-01-01T12:34:56Z",
        }]
    if url == KALSHI_MARKETS:
        return {"markets": [{
            "ticker": "K-EVENT-1", "title": "Will event two occur?",
            "last_price_dollars": "0.6000", "yes_bid_dollars": "0.5800",
            "yes_ask_dollars": "0.6200", "liquidity_dollars": "5000",
            "volume_24h_fp": "800", "rules_primary": "Official publication",
        }]}
    raise AssertionError(url)


def test_live_public_intake_is_read_only_and_hashes_snapshot(tmp_path: Path) -> None:
    result = run(output_path=tmp_path / "result.json", fetcher=_fetch)
    assert result["passed"]
    assert result["source_receipt"]["market_count"] == 2
    assert result["source_receipt"]["platform_counts"] == {"polymarket": 1, "kalshi": 1}
    assert result["geographic_eligibility"]["blocked"] is False
    assert len(result["source_receipt"]["snapshot_sha256"]) == 64
    assert all(row["trade_edge"] is None for row in result["research_candidates"])
    polymarket = next(row for row in result["market_snapshot"] if row["platform"] == "polymarket")
    assert polymarket["close_time"] == "2099-01-01T12:34:56Z"
    assert result["gate"]["credentials_loaded"] is False
    assert result["gate"]["orders_submitted"] == 0
    assert result["gate"]["live_capital_at_risk"] == 0
    assert result["gate"]["live_trading_enabled"] is False


def test_paper_decision_requires_robust_after_cost_edge() -> None:
    market = {
        "market_id": "poly-1", "platform": "polymarket", "yes_bid": .40,
        "yes_ask": .44, "yes_probability": .42, "resolution_ready": True,
    }
    accepted = paper_decision(market=market, forecast_probability=.62, uncertainty=.04)
    rejected = paper_decision(market=market, forecast_probability=.47, uncertainty=.04)
    assert accepted["accepted"] and accepted["side"] == "yes"
    assert 0 < accepted["paper_stake"] <= 10
    assert accepted["live_stake"] == 0
    assert rejected["side"] == "abstain" and rejected["paper_stake"] == 0
    assert len(accepted["commitment_sha256"]) == 64


def test_market_creation_is_a_reviewed_unsubmitted_proposal() -> None:
    poly = market_proposal_draft(
        platform="polymarket", title="Will the official measure exceed 10?",
        resolution_source="Official statistics agency", close_time="2027-01-01T00:00:00Z",
        demand_evidence="Existing related markets have sustained volume.",
    )
    kalshi = market_proposal_draft(
        platform="kalshi", title="Will the official measure exceed 10?",
        resolution_source="Official statistics agency", close_time="2027-01-01T00:00:00Z",
        demand_evidence="Existing related markets have sustained volume.",
    )
    assert poly["route"] == "community_market_proposal"
    assert kalshi["route"] == "regulated_market_suggestion"
    assert poly["complete"] and kalshi["complete"]
    assert not poly["submitted"] and not kalshi["submitted"]
    assert poly["requires_human_review"]


def test_live_capital_gate_requires_longitudinal_edge_and_tight_loss_limits() -> None:
    mandate = {
        "owner_approved": True, "account_owner_verified": True,
        "jurisdiction_confirmed": True, "platform": "polymarket",
        "per_order_approval": True, "bankroll": 1_000,
        "max_order": 10, "max_daily_loss": 20, "max_total_exposure": 50,
    }
    performance = {
        "settled_forecasts": 100, "brier_advantage": .02,
        "net_return_after_costs": .05, "max_drawdown": .04,
    }
    gate = assess_live_capital_gate(
        mandate=mandate, performance=performance,
        geoblock={"checked": True, "blocked": False},
    )
    assert gate["qualified_for_live_order_proposals"]
    assert gate["live_execution_enabled"] is False
    assert gate["orders_submitted"] == 0
    unsafe = assess_live_capital_gate(
        mandate=mandate | {"max_order": 100}, performance=performance,
        geoblock={"checked": True, "blocked": False},
    )
    assert not unsafe["qualified_for_live_order_proposals"]
    assert "order_cap_at_most_one_percent" in unsafe["blockers"]


def test_paper_commitment_is_immutable_and_scored_only_on_later_settlement(tmp_path: Path) -> None:
    state_path = tmp_path / "paper.json"
    market = {
        "market_id": "poly-1", "platform": "polymarket", "title": "Will X occur?",
        "yes_bid": .40, "yes_ask": .44, "yes_probability": .42,
        "resolution_ready": True,
    }
    commitment = commit_paper_forecast(
        state_path=state_path, market=market,
        forecast_probability=.62, uncertainty=.04,
    )
    assert commitment["status"] == "pending_settlement"
    duplicate = commit_paper_forecast(
        state_path=state_path, market=market,
        forecast_probability=.62, uncertainty=.04,
    )
    # The timestamps differ, so a later decision is a distinct commitment;
    # neither may overwrite the earlier record.
    assert duplicate["commitment_id"] != commitment["commitment_id"]
    settlement = score_paper_settlement(
        state_path=state_path, commitment_id=commitment["commitment_id"], outcome=1,
        settlement_source="Official platform settlement",
        settled_at="2099-01-01T00:00:00+00:00",
    )
    assert settlement["independent_outcome_after_commitment"]
    assert settlement["brier_score"] == .1444
    assert settlement["paper_net_pnl"] > 0
    assert settlement["live_net_pnl"] == 0
    try:
        score_paper_settlement(
            state_path=state_path, commitment_id=commitment["commitment_id"], outcome=1,
            settlement_source="Official platform settlement",
            settled_at="2099-01-02T00:00:00+00:00",
        )
        raise AssertionError("commitment scored twice")
    except ValueError:
        pass
    assess_live_capital_gate,
