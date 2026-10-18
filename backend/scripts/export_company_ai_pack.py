from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _safe_segment(value: str) -> str:
    return str(value).replace("/", "_").replace("\\", "_").replace(":", "-").strip()


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _tail_jsonl(path: Path, n: int = 200) -> List[Dict[str, Any]]:
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


def _list_periods(base_dir: Path, company_safe: str) -> List[str]:
    periods: set[str] = set()

    d_tm = base_dir / "company_trigger_maps" / company_safe
    if d_tm.exists():
        periods.update(p.stem for p in d_tm.glob("*.json"))

    d_vw = base_dir / "variable_watch" / company_safe
    if d_vw.exists():
        periods.update(p.stem for p in d_vw.glob("*.json"))

    d_c = base_dir / "commentary" / company_safe
    if d_c.exists():
        periods.update(p.stem for p in d_c.glob("*.json"))

    return sorted(periods)


def _paths(base_dir: Path, company_ref: str, period: str) -> Dict[str, Path]:
    cs = _safe_segment(company_ref)
    ps = _safe_segment(period)
    return {
        "variable_watch": base_dir / "variable_watch" / cs / f"{ps}.json",
        "trigger_map": base_dir / "company_trigger_maps" / cs / f"{ps}.json",
        "commentary": base_dir / "commentary" / cs / f"{ps}.json",
        "parsed_text": base_dir / "parsed_text" / f"{cs}_{ps}.txt",
    }


def _market_snapshot_paths(base_dir: Path, company_ref: str) -> Dict[str, Path]:
    cs = _safe_segment(company_ref)
    root = base_dir / "market_snapshots" / cs
    return {
        "root": root,
        "current": root / "current.json",
    }


def _list_market_snapshot_history(base_dir: Path, company_ref: str, n: int = 50) -> List[Dict[str, Any]]:
    cs = _safe_segment(company_ref)
    root = base_dir / "market_snapshots" / cs
    if not root.exists():
        return []

    out: List[Dict[str, Any]] = []
    files = sorted(
        [p for p in root.glob("*.json") if p.name != "current.json"],
        key=lambda p: p.name
    )[-n:]

    for p in files:
        obj = _read_json(p)
        if isinstance(obj, dict):
            out.append(obj)

    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-dir", default=str(Path(".runtime/equities").resolve()))
    ap.add_argument("--company-ref", required=True)  # e.g. company/PAGE.L
    ap.add_argument("--last", type=int, default=10)
    ap.add_argument("--out", default=None)  # e.g. _inputs/ai_exports/company_PAGE.L_last10.json
    ap.add_argument("--history-tail", type=int, default=120)
    ap.add_argument("--market-history-tail", type=int, default=20)
    args = ap.parse_args()

    base_dir = Path(args.base_dir).resolve()
    company_ref = str(args.company_ref).strip()
    company_safe = _safe_segment(company_ref)

    periods_all = _list_periods(base_dir, company_safe)
    periods = periods_all[-max(1, int(args.last)):] if periods_all else []

    intel_root = base_dir / "company_intelligence" / company_safe
    snapshot = _read_json(intel_root / "snapshot.json")
    sqi_hist = _tail_jsonl(intel_root / "sqi_history.jsonl", n=int(args.history_tail))
    score_hist = _tail_jsonl(intel_root / "score_history.jsonl", n=int(args.history_tail))
    thesis_cur = _read_json(intel_root / "thesis" / "current.json")

    market_paths = _market_snapshot_paths(base_dir, company_ref)
    market_current = _read_json(market_paths["current"])
    market_history = _list_market_snapshot_history(
        base_dir,
        company_ref,
        n=int(args.market_history_tail),
    )

    items: List[Dict[str, Any]] = []
    all_feed_ids: set[str] = set()

    for per in periods:
        p = _paths(base_dir, company_ref, per)
        vw = _read_json(p["variable_watch"]) or {}
        tm = _read_json(p["trigger_map"]) or {}
        cm = _read_json(p["commentary"]) or {}

        vars_ = vw.get("variables") if isinstance(vw.get("variables"), list) else []
        for v in vars_:
            if isinstance(v, dict) and v.get("feed_id"):
                all_feed_ids.add(str(v["feed_id"]))

        trig = tm.get("trigger_entries")
        if not isinstance(trig, list):
            trig = tm.get("triggers")
        if isinstance(trig, list):
            for t in trig:
                if isinstance(t, dict) and t.get("feed_id"):
                    all_feed_ids.add(str(t["feed_id"]))

        items.append(
            {
                "fiscal_period_ref": per,
                "paths": {k: str(v) for k, v in p.items()},
                "commentary": cm,
                "variable_watch": vw,
                "trigger_map": tm,
            }
        )

    out_obj: Dict[str, Any] = {
        "company_ref": company_ref,
        "periods_included": periods,
        "period_count": len(periods),
        "feed_ids_union": sorted(all_feed_ids),
        "intelligence": {
            "snapshot": snapshot,
            "sqi_history_tail": sqi_hist,
            "score_history_tail": score_hist,
            "thesis_current": thesis_cur,
        },
        "market": {
            "paths": {k: str(v) for k, v in market_paths.items()},
            "current": market_current,
            "history_tail": market_history,
        },
        "period_artifacts": items,
    }

    out_path = Path(args.out) if args.out else Path("_inputs/ai_exports") / f"{company_safe}_last{len(periods)}.json"
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK: wrote AI pack -> {out_path}")
    print(f"periods: {periods}")
    if market_current:
        print("market_snapshot: found")
    else:
        print("market_snapshot: missing")


if __name__ == "__main__":
    main()