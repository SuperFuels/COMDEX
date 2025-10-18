"""
Morphic Ingest Bridge
────────────────────────────────────────────
Records ψ–κ–T–Φ resonance metrics and coherence drift (Δφ, Δσ)
from the Resonant Synchronization Layer into the MorphicLedger.

Each received sync packet:
  • Computes local deltas between previous and current ψ–κ–T–Φ values
  • Writes coherent state deltas into the MorphicLedger (if available)
  • Falls back to JSONL backup log if Ledger unavailable

Used by:
  backend/AION/system/network_sync/orchestrator.py
────────────────────────────────────────────
"""

import os
import time
import json
import traceback
from datetime import datetime

# ───────────────────────────────────────────────
# MorphicLedger Import (safe fallback)
# ───────────────────────────────────────────────
try:
    from backend.modules.holograms.morphic_ledger import MorphicLedger
    LEDGER_AVAILABLE = True
except Exception as e:
    print(f"[⚠️ MorphicIngestBridge] MorphicLedger unavailable: {e}")
    LEDGER_AVAILABLE = False
    MorphicLedger = None

# ───────────────────────────────────────────────
# Configuration
# ───────────────────────────────────────────────
BACKUP_LOG = "backend/logs/morphic_ingest_backup.jsonl"
os.makedirs(os.path.dirname(BACKUP_LOG), exist_ok=True)

# cache of last known node states for delta computation
_last_state = {}

# ───────────────────────────────────────────────
# Utility Functions
# ───────────────────────────────────────────────
def compute_deltas(node_id, metrics):
    """Compute Δφ and Δσ (stability drift) between previous and current states."""
    prev = _last_state.get(node_id)
    if not prev:
        _last_state[node_id] = metrics
        return {"dphi": 0.0, "dsigma": 0.0}

    dphi = metrics["phi"] - prev["phi"]
    dsigma = (
        abs(metrics["psi"] - prev["psi"]) +
        abs(metrics["kappa"] - prev["kappa"]) +
        abs(metrics["T"] - prev["T"])
    ) / 3.0

    _last_state[node_id] = metrics
    return {"dphi": round(dphi, 6), "dsigma": round(dsigma, 6)}

# ───────────────────────────────────────────────
# Fallback write
# ───────────────────────────────────────────────
def backup_write(entry):
    """Append a record to the local JSONL file if MorphicLedger is unavailable."""
    try:
        with open(BACKUP_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"[❌ MorphicIngestBridge] Failed to write backup log: {e}")

# ───────────────────────────────────────────────
# Main Ingest Function
# ───────────────────────────────────────────────
def ingest_sync_packet(packet):
    """
    Called by orchestrator after each sync update.
    Records resonance metrics and deltas to MorphicLedger or backup.
    """
    try:
        node_id = packet.get("node_id", "unknown")
        metrics = {k: packet.get(k) for k in ["psi", "kappa", "T", "phi"]}
        deltas = compute_deltas(node_id, metrics)

        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "node_id": node_id,
            "role": packet.get("role"),
            "metrics": metrics,
            "deltas": deltas,
        }

        # write to MorphicLedger
        if LEDGER_AVAILABLE:
            try:
                ledger = MorphicLedger.get_instance()
                ledger.append_entry(
                    stream="ResonantSyncFeed",
                    data=record,
                    tags=["resonance", "sync", node_id]
                )
                print(f"[🧭 MorphicIngest] {node_id} Δφ={deltas['dphi']:.3f} Δσ={deltas['dsigma']:.3f}")
            except Exception as le:
                print(f"[⚠️ MorphicIngestBridge] Ledger write failed: {le}")
                backup_write(record)
        else:
            backup_write(record)

    except Exception as e:
        print(f"[❌ MorphicIngestBridge] Ingest error: {e}")
        print(traceback.format_exc())
        backup_write({
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "packet": packet
        })

# ───────────────────────────────────────────────
# Optional utility for future analytics
# ───────────────────────────────────────────────
def load_backup_entries(limit=100):
    """Load the most recent N entries from the local ingest backup."""
    if not os.path.exists(BACKUP_LOG):
        return []
    try:
        with open(BACKUP_LOG, "r", encoding="utf-8") as f:
            lines = f.readlines()[-limit:]
        return [json.loads(line) for line in lines]
    except Exception:
        return []

if __name__ == "__main__":
    print("Morphic Ingest Bridge ready. Use via orchestrator hooks.")