# /workspaces/COMDEX/backend/modules/aion_trading/dmip_learning_summary.py
from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


# ---------------------------------------------------------------------
# Paths (read-only summaries over append-only JSONL capture)
# ---------------------------------------------------------------------

_DMIP_LLM_ACCURACY_PATH = Path(".runtime/COMDEX_MOVE/data/trading/dmip_llm_accuracy.jsonl")
_DMIP_TASK_TRACKING_PATH = Path(".runtime/COMDEX_MOVE/data/trading/dmip_task_tracking.jsonl")


# ---------------------------------------------------------------------
# Small safe coercion helpers
# ---------------------------------------------------------------------

def _safe_dict(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> List[Any]:
    return list(value) if isinstance(value, list) else []


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


# ---------------------------------------------------------------------
# JSONL read helpers (fail-open)
# ---------------------------------------------------------------------

def _read_jsonl_rows(
    path: Path,
    *,
    max_rows: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Read JSONL rows fail-open.
    Returns (rows, error_str_or_none).
    """
    try:
        if not path.exists():
            return [], None

        rows: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                try:
                    obj = json.loads(s)
                    if isinstance(obj, dict):
                        rows.append(obj)
                except Exception:
                    # Skip malformed lines (non-blocking)
                    continue

        if isinstance(max_rows, int) and max_rows > 0 and len(rows) > max_rows:
            rows = rows[-max_rows:]

        return rows, None
    except Exception as e:
        return [], f"jsonl_read_error:{e}"


def _apply_time_window(
    rows: Iterable[Dict[str, Any]],
    *,
    since_unix: Optional[float] = None,
    days: Optional[int] = None,
    now_unix: Optional[float] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Filter rows by time window using timestamp_unix.
    """
    now_ts = float(now_unix if now_unix is not None else time.time())
    since_ts: Optional[float] = None

    if since_unix is not None:
        since_ts = float(since_unix)
    elif isinstance(days, int) and days > 0:
        since_ts = now_ts - (days * 86400.0)

    out: List[Dict[str, Any]] = []
    min_ts: Optional[float] = None
    max_ts: Optional[float] = None

    for row in rows:
        ts = _safe_float(row.get("timestamp_unix"), 0.0)
        if ts <= 0:
            continue
        if since_ts is not None and ts < since_ts:
            continue
        out.append(row)
        min_ts = ts if min_ts is None else min(min_ts, ts)
        max_ts = ts if max_ts is None else max(max_ts, ts)

    return out, {
        "now_unix": now_ts,
        "since_unix": since_ts,
        "window_days": days if (isinstance(days, int) and days > 0 and since_unix is None) else None,
        "filtered_min_timestamp_unix": min_ts,
        "filtered_max_timestamp_unix": max_ts,
        "row_count_after_time_filter": len(out),
    }


# ---------------------------------------------------------------------
# Counter utilities
# ---------------------------------------------------------------------

def _counter_dict(counter: Counter) -> Dict[str, int]:
    return {str(k): int(v) for k, v in counter.items()}


def _rate_dict(counter: Counter, total: int) -> Dict[str, float]:
    if total <= 0:
        return {}
    return {str(k): float(v) / float(total) for k, v in counter.items()}


def _bucket_summary(
    *,
    rows: List[Dict[str, Any]],
    key_fn,
) -> Dict[str, Dict[str, Any]]:
    """
    Generic grouping summary for LLM accuracy rows.
    """
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        k = _safe_str(key_fn(row), "unknown") or "unknown"
        groups[k].append(row)

    result: Dict[str, Dict[str, Any]] = {}
    for group_key in sorted(groups.keys()):
        g_rows = groups[group_key]

        agreement_ctr: Counter = Counter()
        selected_bias_ctr: Counter = Counter()
        confidence_ctr: Counter = Counter()

        claude_bias_ctr: Counter = Counter()
        gpt4_bias_ctr: Counter = Counter()

        timestamps: List[float] = []

        for r in g_rows:
            agreement = _safe_str(r.get("agreement"), "unknown").lower() or "unknown"
            selected_bias = _safe_str(r.get("selected_bias"), "UNKNOWN").upper() or "UNKNOWN"
            confidence = _safe_str(r.get("confidence"), "UNKNOWN").upper() or "UNKNOWN"

            llm_pair = _safe_dict(r.get("llm_pair"))
            claude_bias = _safe_str(llm_pair.get("claude_bias"), "UNKNOWN").upper() or "UNKNOWN"
            gpt4_bias = _safe_str(llm_pair.get("gpt4_bias"), "UNKNOWN").upper() or "UNKNOWN"

            ts = _safe_float(r.get("timestamp_unix"), 0.0)
            if ts > 0:
                timestamps.append(ts)

            agreement_ctr[agreement] += 1
            selected_bias_ctr[selected_bias] += 1
            confidence_ctr[confidence] += 1
            claude_bias_ctr[claude_bias] += 1
            gpt4_bias_ctr[gpt4_bias] += 1

        n = len(g_rows)
        result[group_key] = {
            "sample_size": n,
            "agreement_counts": _counter_dict(agreement_ctr),
            "agreement_rates": _rate_dict(agreement_ctr, n),
            "selected_bias_counts": _counter_dict(selected_bias_ctr),
            "selected_bias_rates": _rate_dict(selected_bias_ctr, n),
            "confidence_counts": _counter_dict(confidence_ctr),
            "confidence_rates": _rate_dict(confidence_ctr, n),
            "claude_bias_counts": _counter_dict(claude_bias_ctr),
            "gpt4_bias_counts": _counter_dict(gpt4_bias_ctr),
            "min_timestamp_unix": (min(timestamps) if timestamps else None),
            "max_timestamp_unix": (max(timestamps) if timestamps else None),
        }

    return result


# ---------------------------------------------------------------------
# Public summaries
# ---------------------------------------------------------------------

def summarize_llm_accuracy(
    *,
    days: Optional[int] = 30,
    since_unix: Optional[float] = None,
    max_rows: Optional[int] = 10000,
    path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Summarize DMIP LLM accuracy capture rows into weighting-ready aggregates.

    Non-blocking / fail-open contract.
    """
    target_path = path or _DMIP_LLM_ACCURACY_PATH
    raw_rows, read_err = _read_jsonl_rows(target_path, max_rows=max_rows)
    filtered_rows, window_meta = _apply_time_window(
        raw_rows,
        since_unix=since_unix,
        days=days,
    )

    # Normalize only known schema-ish rows, but tolerate evolution
    rows: List[Dict[str, Any]] = []
    for r in filtered_rows:
        rows.append(_safe_dict(r))

    total = len(rows)
    agreement_ctr: Counter = Counter()
    selected_bias_ctr: Counter = Counter()
    confidence_ctr: Counter = Counter()
    checkpoint_ctr: Counter = Counter()
    pair_ctr: Counter = Counter()

    for r in rows:
        agreement_ctr[_safe_str(r.get("agreement"), "unknown").lower() or "unknown"] += 1
        selected_bias_ctr[_safe_str(r.get("selected_bias"), "UNKNOWN").upper() or "UNKNOWN"] += 1
        confidence_ctr[_safe_str(r.get("confidence"), "UNKNOWN").upper() or "UNKNOWN"] += 1
        checkpoint_ctr[_safe_str(r.get("checkpoint"), "unknown") or "unknown"] += 1
        pair_ctr[_safe_str(r.get("pair"), "unknown") or "unknown"] += 1

    by_pair = _bucket_summary(rows=rows, key_fn=lambda r: r.get("pair"))
    by_checkpoint = _bucket_summary(rows=rows, key_fn=lambda r: r.get("checkpoint"))

    # pair+checkpoint composite buckets (useful for weighting synthesis)
    by_pair_checkpoint = _bucket_summary(
        rows=rows,
        key_fn=lambda r: f"{_safe_str(r.get('pair'),'unknown')}|{_safe_str(r.get('checkpoint'),'unknown')}",
    )

    out: Dict[str, Any] = {
        "ok": True,
        "non_blocking": True,
        "schema_version": "aion.dmip_learning_summary_result.v1",
        "summary_type": "llm_accuracy",
        "path": str(target_path),
        "counts": {
            "rows_read": len(raw_rows),
            "rows_summarized": total,
        },
        "recency_window": window_meta,
        "totals": {
            "sample_size": total,
            "agreement_counts": _counter_dict(agreement_ctr),
            "agreement_rates": _rate_dict(agreement_ctr, total),
            "selected_bias_counts": _counter_dict(selected_bias_ctr),
            "selected_bias_rates": _rate_dict(selected_bias_ctr, total),
            "confidence_counts": _counter_dict(confidence_ctr),
            "confidence_rates": _rate_dict(confidence_ctr, total),
            "checkpoint_counts": _counter_dict(checkpoint_ctr),
            "pair_counts": _counter_dict(pair_ctr),
        },
        "by_pair": by_pair,
        "by_checkpoint": by_checkpoint,
        "by_pair_checkpoint": by_pair_checkpoint,
        "warnings": [],
        "error": None,
        "message": None,
    }

    if read_err:
        out["ok"] = False
        out["error"] = "llm_accuracy_summary_read_error"
        out["message"] = read_err
        out["warnings"] = ["read_failed_fail_open"]

    return out


def summarize_task_tracking(
    *,
    days: Optional[int] = 30,
    since_unix: Optional[float] = None,
    max_rows: Optional[int] = 10000,
    path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Optional task tracking summary (useful for operational evidence / P3R).
    """
    target_path = path or _DMIP_TASK_TRACKING_PATH
    raw_rows, read_err = _read_jsonl_rows(target_path, max_rows=max_rows)
    filtered_rows, window_meta = _apply_time_window(
        raw_rows,
        since_unix=since_unix,
        days=days,
    )

    rows = [_safe_dict(r) for r in filtered_rows]
    total = len(rows)

    stage_ctr: Counter = Counter()
    status_ctr: Counter = Counter()
    checkpoint_ctr: Counter = Counter()
    pair_ctr: Counter = Counter()

    for r in rows:
        stage_ctr[_safe_str(r.get("stage"), "unknown") or "unknown"] += 1
        status_ctr[_safe_str(r.get("status"), "unknown") or "unknown"] += 1
        checkpoint_ctr[_safe_str(r.get("checkpoint"), "unknown") or "unknown"] += 1
        pair_ctr[_safe_str(r.get("pair"), "unknown") or "unknown"] += 1

    out: Dict[str, Any] = {
        "ok": True,
        "non_blocking": True,
        "schema_version": "aion.dmip_learning_summary_result.v1",
        "summary_type": "task_tracking",
        "path": str(target_path),
        "counts": {
            "rows_read": len(raw_rows),
            "rows_summarized": total,
        },
        "recency_window": window_meta,
        "totals": {
            "sample_size": total,
            "stage_counts": _counter_dict(stage_ctr),
            "stage_rates": _rate_dict(stage_ctr, total),
            "status_counts": _counter_dict(status_ctr),
            "status_rates": _rate_dict(status_ctr, total),
            "checkpoint_counts": _counter_dict(checkpoint_ctr),
            "pair_counts": _counter_dict(pair_ctr),
        },
        "warnings": [],
        "error": None,
        "message": None,
    }

    if read_err:
        out["ok"] = False
        out["error"] = "task_tracking_summary_read_error"
        out["message"] = read_err
        out["warnings"] = ["read_failed_fail_open"]

    return out


def get_llm_weighting_summary(
    *,
    days: Optional[int] = 30,
    since_unix: Optional[float] = None,
    pair: Optional[str] = None,
    checkpoint: Optional[str] = None,
    max_rows: Optional[int] = 10000,
) -> Dict[str, Any]:
    """
    Weighting-ready read-only summary facade for P3C / P3D.

    Returns:
      - global summary
      - optional focused bucket summary for pair/checkpoint
      - simple weighting hints (sample-size + agreement-based)
    """
    base = summarize_llm_accuracy(
        days=days,
        since_unix=since_unix,
        max_rows=max_rows,
    )

    # Fail-open passthrough
    if not bool(base.get("ok", False)):
        return {
            **base,
            "summary_type": "llm_weighting_summary",
            "focus": {
                "pair": _safe_str(pair) or None,
                "checkpoint": _safe_str(checkpoint) or None,
            },
            "weighting_hints": {},
        }

    focus_pair = _safe_str(pair)
    focus_checkpoint = _safe_str(checkpoint)

    focused: Dict[str, Any] = {}
    if focus_pair and focus_checkpoint:
        key = f"{focus_pair}|{focus_checkpoint}"
        focused = _safe_dict(base.get("by_pair_checkpoint", {}).get(key))
    elif focus_pair:
        focused = _safe_dict(base.get("by_pair", {}).get(focus_pair))
    elif focus_checkpoint:
        focused = _safe_dict(base.get("by_checkpoint", {}).get(focus_checkpoint))

    sample_size = _safe_int(focused.get("sample_size"), 0) if focused else 0
    agreement_rates = _safe_dict(focused.get("agreement_rates")) if focused else {}
    agree_rate = _safe_float(agreement_rates.get("agree"), 0.0)
    disagree_rate = _safe_float(agreement_rates.get("disagree"), 0.0)

    # Lightweight hinting only (P3D prep), no direct writes/actions
    confidence_band = "LOW"
    if sample_size >= 50 and agree_rate >= 0.70 and disagree_rate <= 0.20:
        confidence_band = "HIGH"
    elif sample_size >= 15 and agree_rate >= 0.55:
        confidence_band = "MEDIUM"

    weighting_hints = {
        "ok": True,
        "read_only": True,
        "focus_pair": (focus_pair or None),
        "focus_checkpoint": (focus_checkpoint or None),
        "sample_size": sample_size,
        "agree_rate": agree_rate,
        "disagree_rate": disagree_rate,
        "confidence_band": confidence_band,
        "notes": [
            "summary_based_hint_only",
            "no_risk_invariants_mutated",
            "use_as_input_to_governed_weighting_not_direct_write",
        ],
    }

    return {
        **base,
        "summary_type": "llm_weighting_summary",
        "focus": {
            "pair": (focus_pair or None),
            "checkpoint": (focus_checkpoint or None),
            "bucket": focused,
        },
        "weighting_hints": weighting_hints,
    }