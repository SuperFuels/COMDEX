"""
CodexTrace Ingest Bridge
───────────────────────────────────────────────
Bridges MorphicLedger ψ-κ-T-Φ resonance metrics into the CodexTrace
symbolic tracing layer.

Each incoming Morphic Ingest frame is:
  * Normalized into symbolic tags (Ψ, Κ, Τ, Φ)
  * Reduced into coherence events (Δφ, Δσ)
  * Appended to CodexTrace via append_trace_entry()
  * Correlated with prior symbolic states for resonance lineage

Usage:
    PYTHONPATH=. python backend/AION/fabric/codextrace_ingest_bridge.py
"""

import os
import json
import time
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path

# ───────────────────────────────────────────────
# Configuration
# ───────────────────────────────────────────────
MORPHIC_FEED = Path("backend/logs/morphic_ingest_backup.jsonl")
CODEXTRACE_LOG = Path("backend/logs/codextrace_ingest.jsonl")
os.makedirs(CODEXTRACE_LOG.parent, exist_ok=True)

# Event compression
DELTA_THRESHOLDS = {
    "dphi": 0.05,   # resonance drift limit
    "dsigma": 0.04  # coherence deviation threshold
}

# ───────────────────────────────────────────────
# Logging
# ───────────────────────────────────────────────
logger = logging.getLogger("CodexTraceIngest")
logger.setLevel(logging.INFO)

fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%H:%M:%S")
ch = logging.StreamHandler()
ch.setFormatter(fmt)
logger.addHandler(ch)

fh = RotatingFileHandler(CODEXTRACE_LOG.with_suffix(".log"), maxBytes=3_000_000, backupCount=2)
fh.setFormatter(fmt)
logger.addHandler(fh)


# ───────────────────────────────────────────────
# Core: Event Parsing + Compression
# ───────────────────────────────────────────────
def classify_event(dphi, dsigma):
    """Assign symbolic resonance event type."""
    if abs(dphi) < DELTA_THRESHOLDS["dphi"] and abs(dsigma) < DELTA_THRESHOLDS["dsigma"]:
        return "StableResonance"
    if abs(dphi) >= DELTA_THRESHOLDS["dphi"] and abs(dsigma) < DELTA_THRESHOLDS["dsigma"]:
        return "PhaseDrift"
    if abs(dsigma) >= DELTA_THRESHOLDS["dsigma"]:
        return "CoherenceFluctuation"
    return "UnknownEvent"


def codify_packet(packet):
    """Convert Morphic packet into CodexTrace symbolic form."""
    m = packet.get("metrics", {})
    d = packet.get("deltas", {})

    # Safely extract numeric values (fallback to 0.0)
    def safe_num(x):
        try:
            return round(float(x), 5)
        except Exception:
            return 0.0

    entry = {
        "timestamp": packet.get("timestamp"),
        "node": packet.get("node_id"),
        "role": packet.get("role"),
        "ψ": safe_num(m.get("psi")),
        "κ": safe_num(m.get("kappa")),
        "T": safe_num(m.get("T")),
        "Φ": safe_num(m.get("phi")),
        "Δφ": safe_num(d.get("dphi")),
        "Δσ": safe_num(d.get("dsigma")),
    }

    # Classify event type
    if abs(entry["Δφ"]) < 0.05 and abs(entry["Δσ"]) < 0.03:
        entry["event"] = "StableResonance"
    elif abs(entry["Δφ"]) < 0.1:
        entry["event"] = "PhaseDrift"
    else:
        entry["event"] = "CoherenceFluctuation"

    return entry


# ───────────────────────────────────────────────
# Persistence
# ───────────────────────────────────────────────
def append_trace_entry(entry):
    """Append symbolic event to CodexTrace journal."""
    try:
        with open(CODEXTRACE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.warning(f"Failed to write CodexTrace entry: {e}")


def tail_morphic_feed():
    """Continuously tail Morphic Ingest feed and write CodexTrace events."""
    logger.info(f"🔭 Watching Morphic feed: {MORPHIC_FEED}")
    pos = 0
    while True:
        if MORPHIC_FEED.exists():
            with open(MORPHIC_FEED, "r", encoding="utf-8") as f:
                f.seek(pos)
                for line in f:
                    try:
                        packet = json.loads(line.strip())
                        entry = codify_packet(packet)
                        append_trace_entry(entry)
                        logger.info(f"[⇢] CodexTrace event: {entry['event']} "
                                    f"(Δφ={entry['Δφ']:.3f}, Δσ={entry['Δσ']:.3f})")
                    except json.JSONDecodeError:
                        continue
                pos = f.tell()
        time.sleep(2)


# ───────────────────────────────────────────────
# Main
# ───────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("🚀 Launching CodexTrace Ingest Bridge ...")
    tail_morphic_feed()