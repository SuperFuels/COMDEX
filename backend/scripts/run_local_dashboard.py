# backend/scripts/run_local_dashboard.py
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

# NOTE:
# - This file must be generic for ALL companies/tickers.
# - No ULVR-specific feed IDs in the backend response layer.
# - Dashboard rows should not depend on variable_watch existing;
#   if variable_watch is missing, we still render rows from trigger_map.

# -------------------------
# utils
# -------------------------

def _safe_segment(value: str) -> str:
    return str(value).replace("/", "_").replace("\\", "_").replace(":", "-").strip()


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _tail_jsonl(path: Path, n: int = 800) -> List[Dict[str, Any]]:
    """
    Read last N jsonl lines into dicts. Best-effort; skips malformed lines.
    """
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()[-n:]
        for ln in lines:
            ln = (ln or "").strip()
            if not ln:
                continue
            try:
                obj = json.loads(ln)
                if isinstance(obj, dict):
                    out.append(obj)
            except Exception:
                continue
    except Exception:
        return []
    return out


def _parse_iso_z(s: Any) -> Optional[datetime]:
    if not s:
        return None
    try:
        ss = str(s).strip()
        if ss.endswith("Z"):
            ss = ss[:-1] + "+00:00"
        return datetime.fromisoformat(ss)
    except Exception:
        return None


def _list_companies(base_dir: Path) -> List[str]:
    root = base_dir / "company_trigger_maps"
    if not root.exists():
        return []
    return sorted([p.name for p in root.iterdir() if p.is_dir()])


def _list_periods_for_company(base_dir: Path, company_safe: str) -> List[str]:
    """
    Periods for dropdown MUST be the union of whatever exists on disk.
    We prefer trigger_maps, but we also accept variable_watch + company_intelligence histories.
    """
    periods: set[str] = set()

    # 1) trigger maps (primary)
    d_tm = base_dir / "company_trigger_maps" / company_safe
    if d_tm.exists():
        periods.update(p.stem for p in d_tm.glob("*.json"))

    # 2) variable watch (secondary)
    d_vw = base_dir / "variable_watch" / company_safe
    if d_vw.exists():
        periods.update(p.stem for p in d_vw.glob("*.json"))

    # 3) intelligence history (optional fallback)
    # base_dir/company_intelligence/<company_safe>/sqi_history.jsonl etc
    d_ci = base_dir / "company_intelligence" / company_safe
    if d_ci.exists():
        for hist in ("sqi_history.jsonl", "score_history.jsonl"):
            p = d_ci / hist
            if p.exists():
                try:
                    for ln in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                        if not ln.strip():
                            continue
                        try:
                            obj = json.loads(ln)
                            if isinstance(obj, dict):
                                fp = obj.get("fiscal_period_ref")
                                if fp:
                                    periods.add(str(fp))
                        except Exception:
                            continue
                except Exception:
                    pass

    return sorted(periods)


def _default_company_and_period(base_dir: Path) -> Tuple[Optional[str], Optional[str]]:
    companies = _list_companies(base_dir)
    if not companies:
        return None, None
    for c in companies:
        periods = _list_periods_for_company(base_dir, c)
        if periods:
            return c, periods[-1]
    return companies[0], None


def _paths_for(base_dir: Path, company_ref: str, fiscal_period: str) -> Dict[str, Path]:
    vw = base_dir / "variable_watch" / _safe_segment(company_ref) / f"{_safe_segment(fiscal_period)}.json"
    tm = base_dir / "company_trigger_maps" / _safe_segment(company_ref) / f"{_safe_segment(fiscal_period)}.json"
    events = base_dir / "company_events" / f"{_safe_segment(company_ref)}.json"
    alerts = base_dir / "alerts" / "alerts.jsonl"
    return {"vw": vw, "tm": tm, "events": events, "alerts": alerts}

def _commentary_path(base_dir: Path, company_ref: str, fiscal_period: str) -> Path:
    company_safe = company_ref.replace("/", "_")
    return base_dir / "commentary" / company_safe / f"{_safe_segment(fiscal_period)}.json"


def _intel_paths(base_dir: Path, company_ref: str) -> Dict[str, Path]:
    """
    Company intelligence dashboard artifacts:
      .runtime/equities/company_intelligence/<company_safe>/...
    """
    company_safe = company_ref.replace("/", "_")
    root = base_dir / "company_intelligence" / company_safe
    return {
        "root": root,
        "snapshot": root / "snapshot.json",
        "score_hist": root / "score_history.jsonl",
        "sqi_hist": root / "sqi_history.jsonl",
        "thesis_cur": root / "thesis" / "current.json",
    }


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        if isinstance(x, bool):
            return None
        if isinstance(x, (int, float)):
            v = float(x)
            return None if v != v else v
        s = str(x).strip()
        if not s:
            return None
        s = s.replace(",", "")
        v = float(s)
        return None if v != v else v
    except Exception:
        return None


def _build_rows(vw: Dict[str, Any], tm: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Build unified “rows” for UI by merging:
      - variable_watch variables (definitions/metadata)
      - trigger_map trigger_entries (latest_value/state/rule)

    HARDEN:
      - If variable_watch is missing/empty, we still render rows from trigger_map.
      - If trigger_map is missing, we render rows from variable_watch (no values).
    """
    vars_ = vw.get("variables") if isinstance(vw.get("variables"), list) else []
    triggers_any = tm.get("trigger_entries")
    if not isinstance(triggers_any, list):
        triggers_any = tm.get("triggers")
    triggers = triggers_any if isinstance(triggers_any, list) else []

    # index triggers by feed_id
    trig_by_feed: Dict[str, Dict[str, Any]] = {}
    for t in triggers:
        if not isinstance(t, dict):
            continue
        fid = str(t.get("feed_id") or "").strip()
        if fid:
            trig_by_feed[fid] = t

    # index vars by feed_id
    var_by_feed: Dict[str, Dict[str, Any]] = {}
    for v in vars_:
        if not isinstance(v, dict):
            continue
        fid = str(v.get("feed_id") or "").strip()
        if fid:
            var_by_feed[fid] = v

    # union feed ids
    feed_ids = sorted(set(list(var_by_feed.keys()) + list(trig_by_feed.keys())))

    rows: List[Dict[str, Any]] = []
    for fid in feed_ids:
        v = var_by_feed.get(fid, {})
        t = trig_by_feed.get(fid, {})

        # prefer variable definitions, fallback to trigger entry fields
        name = (
            v.get("name")
            or t.get("variable_name")
            or t.get("name")
            or fid
        )

        category = (
            v.get("category")
            or t.get("category")
            or "unknown"
        )

        update_frequency = v.get("update_frequency") or v.get("frequency") or v.get("cadence")
        data_source = v.get("data_source") or t.get("data_source") or t.get("data_source_id")

        # thresholds: master format may be separate keys, trigger_map may have threshold_rule string
        threshold_rule = str(t.get("threshold_rule") or "").strip()
        threshold_early = v.get("threshold_early") if "threshold_early" in v else t.get("threshold_early")
        threshold_confirm = v.get("threshold_confirm") if "threshold_confirm" in v else t.get("threshold_confirm")
        threshold_break = v.get("threshold_break") if "threshold_break" in v else t.get("threshold_break")

        impact_direction = (
            v.get("direction")
            or t.get("impact_direction")
            or "pos"
        )

        impact_weight = _safe_float(v.get("impact_weight"))
        if impact_weight is None:
            impact_weight = _safe_float(t.get("impact_weight"))

        why = v.get("why_it_matters") or v.get("rationale") or ""

        latest_value = t.get("latest_value")
        current_state = t.get("current_state", "inactive")
        last_updated_at = t.get("last_updated_at")

        rows.append(
            {
                "name": name,
                "feed_id": fid,
                "category": category,
                "update_frequency": update_frequency,
                "data_source": data_source,
                "why_it_matters": why,

                # thresholds / rules
                "threshold_rule": threshold_rule,
                "threshold_early": threshold_early,
                "threshold_confirm": threshold_confirm,
                "threshold_break": threshold_break,

                # impact
                "impact_direction": impact_direction,
                "impact_weight": impact_weight,

                # live state/value
                "latest_value": latest_value,
                "current_state": current_state,
                "last_updated_at": last_updated_at,
            }
        )

    def _rank(r: Dict[str, Any]) -> Tuple[int, float, str]:
        cat = str(r.get("category") or "").lower()
        # put the most “market-moving” classes first; generic
        if cat == "fx":
            bucket = 0
        elif cat == "commodity":
            bucket = 1
        elif cat in {"rates", "macro"}:
            bucket = 2
        else:
            bucket = 3

        w = r.get("impact_weight")
        ww = float(w) if isinstance(w, (int, float)) else -1.0

        return (bucket, -ww, str(r.get("feed_id") or ""))

    rows.sort(key=_rank)
    return rows


def _recent_alerts_for(
    *,
    alerts: List[Dict[str, Any]],
    company_ref: str,
    fiscal_period: str,
    recent_hours: int,
) -> List[Dict[str, Any]]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=int(recent_hours))
    out: List[Dict[str, Any]] = []

    for a in alerts:
        if not isinstance(a, dict):
            continue
        if str(a.get("company_ref") or "").strip() != company_ref:
            continue

        tmid = str(a.get("trigger_map_id") or "")
        if fiscal_period and f"/trigger_map/{fiscal_period}" not in tmid:
            continue

        dt = _parse_iso_z(a.get("as_of"))
        if dt is None:
            continue
        if dt >= cutoff:
            out.append(a)

    out.sort(key=lambda x: _parse_iso_z(x.get("as_of")) or datetime(1970, 1, 1, tzinfo=timezone.utc))
    return out


def _row_by_feed(rows: List[Dict[str, Any]], feed_id: str) -> Optional[Dict[str, Any]]:
    fid = str(feed_id or "").strip()
    for r in rows:
        if str(r.get("feed_id") or "").strip() == fid:
            return r
    return None


def _fx_summary_generic(rows: List[Dict[str, Any]], limit: int = 4) -> Dict[str, Any]:
    """
    Generic FX summary:
      - pick up to `limit` FX rows, prioritizing:
          1) confirmed/broken (active signals)
          2) impact_weight (desc)
          3) non-null latest_value
    Output shape is stable for UI, but not ticker-specific.
    """
    fx = [r for r in rows if str(r.get("category") or "").lower() == "fx"]

    def _score(r: Dict[str, Any]) -> Tuple[int, float, int, str]:
        st = str(r.get("current_state") or "").lower()
        state_rank = 2
        if st == "broken":
            state_rank = 0
        elif st == "confirmed":
            state_rank = 1

        w = r.get("impact_weight")
        ww = float(w) if isinstance(w, (int, float)) else 0.0

        has_val = 0 if r.get("latest_value") is not None else 1
        return (state_rank, -ww, has_val, str(r.get("feed_id") or ""))

    fx.sort(key=_score)
    picked = fx[: max(0, int(limit))]

    # keep UI-friendly keys
    out: Dict[str, Any] = {}
    for i, r in enumerate(picked, start=1):
        out[f"fx_{i}"] = r
    return out


def build_company_snapshot(
    *,
    base_dir: Path,
    ticker: str,
    latest_period: Optional[str] = None,
    acs_rows: int = 10,
    include_trigger_map: bool = False,
) -> Dict[str, Any]:
    """
    Local snapshot for the dashboard UI.
    Reads:
      - company_trigger_maps/<company_folder>/<period>.json
      - bqs_history/<company_folder>.jsonl
      - acs_history/<company_folder>.jsonl
    """
    company_ref = f"company/{ticker}".strip()
    company_safe = _safe_segment(company_ref)

    periods = _list_periods_for_company(base_dir, company_safe)
    period = latest_period or (periods[-1] if periods else None)
    if not period:
        raise FileNotFoundError(f"No periods found for {company_ref}")

    tm_path = base_dir / "company_trigger_maps" / company_safe / f"{_safe_segment(period)}.json"
    tm = _read_json(tm_path) or {}

    bqs_path = base_dir / "bqs_history" / f"{company_safe}.jsonl"
    acs_path = base_dir / "acs_history" / f"{company_safe}.jsonl"

    bqs_rows = _tail_jsonl(bqs_path, n=800)
    acs_tail = _tail_jsonl(acs_path, n=max(800, int(acs_rows) * 20))

    bqs_latest = bqs_rows[-1] if bqs_rows else None
    acs_recent = acs_tail[-int(acs_rows):] if acs_tail else []
    acs_latest = acs_recent[-1] if acs_recent else None

    entries = tm.get("trigger_entries") if isinstance(tm.get("trigger_entries"), list) else []
    variables_total = len(entries)
    variables_with_value = sum(1 for t in entries if isinstance(t, dict) and t.get("latest_value") is not None)
    variables_confirmed = sum(
        1 for t in entries
        if isinstance(t, dict) and str(t.get("current_state") or "").lower() == "confirmed"
    )

    reports_ingested = len(
        {
            str(r.get("source_document_ref") or "").strip()
            for r in bqs_rows
            if isinstance(r, dict) and str(r.get("source_document_ref") or "").strip()
        }
    )

    last_candidates: List[datetime] = []
    for t in entries:
        if not isinstance(t, dict):
            continue
        dt = _parse_iso_z(t.get("last_updated_at"))
        if dt:
            last_candidates.append(dt)
    if isinstance(bqs_latest, dict):
        dt = _parse_iso_z(bqs_latest.get("as_of"))
        if dt:
            last_candidates.append(dt)
    if isinstance(acs_latest, dict):
        dt = _parse_iso_z(acs_latest.get("as_of"))
        if dt:
            last_candidates.append(dt)

    last_updated_at = max(last_candidates).isoformat() if last_candidates else None

    if reports_ingested < 2:
        maturity = "EARLY_STAGE"
    elif reports_ingested >= 4 and variables_confirmed >= 5:
        maturity = "READY"
    elif variables_confirmed < 3:
        maturity = "CALIBRATING"
    else:
        maturity = "CALIBRATING"

    snap: Dict[str, Any] = {
        "company_ref": company_ref,
        "latest_period": period,
        "bqs_latest": bqs_latest,
        "acs_latest": acs_latest,
        "acs_recent": acs_recent,
        "health": {
            "reports_ingested": reports_ingested,
            "variables_total": variables_total,
            "variables_with_value": variables_with_value,
            "variables_confirmed": variables_confirmed,
            "maturity": maturity,
            "last_updated_at": last_updated_at,
        },
    }

    if include_trigger_map:
        snap["trigger_map"] = tm

    return snap


# -------------------------
# app
# -------------------------

# -------------------------
# app
# -------------------------

def make_app(*, base_dir: Path, default_company_ref: Optional[str], default_fiscal_period: Optional[str]) -> FastAPI:
    app = FastAPI(title="FTSE HACKERS")

    @app.get("/api/index")
    def api_index(recent_hours: int = 24) -> JSONResponse:
        companies_safe = _list_companies(base_dir)
        alerts_path = base_dir / "alerts" / "alerts.jsonl"
        alerts = _tail_jsonl(alerts_path, n=1200)

        out: List[Dict[str, Any]] = []
        for c_safe in companies_safe:
            periods = _list_periods_for_company(base_dir, c_safe)
            company_ref = c_safe.replace("company_", "company/")
            latest_period = periods[-1] if periods else None

            ev_path = base_dir / "company_events" / f"{c_safe}.json"
            ev = _read_json(ev_path) or {}

            rec: List[Dict[str, Any]] = []
            if latest_period:
                rec = _recent_alerts_for(
                    alerts=alerts,
                    company_ref=company_ref,
                    fiscal_period=latest_period,
                    recent_hours=recent_hours,
                )

            ip = _intel_paths(base_dir, company_ref)
            snap = _read_json(ip["snapshot"]) or None
            thesis_cur = _read_json(ip["thesis_cur"]) or None

            health = {
                "sqi_score": (snap or {}).get("sqi", {}).get("sqi_score") if isinstance(snap, dict) else None,
                "bqs": (snap or {}).get("scores", {}).get("bqs") if isinstance(snap, dict) else None,
                "acs": (snap or {}).get("scores", {}).get("acs") if isinstance(snap, dict) else None,
                "thesis_status": (thesis_cur or {}).get("status") if isinstance(thesis_cur, dict) else None,
            }

            out.append(
                {
                    "company_safe": c_safe,
                    "company_ref": company_ref,
                    "periods": periods,
                    "latest_period": latest_period,
                    "events": {
                        "next_reporting_date": ev.get("next_reporting_date"),
                        "window_start": ev.get("window_start"),
                        "window_end": ev.get("window_end"),
                        "source": ev.get("source"),
                        "notes": ev.get("notes"),
                    },
                    "recent_alerts_count": len(rec),
                    "recent_alerts": rec[-5:],
                    "health": health,
                }
            )

        return JSONResponse({"base_dir": str(base_dir), "recent_hours": int(recent_hours), "companies": out})

    @app.get("/api/state")

    def api_state(
        company_ref: Optional[str] = None,
        fiscal_period: Optional[str] = None,
        recent_hours: int = 24,
    ) -> JSONResponse:
        cref = (company_ref or default_company_ref or "").strip()
        per = (fiscal_period or default_fiscal_period or "").strip()

        if not cref:
            raise HTTPException(status_code=404, detail="No companies found under runtime base_dir.")

        if not per:
            company_safe = _safe_segment(cref)
            periods = _list_periods_for_company(base_dir, company_safe)
            if not periods:
                raise HTTPException(status_code=404, detail=f"No periods found for {cref}.")
            per = periods[-1]

        paths = _paths_for(base_dir, cref, per)

        vw = _read_json(paths["vw"]) or {}
        tm = _read_json(paths["tm"]) or {}
        ev = _read_json(paths["events"]) or {}
        alerts = _tail_jsonl(paths["alerts"], n=1200)

        # NEW: commentary (board-pack commentary JSON)
        commentary_path = _commentary_path(base_dir, cref, per)
        commentary = _read_json(commentary_path) if commentary_path.exists() else None

        rows = _build_rows(vw, tm)

        recent = _recent_alerts_for(
            alerts=alerts,
            company_ref=cref,
            fiscal_period=per,
            recent_hours=recent_hours,
        )

        ip = _intel_paths(base_dir, cref)
        intelligence_snapshot = _read_json(ip["snapshot"]) or None
        score_history_tail = _tail_jsonl(ip["score_hist"], n=60)
        sqi_history_tail = _tail_jsonl(ip["sqi_hist"], n=60)
        thesis_current = _read_json(ip["thesis_cur"]) or None

        fx_summary = _fx_summary_generic(rows, limit=4)

        return JSONResponse(
            {
                "company_ref": cref,
                "fiscal_period_ref": per,
                "recent_hours": int(recent_hours),
                "paths": {k: str(v) for k, v in paths.items()},
                # NEW
                "commentary_ref": str(commentary_path),
                "commentary": commentary,

                "events": ev,
                "rows": rows,
                "fx_summary": fx_summary,
                "recent_alerts": recent[-50:],
                "intelligence_snapshot": intelligence_snapshot,
                "score_history_tail": score_history_tail,
                "sqi_history_tail": sqi_history_tail,
                "thesis_current": thesis_current,
            }
        )

    @app.get("/api/dashboard/company/{ticker}")
    def api_company_snapshot(ticker: str, period: str = "", n: int = 10) -> JSONResponse:
        try:
            snap = build_company_snapshot(
                base_dir=base_dir,
                ticker=ticker,
                latest_period=period or None,
                acs_rows=int(n),
                include_trigger_map=False,
            )
            return JSONResponse(snap)
        except Exception as e:
            raise HTTPException(status_code=500, detail=repr(e))

    # NOTE: Generic dashboard HTML/JS (no ticker-specific feed IDs)
    @app.get("/", response_class=HTMLResponse)
    def home() -> HTMLResponse:
        html = r"""<!doctype html>

<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>FTSE HACKERS</title>
  <style>
    :root{
      --bg:#f5f6f8;
      --muted:rgba(15,23,42,.55);
      --ink:#0b0f19;
      --line:rgba(15,23,42,.10);
      --pill:rgba(15,23,42,.06);
      --accent:#1f6feb;
      --warn:#f59e0b;
      --bad:#ef4444;
      --good:#10b981;
    }
    html,body{height:100%;}
    body{
      margin:0;
      font-family: ui-sans-serif,-apple-system,system-ui,Segoe UI,Roboto,Helvetica,Arial;
      background:
        radial-gradient(1200px 700px at 15% -10%, rgba(31,111,235,.12), transparent 60%),
        radial-gradient(900px 600px at 85% 0%, rgba(0,0,0,.06), transparent 60%),
        var(--bg);
      color:var(--ink);
    }
    .topbar{
      position:sticky; top:0; z-index:20;
      backdrop-filter: blur(12px);
      background: rgba(245,246,248,.78);
      border-bottom:1px solid var(--line);
    }
    .topbar-inner{
      max-width:1320px; margin:0 auto;
      display:flex; align-items:center; justify-content:space-between;
      padding:14px 18px; gap:12px;
    }
    .brand{display:flex; align-items:baseline; gap:10px; font-weight:900; letter-spacing:-.03em;}
    .brand .name{font-size:18px;}
    .brand .tag{
      font-size:12px; color:var(--muted);
      padding:4px 10px; border-radius:999px;
      background:var(--pill); border:1px solid var(--line);
    }
    .container{max-width:1320px; margin:0 auto; padding:18px 18px 36px;}
    .hero{
      border:1px solid var(--line);
      border-radius:26px;
      padding:26px;
      background: linear-gradient(180deg, rgba(255,255,255,.92), rgba(255,255,255,.78));
      box-shadow: 0 18px 60px rgba(15,23,42,.10);
    }
    .hero h1{
      margin:0;
      font-size:64px;
      letter-spacing:-.06em;
      font-weight:950;
      font-style: italic;
      line-height:1.02;
    }
    .hero p{
      margin:10px 0 0 0;
      color:var(--muted);
      max-width:920px;
      font-size:15px;
      line-height:1.55;
    }
    .controls{
      margin-top:18px;
      display:flex; flex-wrap:wrap; gap:10px; align-items:center;
    }
    select,input{
      border-radius:14px;
      border:1px solid var(--line);
      background: rgba(255,255,255,.92);
      color:var(--ink);
      padding:10px 12px;
      font-size:14px;
      outline:none;
      min-width:260px;
      box-shadow: 0 6px 18px rgba(15,23,42,.06);
    }
    input::placeholder{color:rgba(15,23,42,.35);}
    button{
      border-radius:14px;
      border:1px solid rgba(31,111,235,.25);
      background: linear-gradient(180deg, rgba(31,111,235,.98), rgba(31,111,235,.78));
      color:white;
      padding:10px 14px;
      font-weight:850;
      cursor:pointer;
      box-shadow: 0 10px 22px rgba(31,111,235,.20);
    }
    button.secondary{
      border:1px solid var(--line);
      background: rgba(255,255,255,.92);
      color:var(--ink);
      box-shadow: 0 10px 22px rgba(15,23,42,.06);
    }
    .meta{
      margin-top:12px;
      display:flex; flex-wrap:wrap; gap:10px;
      color:var(--muted);
      font-size:13px;
    }
    code{font-family: ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono","Courier New",monospace;}
    .meta code{
      background: rgba(15,23,42,.05);
      padding:2px 6px;
      border-radius:8px;
      border:1px solid var(--line);
    }

    .healthstrip{margin-top:10px; display:grid; grid-template-columns:repeat(4,minmax(180px,1fr)); gap:10px;}
    @media (max-width:980px){.healthstrip{grid-template-columns:repeat(2,minmax(180px,1fr));}}
    .hitem{
      background: rgba(255,255,255,.92);
      border:1px solid var(--line);
      border-radius:16px;
      padding:10px 12px;
      box-shadow: 0 10px 22px rgba(15,23,42,.06);
    }
    .hlabel{color:var(--muted); font-size:11px; letter-spacing:.12em; text-transform:uppercase;}
    .hval{margin-top:6px; font-size:18px; font-weight:950; letter-spacing:-.02em;}
    .hsub{margin-top:6px; color:var(--muted); font-size:12px;}

    /* FX strip is now generic: it shows up to 4 FX rows returned by /api/state */
    .fxstrip{margin-top:12px; display:grid; grid-template-columns:repeat(4,minmax(180px,1fr)); gap:10px;}
    @media (max-width:980px){.fxstrip{grid-template-columns:repeat(2,minmax(180px,1fr));}}
    .fxitem{
      background: rgba(255,255,255,.92);
      border:1px solid var(--line);
      border-radius:16px;
      padding:10px 12px;
      box-shadow: 0 10px 22px rgba(15,23,42,.06);
    }
    .fxlabel{color:var(--muted); font-size:11px; letter-spacing:.12em; text-transform:uppercase;}
    .fxval{margin-top:6px; font-size:18px; font-weight:900; letter-spacing:-.02em;}

    .tiles{margin-top:14px; display:grid; grid-template-columns:repeat(1,minmax(0,1fr)); gap:12px;}
    @media (min-width:820px){.tiles{grid-template-columns:repeat(2,minmax(0,1fr));}}
    @media (min-width:1100px){.tiles{grid-template-columns:repeat(3,minmax(0,1fr));}}

    .tile{
      border:1px solid var(--line);
      border-radius:18px;
      padding:14px;
      background: rgba(255,255,255,.92);
      box-shadow: 0 14px 40px rgba(15,23,42,.10);
      cursor:pointer;
      transition: transform 120ms ease, border-color 120ms ease;
    }
    .tile:hover{transform: translateY(-1px); border-color: rgba(31,111,235,.30);}
    .tile-top{display:flex; align-items:flex-start; justify-content:space-between; gap:12px;}
    .tile h4{margin:0; font-size:16px; letter-spacing:-.02em;}
    .tile .sub{margin-top:4px; color:var(--muted); font-size:12px;}
    .badge{
      display:inline-flex; align-items:center; gap:8px;
      padding:6px 10px;
      border-radius:999px;
      border:1px solid var(--line);
      background: rgba(15,23,42,.04);
      font-size:12px;
      font-weight:900;
      white-space:nowrap;
    }
    .badge.hit{background: rgba(245,158,11,.14); border-color: rgba(245,158,11,.28); color:#8a4b00;}
    .badge.ok{background: rgba(16,185,129,.14); border-color: rgba(16,185,129,.28); color:#065f46;}

    .tile-grid{margin-top:12px; display:grid; grid-template-columns:1fr 1fr; gap:10px;}
    .kv{
      background: rgba(15,23,42,.03);
      border:1px solid var(--line);
      border-radius:14px;
      padding:10px;
    }
    .kv .k{color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.12em;}
    .kv .v{margin-top:6px; font-size:13px; font-weight:800;}

    .grid{display:grid; grid-template-columns:1fr; gap:14px; margin-top:14px;}
    @media (min-width:960px){.grid{grid-template-columns:1.25fr .75fr;}}
    .card{
      background: rgba(255,255,255,.92);
      border:1px solid var(--line);
      border-radius:18px;
      padding:14px;
      box-shadow: 0 12px 34px rgba(15,23,42,.10);
    }
    .card h3{
      margin:0 0 10px 0;
      font-size:12px;
      text-transform:uppercase;
      letter-spacing:.14em;
      color:var(--muted);
    }

    table{width:100%; border-collapse:collapse; font-size:13px;}
    th,td{padding:10px 8px; border-bottom:1px solid var(--line); vertical-align:top;}
    th{text-align:left; color:var(--muted); font-weight:800; font-size:12px;}

    .pill{
      display:inline-flex; align-items:center; gap:6px;
      padding:4px 10px; border-radius:999px;
      background: rgba(15,23,42,.05);
      border:1px solid var(--line);
      font-size:12px; font-weight:900;
      white-space:nowrap;
    }
    .dot{width:8px; height:8px; border-radius:999px; background:#9ca3af;}
    .inactive .dot{background:#9ca3af;}
    .building .dot{background:var(--warn);}
    .confirmed .dot{background:var(--good);}
    .broken .dot{background:var(--bad);}

    .panel{
      background: #0b1020;
      border:1px solid rgba(15,23,42,.12);
      border-radius:16px;
      padding:12px;
      overflow:auto;
      max-height:520px;
      font-family: ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono","Courier New",monospace;
      font-size:12px;
      white-space:pre;
      color:#e5e7eb;
    }

    .banner{
      margin-top:14px;
      border-radius:18px;
      padding:14px;
      border:1px solid rgba(245,158,11,.35);
      background: rgba(245,158,11,.14);
      color:#8a4b00;
      display:none;
      font-weight:900;
    }

    /* snapshot blocks */
    .snapgrid{margin-top:12px; display:grid; grid-template-columns:1fr; gap:12px;}
    @media (min-width:960px){.snapgrid{grid-template-columns:1fr 1fr;}}
    .muted{color:var(--muted);}
    .big{font-weight:950; font-size:22px; letter-spacing:-.02em;}

    /* table inside dark panel needs explicit header color */
    .panel table th{color:rgba(255,255,255,.70); border-bottom:1px solid rgba(255,255,255,.12);}
    .panel table td{border-bottom:1px solid rgba(255,255,255,.08);}
    .panel code{color:#e5e7eb;}
  </style>
</head>
<body>
  <div class="topbar">
    <div class="topbar-inner">
      <div class="brand">
        <div class="name">FTSE HACKERS</div>
        <div class="tag">local runtime dashboard</div>
      </div>
      <div style="display:flex; gap:10px; align-items:center;">
        <span style="color:var(--muted); font-size:12px;">Runtime:</span>
        <span style="font-size:12px;"><code id="runtime">…</code></span>
      </div>
    </div>
  </div>

  <div class="container">
    <div class="hero">
      <h1>FTSE HACKERS</h1>
      <p>Tiles = “what matters now”. Click a company to drill down. Triggers ≠ trades. “MAKE TRADE” only comes from thesis.</p>

      <div class="controls">
        <input id="search" placeholder="Search company (e.g. ULVR.L)..." />
        <select id="company"></select>
        <select id="period"></select>
        <input id="recentHours" type="number" min="1" max="168" value="24" style="min-width:140px" />
        <button id="btnLoad">Load</button>
        <button class="secondary" id="btnRefresh">Refresh</button>
      </div>

      <div class="meta" id="meta"></div>
      <div class="healthstrip" id="healthstrip"></div>
      <div class="fxstrip" id="fxstrip"></div>

      <div class="snapgrid" id="snapgrid">
        <div class="card">
          <h3>BQS (latest)</h3>
          <div id="bqsCard" class="muted">—</div>
        </div>
        <div class="card">
          <h3>ACS (recent)</h3>
          <div class="panel" id="acsPanel">—</div>
        </div>
      </div>

      <div class="card" style="margin-top:12px;">
        <h3>Intelligence Health Monitor</h3>
        <div id="healthCard" class="muted">—</div>
      </div>

      <div class="card" style="margin-top:12px;">
        <h3>Board Pack Commentary</h3>
        <div id="commentaryCard" class="muted">—</div>
      </div>

      <div class="tiles" id="tiles"></div>
      <div class="banner" id="banner"></div>
    </div>

    <div class="grid">
      <div class="card">
        <h3>Variables / Triggers</h3>
        <table>
          <thead>
            <tr>
              <th>Name</th><th>Feed</th><th>Category</th><th>Value</th><th>State</th><th>Rule</th><th>Updated</th>
            </tr>
          </thead>
          <tbody id="tbody"></tbody>
        </table>
      </div>

      <div class="card">
        <h3>Recent trigger hits</h3>
        <div class="panel" id="recent">Loading…</div>
      </div>
    </div>
  </div>

<script>
let INDEX = null;

function statePill(state) {
  const s = (state || "inactive").toLowerCase();
  return `<span class="pill ${s}"><span class="dot"></span>${state || ""}</span>`;
}

function fmtDate(s) {
  if (!s) return "—";
  return s;
}

function fmtVal(x) {
  if (x === null || x === undefined || x === "") return "—";
  return String(x);
}

function esc(x) {
  const s = (x === null || x === undefined) ? "" : String(x);
  return s
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function setMeta(data) {
  const el = document.getElementById("meta");
  const ev = data.events || {};
  el.innerHTML = `
    <div><b>Company:</b> <code>${esc(data.company_ref)}</code></div>
    <div><b>Period:</b> <code>${esc(data.fiscal_period_ref)}</code></div>
    <div><b>Next report:</b> <code>${esc(fmtDate(ev.next_reporting_date))}</code></div>
    <div><b>Window:</b> <code>${esc(fmtDate(ev.window_start))} → ${esc(fmtDate(ev.window_end))}</code></div>
  `;
}

function renderCommentary(data) {
  const refEl = document.getElementById("commentaryRef");
  const panel = document.getElementById("commentaryPanel");
  if (!panel) return;

  const ref = data.commentary_ref || "—";
  const c = data.commentary || null;

  if (refEl) refEl.textContent = ref;

  if (!c) {
    panel.textContent = "— no commentary file found for this company/period —";
    return;
  }
  panel.textContent = JSON.stringify(c, null, 2);
}

function renderHealthStrip(data) {
  const strip = document.getElementById("healthstrip");
  const snap = data.intelligence_snapshot || null;
  const thesis = data.thesis_current || null;

  const sqi = snap?.sqi?.sqi_score ?? snap?.sqi_score ?? snap?.sqi?.score ?? null;
  const drift = snap?.sqi?.drift ?? snap?.drift ?? null;
  const bqs = snap?.scores?.bqs;
  const acs = snap?.scores?.acs;
  const qseen = snap?.maturity?.quarters_seen ?? snap?.sqi?.quarters_seen ?? null;
  const status = thesis?.status || "—";
  const dir = thesis?.thesis_direction || thesis?.direction || "—";

  const line = (label, val, sub=null) => {
    const v = (val === null || val === undefined || val === "") ? "—" : String(val);
    return `
      <div class="hitem">
        <div class="hlabel">${esc(label)}</div>
        <div class="hval">${esc(v)}</div>
        <div class="hsub">${esc(sub || "")}</div>
      </div>
    `;
  };

  strip.innerHTML = `
    ${line("SQI", (typeof sqi === "number" ? sqi.toFixed(3) : sqi), (drift !== null && drift !== undefined) ? `drift: ${drift}` : "")}
    ${line("BQS", (typeof bqs === "number" ? bqs.toFixed(1) : bqs), "board-quality")}
    ${line("ACS", (typeof acs === "number" ? acs.toFixed(1) : acs), `maturity: ${qseen ?? "—"} qtrs`)}
    ${line("Thesis", `${status}`, `direction: ${dir}`)}
  `;
}

function renderFxStrip(data) {
  const fx = data.fx_summary || {};
  const strip = document.getElementById("fxstrip");

  // backend returns fx_1..fx_4 (optional)
  const keys = Object.keys(fx).filter(k => k.startsWith("fx_")).sort();

  const item = (k, r) => {
    const name = r?.name || r?.feed_id || k;
    const val = fmtVal(r?.latest_value);
    const st = r?.current_state || "inactive";
    return `
      <div class="fxitem">
        <div class="fxlabel">${esc(name)}</div>
        <div class="fxval">${esc(val)}</div>
        <div style="margin-top:6px;">${statePill(st)}</div>
      </div>
    `;
  };

  if (!keys.length) {
    strip.innerHTML = `
      <div class="fxitem" style="grid-column:1/-1;">
        <div class="fxlabel">FX</div>
        <div class="fxval">—</div>
        <div style="margin-top:6px; color:var(--muted); font-size:12px;">No FX rows for this company/period.</div>
      </div>
    `;
    return;
  }

  strip.innerHTML = keys.map(k => item(k, fx[k])).join("");
}

function shouldMakeTrade(thesisCurrent) {
  if (!thesisCurrent) return false;
  const st = String(thesisCurrent.status || "").toLowerCase().trim();
  return (st === "enter" || st === "exit");
}

function renderCompanySnapshot(snap) {
  const fmt = (x, digits = null) => {
    if (x === null || x === undefined || x === "") return "—";
    if (typeof x === "number" && Number.isFinite(x)) {
      return digits === null ? String(x) : x.toFixed(digits);
    }
    return String(x);
  };

  const fmtDir = (x) => {
    const s = (x === null || x === undefined) ? "" : String(x).toLowerCase().trim();
    if (!s) return "—";
    if (s === "pos") return "pos";
    if (s === "neg") return "neg";
    if (s === "flat") return "flat";
    return s;
  };

  // BQS
  const bqs = snap?.bqs_latest?.bqs || null;
  const bqsAsOf = snap?.bqs_latest?.as_of || null;
  const bqsSrc = snap?.bqs_latest?.source_document_ref || null;

  const bqsEl = document.getElementById("bqsCard");
  if (bqsEl) {
    const comp = (typeof bqs?.composite === "number") ? bqs.composite.toFixed(2) : "—";
    const comps = Array.isArray(bqs?.components) ? bqs.components : [];

    bqsEl.innerHTML = `
      <div class="big">${esc(comp)}</div>
      <div class="muted" style="font-size:12px; margin-top:4px;">
        as_of: <code>${esc(bqsAsOf || "—")}</code> • src: <code>${esc(bqsSrc || "—")}</code>
      </div>
      <div style="margin-top:10px;">
        <table>
          <thead>
            <tr><th>Component</th><th>Score</th><th>Evidence</th></tr>
          </thead>
          <tbody>
            ${comps.map(c => `
              <tr>
                <td>${esc(c.label || c.key || "")}</td>
                <td><b>${esc((c.score === 0 || c.score) ? c.score : "—")}</b></td>
                <td>${esc(c.evidence || "")}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  // ACS
  const acsEl = document.getElementById("acsPanel");
  if (acsEl) {
    const rec = Array.isArray(snap?.acs_recent) ? snap.acs_recent : [];

    // de-dupe by (fiscal_period_ref + event_type) keeping latest as_of
    const byKey = new Map();
    for (const r of rec) {
      const per = r?.fiscal_period_ref || "—";
      const typ = r?.event_type || "—";
      const key = `${per}::${typ}`;
      const prev = byKey.get(key);
      if (!prev) { byKey.set(key, r); continue; }
      const a = String(prev?.as_of || "");
      const b = String(r?.as_of || "");
      if (b > a) byKey.set(key, r);
    }

    const rows = Array.from(byKey.values()).sort((a, b) => {
      const pa = String(a?.fiscal_period_ref || "");
      const pb = String(b?.fiscal_period_ref || "");
      if (pa === pb) return String(b?.as_of || "").localeCompare(String(a?.as_of || ""));
      return pb.localeCompare(pa);
    });

    acsEl.innerHTML = `
      <div style="overflow:auto;">
        <table style="width:100%; border-collapse:collapse;">
          <thead>
            <tr>
              <th>Period</th>
              <th>FX</th>
              <th>USG dir</th>
              <th>Volume dir</th>
              <th>Actual</th>
              <th>Accuracy</th>
              <th>as_of</th>
            </tr>
          </thead>
          <tbody>
            ${rows.length ? rows.map(r => {
              const p = r?.predicted || {};
              return `
                <tr>
                  <td><code>${esc(r?.fiscal_period_ref ?? "—")}</code></td>
                  <td>${esc(fmt(p.fx_drag_pct, 2))}</td>
                  <td>${esc(fmtDir(p.usg_dir))}</td>
                  <td>${esc(fmtDir(p.volume_dir))}</td>
                  <td>${esc(fmt(r?.actual))}</td>
                  <td>${esc(fmt(r?.accuracy))}</td>
                  <td>${esc(fmt(r?.as_of))}</td>
                </tr>
              `;
            }).join("") : `
              <tr><td colspan="7" style="padding:12px; color:rgba(255,255,255,.70);">— no ACS rows yet —</td></tr>
            `}
          </tbody>
        </table>
      </div>
    `;
  }

  // Health
  const h = snap?.health || {};
  const healthEl = document.getElementById("healthCard");
  if (healthEl) {
    healthEl.innerHTML = `
      <div><b>reports_ingested:</b> <code>${esc(h.reports_ingested ?? "—")}</code></div>
      <div><b>variables_total:</b> <code>${esc(h.variables_total ?? "—")}</code></div>
      <div><b>variables_with_value:</b> <code>${esc(h.variables_with_value ?? "—")}</code></div>
      <div><b>variables_confirmed:</b> <code>${esc(h.variables_confirmed ?? "—")}</code></div>
      <div><b>maturity:</b> <code>${esc(h.maturity ?? "—")}</code></div>
      <div><b>last_updated_at:</b> <code>${esc(h.last_updated_at ?? "—")}</code></div>
    `;
  }
}

function renderTiles() {
  const tiles = document.getElementById("tiles");
  tiles.innerHTML = "";
  const recentHours = parseInt(document.getElementById("recentHours").value || "24", 10);

  for (const c of (INDEX?.companies || [])) {
    const hits = c.recent_alerts_count || 0;
    const ev = c.events || {};
    const badge = hits > 0
      ? `<span class="badge hit">Trigger hit • ${hits}</span>`
      : `<span class="badge ok">OK</span>`;

    const div = document.createElement("div");
    div.className = "tile";
    div.innerHTML = `
      <div class="tile-top">
        <div>
          <h4>${esc(c.company_ref)}</h4>
          <div class="sub">Latest period: <b>${esc(c.latest_period || "—")}</b> • Alerts window: <b>${recentHours}h</b></div>
        </div>
        ${badge}
      </div>
      <div class="tile-grid">
        <div class="kv">
          <div class="k">Next reporting date</div>
          <div class="v">${esc(fmtDate(ev.next_reporting_date))}</div>
        </div>
        <div class="kv">
          <div class="k">Reporting window</div>
          <div class="v">${esc(fmtDate(ev.window_start))} → ${esc(fmtDate(ev.window_end))}</div>
        </div>
      </div>
    `;
    div.onclick = async () => {
      document.getElementById("company").value = c.company_ref;
      fillPeriodsForSelected();
      if (c.latest_period) document.getElementById("period").value = c.latest_period;
      await loadState();
      window.scrollTo({ top: 0, behavior: "smooth" });
    };
    tiles.appendChild(div);
  }
}

async function loadIndex() {
  const recentHours = parseInt(document.getElementById("recentHours").value || "24", 10);
  const res = await fetch(`/api/index?recent_hours=${encodeURIComponent(recentHours)}`);
  if (!res.ok) throw new Error(`index ${res.status}`);
  INDEX = await res.json();

  document.getElementById("runtime").textContent = INDEX.base_dir || "";

  const companySel = document.getElementById("company");
  companySel.innerHTML = "";
  for (const c of (INDEX.companies || [])) {
    const opt = document.createElement("option");
    opt.value = c.company_ref;
    opt.textContent = c.company_ref;
    companySel.appendChild(opt);
  }

  if ((INDEX.companies || []).length) {
    companySel.value = INDEX.companies[0].company_ref;
    fillPeriodsForSelected();
  }

  companySel.onchange = () => fillPeriodsForSelected();

  const search = document.getElementById("search");
  search.oninput = () => {
    const q = (search.value || "").toLowerCase().trim();
    if (!q) return;
    for (const c of (INDEX.companies || [])) {
      if ((c.company_ref || "").toLowerCase().includes(q)) {
        companySel.value = c.company_ref;
        fillPeriodsForSelected();
        break;
      }
    }
  };

  renderTiles();
}

function fillPeriodsForSelected() {
  const companySel = document.getElementById("company");
  const periodSel = document.getElementById("period");
  const cref = companySel.value;

  const item = (INDEX?.companies || []).find(x => x.company_ref === cref);
  const periods = item?.periods || [];

  periodSel.innerHTML = "";
  for (const p of periods) {
    const opt = document.createElement("option");
    opt.value = p;
    opt.textContent = p;
    periodSel.appendChild(opt);
  }
  if (periods.length) periodSel.value = periods[periods.length - 1];
}

async function loadState() {
  const cref = document.getElementById("company").value;
  const per = document.getElementById("period").value;
  const recentHours = parseInt(document.getElementById("recentHours").value || "24", 10);

  const url = `/api/state?company_ref=${encodeURIComponent(cref)}&fiscal_period=${encodeURIComponent(per)}&recent_hours=${encodeURIComponent(recentHours)}`;
  const tick = (cref.split("/")[1] || "").trim();

  const [data, snap] = await Promise.all([
    fetch(url).then(r => {
      if (!r.ok) throw new Error(`state ${r.status}`);
      return r.json();
    }),
    tick
      ? fetch(`/api/dashboard/company/${encodeURIComponent(tick)}?period=${encodeURIComponent(per)}&n=10`).then(r => {
          if (!r.ok) throw new Error(`snapshot ${r.status}`);
          return r.json();
        })
      : Promise.resolve(null),
  ]);

  setMeta(data);
  renderHealthStrip(data);
  renderFxStrip(data);
  renderCommentary(data);

  if (snap) renderCompanySnapshot(snap);

  const banner = document.getElementById("banner");
  const ra = data.recent_alerts || [];
  const thesis = data.thesis_current || null;

  if (shouldMakeTrade(thesis)) {
    banner.style.display = "block";
    banner.textContent = `ALERT: MAKE TRADE • thesis status=${thesis.status}`;
  } else if (ra.length > 0) {
    banner.style.display = "block";
    banner.textContent = `Trigger hit • ${ra.length} trigger event(s) in last ${recentHours}h`;
  } else {
    banner.style.display = "none";
    banner.textContent = "";
  }

  const tbody = document.getElementById("tbody");
  tbody.innerHTML = "";
  for (const r of (data.rows || [])) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${esc(r.name ?? "")}</td>
      <td>${esc(r.feed_id ?? "")}</td>
      <td>${esc(r.category ?? "")}</td>
      <td>${esc(r.latest_value ?? "")}</td>
      <td>${statePill(r.current_state)}</td>
      <td>${esc(r.threshold_rule ?? "")}</td>
      <td>${esc(r.last_updated_at ?? "")}</td>
    `;
    tbody.appendChild(tr);
  }

  const recent = document.getElementById("recent");
  recent.textContent = JSON.stringify(ra.slice(-50), null, 2);
}

async function boot() {
  await loadIndex();
  await loadState();
  setInterval(() => loadState().catch(() => {}), 5000);
}

document.getElementById("btnLoad").onclick = () => loadState();
document.getElementById("btnRefresh").onclick = async () => { await loadIndex(); await loadState(); };
document.getElementById("recentHours").onchange = async () => { await loadIndex(); await loadState(); };

boot();
</script>
</body>
</html>
"""
        return HTMLResponse(html)

    return app
# -------------------------
# entrypoint
# -------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-dir", default=str(Path(".runtime/equities").resolve()))
    ap.add_argument("--company-ref", default=None)
    ap.add_argument("--fiscal-period", default=None)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8787)
    args = ap.parse_args()

    base_dir = Path(args.base_dir).resolve()
    default_company_ref = args.company_ref
    default_fiscal_period = args.fiscal_period

    if not default_company_ref or not default_fiscal_period:
        c_safe, per = _default_company_and_period(base_dir)
        if not default_company_ref and c_safe:
            default_company_ref = c_safe.replace("company_", "company/")
        if not default_fiscal_period and per:
            default_fiscal_period = per

    app = make_app(
        base_dir=base_dir,
        default_company_ref=default_company_ref,
        default_fiscal_period=default_fiscal_period,
    )
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()