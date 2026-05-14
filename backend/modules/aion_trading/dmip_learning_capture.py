from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------
# Paths (append-only JSONL, paper-safe)
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


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"1", "true", "yes", "y", "on"}:
            return True
        if v in {"0", "false", "no", "n", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def _safe_float_list(value: Any, *, limit: int = 8) -> List[float]:
    out: List[float] = []
    for x in _safe_list(value)[: max(0, int(limit))]:
        try:
            out.append(float(x))
        except Exception:
            continue
    return out


# ---------------------------------------------------------------------
# JSONL append helper
# ---------------------------------------------------------------------

def _atomic_append_jsonl(path: Path, row: Dict[str, Any]) -> None:
    """
    Simple append-safe JSONL write.
    Creates parent directory if needed.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(line)


# ---------------------------------------------------------------------
# Builders (schema-stable rows)
# ---------------------------------------------------------------------

def _build_llm_accuracy_row(
    *,
    checkpoint: str,
    pair: str,
    llm_pair: Dict[str, Any],
    agreement: str,
    selected_bias: str,
    confidence: str,
    source: str,
) -> Dict[str, Any]:
    llm_pair = _safe_dict(llm_pair)

    return {
        "schema_version": "aion.dmip_llm_accuracy_event.v1",
        "event_id": f"dmip_llmacc_{uuid.uuid4().hex[:16]}",
        "timestamp_unix": time.time(),
        "checkpoint": _safe_str(checkpoint),
        "pair": _safe_str(pair),
        "source": _safe_str(source, "dmip_runtime") or "dmip_runtime",
        "agreement": _safe_str(agreement, "partial").lower() or "partial",
        "selected_bias": _safe_str(selected_bias).upper(),
        "confidence": _safe_str(confidence).upper(),
        "llm_pair": {
            "claude_bias": _safe_str(llm_pair.get("claude_bias")).upper(),
            "gpt4_bias": _safe_str(llm_pair.get("gpt4_bias")).upper(),
            "confidence": _safe_str(llm_pair.get("confidence")).upper(),
            "key_levels": _safe_float_list(llm_pair.get("key_levels"), limit=8),
            "has_extra_fields": len(llm_pair) > 4,
        },
        "metadata": {
            "capture_layer": "dmip_learning_capture",
            "non_blocking": True,
            "paper_safe": True,
        },
    }


def _build_task_tracking_row(
    *,
    checkpoint: str,
    pair: str,
    stage: str,
    status: str,
    details: Dict[str, Any],
    source: str,
) -> Dict[str, Any]:
    return {
        "schema_version": "aion.dmip_task_tracking_event.v1",
        "event_id": f"dmip_task_{uuid.uuid4().hex[:16]}",
        "timestamp_unix": time.time(),
        "checkpoint": _safe_str(checkpoint),
        "pair": _safe_str(pair),
        "stage": _safe_str(stage),
        "status": _safe_str(status),
        "source": _safe_str(source, "dmip_runtime") or "dmip_runtime",
        "details": _safe_dict(details),
        "metadata": {
            "capture_layer": "dmip_learning_capture",
            "non_blocking": True,
            "paper_safe": True,
        },
    }


# ---------------------------------------------------------------------
# Public API (non-blocking-friendly stubs with real append)
# ---------------------------------------------------------------------

def log_llm_accuracy_stub(
    *,
    checkpoint: str,
    pair: str,
    llm_pair: Dict[str, Any],
    agreement: str,
    selected_bias: str,
    confidence: str,
    source: str = "dmip_runtime",
) -> Dict[str, Any]:
    """
    Append-only capture for DMIP LLM consultation processing.

    Contract is intentionally non-blocking-friendly:
      - returns structured result
      - no exception leak (fail-open)
      - includes `non_blocking=True`
    """
    row = _build_llm_accuracy_row(
        checkpoint=checkpoint,
        pair=pair,
        llm_pair=_safe_dict(llm_pair),
        agreement=agreement,
        selected_bias=selected_bias,
        confidence=confidence,
        source=source,
    )

    out: Dict[str, Any] = {
        "ok": False,
        "non_blocking": True,
        "event": "llm_accuracy_logged",
        "capture_type": "dmip_llm_accuracy_append",
        "path": str(_DMIP_LLM_ACCURACY_PATH),
        "event_id": row["event_id"],
        "checkpoint": row["checkpoint"],
        "pair": row["pair"],
        "agreement": row["agreement"],
        "selected_bias": row["selected_bias"],
        "confidence": row["confidence"],
        "row": row,
        "error": None,
        "message": None,
    }

    try:
        _atomic_append_jsonl(_DMIP_LLM_ACCURACY_PATH, row)
        out["ok"] = True
    except Exception as e:
        out["ok"] = False
        out["error"] = "dmip_llm_accuracy_append_failed"
        out["message"] = str(e)

    return out


def log_task_tracking_stub(
    *,
    checkpoint: str,
    pair: str,
    stage: str,
    status: str,
    details: Optional[Dict[str, Any]] = None,
    source: str = "dmip_runtime",
) -> Dict[str, Any]:
    """
    Append-only task tracking capture for DMIP processing stages.
    Non-blocking by design.
    """
    row = _build_task_tracking_row(
        checkpoint=checkpoint,
        pair=pair,
        stage=stage,
        status=status,
        details=_safe_dict(details),
        source=source,
    )

    out: Dict[str, Any] = {
        "ok": False,
        "non_blocking": True,
        "event": "dmip_task_tracked",
        "capture_type": "dmip_task_tracking_append",
        "path": str(_DMIP_TASK_TRACKING_PATH),
        "event_id": row["event_id"],
        "checkpoint": row["checkpoint"],
        "pair": row["pair"],
        "stage": row["stage"],
        "status": row["status"],
        "row": row,
        "error": None,
        "message": None,
    }

    try:
        _atomic_append_jsonl(_DMIP_TASK_TRACKING_PATH, row)
        out["ok"] = True
    except Exception as e:
        out["ok"] = False
        out["error"] = "dmip_task_tracking_append_failed"
        out["message"] = str(e)

    return out
