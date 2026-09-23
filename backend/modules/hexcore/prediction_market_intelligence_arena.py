"""Governed real-world prediction-market intelligence arena.

Public endpoints are read live. Forecasts and paper orders are frozen before
later settlement. This module never loads trading credentials, submits orders,
funds wallets, proposes resolutions, or submits market suggestions.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping


SCHEMA = "aion.hexcore.prediction_market_intelligence_arena.v1"
POLYMARKET_MARKETS = "https://gamma-api.polymarket.com/markets"
POLYMARKET_GEOBLOCK = "https://polymarket.com/api/geoblock"
KALSHI_MARKETS = "https://external-api.kalshi.com/trade-api/v2/markets"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def _json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            result = json.loads(value)
            return result if isinstance(result, list) else []
        except json.JSONDecodeError:
            return []
    return []


def _fetch_json(url: str, *, params: Mapping[str, Any] | None = None,
                timeout: float = 12.0) -> Any:
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "AION-governed-public-market-research/1.0",
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _poly_market(row: Mapping[str, Any]) -> dict[str, Any] | None:
    outcomes = [str(item).lower() for item in _json_list(row.get("outcomes"))]
    prices = [_number(item, -1) for item in _json_list(row.get("outcomePrices"))]
    yes_index = outcomes.index("yes") if "yes" in outcomes else 0
    probability = prices[yes_index] if yes_index < len(prices) else _number(row.get("lastTradePrice"), -1)
    if not 0 <= probability <= 1:
        return None
    bid = _number(row.get("bestBid"), probability)
    ask = _number(row.get("bestAsk"), probability)
    events = row.get("events") if isinstance(row.get("events"), list) else []
    event = events[0] if events and isinstance(events[0], Mapping) else {}
    event_metadata = event.get("eventMetadata") if isinstance(event.get("eventMetadata"), Mapping) else {}
    return {
        "platform": "polymarket",
        "market_id": str(row.get("conditionId") or row.get("id") or ""),
        "ticker": str(row.get("slug") or row.get("id") or ""),
        "title": str(row.get("question") or "").strip(),
        "event_title": str(event.get("title") or row.get("question") or "").strip(),
        "market_description": str(row.get("description") or "").strip(),
        "market_type": str(row.get("sportsMarketType") or "event_contract"),
        "event_start_time": event.get("startTime") or row.get("gameStartTime") or row.get("endDate"),
        "event_live": bool(event.get("live")),
        "event_ended": bool(event.get("ended")),
        "event_score": event.get("score"),
        "event_period": event.get("period"),
        "platform_context": str(event_metadata.get("context_description") or ""),
        "yes_probability": probability,
        "yes_bid": bid if 0 <= bid <= 1 else probability,
        "yes_ask": ask if 0 <= ask <= 1 else probability,
        "liquidity": _number(row.get("liquidityNum") or row.get("liquidity")),
        "volume_24h": _number(row.get("volume24hr")),
        # ``endDateIso`` may be date-only while ``endDate`` retains the actual
        # event deadline. Prefer the precise timestamp for fast settlement.
        "close_time": row.get("endDate") or row.get("endDateIso"),
        "resolution_source": str(row.get("resolutionSource") or ""),
        "restricted": bool(row.get("restricted")),
        "source_updated": row.get("updatedAt"),
    }


def _kalshi_market(row: Mapping[str, Any]) -> dict[str, Any] | None:
    probability = _number(row.get("last_price_dollars"), -1)
    bid = _number(row.get("yes_bid_dollars"), probability)
    ask = _number(row.get("yes_ask_dollars"), probability)
    if not 0 <= probability <= 1:
        if 0 <= bid <= 1 and 0 <= ask <= 1:
            probability = (bid + ask) / 2
        else:
            return None
    return {
        "platform": "kalshi",
        "market_id": str(row.get("ticker") or ""),
        "ticker": str(row.get("ticker") or ""),
        "title": str(row.get("title") or row.get("subtitle") or "").strip(),
        "event_title": str(row.get("title") or row.get("subtitle") or "").strip(),
        "market_description": str(row.get("rules_primary") or "").strip(),
        "market_type": str(row.get("market_type") or "event_contract"),
        "event_start_time": row.get("open_time") or row.get("expected_expiration_time"),
        "event_live": False,
        "event_ended": False,
        "yes_probability": probability,
        "yes_bid": bid if 0 <= bid <= 1 else probability,
        "yes_ask": ask if 0 <= ask <= 1 else probability,
        "liquidity": _number(row.get("liquidity_dollars")),
        "volume_24h": _number(row.get("volume_24h_fp")),
        "close_time": row.get("close_time") or row.get("expiration_time"),
        "resolution_source": str(row.get("rules_primary") or ""),
        "restricted": False,
        "source_updated": row.get("updated_time"),
    }


def _rank_research_candidate(row: Mapping[str, Any]) -> dict[str, Any]:
    spread = max(0.0, _number(row.get("yes_ask")) - _number(row.get("yes_bid")))
    liquidity = max(0.0, _number(row.get("liquidity")))
    volume = max(0.0, _number(row.get("volume_24h")))
    resolution_ready = bool(str(row.get("resolution_source") or "").strip())
    # This ranks research value, not expected profit. No independent forecast
    # exists at intake, therefore ``trade_edge`` must remain unknown.
    score = math.log1p(liquidity) + 0.5 * math.log1p(volume) - 5 * spread + int(resolution_ready)
    return dict(row) | {
        "spread": spread,
        "resolution_ready": resolution_ready,
        "research_priority_score": round(score, 8),
        "trade_edge": None,
        "action": "research_then_abstain_until_independent_probability",
    }


def paper_decision(*, market: Mapping[str, Any], forecast_probability: float,
                   uncertainty: float, fee_and_slippage: float = 0.02,
                   paper_bankroll: float = 1_000.0, max_fraction: float = 0.01,
                   minimum_robust_edge: float = 0.03) -> dict[str, Any]:
    if not 0 <= forecast_probability <= 1 or not 0 <= uncertainty <= 0.5:
        raise ValueError("invalid forecast or uncertainty")
    yes_ask = _number(market.get("yes_ask"), _number(market.get("yes_probability")))
    yes_bid = _number(market.get("yes_bid"), _number(market.get("yes_probability")))
    robust_yes = forecast_probability - uncertainty - yes_ask - fee_and_slippage
    no_price = 1 - yes_bid
    robust_no = (1 - forecast_probability) - uncertainty - no_price - fee_and_slippage
    best_side, best_edge = max((("yes", robust_yes), ("no", robust_no)), key=lambda item: item[1])
    accepted = best_edge >= minimum_robust_edge and bool(market.get("resolution_ready"))
    fraction = min(max_fraction, max(0.0, best_edge / max(1e-9, 1 - best_edge))) if accepted else 0.0
    stake = round(paper_bankroll * fraction, 2)
    entry_price = yes_ask if best_side == "yes" else no_price
    result = {
        "market_id": market.get("market_id"),
        "platform": market.get("platform"),
        "forecast_probability": forecast_probability,
        "uncertainty": uncertainty,
        "fee_and_slippage": fee_and_slippage,
        "side": best_side if accepted else "abstain",
        "entry_price": round(entry_price, 8) if accepted else None,
        "robust_edge": round(best_edge, 8),
        "paper_stake": stake,
        "live_stake": 0.0,
        "accepted": accepted,
        "committed_at": _now(),
    }
    return result | {"commitment_sha256": _digest(result)}


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def commit_paper_forecast(*, state_path: Path, market: Mapping[str, Any],
                          forecast_probability: float, uncertainty: float,
                          fee_and_slippage: float = .02) -> dict[str, Any]:
    decision = paper_decision(
        market=market, forecast_probability=forecast_probability,
        uncertainty=uncertainty, fee_and_slippage=fee_and_slippage,
    )
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        state = {"schema_version": SCHEMA + ".paper_ledger", "commitments": [], "settlements": []}
    identifier = "prediction_commitment_" + decision["commitment_sha256"][:20]
    record = decision | {
        "commitment_id": identifier,
        "market_title": market.get("title"),
        "market_snapshot_sha256": _digest(dict(market)),
        "status": "pending_settlement" if decision["accepted"] else "abstained",
    }
    existing = next((row for row in state["commitments"]
                     if row["commitment_id"] == identifier), None)
    if existing is None:
        state["commitments"].append(record)
    elif existing != record:
        raise ValueError("commitment collision or mutation")
    state["updated_at"] = _now()
    _atomic_json(state_path, state)
    return record


def score_paper_settlement(*, state_path: Path, commitment_id: str, outcome: int,
                           settlement_source: str, settled_at: str) -> dict[str, Any]:
    if outcome not in {0, 1} or not settlement_source.strip():
        raise ValueError("invalid independent settlement")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    commitment = next((row for row in state.get("commitments") or []
                       if row.get("commitment_id") == commitment_id), None)
    if commitment is None or commitment.get("status") != "pending_settlement":
        raise ValueError("no pending commitment")
    committed_epoch = datetime.fromisoformat(
        str(commitment["committed_at"]).replace("Z", "+00:00")).timestamp()
    settled_epoch = datetime.fromisoformat(str(settled_at).replace("Z", "+00:00")).timestamp()
    if settled_epoch <= committed_epoch:
        raise ValueError("settlement must be later than commitment")
    forecast = _number(commitment["forecast_probability"])
    brier = (forecast - outcome) ** 2
    side_outcome = outcome if commitment["side"] == "yes" else 1 - outcome
    stake = _number(commitment["paper_stake"])
    entry = _number(commitment["entry_price"])
    quantity = stake / entry if entry > 0 else 0.0
    estimated_cost = quantity * _number(commitment.get("fee_and_slippage"))
    net_pnl = round(quantity * side_outcome - stake - estimated_cost, 8)
    settlement = {
        "commitment_id": commitment_id,
        "outcome": outcome,
        "settlement_source": settlement_source.strip(),
        "settled_at": settled_at,
        "brier_score": round(brier, 8),
        "paper_net_pnl": net_pnl,
        "estimated_fees_and_slippage": round(estimated_cost, 8),
        "live_net_pnl": 0.0,
        "independent_outcome_after_commitment": True,
    }
    settlement["settlement_sha256"] = _digest(settlement)
    state["settlements"].append(settlement)
    for row in state["commitments"]:
        if row.get("commitment_id") == commitment_id:
            row["status"] = "settled"
            row["settlement_sha256"] = settlement["settlement_sha256"]
    state["updated_at"] = _now()
    _atomic_json(state_path, state)
    return settlement


def market_proposal_draft(*, platform: str, title: str, resolution_source: str,
                          close_time: str, demand_evidence: str) -> dict[str, Any]:
    if platform not in {"polymarket", "kalshi"}:
        raise ValueError("unsupported platform")
    complete = all(str(value).strip() for value in (title, resolution_source, close_time, demand_evidence))
    route = "community_market_proposal" if platform == "polymarket" else "regulated_market_suggestion"
    draft = {
        "platform": platform,
        "title": title.strip(),
        "resolution_source": resolution_source.strip(),
        "close_time": close_time.strip(),
        "demand_evidence": demand_evidence.strip(),
        "route": route,
        "complete": complete,
        "submitted": False,
        "requires_human_review": True,
    }
    return draft | {"draft_sha256": _digest(draft)}


def assess_live_capital_gate(*, mandate: Mapping[str, Any],
                             performance: Mapping[str, Any],
                             geoblock: Mapping[str, Any]) -> dict[str, Any]:
    """Assess whether AION may prepare (not submit) a live order proposal."""
    bankroll = _number(mandate.get("bankroll"))
    max_order = _number(mandate.get("max_order"))
    max_daily_loss = _number(mandate.get("max_daily_loss"))
    max_total_exposure = _number(mandate.get("max_total_exposure"))
    checks = {
        "owner_approved": mandate.get("owner_approved") is True,
        "account_owner_verified": mandate.get("account_owner_verified") is True,
        "jurisdiction_confirmed": mandate.get("jurisdiction_confirmed") is True,
        "platform_supported": mandate.get("platform") in {"polymarket", "kalshi"},
        "platform_geoblock_clear": geoblock.get("checked") is True and geoblock.get("blocked") is False,
        "per_order_approval": mandate.get("per_order_approval") is True,
        "positive_bankroll": bankroll > 0,
        "order_cap_at_most_one_percent": 0 < max_order <= bankroll * .01,
        "daily_loss_cap_at_most_two_percent": 0 < max_daily_loss <= bankroll * .02,
        "exposure_cap_at_most_five_percent": 0 < max_total_exposure <= bankroll * .05,
        "at_least_one_hundred_settled_forecasts": int(performance.get("settled_forecasts") or 0) >= 100,
        "beats_market_brier_by_one_point": _number(performance.get("brier_advantage")) >= .01,
        "paper_profit_after_all_costs": _number(performance.get("net_return_after_costs")) > 0,
        "paper_drawdown_below_five_percent": 0 <= _number(performance.get("max_drawdown"), 1) <= .05,
    }
    qualified = all(checks.values())
    result = {
        "qualified_for_live_order_proposals": qualified,
        "live_execution_enabled": False,
        "orders_submitted": 0,
        "checks": checks,
        "blockers": [key for key,value in checks.items() if not value],
        "next_authority": "separate owner approval for one exact bounded order" if qualified else "close blockers",
    }
    return result | {"gate_sha256": _digest(result)}


def run(*, output_path: Path | None = None, state_path: Path | None = None,
        fetcher: Callable[..., Any] = _fetch_json, limit: int = 100) -> dict[str, Any]:
    snapshots: list[dict[str, Any]] = []
    incidents: list[dict[str, Any]] = []
    geoblock: dict[str, Any] = {"checked": False, "blocked": None}
    try:
        raw_geo = fetcher(POLYMARKET_GEOBLOCK)
        geoblock = {"checked": True, "blocked": bool(raw_geo.get("blocked")),
                    "country": raw_geo.get("country"), "region": raw_geo.get("region")}
    except Exception as exc:  # fail closed for trading, but public research may continue
        incidents.append({"source": "polymarket_geoblock", "error": type(exc).__name__})
    try:
        rows = fetcher(POLYMARKET_MARKETS, params={"active": "true", "closed": "false",
                                                    "limit": limit, "order": "volume24hr",
                                                    "ascending": "false"})
        snapshots.extend(item for row in (rows or []) if (item := _poly_market(row)))
    except Exception as exc:
        incidents.append({"source": "polymarket", "error": type(exc).__name__})
    try:
        payload = fetcher(KALSHI_MARKETS, params={"limit": limit, "status": "open"})
        snapshots.extend(item for row in (payload.get("markets") or []) if (item := _kalshi_market(row)))
    except Exception as exc:
        incidents.append({"source": "kalshi", "error": type(exc).__name__})
    ranked = sorted((_rank_research_candidate(row) for row in snapshots),
                    key=lambda row: row["research_priority_score"], reverse=True)
    source_receipt = {
        "observed_at": _now(), "market_count": len(ranked),
        "platform_counts": {name: sum(row["platform"] == name for row in ranked)
                            for name in ("polymarket", "kalshi")},
        "snapshot_sha256": _digest(ranked),
    }
    if state_path is None and output_path is not None:
        state_path = output_path.parent / "prediction_market_intelligence_state.json"
    try:
        paper_state = json.loads(state_path.read_text(encoding="utf-8")) if state_path else {}
    except (FileNotFoundError, json.JSONDecodeError):
        paper_state = {}
    commitments = paper_state.get("commitments") or []
    settlements = paper_state.get("settlements") or []
    payload = {
        "schema_version": SCHEMA,
        "status": "live_public_research" if ranked else "public_sources_unavailable",
        "passed": bool(ranked),
        "source_receipt": source_receipt,
        "geographic_eligibility": geoblock,
        "research_candidates": ranked[:25],
        "market_snapshot": ranked,
        "incidents": incidents,
        "paper_ledger": {
            "commitments": len(commitments),
            "pending": sum(row.get("status") == "pending_settlement" for row in commitments),
            "abstained": sum(row.get("status") == "abstained" for row in commitments),
            "settled": len(settlements),
            "net_pnl": round(sum(_number(row.get("paper_net_pnl")) for row in settlements), 8),
            "mean_brier": round(sum(_number(row.get("brier_score")) for row in settlements) / len(settlements), 8) if settlements else None,
        },
        "gate": {
            "public_data_only": True,
            "credentials_loaded": False,
            "orders_submitted": 0,
            "markets_created": 0,
            "market_suggestions_submitted": 0,
            "live_capital_at_risk": 0,
            "paper_trading_enabled": True,
            "live_trading_enabled": False,
            "live_requires_platform_eligibility": True,
            "live_requires_owner_signed_loss_budget": True,
            "live_requires_per_order_approval_during_qualification": True,
        },
        "claim_boundary": (
            "Live public markets were observed. Candidate ranking measures research value, not alpha. "
            "No independent event forecast, profitable edge, live order, market creation or investment "
            "performance is claimed."
        ),
    }
    payload["result_sha256"] = _digest(payload)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = output_path.with_suffix(output_path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(temporary, output_path)
    return payload


if __name__ == "__main__":
    root = Path(os.getenv("AION_REPO_ROOT", ".")).resolve()
    print(json.dumps(run(output_path=root / "results/hexcore_prediction_market_intelligence.json"), indent=2))
