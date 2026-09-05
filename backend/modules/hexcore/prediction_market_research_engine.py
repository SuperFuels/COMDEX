"""Source-backed, market-blind research for the AION paper prediction game.

The researcher never receives the market price. It uses current web evidence to
produce an independently frozen probability and uncertainty interval. A paper
trade may consume only a packet that passes the evidence and timing gates.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

SCHEMA = "aion.hexcore.prediction_market_research.v2"
RESEARCH_QUALITY_VERSION = 2
DEFAULT_MODEL = "gpt-5-mini"
MAX_RESEARCH_PER_UTC_DAY = 10
MAX_NEW_RESEARCH_PER_CYCLE = 3
RESEARCH_REFRESH_HOURS = 6
MIN_INDEPENDENT_SOURCES = 3
MIN_SOURCE_DOMAINS = 2


def _valid_openai_key(value: Any) -> str:
    match = re.search(r"(?:sk|sess)-[A-Za-z0-9_-]{30,}", str(value or ""))
    return match.group(0) if match and match.group(0).isascii() else ""


def _load_research_key() -> str:
    repo_root = Path(__file__).resolve().parents[3]
    # Prefer the repository's intentionally configured credential over a stale
    # inherited shell value. Never return or serialize this secret downstream.
    for path in (repo_root / ".env.local", repo_root / "backend/.env.local", repo_root / ".env"):
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip().removeprefix("export ").strip()
            key, separator, value = line.partition("=")
            if separator and key.strip() == "OPENAI_API_KEY":
                candidate = _valid_openai_key(value)
                if candidate:
                    return candidate
    candidate = _valid_openai_key(os.getenv("OPENAI_API_KEY", ""))
    if candidate:
        return candidate
    raise RuntimeError("VALID_OPENAI_RESEARCH_KEY_UNAVAILABLE")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temp.read_text(encoding="utf-8"))
    os.replace(temp, path)


def _epoch(value: Any) -> float | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


DISALLOWED_SOURCE_FRAGMENTS = (
    "bet", "odds", "gambl", "polymarket", "kalshi", "smarkets", "predictz",
    "soccerpunter", "tipmanager", "tips.gg", "reddit.com",
)


def _normal_url(value: str) -> str:
    parsed = urlparse(value)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")


def _response_sources(response: Any, selected: list[Mapping[str, Any]]) -> list[dict[str, str]]:
    payload = response.model_dump() if hasattr(response, "model_dump") else dict(response)
    discovered: dict[str, dict[str, str]] = {}
    for item in payload.get("output") or []:
        action = item.get("action") if isinstance(item, Mapping) else None
        for source in (action or {}).get("sources") or []:
            url = str(source.get("url") or "").strip()
            domain = urlparse(url).netloc.lower().removeprefix("www.")
            if not url or not domain:
                continue
            discovered[_normal_url(url)] = {
                "url": url,
                "domain": domain,
                "title": str(source.get("title") or domain),
            }
    unique: dict[str, dict[str, str]] = {}
    for source in selected:
        requested = _normal_url(str(source.get("url") or ""))
        verified = discovered.get(requested)
        if not verified:
            continue
        domain = verified["domain"]
        if any(fragment in domain for fragment in DISALLOWED_SOURCE_FRAGMENTS):
            continue
        unique[requested] = verified | {
            "claim": str(source.get("claim") or ""),
            "source_type": str(source.get("source_type") or ""),
        }
    return list(unique.values())


def _openai_web_forecast(market: Mapping[str, Any], *, model: str) -> dict[str, Any]:
    from openai import OpenAI

    api_key = _load_research_key()
    # Deliberately omit every market price, spread, volume and crowd forecast.
    evidence_subject = {
        "question": market.get("title"),
        "event": market.get("event_title") or market.get("title"),
        "market_type": market.get("market_type"),
        "rules": market.get("market_description"),
        "scheduled_start": market.get("event_start_time"),
        "scheduled_close": market.get("close_time"),
        "resolution_source": market.get("resolution_source"),
    }
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "domain": {"type": "string"},
            "probability_yes": {"type": "number", "minimum": 0, "maximum": 1},
            "uncertainty": {"type": "number", "minimum": 0.05, "maximum": 0.35},
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
            "base_rate": {"type": "string"},
            "evidence_for": {"type": "array", "items": {"type": "string"}},
            "evidence_against": {"type": "array", "items": {"type": "string"}},
            "key_variables": {"type": "array", "items": {"type": "string"}},
            "missing_information": {"type": "array", "items": {"type": "string"}},
            "reasoning_summary": {"type": "string"},
            "sources_used": {"type": "array", "items": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "title": {"type": "string"}, "url": {"type": "string"},
                    "claim": {"type": "string"},
                    "source_type": {"type": "string", "enum": [
                        "primary_official", "statistics_database", "independent_reporting"
                    ]},
                },
                "required": ["title", "url", "claim", "source_type"],
            }},
            "abstain": {"type": "boolean"},
            "abstain_reason": {"type": "string"},
        },
        "required": ["domain", "probability_yes", "uncertainty", "confidence", "base_rate",
                     "evidence_for", "evidence_against", "key_variables", "missing_information",
                     "reasoning_summary", "sources_used", "abstain", "abstain_reason"],
    }
    prompt = f"""You are AION's independent prediction researcher. Research the event below using current web sources.

Hard rules:
- Do not search for, cite, infer from, or mention Polymarket, Kalshi, betting odds, market prices, trader consensus, prediction sites, tip sites, or bookmaker odds.
- Build a probability from domain fundamentals: historical base rates, current official facts, recent form/data, participants, injuries/lineups where relevant, incentives, timing, and contrary evidence.
- Prefer primary official sources and high-quality independent reporting. Resolve contradictions.
- Use at least three sources across at least two domains. Include at least one primary official or statistics source and one established independent news source. Put only sources actually used into sources_used. If this is impossible, abstain.
- The event must not already have started. If it has started or live information leaks the result, abstain.
- State both evidence for and evidence against. Do not invent missing facts.
- uncertainty is an absolute probability margin. Use at least 0.05 and increase it for weak or incomplete evidence.
- Return a market-blind probability for YES. This forecast will be frozen before any price comparison.

Event packet:
{json.dumps(evidence_subject, indent=2)}"""
    client = OpenAI(api_key=api_key, timeout=90)
    response = client.responses.create(
        model=model,
        tools=[{"type": "web_search", "search_context_size": "high"}],
        include=["web_search_call.action.sources"],
        input=prompt,
        text={"format": {"type": "json_schema", "name": "independent_forecast",
                         "strict": True, "schema": schema}},
        store=False,
    )
    forecast = json.loads(response.output_text)
    return {
        "forecast": forecast,
        "sources": _response_sources(response, list(forecast.get("sources_used") or [])),
        "provider": "openai_responses_web_search",
        "model": model,
        "response_id": getattr(response, "id", None),
        "usage": (response.usage.model_dump() if getattr(response, "usage", None) else {}),
    }


def _candidate(market: Mapping[str, Any], now_epoch: float) -> bool:
    close = _epoch(market.get("close_time"))
    start = _epoch(market.get("event_start_time")) or close
    bid, ask = market.get("yes_bid"), market.get("yes_ask")
    try:
        book_ok = 0 < float(bid) <= float(ask) < 1 and float(ask) - float(bid) <= .06
    except (TypeError, ValueError):
        book_ok = False
    return bool(
        book_ok
        and market.get("resolution_ready")
        and close and now_epoch < close <= now_epoch + 24 * 3600
        and start and start > now_epoch + 10 * 60
        and not market.get("event_live")
        and not market.get("event_ended")
    )


def _validated_packet(market: Mapping[str, Any], research: Mapping[str, Any],
                      snapshot_sha: str) -> dict[str, Any]:
    forecast = research.get("forecast") or {}
    sources = list(research.get("sources") or [])
    domains = sorted({str(row.get("domain") or "") for row in sources if row.get("domain")})
    probability = float(forecast.get("probability_yes", math.nan))
    uncertainty = float(forecast.get("uncertainty", math.nan))
    evidence_for = list(forecast.get("evidence_for") or [])
    evidence_against = list(forecast.get("evidence_against") or [])
    blockers = []
    if len(sources) < MIN_INDEPENDENT_SOURCES:
        blockers.append("fewer_than_three_independent_sources")
    if len(domains) < MIN_SOURCE_DOMAINS:
        blockers.append("fewer_than_two_source_domains")
    if not math.isfinite(probability) or not 0 <= probability <= 1:
        blockers.append("invalid_probability")
    if not math.isfinite(uncertainty) or not .05 <= uncertainty <= .35:
        blockers.append("invalid_uncertainty")
    if not evidence_for or not evidence_against:
        blockers.append("one_sided_analysis")
    source_types = {str(row.get("source_type") or "") for row in sources}
    if not source_types.intersection({"primary_official", "statistics_database"}):
        blockers.append("no_authoritative_or_statistical_source")
    if "independent_reporting" not in source_types:
        blockers.append("no_independent_reporting_source")
    if forecast.get("abstain"):
        blockers.append("researcher_abstained")
    core = {
        "schema_version": SCHEMA + ".packet",
        "research_quality_version": RESEARCH_QUALITY_VERSION,
        "market_id": market.get("market_id"),
        "platform": market.get("platform"),
        "title": market.get("title"),
        "event_title": market.get("event_title"),
        "market_snapshot_sha256": snapshot_sha,
        "researched_at": _now(),
        "independent_from_market_price": True,
        "market_price_disclosed_to_researcher": False,
        "probability_yes": probability if math.isfinite(probability) else None,
        "uncertainty": uncertainty if math.isfinite(uncertainty) else None,
        "confidence": forecast.get("confidence"),
        "base_rate": forecast.get("base_rate"),
        "evidence_for": evidence_for,
        "evidence_against": evidence_against,
        "key_variables": forecast.get("key_variables") or [],
        "missing_information": forecast.get("missing_information") or [],
        "reasoning_summary": forecast.get("reasoning_summary"),
        "abstain_reason": forecast.get("abstain_reason"),
        "sources": sources,
        "source_domains": domains,
        "provider": research.get("provider"),
        "model": research.get("model"),
        "response_id": research.get("response_id"),
        "usage": research.get("usage") or {},
        "blockers": blockers,
        "usable_for_paper_decision": not blockers,
    }
    core["research_packet_sha256"] = _digest(core)
    return core


def run(*, market_snapshot_path: Path, state_path: Path, result_path: Path,
        forecaster: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
        model: str | None = None, max_new_research: int = MAX_NEW_RESEARCH_PER_CYCLE) -> dict[str, Any]:
    snapshot = json.loads(market_snapshot_path.read_text(encoding="utf-8"))
    markets = snapshot.get("market_snapshot") or []
    snapshot_sha = str((snapshot.get("source_receipt") or {}).get("snapshot_sha256") or "")
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        state = {"schema_version": SCHEMA + ".state", "packets": [], "incidents": []}
    today = _now()[:10]
    researched_today = sum(str(row.get("researched_at", ""))[:10] == today
                           for row in state.get("packets") or [])
    allowance = max(0, min(max_new_research, MAX_RESEARCH_PER_UTC_DAY - researched_today))
    now_epoch = datetime.now(timezone.utc).timestamp()
    known = {
        str(row.get("market_id"))
        for row in state.get("packets") or []
        if int(row.get("research_quality_version") or 0) >= RESEARCH_QUALITY_VERSION
        and _epoch(row.get("researched_at")) is not None
        and now_epoch - float(_epoch(row.get("researched_at"))) <= RESEARCH_REFRESH_HOURS * 3600
    }
    candidates = [row for row in markets if str(row.get("market_id")) not in known
                  and _candidate(row, now_epoch)]
    candidates.sort(key=lambda row: float(row.get("research_priority_score") or 0), reverse=True)
    created = []
    incidents = []
    selected_model = model or os.getenv("AION_PREDICTION_RESEARCH_MODEL", DEFAULT_MODEL)
    for market in candidates[:allowance]:
        try:
            raw = dict(forecaster(market) if forecaster else _openai_web_forecast(market, model=selected_model))
            packet = _validated_packet(market, raw, snapshot_sha)
            state.setdefault("packets", []).append(packet)
            created.append(packet)
        except Exception as exc:
            incident = {"market_id": market.get("market_id"), "error": type(exc).__name__,
                        "detail": str(exc)[:300], "at": _now()}
            state.setdefault("incidents", []).append(incident)
            incidents.append(incident)
    state["updated_at"] = _now()
    _atomic(state_path, state)
    all_packets = list(state.get("packets") or [])
    quality_packets = [row for row in all_packets
                       if int(row.get("research_quality_version") or 0) >= RESEARCH_QUALITY_VERSION]
    legacy_packets = [row for row in all_packets
                      if int(row.get("research_quality_version") or 0) < RESEARCH_QUALITY_VERSION]
    usable = [row for row in quality_packets
              if row.get("usable_for_paper_decision")
              and int(row.get("research_quality_version") or 0) >= RESEARCH_QUALITY_VERSION]
    result = {
        "schema_version": SCHEMA,
        "status": "source_backed_research_active",
        "passed": not incidents,
        "created_packets": created,
        "research_packets": usable,
        "summary": {
            "candidates_available": len(candidates),
            "researched_today": researched_today + len(created),
            "daily_research_cap": MAX_RESEARCH_PER_UTC_DAY,
            "total_packets": len(all_packets),
            "current_quality_packets": len(quality_packets),
            "legacy_packets_excluded": len(legacy_packets),
            "usable_packets": len(usable),
            "abstained_or_blocked": len(quality_packets) - len(usable),
            "api_calls_this_cycle": len(created),
        },
        "incidents": incidents,
        "gate": {"market_price_hidden_from_researcher": True, "minimum_sources": 3,
                 "minimum_source_domains": 2, "event_must_not_have_started": True,
                 "research_refresh_hours": RESEARCH_REFRESH_HOURS,
                 "paper_only": True, "orders_submitted": 0, "live_capital_at_risk": 0},
        "claim_boundary": "A source-backed forecast is evidence of analysis, not proof of a profitable edge. Only later settlements can measure forecasting skill.",
    }
    result["result_sha256"] = _digest(result)
    _atomic(result_path, result)
    return result


if __name__ == "__main__":
    root = Path(os.getenv("AION_REPO_ROOT", ".")).resolve()
    print(json.dumps(run(
        market_snapshot_path=root / "results/hexcore_prediction_market_intelligence.json",
        state_path=root / "results/prediction_market_research_state.json",
        result_path=root / "results/hexcore_prediction_market_research.json",
    ), indent=2))
