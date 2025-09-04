# backend/modules/codex/collapse_trace_exporter.py
import os
import json
import logging
import itertools
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Any

from backend.modules.hexcore.memory_engine import MEMORY  # Keep as-is

EXPORT_PATH = "data/logs/collapse_trace_log.dc.json"  # Customize as needed
logger = logging.getLogger(__name__)


def export_collapse_trace(
    expression: str,
    output: str,
    adapter_name: str,
    identity: Optional[str] = None,
    timestamp: Optional[float] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Append a Codex collapse-trace line to the JSONL log at EXPORT_PATH.
    """
    try:
        if timestamp is None:
            timestamp = datetime.utcnow().timestamp()

        ghx_projection_id = extra.get("ghx_projection_id") if extra else None
        vault_snapshot_id = extra.get("vault_snapshot_id") if extra else None
        qglyph_id = extra.get("qglyph_id") if extra else None

        dream_pack = {
            "scroll_tree": getattr(MEMORY, "scroll_tree", None),
            "entropy_state": MEMORY.get_runtime_entropy_snapshot()
            if hasattr(MEMORY, "get_runtime_entropy_snapshot")
            else None,
            "memory_tags": getattr(MEMORY, "active_tags", []),
        }

        trace: Dict[str, Any] = {
            "type": "collapse_trace",
            "expression": expression,
            "output": output,
            "adapter": adapter_name,
            "identity": identity,
            "timestamp": timestamp,
            "hologram": {
                "ghx_data": extra.get("ghx_data") if extra and "ghx_data" in extra else None,
                "trigger_metadata": extra.get("trigger_metadata") if extra and "trigger_metadata" in extra else None,
                "signature_block": {
                    "ghx_projection_id": ghx_projection_id,
                    "vault_snapshot_id": vault_snapshot_id,
                    "qglyph_id": qglyph_id,
                },
                "dream_pack": dream_pack,
            },
        }

        # copy any extra fields (except reserved keys already embedded above)
        if extra:
            for key, value in extra.items():
                if key not in (
                    "ghx_data",
                    "trigger_metadata",
                    "ghx_projection_id",
                    "vault_snapshot_id",
                    "qglyph_id",
                ):
                    trace[key] = value

        os.makedirs(os.path.dirname(EXPORT_PATH), exist_ok=True)
        with open(EXPORT_PATH, "a", encoding="utf-8") as f:
            json.dump(trace, f, ensure_ascii=False)
            f.write("\n")

        logger.info(f"[CollapseTraceExporter] Exported trace for {expression} → {output}")

    except Exception as e:
        logger.error(f"[CollapseTraceExporter] Failed to export collapse trace: {e}")

def log_collapse_trace(wave: "WaveState") -> None:
    """
    Logs a symbolic collapse trace directly from a WaveState instance.
    """
    try:
        timestamp = datetime.utcnow().timestamp()

        trace = {
            "type": "collapse_trace",
            "event": "collapse",
            "wave_id": wave.id,
            "carrier_type": wave.carrier_type,
            "modulation_strategy": wave.modulation_strategy,
            "delay_ms": wave.delay_ms,
            "coherence": getattr(wave, "coherence", None),
            "origin_trace": wave.origin_trace,
            "glyph_data": wave.glyph_data,
            "metadata": wave.metadata,
            "timestamp": timestamp,
        }

        os.makedirs(os.path.dirname(EXPORT_PATH), exist_ok=True)
        with open(EXPORT_PATH, "a", encoding="utf-8") as f:
            json.dump(trace, f, ensure_ascii=False)
            f.write("\n")

        logger.info(f"[CollapseTraceExporter] Logged collapse trace for WaveState {wave.id}")

    except Exception as e:
        logger.error(f"[CollapseTraceExporter] Failed to log WaveState collapse trace: {e}")

def log_beam_prediction(
    container_id: str,
    beam_id: str,
    prediction: Optional[str],
    sqi_score: Optional[float],
    collapse_state: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Logs a prediction + SQI score emitted during wave collapse simulation.

    Used for GHX replay, compliance, mutation audit, etc.
    """
    try:
        timestamp = datetime.utcnow().timestamp()

        trace = {
            "type": "beam_prediction",
            "event": "sqi_prediction",
            "container_id": container_id,
            "beam_id": beam_id,
            "prediction": prediction,
            "sqi_score": sqi_score,
            "collapse_state": collapse_state,
            "metadata": metadata or {},
            "timestamp": timestamp,
        }

        os.makedirs(os.path.dirname(EXPORT_PATH), exist_ok=True)
        with open(EXPORT_PATH, "a", encoding="utf-8") as f:
            json.dump(trace, f, ensure_ascii=False)
            f.write("\n")

        logger.info(f"[CollapseTraceExporter] Logged beam prediction for {beam_id}")

    except Exception as e:
        logger.error(f"[CollapseTraceExporter] Failed to log beam prediction: {e}")

def log_soullaw_event(
    verdict: str,  # "violation" or "approval"
    glyph: str,
    lock_hash: Optional[str] = None,
    triggered_by: Optional[str] = None,
    origin: Optional[str] = "soul_law_validator",
) -> None:
    """
    Log a SoulLaw event into the same JSONL stream as collapse traces.
    """
    try:
        timestamp = datetime.utcnow().timestamp()
        trace = {
            "type": "soullaw_event",
            "event": f"soullaw_{verdict}",
            "glyph": glyph,
            "lock_hash": lock_hash,
            "triggered_by": triggered_by,
            "origin": origin,
            "timestamp": timestamp,
        }

        os.makedirs(os.path.dirname(EXPORT_PATH), exist_ok=True)
        with open(EXPORT_PATH, "a", encoding="utf-8") as f:
            json.dump(trace, f, ensure_ascii=False)
            f.write("\n")

        logger.info(f"[CollapseTraceExporter] Logged SoulLaw {verdict} for glyph: {glyph}")

    except Exception as e:
        logger.warning(f"[CollapseTraceExporter] Failed to log SoulLaw event: {e}")


# --- Compatibility: provide get_recent_collapse_traces for bundle_builder ----
def get_recent_collapse_traces(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Return the most recent collapse traces.

    Preference order:
      1) Canonical exporter in backend.modules.collapse (if present)
      2) Fallback: tail the local JSONL log at EXPORT_PATH
    """
    # Try canonical implementation
    try:
        from backend.modules.collapse.collapse_trace_exporter import (  # type: ignore
            get_recent_collapse_traces as _canonical_get_recent_collapse_traces,
        )

        # Some versions accept (limit) or (limit, load=True). Call defensively.
        try:
            return _canonical_get_recent_collapse_traces(limit)  # simple signature
        except TypeError:
            return _canonical_get_recent_collapse_traces(limit=limit)  # kw-only
    except Exception:
        pass  # fall through to local log tail

    # Fallback: read last N JSON lines of our log
    path = Path(EXPORT_PATH)
    if not path.exists():
        return []

    try:
        with path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        # latest last → first; take last N then reverse back to chronological
        last = list(itertools.islice(reversed(lines), 0, max(0, int(limit))))
        out: List[Dict[str, Any]] = []
        for line in reversed(last):
            try:
                obj = json.loads(line.strip())
                if isinstance(obj, dict):
                    out.append(obj)
            except Exception:
                continue
        return out
    except Exception as e:
        logger.warning(f"[CollapseTraceExporter] Failed to read local collapse traces: {e}")
        return []


__all__ = [
    "export_collapse_trace",
    "log_soullaw_event",
    "get_recent_collapse_traces",
    "log_beam_prediction",
]