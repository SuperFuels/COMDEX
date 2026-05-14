#!/usr/bin/env python3
"""
AION Live Dashboard Aggregator (compatible w/ legacy + bridge + cognitive JSONL schemas)

Reads:  data/analysis/aion_live_dashboard.jsonl
Writes: data/analysis/aion_live_dashboard.json

Supports keys:
  - legacy/cognitive: "Φ_coherence", "Φ_entropy", "ΔΦ", "SQI", "Θ_frequency"
  - bridge: "ρ", "Ī", "⟲", plus optional "locked", "lock_id", "threshold"
  - mixed: "Phi_coherence"/"Phi_entropy"/"resonance_delta" aliases

Produces:
  - overall aggregates
  - recent-window aggregates
  - breakdowns by mode/type/base_url/command + lock states
  - homeostasis section (checkpoint counts, lock counts, lock rate, last lock event)
  - meaningful "last" event (skips empty/no-op rows)
  - ΔΦ backfill if producer didn’t log it (derived from consecutive ⟲ values)
"""

from __future__ import annotations

import json
import os
import time
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional, Tuple


LOG = Path("data/analysis/aion_live_dashboard.jsonl")
OUT = Path("data/analysis/aion_live_dashboard.json")

RECENT_N_DEFAULT = int(os.getenv("AION_DASH_RECENT_N", "200"))
TAIL_BYTES_DEFAULT = int(os.getenv("AION_DASH_TAIL_BYTES", "512000"))  # 512KB


def _is_num(x: Any) -> bool:
    return isinstance(x, (int, float)) and x == x  # NaN guard


def _pick_first_num(d: Dict[str, Any], keys: Iterable[str]) -> Optional[float]:
    for k in keys:
        v = d.get(k)
        if _is_num(v):
            return float(v)
    return None


def _pick_first_str(d: Dict[str, Any], keys: Iterable[str]) -> Optional[str]:
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _safe_mean(vals: List[float]) -> Optional[float]:
    return round(mean(vals), 3) if vals else None


def _safe_min(vals: List[float]) -> Optional[float]:
    return round(min(vals), 3) if vals else None


def _safe_max(vals: List[float]) -> Optional[float]:
    return round(max(vals), 3) if vals else None


def _summarize_series(vals: List[float]) -> Dict[str, Optional[float]]:
    return {"avg": _safe_mean(vals), "min": _safe_min(vals), "max": _safe_max(vals), "n": len(vals)}


def _extract_metrics(row: Dict[str, Any]) -> Dict[str, Optional[float]]:
    sqi = _pick_first_num(row, ("SQI", "sqi", "sqi_checkpoint", "avg_SQI"))
    rho = _pick_first_num(row, ("ρ", "Phi_coherence", "Φ_coherence", "rho", "Rho"))
    iota = _pick_first_num(row, ("Ī", "Phi_entropy", "Φ_entropy", "iota", "Iota"))
    dphi = _pick_first_num(row, ("ΔΦ", "dphi", "delta_phi", "resonance_delta", "DeltaPhi"))
    eq = _pick_first_num(row, ("⟲", "res_eq", "equilibrium"))
    theta = _pick_first_num(row, ("Θ_frequency", "theta_frequency", "Theta_frequency"))
    return {"SQI": sqi, "rho": rho, "iota": iota, "dphi": dphi, "eq": eq, "theta": theta}


def _extract_tags(row: Dict[str, Any]) -> Dict[str, Any]:
    mode = _pick_first_str(row, ("mode", "Mode"))
    typ = _pick_first_str(row, ("type", "Type"))
    base_url = _pick_first_str(row, ("base_url", "url", "BaseURL"))
    cmd = _pick_first_str(row, ("command", "cmd", "Command"))

    locked = row.get("locked") if isinstance(row.get("locked"), bool) else None
    lock_id = row.get("lock_id") if isinstance(row.get("lock_id"), str) and row.get("lock_id").strip() else None
    threshold = _pick_first_num(row, ("threshold", "thr"))

    if not typ and cmd:
        if cmd == "sqi_checkpoint" or cmd.startswith("checkpoint"):
            typ = "checkpoint"
        elif cmd == "homeostasis_lock" or cmd.startswith("homeostasis"):
            typ = "homeostasis_lock"

    return {
        "mode": mode,
        "type": typ,
        "base_url": base_url,
        "command": cmd,
        "locked": locked,
        "lock_id": lock_id,
        "threshold": threshold,
    }


def _tail_jsonl(path: Path, max_bytes: int, max_lines: int = 20000) -> Tuple[List[Dict[str, Any]], int]:
    if not path.exists():
        return [], 0

    bad = 0
    rows: List[Dict[str, Any]] = []
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            end = f.tell()
            size = min(end, max_bytes)
            f.seek(max(0, end - size))
            chunk = f.read().decode("utf-8", errors="ignore")

        lines = [ln for ln in chunk.splitlines() if ln.strip()]
        for ln in lines[-max_lines:]:
            try:
                obj = json.loads(ln)
                if isinstance(obj, dict) and obj:
                    rows.append(obj)
                else:
                    bad += 1
            except Exception:
                bad += 1
    except Exception:
        return [], 0

    return rows, bad


def read_rows() -> Tuple[List[Dict[str, Any]], int]:
    if os.getenv("AION_DASH_FULL_READ", "0") == "1":
        rows: List[Dict[str, Any]] = []
        bad = 0
        with open(LOG, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                try:
                    obj = json.loads(s)
                    if isinstance(obj, dict) and obj:
                        rows.append(obj)
                    else:
                        bad += 1
                except Exception:
                    bad += 1
        return rows, bad

    return _tail_jsonl(LOG, max_bytes=TAIL_BYTES_DEFAULT)


def build_summary(rows: List[Dict[str, Any]], bad_lines: int, recent_n: int) -> Dict[str, Any]:
    all_sqi: List[float] = []
    all_rho: List[float] = []
    all_iota: List[float] = []
    all_dphi: List[float] = []
    all_eq: List[float] = []
    all_theta: List[float] = []

    mode_ctr = Counter()
    type_ctr = Counter()
    base_ctr = Counter()
    cmd_ctr = Counter()
    lock_ctr = Counter()

    sqi_checkpoint_events = 0
    homeostasis_lock_events = 0
    locked_true = 0
    locked_false = 0
    last_homeostasis = None

    normalized_rows: List[Dict[str, Any]] = []

    # ΔΦ backfill from ⟲ drift (only if producer didn’t log ΔΦ)
    last_eq_seen: float | None = None

    for r in rows:
        m = _extract_metrics(r)
        t = _extract_tags(r)

        # If producer didn't log ΔΦ, derive it from consecutive ⟲ values (equilibrium drift)
        dphi_filled = m["dphi"]
        if dphi_filled is None and m["eq"] is not None:
            if last_eq_seen is None:
                dphi_filled = None
            else:
                dphi_filled = abs(float(m["eq"]) - float(last_eq_seen))

        if m["eq"] is not None:
            last_eq_seen = float(m["eq"])

        if m["SQI"] is not None:
            all_sqi.append(m["SQI"])
        if m["rho"] is not None:
            all_rho.append(m["rho"])
        if m["iota"] is not None:
            all_iota.append(m["iota"])
        if dphi_filled is not None:
            all_dphi.append(dphi_filled)
        if m["eq"] is not None:
            all_eq.append(m["eq"])
        if m["theta"] is not None:
            all_theta.append(m["theta"])

        if t["mode"]:
            mode_ctr[t["mode"]] += 1
        if t["type"]:
            type_ctr[t["type"]] += 1
        if t["base_url"]:
            base_ctr[t["base_url"]] += 1
        if t["command"]:
            cmd_ctr[t["command"]] += 1

        if t["locked"] is True:
            lock_ctr["locked_true"] += 1
        elif t["locked"] is False:
            lock_ctr["locked_false"] += 1

        nr = {
            "timestamp": r.get("timestamp"),
            "command": t["command"],
            "mode": t["mode"],
            "type": t["type"],
            "base_url": t["base_url"],
            "SQI": m["SQI"],
            "ρ": m["rho"],
            "Ī": m["iota"],
            "ΔΦ": dphi_filled,
            "⟲": m["eq"],
            "Θ_frequency": m["theta"],
            "locked": t["locked"],
            "lock_id": t["lock_id"],
            "threshold": t["threshold"],
        }
        normalized_rows.append(nr)

        if nr["command"] == "sqi_checkpoint" or nr["type"] == "checkpoint":
            sqi_checkpoint_events += 1

        if nr["command"] == "homeostasis_lock" or nr["type"] == "homeostasis_lock":
            homeostasis_lock_events += 1
            last_homeostasis = nr
            if nr.get("locked") is True:
                locked_true += 1
            elif nr.get("locked") is False:
                locked_false += 1

    recent = normalized_rows[-recent_n:] if recent_n > 0 else normalized_rows

    def _series(key: str) -> List[float]:
        out: List[float] = []
        for x in recent:
            v = x.get(key)
            if _is_num(v):
                out.append(float(v))
        return out

    def _is_meaningful(x: Dict[str, Any]) -> bool:
        return any(
            x.get(k) is not None
            for k in ("command", "SQI", "ρ", "Ī", "ΔΦ", "⟲", "locked", "lock_id", "threshold", "Θ_frequency")
        )

    last = None
    for x in reversed(normalized_rows):
        if _is_meaningful(x):
            last = x
            break

    denom = locked_true + locked_false
    locked_rate = round(locked_true / denom, 3) if denom > 0 else None

    return {
        "generated_at": time.time(),
        "events": len(rows),
        "bad_lines": bad_lines,
        "paths": {"log": str(LOG), "out": str(OUT)},
        "all": {
            "SQI": _summarize_series(all_sqi),
            "ρ": _summarize_series(all_rho),
            "Ī": _summarize_series(all_iota),
            "ΔΦ": _summarize_series(all_dphi),
            "⟲": _summarize_series(all_eq),
            "Θ_frequency": _summarize_series(all_theta),
        },
        "recent": {
            "window": min(recent_n, len(rows)) if rows else 0,
            "SQI": _summarize_series(_series("SQI")),
            "ρ": _summarize_series(_series("ρ")),
            "Ī": _summarize_series(_series("Ī")),
            "ΔΦ": _summarize_series(_series("ΔΦ")),
            "⟲": _summarize_series(_series("⟲")),
            "Θ_frequency": _summarize_series(_series("Θ_frequency")),
        },
        "breakdown": {
            "mode": dict(mode_ctr.most_common(20)),
            "type": dict(type_ctr.most_common(20)),
            "base_url": dict(base_ctr.most_common(20)),
            "command": dict(cmd_ctr.most_common(50)),
            "locks": dict(lock_ctr.most_common(10)),
        },
        "homeostasis": {
            "sqi_checkpoint_events": sqi_checkpoint_events,
            "homeostasis_lock_events": homeostasis_lock_events,
            "locked_true": locked_true,
            "locked_false": locked_false,
            "locked_rate": locked_rate,
            "last": last_homeostasis,
        },
        "last": last,
    }


def main() -> None:
    if not LOG.exists():
        print("No dashboard log yet.")
        return

    rows, bad = read_rows()
    summary = build_summary(rows, bad_lines=bad, recent_n=RECENT_N_DEFAULT)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote dashboard summary -> {OUT}")


if __name__ == "__main__":
    main()