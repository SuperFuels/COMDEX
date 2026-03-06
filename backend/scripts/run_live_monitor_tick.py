# /workspaces/COMDEX/backend/scripts/run_live_monitor_tick.py
from __future__ import annotations

"""
One monitoring tick (feeds -> trigger maps -> alerts).

v3 does:
- load variable_watch for company + period
- load trigger_map for company + period (ONLY this period is mutated)
- backfill trigger_entries[].feed_id from variable_watch by variable_name match
- parse threshold_confirm/early into trigger_entries[].threshold_rule (cross_above/cross_below)
- fetch ECB daily FX rates (spot) for EUR/<CCY> pairs
- maintain strict quarter-to-date averages per FX feed:
    <base_dir>/fx_quarter_avg/<feed_id>/<YYYY-Q#>.json
- optionally compute EWMA-smoothed average (half-life days)
- update ONLY the selected trigger_map in-place (no cross-quarter contamination)
- append alerts to: <base_dir>/alerts/alerts.jsonl

Run:
  python -m backend.scripts.run_live_monitor_tick \
    --base-dir /workspaces/COMDEX/.runtime/equities \
    --company-ref company/ULVR.L \
    --fiscal-period 2026-Q1 \
    --fx-mode ewma \
    --strict-quarter
"""

import argparse
import json
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.modules.aion_equities.feeds.yfinance_commodities import (
    commodity_update_for_feed,
)
# -------------------------
# basic utils
# -------------------------

_ALLOWED_TRIGGER_STATES = {"inactive", "early_watch", "building", "confirmed", "broken"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_segment(value: str) -> str:
    return str(value).replace("/", "_").replace("\\", "_").replace(":", "-").strip()


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


# -------------------------
# quarter helpers
# -------------------------

def _quarter_from_date(d: date) -> str:
    q = ((d.month - 1) // 3) + 1
    return f"{d.year}-Q{q}"


def _strict_quarter_guard(target_period: str, *, now: Optional[datetime] = None) -> None:
    now = now or datetime.now(timezone.utc)
    expected = _quarter_from_date(now.date())
    if str(target_period) != expected:
        raise SystemExit(
            f"STRICT_QUARTER: refusing to run for {target_period} because today is {expected}. "
            f"(Disable --strict-quarter if you intentionally want a non-current quarter.)"
        )


# -------------------------
# threshold rule parsing
# -------------------------

def _parse_threshold_rule(threshold_text: str) -> Optional[str]:
    """
    Converts a human threshold like:
      "quarterly avg EUR/BRL <= 6.0 for 4 consecutive weeks"
      "quarterly avg EUR/USD >= 1.15 for 8 consecutive weeks"
    into tracker rule:
      "cross_below:6.0" or "cross_above:1.15"
    """
    s = str(threshold_text or "").strip()
    if not s:
        return None

    m = re.search(r"(<=|>=|<|>)\s*([0-9]+(?:\.[0-9]+)?)", s)
    if not m:
        return None

    op = m.group(1)
    num = m.group(2)

    if op in ("<", "<="):
        return f"cross_below:{num}"
    if op in (">", ">="):
        return f"cross_above:{num}"
    return None


# -------------------------
# file loading helpers
# -------------------------

def _get_latest_period(company_ref: str, base_dir: Path) -> Optional[str]:
    d = base_dir / "variable_watch" / _safe_segment(company_ref)
    if not d.exists():
        return None
    periods = sorted(p.stem for p in d.glob("*.json"))
    return periods[-1] if periods else None


def _load_variable_watch(company_ref: str, fiscal_period: str, base_dir: Path) -> Dict[str, Any]:
    p = base_dir / "variable_watch" / _safe_segment(company_ref) / f"{_safe_segment(fiscal_period)}.json"
    return _read_json(p)


def _load_trigger_map(company_ref: str, fiscal_period: str, base_dir: Path) -> Dict[str, Any]:
    p = base_dir / "company_trigger_maps" / _safe_segment(company_ref) / f"{_safe_segment(fiscal_period)}.json"
    return _read_json(p)


def _save_trigger_map(payload: Dict[str, Any], base_dir: Path) -> None:
    company_ref = payload["company_ref"]
    fiscal_period = payload["fiscal_period_ref"]
    p = base_dir / "company_trigger_maps" / _safe_segment(company_ref) / f"{_safe_segment(fiscal_period)}.json"
    _write_json(p, payload)


def _var_index_by_name(vars_: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for v in vars_:
        name = str(v.get("name") or "").strip().lower()
        if name:
            out[name] = v
    return out


def _backfill_trigger_feed_ids(
    *,
    trigger_map: Dict[str, Any],
    variables: List[Dict[str, Any]],
) -> Tuple[Dict[str, Any], int]:
    """
    Backfill trigger_entries[].feed_id and trigger_entries[].threshold_rule
    from variable_watch by matching variable_name == variable.name (case-insensitive).

    - feed_id is required for routing
    - threshold_rule is required for state transitions
    """
    idx = _var_index_by_name(variables)
    patched = 0

    entries = trigger_map.get("trigger_entries") or []
    if not isinstance(entries, list):
        return trigger_map, 0

    for t in entries:
        if not isinstance(t, dict):
            continue

        nm = str(t.get("variable_name") or "").strip().lower()
        if not nm:
            continue

        v = idx.get(nm)
        if not v:
            continue

        # 1) feed_id
        if not str(t.get("feed_id") or "").strip():
            fid = str(v.get("feed_id") or "").strip()
            if fid:
                t["feed_id"] = fid
                patched += 1

        # 2) threshold_rule
        if not str(t.get("threshold_rule") or "").strip():
            rule = _parse_threshold_rule(v.get("threshold_confirm")) or _parse_threshold_rule(v.get("threshold_early"))
            if rule:
                t["threshold_rule"] = rule
                patched += 1

    # keep a legacy alias for any older readers that expect "triggers"
    trigger_map["triggers"] = deepcopy(trigger_map.get("trigger_entries") or [])
    return trigger_map, patched


# -------------------------
# ECB FX fetch (spot)
# -------------------------

ECB_XML_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"


def _fetch_text(url: str, timeout_s: int = 15) -> str:
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": "AION/1.0"})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def fetch_ecb_rates() -> Tuple[str, Dict[str, float]]:
    """Returns (as_of_date, rates) where rates are 1 EUR -> <CCY> amounts."""
    import xml.etree.ElementTree as ET

    xml = _fetch_text(ECB_XML_URL)
    root = ET.fromstring(xml)

    cube_time = None
    rates: Dict[str, float] = {}

    for elem in root.iter():
        tag = elem.tag
        if tag.endswith("Cube") and "time" in elem.attrib:
            cube_time = elem.attrib.get("time")
        if tag.endswith("Cube") and "currency" in elem.attrib and "rate" in elem.attrib:
            ccy = str(elem.attrib.get("currency") or "").upper().strip()
            rate = _safe_float(elem.attrib.get("rate"))
            if ccy and rate is not None:
                rates[ccy] = float(rate)

    as_of = cube_time or _utc_now_iso()[:10]
    return as_of, rates


def resolve_fx_spot(feed_id: str, *, ecb_rates: Dict[str, float]) -> Optional[float]:
    """
    Supports feed_ids like:
      eur_usd_quarterly_avg
      eur_brl_quarterly_avg

    Spot mapping (1 EUR -> CCY).
    """
    fid = str(feed_id).strip().lower()
    if not fid.startswith("eur_"):
        return None
    parts = fid.split("_")
    if len(parts) < 2:
        return None
    ccy = parts[1].upper()
    return ecb_rates.get(ccy)


# -------------------------
# FX quarter avg store + EWMA
# -------------------------

def _fx_store_path(base_dir: Path, feed_id: str, fiscal_period: str) -> Path:
    return base_dir / "fx_quarter_avg" / _safe_segment(feed_id) / f"{_safe_segment(fiscal_period)}.json"


def _alpha_from_half_life(days: float) -> float:
    # alpha = 1 - 0.5^(1/half_life)
    if days <= 0:
        raise ValueError("half_life_days must be > 0")
    return 1.0 - pow(0.5, 1.0 / days)


def _ewma(values: List[float], alpha: float) -> Optional[float]:
    if not values:
        return None
    v = None
    for x in values:
        if v is None:
            v = float(x)
        else:
            v = (alpha * float(x)) + ((1.0 - alpha) * v)
    return v


def _load_fx_store(base_dir: Path, feed_id: str, fiscal_period: str) -> Dict[str, Any]:
    p = _fx_store_path(base_dir, feed_id, fiscal_period)
    if not p.exists():
        return {
            "feed_id": feed_id,
            "fiscal_period_ref": fiscal_period,
            "samples": [],  # [{as_of_date, spot}]
            "running_avg": None,
            "ewma_avg": None,
            "sample_count": 0,
            "last_updated_at": None,
            "generated_by": "backend.scripts.run_live_monitor_tick",
        }
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {
            "feed_id": feed_id,
            "fiscal_period_ref": fiscal_period,
            "samples": [],
            "running_avg": None,
            "ewma_avg": None,
            "sample_count": 0,
            "last_updated_at": None,
            "generated_by": "backend.scripts.run_live_monitor_tick",
        }


def _save_fx_store(base_dir: Path, feed_id: str, fiscal_period: str, payload: Dict[str, Any]) -> None:
    p = _fx_store_path(base_dir, feed_id, fiscal_period)
    _write_json(p, payload)


def _upsert_fx_sample(
    *,
    base_dir: Path,
    feed_id: str,
    fiscal_period: str,
    as_of_date: str,  # YYYY-MM-DD
    spot: float,
    ewma_half_life_days: float,
    write: bool,
) -> Dict[str, Any]:
    """
    Store one sample per day per feed_id per quarter.
    Compute running_avg and ewma_avg across all quarter samples.
    """
    st = _load_fx_store(base_dir, feed_id, fiscal_period)
    samples = st.get("samples") if isinstance(st.get("samples"), list) else []

    # de-dupe by as_of_date
    by_day: Dict[str, float] = {}
    for s in samples:
        if not isinstance(s, dict):
            continue
        d = str(s.get("as_of_date") or "").strip()
        v = _safe_float(s.get("spot"))
        if d and v is not None:
            by_day[d] = float(v)

    by_day[str(as_of_date)] = float(spot)

    # rebuild ordered
    days_sorted = sorted(by_day.keys())
    series = [by_day[d] for d in days_sorted]

    running_avg = (sum(series) / len(series)) if series else None
    alpha = _alpha_from_half_life(float(ewma_half_life_days))
    ewma_avg = _ewma(series, alpha)

    st["feed_id"] = feed_id
    st["fiscal_period_ref"] = fiscal_period
    st["samples"] = [{"as_of_date": d, "spot": by_day[d]} for d in days_sorted]
    st["sample_count"] = len(series)
    st["running_avg"] = running_avg
    st["ewma_avg"] = ewma_avg
    st["last_updated_at"] = f"{as_of_date}T00:00:00Z"
    st["generated_by"] = "backend.scripts.run_live_monitor_tick"

    if write:
        _save_fx_store(base_dir, feed_id, fiscal_period, st)

    return st


# -------------------------
# trigger state update (local, period-isolated)
# -------------------------

def _infer_trigger_state(
    *,
    current_state: str,
    threshold_rule: str,
    previous_value: Any,
    value: Any,
) -> str:
    """
    Same semantics as LiveVariableTracker, but we run it locally so we ONLY mutate
    the single trigger_map file for the requested fiscal_period.
    """
    current_state = str(current_state or "inactive").strip().lower()
    if current_state not in _ALLOWED_TRIGGER_STATES:
        current_state = "inactive"

    rule = str(threshold_rule or "").strip().lower()
    prev_num = _safe_float(previous_value)
    value_num = _safe_float(value)

    if rule in {"", "manual"}:
        return current_state

    if rule.startswith("cross_above:"):
        target = _safe_float(rule.split(":", 1)[1])
        if target is not None and value_num is not None:
            if value_num >= target:
                return "confirmed"
            if prev_num is not None and prev_num < target and value_num < target:
                return "building"
            return "inactive"

    if rule.startswith("cross_below:"):
        target = _safe_float(rule.split(":", 1)[1])
        if target is not None and value_num is not None:
            if value_num <= target:
                return "confirmed"
            if prev_num is not None and prev_num > target and value_num > target:
                return "building"
            return "inactive"

    if rule == "two_consecutive_improvements":
        if prev_num is None or value_num is None:
            return "early_watch"
        if value_num > prev_num:
            if current_state in {"early_watch", "building"}:
                return "confirmed"
            return "building"
        if value_num < prev_num:
            return "broken"
        return current_state

    if rule == "two_consecutive_deteriorations":
        if prev_num is None or value_num is None:
            return "early_watch"
        if value_num < prev_num:
            if current_state in {"early_watch", "building"}:
                return "confirmed"
            return "building"
        if value_num > prev_num:
            return "broken"
        return current_state

    return current_state


def _apply_feed_to_trigger_map(
    *,
    trigger_map: Dict[str, Any],
    feed_id: str,
    value: float,
    as_of: str,
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Mutates trigger_map in-place:
      - updates any trigger_entries where trigger.feed_id == feed_id
      - appends update_history
      - returns an event shape similar to LiveVariableTracker
    """
    trigger_map_id = str(trigger_map.get("company_trigger_map_id") or "").strip()
    company_ref = str(trigger_map.get("company_ref") or "").strip()

    entries = trigger_map.get("trigger_entries") or []
    if not isinstance(entries, list):
        entries = []

    updates: List[Dict[str, Any]] = []
    changed = False

    for t in entries:
        if not isinstance(t, dict):
            continue

        if str(t.get("feed_id") or "").strip() != str(feed_id).strip():
            continue

        previous_value = t.get("latest_value")
        previous_state = t.get("current_state", "inactive")

        new_state = _infer_trigger_state(
            current_state=previous_state,
            threshold_rule=str(t.get("threshold_rule") or ""),
            previous_value=previous_value,
            value=value,
        )

        t["latest_value"] = float(value)
        t["last_updated_at"] = str(as_of)
        t["current_state"] = str(new_state)

        t.setdefault("update_history", []).append(
            {
                "as_of": str(as_of),
                "feed_id": str(feed_id),
                "value": float(value),
                "previous_state": str(previous_state),
                "new_state": str(new_state),
                "metadata": deepcopy(metadata),
            }
        )

        changed = True
        updates.append(
            {
                "company_ref": company_ref,
                "trigger_map_id": trigger_map_id,
                "trigger_id": t.get("trigger_id"),
                "feed_id": str(feed_id),
                "value": float(value),
                "state": str(new_state),
            }
        )

    # keep a legacy alias for any older readers that expect "triggers"
    trigger_map["triggers"] = deepcopy(trigger_map.get("trigger_entries") or [])

    return {
        "changed": changed,
        "event": {
            "feed_id": str(feed_id),
            "as_of": str(as_of),
            "value": float(value),
            "metadata": deepcopy(metadata),
            "affected_trigger_maps": [trigger_map_id] if updates else [],
            "updates": updates,
        },
    }


# -------------------------
# ticks
# -------------------------

@dataclass
class FeedTick:
    feed_id: str
    value: float
    as_of: str
    meta: Dict[str, Any]


def _choose_fx_value(mode: str, *, spot: float, running_avg: Optional[float], ewma_avg: Optional[float]) -> float:
    m = str(mode or "spot").strip().lower()
    if m == "avg":
        return float(running_avg if running_avg is not None else spot)
    if m == "ewma":
        return float(ewma_avg if ewma_avg is not None else (running_avg if running_avg is not None else spot))
    return float(spot)


def _commodity_tick_for_feed(feed_id: str) -> Optional[Dict[str, Any]]:
    """
    Yahoo/yfinance commodity fetch.

    Returns:
      {
        feed_id,
        current_value,
        current_value_as_of (YYYY-MM-DD),
        unit,
        currency,
        target_currency (optional),
        source
      }
    """
    fid = str(feed_id or "").strip()

    # Map feed_id -> Yahoo ticker + expectations
    # NOTE: Palm oil futures on Yahoo can be MYR-denominated (common).
    # We keep currency from yfinance if available, and set target_currency="USD" so
    # run_live_monitor_tick can convert using ECB cross rates.
    mapping = {
        "palm_oil_fcpo_price": {
            "ticker": "KO=F",          # Palm Oil Futures (Yahoo)
            "unit": "tonne",           # treat as per-tonne style
            "target_currency": "USD",  # convert if needed so your thresholds stay USD-based
        },
        "brent_crude_daily": {
            "ticker": "BZ=F",          # Brent Crude Oil Futures (Yahoo)
            "unit": "barrel",
            "target_currency": "USD",
        },
    }

    cfg = mapping.get(fid)
    if not cfg:
        return None

    try:
        import yfinance as yf
    except Exception:
        # yfinance not installed
        return None

    try:
        tkr = yf.Ticker(cfg["ticker"])
        hist = tkr.history(period="10d")
        if hist is None or getattr(hist, "empty", True):
            return None

        latest = hist.iloc[-1]
        close = _safe_float(latest.get("Close"))
        if close is None:
            return None

        dt = hist.index[-1]
        as_of_date = dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(dt)[:10]

        # Try to get currency from Yahoo metadata (best-effort)
        ccy = None
        try:
            info = getattr(tkr, "fast_info", None) or {}
            ccy = info.get("currency") or None
        except Exception:
            ccy = None

        if not ccy:
            try:
                info = tkr.info or {}
                ccy = info.get("currency") or None
            except Exception:
                ccy = None

        ccy = str(ccy).upper().strip() if ccy else None

        # Units: keep simple but consistent
        # - Brent: USD/barrel
        # - Palm: MYR/tonne or USD/tonne depending on Yahoo
        unit = cfg.get("unit") or "other"
        target_ccy = str(cfg.get("target_currency") or "").strip().upper() or None

        return {
            "feed_id": fid,
            "current_value": float(close),
            "current_value_as_of": as_of_date,
            "unit": unit,
            "currency": ccy,                 # what Yahoo says (often MYR for palm oil)
            "target_currency": target_ccy,   # what we want for thresholds (USD)
            "source": f"yfinance/{cfg['ticker']}",
        }
    except Exception:
        return None


def build_feed_ticks_from_variables(
    *,
    variables: List[Dict[str, Any]],
    base_dir: Path,
    fiscal_period: str,
    fx_mode: str,
    ewma_half_life_days: float,
    write_fx_store: bool,
) -> List[FeedTick]:
    """
    Builds feed ticks for:
      - FX variables (ECB spot -> quarter avg store -> chosen mode spot/avg/ewma)
      - Commodity variables (Yahoo/yfinance via commodity_update_for_feed)

    Notes:
      - Commodities do NOT use the FX quarter-avg store.
      - For commodities, we optionally convert raw currency -> target_currency (USD)
        using ECB cross rates via EUR (if available) so USD thresholds stay valid.
      - We keep metadata rich so debugging is easy.
    """
    ecb_as_of, ecb_rates = fetch_ecb_rates()

    ticks: List[FeedTick] = []

    for v in variables:
        fid = str(v.get("feed_id") or "").strip()
        if not fid:
            continue

        cat = str(v.get("category") or "").strip().lower()

        # -------------------------
        # FX
        # -------------------------
        if cat == "fx":
            spot = resolve_fx_spot(fid, ecb_rates=ecb_rates)
            if spot is None:
                continue

            fx_state = _upsert_fx_sample(
                base_dir=base_dir,
                feed_id=fid,
                fiscal_period=fiscal_period,
                as_of_date=ecb_as_of,
                spot=float(spot),
                ewma_half_life_days=float(ewma_half_life_days),
                write=write_fx_store,
            )

            running_avg = _safe_float(fx_state.get("running_avg"))
            ewma_avg = _safe_float(fx_state.get("ewma_avg"))
            chosen = _choose_fx_value(
                fx_mode,
                spot=float(spot),
                running_avg=running_avg,
                ewma_avg=ewma_avg,
            )

            ticks.append(
                FeedTick(
                    feed_id=fid,
                    value=float(chosen),
                    as_of=f"{ecb_as_of}T00:00:00Z",
                    meta={
                        "source": "ecb",
                        "kind": "fx_quarter_avg",
                        "spot": float(spot),
                        "running_avg": running_avg,
                        "ewma_avg": ewma_avg,
                        "sample_count": int(fx_state.get("sample_count") or 0),
                        "fx_mode": str(fx_mode),
                        "quarter": str(fiscal_period),
                    },
                )
            )
            continue

        # -------------------------
        # COMMODITY (Yahoo/yfinance) + optional FX conversion
        # -------------------------
        if cat == "commodity":
            upd = commodity_update_for_feed(fid)
            if not upd:
                continue

            raw_val = _safe_float(upd.get("current_value"))
            as_of_date = str(upd.get("current_value_as_of") or "").strip()  # YYYY-MM-DD
            if raw_val is None or not as_of_date:
                continue

            raw_ccy = str(upd.get("currency") or "").strip().upper() or None
            target_ccy = str(upd.get("target_currency") or "").strip().upper() or None

            converted_val: Optional[float] = None
            conversion_used: Optional[Dict[str, Any]] = None

            # Convert raw_ccy -> target_ccy using ECB cross via EUR:
            # ECB gives 1 EUR -> USD and 1 EUR -> MYR etc.
            # target_per_raw = (target_per_EUR) / (raw_per_EUR)
            if raw_ccy and target_ccy and raw_ccy != target_ccy:
                eur_to_raw = _safe_float(ecb_rates.get(raw_ccy))
                eur_to_target = _safe_float(ecb_rates.get(target_ccy))
                if eur_to_raw is not None and eur_to_target is not None and eur_to_raw > 0:
                    target_per_raw = float(eur_to_target) / float(eur_to_raw)
                    converted_val = float(raw_val) * target_per_raw
                    conversion_used = {
                        "method": "ecb_cross_via_eur",
                        "raw_ccy": raw_ccy,
                        "target_ccy": target_ccy,
                        "eur_to_raw": float(eur_to_raw),
                        "eur_to_target": float(eur_to_target),
                        "target_per_raw": float(target_per_raw),
                        "as_of": ecb_as_of,
                    }

            final_val = float(converted_val) if converted_val is not None else float(raw_val)
            final_ccy = target_ccy if converted_val is not None else raw_ccy

            ticks.append(
                FeedTick(
                    feed_id=fid,
                    value=float(final_val),
                    as_of=f"{as_of_date}T00:00:00Z",
                    meta={
                        "source": "yfinance",
                        "kind": "commodity_close",
                        "raw_close": float(raw_val),
                        "raw_currency": raw_ccy,
                        "value_currency": final_ccy,
                        "conversion": conversion_used,
                        "raw": deepcopy(upd),
                    },
                )
            )
            continue

        continue

    uniq: Dict[str, FeedTick] = {}
    for t in ticks:
        uniq[t.feed_id] = t
    return list(uniq.values())


def run_tick(
    *,
    base_dir: Path,
    company_ref: str,
    fiscal_period: str,
    dry_run: bool,
    fx_mode: str,
    ewma_half_life_days: float,
    strict_quarter: bool,
) -> Dict[str, Any]:
    now_iso = _utc_now_iso()

    if strict_quarter:
        _strict_quarter_guard(fiscal_period)

    vw = _load_variable_watch(company_ref, fiscal_period, base_dir)
    variables = vw.get("variables") or []

    # Load ONLY this quarter's trigger map (we will ONLY mutate/save this file)
    tmap = _load_trigger_map(company_ref, fiscal_period, base_dir)

    # backfill feed_id + threshold_rule into trigger map file
    tmap, patched = _backfill_trigger_feed_ids(trigger_map=tmap, variables=variables)
    if patched and not dry_run:
        _save_trigger_map(tmap, base_dir)

    ticks = build_feed_ticks_from_variables(
        variables=variables,
        base_dir=base_dir,
        fiscal_period=fiscal_period,
        fx_mode=fx_mode,
        ewma_half_life_days=ewma_half_life_days,
        write_fx_store=(not dry_run),
    )

    updates: List[Dict[str, Any]] = []
    trigger_map_changed = False

    for t in ticks:
        if dry_run:
            updates.append(
                {"feed_id": t.feed_id, "value": t.value, "as_of": t.as_of, "metadata": t.meta, "dry_run": True}
            )
            continue

        res = _apply_feed_to_trigger_map(
            trigger_map=tmap,
            feed_id=t.feed_id,
            value=t.value,
            as_of=t.as_of,
            metadata=t.meta,
        )
        trigger_map_changed = trigger_map_changed or bool(res.get("changed"))
        ev = res.get("event") or {}
        updates.append(ev)

        # alerts for confirmed/broken (ONLY for this quarter's trigger map)
        for u in ev.get("updates") or []:
            st = str(u.get("state") or "").strip().lower()
            if st in {"confirmed", "broken"}:
                _append_jsonl(
                    base_dir / "alerts" / "alerts.jsonl",
                    {
                        "as_of": ev.get("as_of"),
                        "company_ref": u.get("company_ref"),
                        "trigger_map_id": u.get("trigger_map_id"),
                        "trigger_id": u.get("trigger_id"),
                        "feed_id": u.get("feed_id"),
                        "value": u.get("value"),
                        "state": u.get("state"),
                        "kind": "trigger_state",
                        "generated_by": "backend.scripts.run_live_monitor_tick",
                    },
                )

    if trigger_map_changed and not dry_run:
        _save_trigger_map(tmap, base_dir)

    return {
        "ok": True,
        "company_ref": company_ref,
        "fiscal_period_ref": fiscal_period,
        "now": now_iso,
        "variable_count": len(variables),
        "ticks_fetched": len(ticks),
        "trigger_feed_id_backfilled": patched,
        "fx_mode": fx_mode,
        "ewma_half_life_days": float(ewma_half_life_days),
        "updates": updates,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-dir", default="/workspaces/COMDEX/.runtime/equities")
    ap.add_argument("--company-ref", required=True)
    ap.add_argument("--fiscal-period", default=None)
    ap.add_argument("--dry-run", action="store_true")

    ap.add_argument("--fx-mode", default="spot", choices=["spot", "avg", "ewma"])
    ap.add_argument("--ewma-half-life-days", type=float, default=14.0)

    # strict quarter = refuse to run for a quarter that isn't "today's quarter"
    ap.add_argument("--strict-quarter", action="store_true")

    args = ap.parse_args()

    base_dir = Path(str(args.base_dir)).resolve()
    company_ref = str(args.company_ref).strip()

    fiscal_period = str(args.fiscal_period).strip() if args.fiscal_period else ""
    if not fiscal_period:
        fiscal_period = _get_latest_period(company_ref, base_dir) or ""
    if not fiscal_period:
        raise SystemExit(f"No variable_watch periods found for {company_ref} under {base_dir}")

    out = run_tick(
        base_dir=base_dir,
        company_ref=company_ref,
        fiscal_period=fiscal_period,
        dry_run=bool(args.dry_run),
        fx_mode=str(args.fx_mode),
        ewma_half_life_days=float(args.ewma_half_life_days),
        strict_quarter=bool(args.strict_quarter),
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()