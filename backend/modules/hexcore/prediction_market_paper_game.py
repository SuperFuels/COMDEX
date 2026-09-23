"""A $1,000 zero-capital prediction-market learning game.

Positions are virtual. Public platform data supplies entry marks and later
settlements. The initial strategy is a falsifiable calibration hypothesis, not
a claim of alpha. Its parameters may only change after scored settlements.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping


SCHEMA = "aion.hexcore.prediction_market_paper_game.v1"
STARTING_CAPITAL = 1_000.0
MAX_ORDER_FRACTION = .01
MAX_EXPOSURE_FRACTION = .05
MAX_DAILY_RISK_FRACTION = .10
SIMULATED_COST_RATE = .01
MAX_HOLD_HOURS = 24
MAX_RESEARCH_AGE_HOURS = 6
MIN_RESEARCH_QUALITY_VERSION = 2


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def _atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def _initial_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "starting_capital": STARTING_CAPITAL,
        "cash": STARTING_CAPITAL,
        "positions": [],
        "settlements": [],
        "strategy": {
            "strategy_id": "market_calibration_shrinkage_v1",
            "hypothesis": "Very high and low crowd probabilities may be overconfident; shrink 30% toward 0.5.",
            "shrinkage": .30,
            "minimum_model_edge": .025,
            "simulated_cost_rate": SIMULATED_COST_RATE,
            "parameters_frozen_until_settlements": 20,
            "claim": "calibration_experiment_not_proven_alpha",
        },
        "created_at": _now(),
    }


def _researched_strategy() -> dict[str, Any]:
    return {
        "strategy_id": "source_backed_independent_forecast_v2",
        "hypothesis": "Market-blind domain research can identify conservative price discrepancies.",
        "minimum_robust_edge": .025,
        "simulated_cost_rate": SIMULATED_COST_RATE,
        "minimum_independent_sources": 3,
        "market_price_hidden_during_research": True,
        "parameters_frozen_until_settlements": 20,
        "claim": "researched_paper_experiment_not_proven_alpha",
    }


def _close_epoch(value: Any) -> float | None:
    if not value:
        return None
    text = str(value)
    if len(text) == 10:
        text += "T23:59:59+00:00"
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _candidate_decision(market: Mapping[str, Any], strategy: Mapping[str, Any],
                        research: Mapping[str, Any] | None) -> dict[str, Any] | None:
    probability = _number(market.get("yes_probability"), -1)
    bid = _number(market.get("yes_bid"), probability)
    ask = _number(market.get("yes_ask"), probability)
    if not .03 <= probability <= .97 or not 0 < bid <= ask < 1:
        return None
    # A platform restriction blocks real execution, not observation of a
    # public contract in this zero-capital learning game. Preserve the flag on
    # every position so it can never be confused with live eligibility.
    if ask - bid > .06 or not market.get("resolution_ready"):
        return None
    close_epoch = _close_epoch(market.get("close_time"))
    now_epoch = datetime.now(timezone.utc).timestamp()
    if close_epoch is None or not now_epoch < close_epoch <= now_epoch + MAX_HOLD_HOURS * 3600:
        return None
    start_epoch = _close_epoch(market.get("event_start_time")) or close_epoch
    if (market.get("event_live") or market.get("event_ended")
            or start_epoch is None or now_epoch >= start_epoch):
        return None
    if not research or not research.get("usable_for_paper_decision"):
        return None
    if int(research.get("research_quality_version") or 0) < MIN_RESEARCH_QUALITY_VERSION:
        return None
    if not research.get("independent_from_market_price") or research.get("market_price_disclosed_to_researcher"):
        return None
    researched_epoch = _close_epoch(research.get("researched_at"))
    if (researched_epoch is None or researched_epoch > now_epoch
            or now_epoch - researched_epoch > MAX_RESEARCH_AGE_HOURS * 3600
            or researched_epoch >= start_epoch):
        return None
    forecast = _number(research.get("probability_yes"), -1)
    uncertainty = _number(research.get("uncertainty"), 1)
    if not 0 <= forecast <= 1 or not .05 <= uncertainty <= .35:
        return None
    yes_edge = forecast - uncertainty - ask - SIMULATED_COST_RATE
    no_entry = 1 - bid
    no_edge = (1 - forecast) - uncertainty - no_entry - SIMULATED_COST_RATE
    side, edge, entry = max((("yes", yes_edge, ask), ("no", no_edge, no_entry)), key=lambda x: x[1])
    if edge < _number(strategy.get("minimum_robust_edge"), .025):
        return None
    return {
        "side": side, "model_probability": round(forecast, 8),
        "forecast_uncertainty": round(uncertainty, 8),
        "model_edge_after_costs": round(edge, 8), "entry_price": round(entry, 8),
        "close_epoch": close_epoch,
    }


def _default_settlement_fetcher(platform: str, market_id: str) -> Mapping[str, Any]:
    if platform == "polymarket":
        url = "https://gamma-api.polymarket.com/markets?" + urllib.parse.urlencode(
            # Gamma excludes archived markets from the default collection.
            # Settlement reconciliation must explicitly query the closed set.
            {"condition_ids": market_id, "closed": "true"}
        )
    elif platform == "kalshi":
        url = "https://external-api.kalshi.com/trade-api/v2/markets/" + market_id
    else:
        return {}
    request = urllib.request.Request(url, headers={
        "Accept": "application/json", "User-Agent": "AION-paper-settlement-check/1.0",
    })
    with urllib.request.urlopen(request, timeout=10) as response:
        payload = json.loads(response.read().decode())
    if platform == "kalshi":
        row = payload.get("market") or payload
        result = str(row.get("result") or "").lower()
        return {"settled": result in {"yes", "no"}, "outcome": 1 if result == "yes" else 0,
                "source": url, "raw_status": row.get("status")}
    if isinstance(payload, list):
        payload = payload[0] if payload else {}
    prices = payload.get("outcomePrices")
    if isinstance(prices, str):
        try: prices = json.loads(prices)
        except json.JSONDecodeError: prices = []
    values = [_number(item, -1) for item in (prices or [])]
    settled = bool(payload.get("closed")) and len(values) >= 2 and max(values) >= .999
    return {"settled": settled, "outcome": 1 if values and values[0] >= .999 else 0,
            "source": url, "raw_status": payload.get("umaResolutionStatus")}


def run(*, market_snapshot_path: Path, state_path: Path, result_path: Path,
        research_path: Path | None = None,
        settlement_fetcher: Callable[[str, str], Mapping[str, Any]] = _default_settlement_fetcher,
        max_new_positions: int = 5) -> dict[str, Any]:
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        state = _initial_state()
    if state.get("strategy", {}).get("strategy_id") != "source_backed_independent_forecast_v2":
        state.setdefault("strategy_history", []).append(state.get("strategy") or {})
        state["strategy"] = _researched_strategy()
    snapshot = json.loads(market_snapshot_path.read_text(encoding="utf-8"))
    markets = snapshot.get("market_snapshot") or snapshot.get("research_candidates") or []
    try:
        research_result = json.loads(research_path.read_text(encoding="utf-8")) if research_path else {}
    except (OSError, json.JSONDecodeError):
        research_result = {}
    research_by_market = {
        (row.get("platform"), row.get("market_id")): row
        for row in research_result.get("research_packets") or []
    }
    live = {(row.get("platform"), row.get("market_id")): row for row in markets}
    incidents: list[dict[str, Any]] = []

    # Mark positions and settle only from later platform-owned observations.
    for position in state["positions"]:
        if position["status"] != "open":
            continue
        key = (position["platform"], position["market_id"])
        row = live.get(key)
        if row:
            side_mark = _number(row.get("yes_bid")) if position["side"] == "yes" else 1 - _number(row.get("yes_ask"))
            position["last_mark"] = round(max(0.0, min(1.0, side_mark)), 8)
            position["last_mark_at"] = snapshot.get("source_receipt", {}).get("observed_at")
        terminal_mark = _number(position.get("last_mark"), .5) <= .001 or _number(
            position.get("last_mark"), .5
        ) >= .999
        if datetime.now(timezone.utc).timestamp() >= _number(position.get("close_epoch")) or terminal_mark:
            try:
                receipt = dict(settlement_fetcher(position["platform"], position["market_id"]))
            except Exception as exc:
                incidents.append({"market_id": position["market_id"], "error": type(exc).__name__})
                continue
            if receipt.get("settled") and receipt.get("outcome") in {0, 1}:
                outcome = int(receipt["outcome"])
                won = outcome == (1 if position["side"] == "yes" else 0)
                gross = position["quantity"] if won else 0.0
                pnl = round(gross - position["stake"] - position["simulated_cost"], 8)
                state["cash"] = round(state["cash"] + gross, 8)
                position.update({"status": "settled", "won": won, "outcome": outcome,
                                 "paper_pnl": pnl, "settlement_source": receipt.get("source"),
                                 "settled_at": _now()})
                forecast_yes = position["model_probability"]
                settlement = {
                    "position_id": position["position_id"], "won": won, "paper_pnl": pnl,
                    "brier_score": round((forecast_yes - outcome) ** 2, 8),
                    "settlement_source": receipt.get("source"), "settled_at": position["settled_at"],
                }
                settlement["receipt_sha256"] = _digest(settlement)
                state["settlements"].append(settlement)

    open_positions = [row for row in state["positions"] if row["status"] == "open"]
    open_exposure = sum(_number(row.get("stake")) for row in open_positions)
    opened_today = sum(_number(row.get("stake")) for row in state["positions"]
                       if str(row.get("opened_at", ""))[:10] == _now()[:10])
    existing = {(row["platform"], row["market_id"]) for row in state["positions"]}
    capacity = min(
        max_new_positions,
        max(0, int((STARTING_CAPITAL * MAX_EXPOSURE_FRACTION - open_exposure) // (STARTING_CAPITAL * MAX_ORDER_FRACTION))),
        max(0, int((STARTING_CAPITAL * MAX_DAILY_RISK_FRACTION - opened_today) // (STARTING_CAPITAL * MAX_ORDER_FRACTION))),
    )
    decisions = []
    for market in markets:
        if capacity <= 0 or (market.get("platform"), market.get("market_id")) in existing:
            continue
        research = research_by_market.get((market.get("platform"), market.get("market_id")))
        decision = _candidate_decision(market, state["strategy"], research)
        if decision is None:
            continue
        stake = min(STARTING_CAPITAL * MAX_ORDER_FRACTION, state["cash"])
        if stake + stake * SIMULATED_COST_RATE > state["cash"]:
            break
        cost = round(stake * SIMULATED_COST_RATE, 8)
        quantity = round(stake / decision["entry_price"], 8)
        core = {
            "platform": market["platform"], "market_id": market["market_id"],
            "title": market["title"], **decision, "stake": round(stake, 8),
            "quantity": quantity, "simulated_cost": cost, "last_mark": decision["entry_price"],
            "market_restricted_for_live_execution": bool(market.get("restricted")),
            "opened_at": _now(), "market_snapshot_sha256": snapshot.get("source_receipt", {}).get("snapshot_sha256"),
            "strategy_id": state["strategy"]["strategy_id"], "status": "open",
            "edge_basis": "market_blind_source_backed_domain_research",
            "research_packet_sha256": research.get("research_packet_sha256"),
            "research_source_count": len(research.get("sources") or []),
            "research_source_domains": research.get("source_domains") or [],
            "research_model": research.get("model"),
            "live_capital": 0.0,
        }
        core["position_id"] = "paper_" + _digest(core)[:20]
        state["positions"].append(core)
        decisions.append(core)
        state["cash"] = round(state["cash"] - stake - cost, 8)
        capacity -= 1

    open_positions = [row for row in state["positions"] if row["status"] == "open"]
    settled = state["settlements"]
    market_value = sum(row["quantity"] * _number(row.get("last_mark")) for row in open_positions)
    account_value = round(state["cash"] + market_value, 8)
    wins = sum(row.get("won") is True for row in settled)
    losses = sum(row.get("won") is False for row in settled)
    tally = {
        "starting_capital": STARTING_CAPITAL,
        "cash": round(state["cash"], 8),
        "open_market_value": round(market_value, 8),
        "account_value": account_value,
        "total_return": round(account_value / STARTING_CAPITAL - 1, 8),
        "open_positions": len(open_positions),
        "total_bets": len(state["positions"]),
        "settled_bets": len(settled),
        "wins": wins, "losses": losses,
        "win_rate": round(wins / len(settled), 8) if settled else None,
        "paper_pnl_realized": round(sum(_number(row.get("paper_pnl")) for row in settled), 8),
        "mean_brier": round(sum(_number(row.get("brier_score")) for row in settled) / len(settled), 8) if settled else None,
    }
    state["updated_at"] = _now()
    state["last_snapshot_sha256"] = snapshot.get("source_receipt", {}).get("snapshot_sha256")
    _atomic(state_path, state)
    result = {
        "schema_version": SCHEMA, "status": "paper_game_active", "passed": True,
        "tally": tally, "new_positions": decisions,
        "open_positions": open_positions, "recent_settlements": settled[-20:],
        "strategy": state["strategy"], "incidents": incidents,
        "gate": {"paper_only": True, "starting_capital": STARTING_CAPITAL,
                 "max_order": STARTING_CAPITAL * MAX_ORDER_FRACTION,
                 "max_daily_risk": STARTING_CAPITAL * MAX_DAILY_RISK_FRACTION,
                 "max_total_exposure": STARTING_CAPITAL * MAX_EXPOSURE_FRACTION,
                 "maximum_time_to_close_hours": MAX_HOLD_HOURS,
                 "maximum_research_age_hours": MAX_RESEARCH_AGE_HOURS,
                 "event_must_not_have_started": True,
                 "minimum_research_quality_version": MIN_RESEARCH_QUALITY_VERSION,
                 "restricted_public_markets_allowed_for_paper_observation": True,
                 "credentials_loaded": False, "orders_submitted": 0,
                 "live_capital_at_risk": 0},
        "claim_boundary": "New positions require market-blind, source-backed event research. This remains a paper experiment; only later settlements can establish whether the researched forecasts add value.",
    }
    result["result_sha256"] = _digest(result)
    _atomic(result_path, result)
    return result


if __name__ == "__main__":
    root = Path(os.getenv("AION_REPO_ROOT", ".")).resolve()
    print(json.dumps(run(
        market_snapshot_path=root / "results/hexcore_prediction_market_intelligence.json",
        research_path=root / "results/hexcore_prediction_market_research.json",
        state_path=root / "results/prediction_market_paper_game_state.json",
        result_path=root / "results/hexcore_prediction_market_paper_game.json",
    ), indent=2))
