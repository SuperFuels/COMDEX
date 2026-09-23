# backend/modules/aion_equities/intelligence_health.py
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List, Set
import json

SCHEMA_VERSION_SQI = "aion.equities.sqi.v2"  # always-float SQI + coverage splits
SCHEMA_VERSION_SCORE_HISTORY = "aion.equities.score_history.v1"
SCHEMA_VERSION_SNAPSHOT = "aion.equities.intelligence_snapshot.v1"

# Categories that SHOULD be “live” or continuously fetchable.
LIVE_CATEGORIES: Set[str] = {"fx", "commodity", "macro", "computed", "subsidiary_leading"}

# Categories that are inherently “reported” (board pack / results doc).
REPORTED_CATEGORIES: Set[str] = {"company_reported"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_segment(s: str) -> str:
    s = str(s or "").strip()
    if not s:
        return "unknown"
    return s.replace("..", "_").replace("/", "_").replace("\\", "_").replace(":", "_")


def _company_safe(company_ref: str) -> str:
    return str(company_ref).replace("/", "_")


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _append_jsonl(path: Path, row: Dict[str, Any], *, dedup_by_day: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if dedup_by_day and path.exists():
        try:
            last = None
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        last = line
            if last:
                prev = json.loads(last)
                prev_day = str(prev.get("as_of", ""))[:10]
                cur_day = str(row.get("as_of", ""))[:10]
                if prev_day == cur_day:
                    lines = path.read_text(encoding="utf-8").splitlines()
                    idx = None
                    for i in range(len(lines) - 1, -1, -1):
                        if lines[i].strip():
                            idx = i
                            break
                    if idx is not None:
                        lines[idx] = json.dumps(row, ensure_ascii=False, sort_keys=True)
                        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                        return
        except Exception:
            pass

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _coalesce_trigger_list(trigger_map: Dict[str, Any]) -> List[Dict[str, Any]]:
    if isinstance(trigger_map.get("triggers"), list):
        return [t for t in trigger_map["triggers"] if isinstance(t, dict)]
    if isinstance(trigger_map.get("trigger_entries"), list):
        return [t for t in trigger_map["trigger_entries"] if isinstance(t, dict)]
    return []


def _norm_dir(v: Any) -> str:
    s = str(v or "").strip().lower()
    if s in {"pos", "positive", "up", "direct", "+", "increase"}:
        return "pos"
    if s in {"neg", "negative", "down", "inverse", "-", "decrease"}:
        return "neg"
    if s in {"neutral", "flat", "none"}:
        return "neutral"
    return "neutral"


def _state(entry: Dict[str, Any]) -> str:
    return str(entry.get("current_state", entry.get("state", "inactive")) or "inactive").strip().lower()


def _is_active_state(st: str) -> bool:
    return st in {"early_watch", "building", "confirmed", "active", "triggered"}


def _extract_value(entry: Dict[str, Any]) -> Optional[float]:
    """
    Treat any numeric as “known”.
    (Trigger maps may use different keys depending on writer.)
    """
    for k in (
        "latest_value",
        "value",
        "current_value",
        "observed_value",
        "last_value",
        "computed_value",
    ):
        v = entry.get(k, None)
        if v is None:
            continue
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)) and v == v:  # not NaN
            return float(v)
    return None


def _weight_from_entry(entry: Dict[str, Any]) -> float:
    w = entry.get("impact_weight", entry.get("weight", None))
    try:
        w = float(w)
        if w != w:  # NaN
            return 0.0
        return max(0.0, w)
    except Exception:
        return 0.0


def _read_trigger_map_from_runtime(base_dir: Path, company_ref: str, fiscal_period: str) -> Optional[Dict[str, Any]]:
    p = base_dir / "company_trigger_maps" / _safe_segment(company_ref) / f"{_safe_segment(fiscal_period)}.json"
    return _read_json(p)


def _read_variable_watch_from_runtime(base_dir: Path, company_ref: str, fiscal_period: str) -> Optional[Dict[str, Any]]:
    p = base_dir / "variable_watch" / _safe_segment(company_ref) / f"{_safe_segment(fiscal_period)}.json"
    return _read_json(p)


def _build_vw_index(vw: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    items: List[Dict[str, Any]] = []
    for k in ("variables", "watch", "entries"):
        if isinstance(vw.get(k), list):
            items = [x for x in vw[k] if isinstance(x, dict)]
            break
    for e in items:
        fid = str(e.get("feed_id") or "").strip()
        tid = str(e.get("trigger_id") or "").strip()
        if fid:
            out[fid] = e
        if tid:
            out[tid] = e
    return out


def _category_for(entry: Dict[str, Any], vw_index: Dict[str, Dict[str, Any]]) -> str:
    cat = entry.get("category") or entry.get("kind") or None
    if isinstance(cat, str) and cat.strip():
        return cat.strip()

    fid = str(entry.get("feed_id") or "").strip()
    tid = str(entry.get("trigger_id") or "").strip()

    for key in (fid, tid):
        if key and key in vw_index:
            c = vw_index[key].get("category")
            if isinstance(c, str) and c.strip():
                return c.strip()

    return "unknown"


def _weight(entry: Dict[str, Any], vw_index: Dict[str, Dict[str, Any]]) -> float:
    """
    priority:
      1) trigger_map impact_weight/weight
      2) variable_watch weight/impact_weight if present
      3) category defaults
    """
    w = _weight_from_entry(entry)
    if w > 0:
        return w

    fid = str(entry.get("feed_id") or "").strip()
    tid = str(entry.get("trigger_id") or "").strip()
    for key in (fid, tid):
        if key and key in vw_index:
            w2 = _weight_from_entry(vw_index[key])
            if w2 > 0:
                return w2

    cat = _category_for(entry, vw_index)
    defaults = {
        "fx": 0.18,
        "commodity": 0.28,
        "subsidiary_leading": 0.20,
        "company_reported": 0.20,
        "computed": 0.10,
        "macro": 0.10,
    }
    return float(defaults.get(cat, 0.10))


def compute_sqi(base_dir: Path, company_ref: str, fiscal_period: str) -> Dict[str, Any]:
    """
    EQ-SQI v2 (policy you asked for):
      - sqi_score ALWAYS float in [0,1]
      - REPORTED vars DO NOT drag the score while the quarter is “in-flight”
        (they show up as quality_flags + missing_reported instead)
      - score is driven by LIVE coverage + live unknown + live conflict
    """
    now = _utc_now_iso()

    tmap = _read_trigger_map_from_runtime(base_dir, company_ref, fiscal_period) or {}
    triggers = _coalesce_trigger_list(tmap)

    vw = _read_variable_watch_from_runtime(base_dir, company_ref, fiscal_period) or {}
    vw_index = _build_vw_index(vw)

    # Totals (ALL)
    known_w_all = 0.0
    unknown_w_all = 0.0
    pos_w = 0.0
    neg_w = 0.0
    neu_w = 0.0

    # Totals (LIVE)
    total_live_w = 0.0
    known_live_w = 0.0
    unknown_live_w = 0.0
    active_pos_live = 0.0
    active_neg_live = 0.0

    # Totals (REPORTED)
    total_reported_w = 0.0
    known_reported_w = 0.0
    missing_reported: List[Dict[str, Any]] = []

    for t in triggers:
        w = _weight(t, vw_index)
        if w <= 0:
            continue

        cat = _category_for(t, vw_index)
        d = _norm_dir(t.get("impact_direction"))
        st = _state(t)
        val = _extract_value(t)

        # direction buckets (ALL weights)
        if d == "pos":
            pos_w += w
        elif d == "neg":
            neg_w += w
        else:
            neu_w += w

        # overall known/unknown (ALL)
        if val is not None:
            known_w_all += w
        else:
            unknown_w_all += w

        # LIVE coverage + penalties
        if cat in LIVE_CATEGORIES:
            total_live_w += w
            if val is not None:
                known_live_w += w
            else:
                unknown_live_w += w

            if _is_active_state(st):
                if d == "pos":
                    active_pos_live += w
                elif d == "neg":
                    active_neg_live += w

        # REPORTED coverage (tracked, but NOT penalizing score)
        elif cat in REPORTED_CATEGORIES:
            total_reported_w += w
            if val is not None:
                known_reported_w += w
            else:
                missing_reported.append(
                    {
                        "trigger_id": t.get("trigger_id"),
                        "feed_id": t.get("feed_id"),
                        "label": t.get("label") or t.get("name"),
                        "category": cat,
                        "impact_weight": w,
                        "state": st,
                    }
                )

    total_w_all = known_w_all + unknown_w_all
    trigger_map_path = str(
        base_dir / "company_trigger_maps" / _safe_segment(company_ref) / f"{_safe_segment(fiscal_period)}.json"
    )

    # Coverage metrics (for dashboard)
    coverage_all = (known_w_all / total_w_all) if total_w_all > 0 else 0.0
    coverage_live = (known_live_w / total_live_w) if total_live_w > 0 else 0.0
    coverage_reported = (known_reported_w / total_reported_w) if total_reported_w > 0 else 0.0

    # Penalties computed ONLY from LIVE vars (this is your requested behavior)
    live_unknown_ratio = (unknown_live_w / total_live_w) if total_live_w > 0 else 1.0
    unknown_penalty = min(0.70, live_unknown_ratio * 0.80)

    denom = max(active_pos_live + active_neg_live, 1e-9)
    conflict = (min(active_pos_live, active_neg_live) / denom)  # 0..0.5-ish
    conflict_penalty = min(0.50, conflict * 0.90)

    dom = max(active_pos_live, active_neg_live) / max(total_live_w, 1e-9) if total_live_w > 0 else 0.0
    signal_bonus = min(0.25, dom * 0.40) * (0.4 + 0.6 * coverage_live)

    net = (active_pos_live - active_neg_live) / max(active_pos_live + active_neg_live, 1e-9)  # -1..1
    leaning = float(net)

    base = coverage_live if total_live_w > 0 else coverage_all
    raw = base - unknown_penalty - conflict_penalty + signal_bonus
    sqi_score = max(0.0, min(1.0, float(raw)))

    quality_flags: List[str] = []
    if total_live_w > 0 and coverage_live < 0.60:
        quality_flags.append("low_live_coverage")
    if missing_reported:
        quality_flags.append("missing_reported_values")
    if total_w_all <= 0:
        quality_flags.append("no_weighted_triggers")

    reason_bits: List[str] = []
    reason_bits.append(f"cov_live={coverage_live:.2f}")
    reason_bits.append(f"cov_all={coverage_all:.2f}")
    reason_bits.append(f"live_unk={live_unknown_ratio:.2f}")
    if conflict_penalty > 0.01:
        reason_bits.append(f"conf={conflict:.2f}")
    if dom > 0.10:
        reason_bits.append(f"dom={dom:.2f}")
    if quality_flags:
        reason_bits.append("flags=" + ",".join(quality_flags))

    return {
        "schema_version": SCHEMA_VERSION_SQI,
        "as_of": now,
        "company_ref": company_ref,
        "fiscal_period_ref": fiscal_period,
        "sqi_score": round(sqi_score, 6),  # ✅ ALWAYS FLOAT
        "leaning": round(leaning, 6),
        # NOTE: keep these as ALL-weights diagnostics (useful in UI)
        "known_weight": round(known_w_all, 6),
        "unknown_weight": round(unknown_w_all, 6),
        "pos_weight": round(pos_w, 6),
        "neg_weight": round(neg_w, 6),
        "neutral_weight": round(neu_w, 6),
        "coverage_live": round(float(coverage_live), 6),
        "coverage_reported": round(float(coverage_reported), 6),
        "coverage_all": round(float(coverage_all), 6),
        "quality_flags": quality_flags,
        "missing_reported": missing_reported[:50],
        "reason_summary": "; ".join(reason_bits)[:240],
        "sqi_debug": {
            "total_w": round(float(total_w_all), 6),
            "total_live_w": round(float(total_live_w), 6),
            "known_live_w": round(float(known_live_w), 6),
            "unknown_live_w": round(float(unknown_live_w), 6),
            "total_reported_w": round(float(total_reported_w), 6),
            "known_reported_w": round(float(known_reported_w), 6),
            "live_unknown_ratio": round(float(live_unknown_ratio), 6),
            "unknown_penalty": round(float(unknown_penalty), 6),
            "conflict": round(float(conflict), 6),
            "conflict_penalty": round(float(conflict_penalty), 6),
            "signal_dom": round(float(dom), 6),
            "signal_bonus": round(float(signal_bonus), 6),
            "base": round(float(base), 6),
            "raw": round(float(raw), 6),
            "active_pos_live": round(float(active_pos_live), 6),
            "active_neg_live": round(float(active_neg_live), 6),
        },
        "computed_from": {
            "trigger_map_path": trigger_map_path,
            "variable_watch_path": str(
                base_dir / "variable_watch" / _safe_segment(company_ref) / f"{_safe_segment(fiscal_period)}.json"
            ),
            "fiscal_period_ref": fiscal_period,
            "timestamp": now,
        },
        "drift": None,
    }


def _ensure_templates(root: Path, company_ref: str, fiscal_period: str) -> Tuple[Optional[Path], Optional[Path]]:
    calib_dir = root / "calibration"
    calib_path = calib_dir / f"{_safe_segment(fiscal_period)}.json"
    if not calib_path.exists():
        _write_json(
            calib_path,
            {
                "schema_version": "aion.equities.calibration.v1",
                "company_ref": company_ref,
                "fiscal_period_ref": fiscal_period,
                "created_at": _utc_now_iso(),
                "predicted": {"composite_fx_estimate": None, "key_triggers_states": {}},
                "actual": {"reported_fx_drag": None, "reported_usg": None, "reported_uvg": None, "reported_uom": None},
                "error_metrics": {"fx_error_pct": None},
                "decisions": {"weight_changes_suggested": [], "threshold_changes_suggested": []},
                "notes": "",
            },
        )

    thesis_dir = root / "thesis"
    thesis_path = thesis_dir / "current.json"
    if not thesis_path.exists():
        _write_json(
            thesis_path,
            {
                "schema_version": "aion.equities.thesis_packet.v1",
                "company_ref": company_ref,
                "created_at": _utc_now_iso(),
                "generated_by": "manual_seed",
                "thesis_direction": "none",
                "entry": None,
                "target": None,
                "stop": None,
                "ev": {},
                "position_size": {"kelly_fraction": None, "caps": {}},
                "time_to_reporting_days": None,
                "status": "watch",
            },
        )

    return calib_path, thesis_path


def _estimate_maturity(base_dir: Path, company_ref: str) -> Dict[str, Any]:
    cref = _safe_segment(company_ref)
    tm_dir = base_dir / "company_trigger_maps" / cref
    vw_dir = base_dir / "variable_watch" / cref

    tm_quarters = sorted([p.stem for p in tm_dir.glob("*.json")]) if tm_dir.exists() else []
    vw_quarters = sorted([p.stem for p in vw_dir.glob("*.json")]) if vw_dir.exists() else []
    quarters = sorted(set(tm_quarters) | set(vw_quarters))

    return {
        "quarters_seen": len(quarters),
        "trigger_maps_seen": len(tm_quarters),
        "variable_watch_seen": len(vw_quarters),
        "latest_quarter": quarters[-1] if quarters else None,
    }


def _compute_acs_bqs(*, maturity: Dict[str, Any], sqi: Dict[str, Any]) -> Tuple[float, float, str]:
    q = float(maturity.get("quarters_seen") or 0)

    unknown_w = float(sqi.get("unknown_weight") or 0.0)
    known_w = float(sqi.get("known_weight") or 0.0)
    total_w = max(known_w + unknown_w, 1e-9)
    unknown_ratio_all = unknown_w / total_w

    coverage_score = max(0.0, 1.0 - unknown_ratio_all)
    quarter_score = min(1.0, q / 8.0)
    acs = 100.0 * (0.55 * coverage_score + 0.45 * quarter_score)

    bqs = 70.0
    notes = f"placeholder: quarters={int(q)}; unknown_ratio_all={unknown_ratio_all:.2f}"
    return round(bqs, 3), round(acs, 3), notes


def update_intelligence_artifacts(
    base_dir: Path,
    company_ref: str,
    fiscal_period: str,
    tick_out: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    company_safe = _company_safe(company_ref)
    root = Path(base_dir) / "company_intelligence" / company_safe

    sqi = compute_sqi(Path(base_dir), company_ref, fiscal_period)

    snap_path = root / "snapshot.json"
    prev_snap = _read_json(snap_path) or {}

    prev_sqi_val: Optional[float] = None
    try:
        v = (prev_snap.get("sqi") or {}).get("sqi_score")
        prev_sqi_val = float(v) if isinstance(v, (int, float)) else None
    except Exception:
        prev_sqi_val = None

    cur_sqi_val: Optional[float] = None
    try:
        v = sqi.get("sqi_score")
        cur_sqi_val = float(v) if isinstance(v, (int, float)) else None
    except Exception:
        cur_sqi_val = None

    sqi["drift"] = (
        round(cur_sqi_val - prev_sqi_val, 6) if (prev_sqi_val is not None and cur_sqi_val is not None) else None
    )

    maturity = _estimate_maturity(Path(base_dir), company_ref)
    bqs, acs, score_notes = _compute_acs_bqs(maturity=maturity, sqi=sqi)

    snapshot = {
        "schema_version": SCHEMA_VERSION_SNAPSHOT,
        "as_of": _utc_now_iso(),
        "company_ref": company_ref,
        "fiscal_period_ref": fiscal_period,
        "maturity": maturity,
        "scores": {"acs": acs, "bqs": bqs, "notes": score_notes, "source": "heuristic_v1"},
        "sqi": sqi,
        "tick_out": tick_out if isinstance(tick_out, dict) else None,
    }
    _write_json(snap_path, snapshot)

    _append_jsonl(
        root / "sqi_history.jsonl",
        {
            "schema_version": sqi.get("schema_version"),
            "as_of": sqi["as_of"],
            "fiscal_period_ref": fiscal_period,
            "sqi_score": sqi.get("sqi_score"),
            "leaning": sqi.get("leaning"),
            "known_weight": sqi.get("known_weight"),
            "unknown_weight": sqi.get("unknown_weight"),
            "pos_weight": sqi.get("pos_weight"),
            "neg_weight": sqi.get("neg_weight"),
            "neutral_weight": sqi.get("neutral_weight"),
            "coverage_live": sqi.get("coverage_live"),
            "coverage_reported": sqi.get("coverage_reported"),
            "coverage_all": sqi.get("coverage_all"),
            "quality_flags": sqi.get("quality_flags"),
            "missing_reported": sqi.get("missing_reported"),
            "drift": sqi.get("drift"),
            "reason_summary": sqi.get("reason_summary"),
            "sqi_debug": sqi.get("sqi_debug"),
            "computed_from": sqi.get("computed_from"),
        },
        dedup_by_day=True,
    )

    _append_jsonl(
        root / "score_history.jsonl",
        {
            "schema_version": SCHEMA_VERSION_SCORE_HISTORY,
            "as_of": snapshot["as_of"],
            "fiscal_period_ref": fiscal_period,
            "bqs": bqs,
            "acs": acs,
            "source": "heuristic_v1",
            "notes": score_notes,
        },
        dedup_by_day=True,
    )

    calib_path, thesis_path = _ensure_templates(root, company_ref, fiscal_period)
    (root / "calibration").mkdir(parents=True, exist_ok=True)
    (root / "thesis").mkdir(parents=True, exist_ok=True)

    return {
        "snapshot": str(snap_path),
        "sqi_history": str(root / "sqi_history.jsonl"),
        "score_history": str(root / "score_history.jsonl"),
        "calibration": str(calib_path) if calib_path else "",
        "thesis_current": str(thesis_path) if thesis_path else "",
    }


__all__ = ["compute_sqi", "update_intelligence_artifacts"]