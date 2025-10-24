# ================================================================
# 📡 CEE Exercise Telemetry Bridge — Phase 45G.8
# ================================================================
"""
Links CEE Lexical Exercise Runtime sessions to CodexMetrics/GHX telemetry.

Consumes:
    data/sessions/lexsession_v1.qdata.json

Produces/updates:
    data/telemetry/lexsession_metrics_overlay.json
    data/telemetry/ghx_sync_log.json

Purpose:
    - Aggregate performance across sessions
    - Feed resonance stats into CodexMetrics dashboard
    - Maintain GHX feedback synchronization log
"""

import json, logging, time
from pathlib import Path

IN_PATH = Path("data/sessions/lexsession_v1.qdata.json")
OUT_OVERLAY = Path("data/telemetry/lexsession_metrics_overlay.json")
OUT_LOG = Path("data/telemetry/ghx_sync_log.json")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
def load_session():
    """Load the most recent lexical session summary."""
    if not IN_PATH.exists():
        logger.warning(f"[CEE-Telemetry] Missing session file: {IN_PATH}")
        return None
    try:
        with open(IN_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[CEE-Telemetry] Could not parse {IN_PATH}: {e}")
        return None

# ----------------------------------------------------------------------
def push_to_codexmetrics(summary: dict):
    """Generate CodexMetrics-compatible overlay."""
    metrics = {
        "timestamp": summary["timestamp"],
        "session": summary["session"],
        "entries": summary["entries"],
        "resonance": summary["averages"]["ρ̄"],
        "intensity": summary["averages"]["Ī"],
        "SQI": summary["averages"]["SQĪ"],
        "performance": summary["averages"]["performance"],
        "schema": "LexTelemetryOverlay.v1",
    }
    OUT_OVERLAY.parent.mkdir(parents=True, exist_ok=True)
    json.dump(metrics, open(OUT_OVERLAY, "w"), indent=2)
    logger.info(f"[CEE-Telemetry] Overlay exported → {OUT_OVERLAY}")
    return metrics

# ----------------------------------------------------------------------
def sync_to_ghx(metrics: dict):
    """Append synchronization log entry for GHX feedback loop."""
    entry = {
        "timestamp": time.time(),
        "source": "CEE-Lexical",
        "synced_metrics": metrics,
        "status": "ok",
    }

    OUT_LOG.parent.mkdir(parents=True, exist_ok=True)
    if OUT_LOG.exists():
        try:
            log = json.load(open(OUT_LOG))
            if not isinstance(log, list):
                log = [log]
        except Exception:
            log = []
    else:
        log = []

    log.append(entry)
    json.dump(log, open(OUT_LOG, "w"), indent=2)
    logger.info(f"[CEE-Telemetry] GHX sync logged ({len(log)} entries)")
    return entry

# ----------------------------------------------------------------------
def transmit():
    """Main telemetry pipeline: session → metrics overlay → GHX log."""
    summary = load_session()
    if not summary:
        return None
    metrics = push_to_codexmetrics(summary)
    sync_to_ghx(metrics)
    print(json.dumps(metrics, indent=2))
    return metrics

# ----------------------------------------------------------------------
if __name__ == "__main__":
    transmit()