from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

OUTPUT = Path("backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs")
REPORT_JSON = OUTPUT / "symatics_symbol_decoder_report.json"


def _as_float(x, default=0.0):
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default


def _extract_symbol_from_obj(obj: object) -> str:
    if not isinstance(obj, dict):
        return ""
    for key in ("symbol_id", "symbol", "predicted_symbol", "id", "name"):
        v = obj.get(key)
        if v not in (None, ""):
            s = str(v)
            # prefer actual IDs like S1/S2/S4 over long names
            if s.startswith("S"):
                return s
            return s
    return ""


def _extract_pred_symbol(row: dict) -> str:
    # direct flat fields
    for key in ("predicted_symbol", "symbol_id", "predicted", "winner", "best_symbol"):
        v = row.get(key)
        if v not in (None, ""):
            s = str(v)
            # sometimes "S2 | S2_beyond_boolean_positive_1_2"
            if "|" in s:
                s = s.split("|", 1)[0].strip()
            return s

    # nested predicted / best_match
    for key in ("predicted_obj", "predicted_match", "predicted", "best_match", "winner_obj"):
        s = _extract_symbol_from_obj(row.get(key))
        if s:
            return s

    # fallback to top match
    top_matches = row.get("top_matches") or []
    if isinstance(top_matches, list) and len(top_matches) >= 1:
        s = _extract_symbol_from_obj(top_matches[0])
        if s:
            return s

    return "?"


def _extract_margin(row: dict) -> float:
    for key in ("runner_up_margin", "margin"):
        if row.get(key) not in (None, ""):
            return _as_float(row.get(key), 0.0)

    runner_up = row.get("runner_up") or {}
    if isinstance(runner_up, dict):
        for key in ("margin", "distance_margin"):
            if runner_up.get(key) not in (None, ""):
                return _as_float(runner_up.get(key), 0.0)

    top_matches = row.get("top_matches") or []
    if isinstance(top_matches, list) and len(top_matches) >= 2:
        d0 = _as_float((top_matches[0] or {}).get("distance"), 0.0)
        d1 = _as_float((top_matches[1] or {}).get("distance"), 0.0)
        return max(0.0, d1 - d0)

    return 0.0


def _extract_runner_up_symbol(row: dict) -> str:
    runner_up = row.get("runner_up") or {}
    s = _extract_symbol_from_obj(runner_up)
    if s:
        return s

    top_matches = row.get("top_matches") or []
    if isinstance(top_matches, list) and len(top_matches) >= 2:
        s = _extract_symbol_from_obj(top_matches[1])
        if s:
            return s

    return "?"


def _load_rows() -> list[dict]:
    payload = json.loads(REPORT_JSON.read_text(encoding="utf-8"))

    if isinstance(payload, list):
        return payload

    for key in ("rows", "observations", "results", "report"):
        v = payload.get(key)
        if isinstance(v, list):
            return v

    raise RuntimeError("Could not find decoder rows in report JSON")


def main() -> None:
    rows = _load_rows()

    normalized = []
    for row in rows:
        pred = _extract_pred_symbol(row)
        semantic = row.get("semantic_state") or row.get("semantic") or "?"
        confidence = _as_float(row.get("confidence"), 0.0)
        margin = _extract_margin(row)
        runner_up = _extract_runner_up_symbol(row)
        source = row.get("source_name") or row.get("source") or "?"

        normalized.append(
            {
                "source": source,
                "pred": str(pred),
                "semantic": str(semantic),
                "confidence": confidence,
                "margin": margin,
                "runner_up": runner_up,
            }
        )

    known = sorted({r["pred"] for r in normalized})
    print(f"Known symbols: {known}")
    print(f"Decoder rows : {len(normalized)}")
    print()

    clusters: dict[str, list[dict]] = {}
    for row in normalized:
        clusters.setdefault(row["pred"], []).append(row)

    print("=== Cluster summary ===")
    for symbol, group in sorted(clusters.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        conf_mean = mean(r["confidence"] for r in group)
        margin_mean = mean(r["margin"] for r in group)
        print(
            f"  {symbol} | count={len(group):3d} | "
            f"conf_mean={conf_mean:0.6f} | margin_mean={margin_mean:0.6f}"
        )

    print()
    print("=== Weak / ambiguous rows to inspect ===")
    weak = sorted(
        normalized,
        key=lambda r: (r["margin"], r["confidence"], r["source"])
    )[:30]

    for r in weak:
        print(
            f"{r['source']} | pred={r['pred']:>3} | runner_up={r['runner_up']:>3} | "
            f"conf={r['confidence']:9.6f} | margin={r['margin']:9.6f}"
        )

    print()
    print("=== Promotion hint ===")
    print("Promote only candidates that recur, remain stable, and stay separable from S1/S2/S4.")


if __name__ == "__main__":
    main()