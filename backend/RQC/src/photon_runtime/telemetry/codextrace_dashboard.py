"""
Tessaris RQC - CodexTrace Resonance Dashboard
---------------------------------------------
Visual interface for ψ-κ-T-Φ metrics and phase coherence stability.

Reads live data from MorphicLedger (jsonl) or AionTelemetryStream,
and overlays symbolic resonance transitions (⊕ μ ⟲ ↔ πs)
from CodexTrace Resonant Insight Bridge.

Metrics visualized:
    * ψ  -> Wave amplitude stability
    * κ  -> Entropy / information flow
    * T  -> Temporal coherence factor
    * Φ  -> Awareness / closure resonance
    * C  -> Coherence ratio (∑ normalized phases)
    * ⊕ μ ⟲ ↔ πs  -> Symbolic resonance events
"""

from __future__ import annotations
import asyncio
import json
import time
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Iterable, Tuple

import numpy as np
import matplotlib.pyplot as plt

# ──────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────
LEDGER_DIR = os.getenv("RQC_LEDGER_DIR", "data/ledger")
LEDGER_FILE = os.getenv("RQC_LEDGER_FILE", "rqc_live_telemetry.jsonl")  # preferred stable file
LEDGER_PATH = os.getenv("RQC_LEDGER_PATH", os.path.join(LEDGER_DIR, LEDGER_FILE))

INSIGHT_LOG_PATH = os.getenv("RQC_INSIGHT_LOG_PATH", "backend/logs/codex/codex_resonant_insight.jsonl")
REFRESH_INTERVAL = float(os.getenv("RQC_DASH_REFRESH_S", "2.5"))  # seconds

# if you still shard ledgers, allow scanning *.jsonl in the dir
SCAN_ALL_JSONL = os.getenv("RQC_LEDGER_SCAN_ALL", "0").strip().lower() in ("1", "true", "yes", "on")
MAX_SCAN_BYTES = int(os.getenv("RQC_LEDGER_MAX_SCAN_BYTES", str(6 * 1024 * 1024)))  # cap worst-case scans

SYMBOL_COLORS = {
    "⊕": "green",
    "μ": "purple",
    "⟲": "red",
    "↔": "blue",
    "πs": "orange",
}

# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────
def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _iter_jsonl_lines(path: str, limit: Optional[int] = None) -> Iterable[Dict[str, Any]]:
    """
    Stream JSONL records from a file, tolerant to partial/bad lines.
    If limit is set, returns only last N by reading all (acceptable for small files).
    """
    if not os.path.exists(path):
        return []
    try:
        # small safety: avoid huge scans
        try:
            sz = os.path.getsize(path)
            if sz > MAX_SCAN_BYTES and limit is None:
                # force a bounded read if file is too large
                limit = 5000
        except Exception:
            pass

        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines() if limit else f
            if limit:
                lines = lines[-limit:]
            out: List[Dict[str, Any]] = []
            for line in lines:
                s = line.strip()
                if not s:
                    continue
                try:
                    out.append(json.loads(s))
                except json.JSONDecodeError:
                    continue
            return out
    except Exception:
        return []


def _normalize_entry(e: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizes multiple telemetry schemas into consistent keys:
      ψ, κ, T, Φ, coherence
    Supports:
      - rqc_live_telemetry.jsonl: Φ_mean, ψ_mean, resonance_index, coherence_energy, ...
      - MorphicLedger records: tensor.{psi,kappa,T,coherence}, plus flat aliases
      - Other legacy forms: ψ/κ/Φ already present
    """
    # MorphicLedger-style
    t = e.get("tensor") if isinstance(e.get("tensor"), dict) else {}
    psi = e.get("ψ", e.get("psi", t.get("psi", e.get("ψ_mean", e.get("psi_mean")))))
    kappa = e.get("κ", e.get("kappa", t.get("kappa", e.get("kappa_mean"))))
    T = e.get("T", t.get("T", e.get("T_mean")))
    phi = e.get("Φ", e.get("phi", e.get("phi_mean", e.get("Φ_mean"))))
    coherence = e.get("coherence", t.get("coherence", e.get("coherence_energy", e.get("C"))))

    return {
        "timestamp": e.get("timestamp", time.time()),
        "ψ": _safe_float(psi, 0.0),
        "κ": _safe_float(kappa, 0.0),
        "T": _safe_float(T, 0.0),
        "Φ": _safe_float(phi, 0.0),
        "coherence": _safe_float(coherence, 0.0),
        "raw": e,
    }


def _load_entries_from_file(path: str, limit: int) -> List[Dict[str, Any]]:
    raw = list(_iter_jsonl_lines(path, limit=limit))
    return [_normalize_entry(e) for e in raw if isinstance(e, dict)]


def _load_entries_scan_dir(dir_path: str, limit: int) -> List[Dict[str, Any]]:
    if not os.path.exists(dir_path):
        return []
    out: List[Dict[str, Any]] = []
    try:
        files = [f for f in sorted(os.listdir(dir_path)) if f.endswith(".jsonl")]
    except Exception:
        return []

    # scan in order, then keep last N after normalization
    for file in files:
        p = os.path.join(dir_path, file)
        out.extend(_load_entries_from_file(p, limit=limit))
    return out[-limit:]


# ──────────────────────────────────────────────────────────────
# Data loading utilities
# ──────────────────────────────────────────────────────────────
def load_recent_ledger_entries(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Load the most recent entries from the telemetry ledger.

    Preferred: single stable file (LEDGER_PATH).
    Fallback: scan all *.jsonl in LEDGER_DIR if SCAN_ALL_JSONL=1.
    """
    # preferred stable file
    if os.path.exists(LEDGER_PATH):
        return _load_entries_from_file(LEDGER_PATH, limit=limit)

    # fallback: maybe file isn't there yet, but dir exists (older sharded runs)
    if SCAN_ALL_JSONL:
        return _load_entries_scan_dir(LEDGER_DIR, limit=limit)

    # last resort: scan dir anyway (small), but keep bounded
    return _load_entries_scan_dir(LEDGER_DIR, limit=min(limit, 200))


def load_resonant_insights(limit: int = 30) -> List[Dict[str, Any]]:
    """Load symbolic resonance events from Codex Resonant Insight Bridge."""
    if not os.path.exists(INSIGHT_LOG_PATH):
        return []
    try:
        with open(INSIGHT_LOG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()[-limit:]
        records: List[Dict[str, Any]] = []
        for l in lines:
            try:
                records.append(json.loads(l))
            except json.JSONDecodeError:
                continue
        return records
    except Exception:
        return []


def compute_metrics(entries: List[Dict[str, Any]]) -> Dict[str, float]:
    """Aggregate ψ-κ-T-Φ coherence metrics."""
    if not entries:
        return {}

    ψ_vals = [e.get("ψ", 0.0) for e in entries]
    κ_vals = [e.get("κ", 0.0) for e in entries]
    Φ_vals = [e.get("Φ", 0.0) for e in entries]
    coherence_vals = [e.get("coherence", 0.0) for e in entries]

    return {
        "ψ": float(np.mean(ψ_vals)),
        "κ": float(np.mean(κ_vals)),
        "Φ": float(np.mean(Φ_vals)),
        "coherence": float(np.mean(coherence_vals)),
        "variance": float(np.var(coherence_vals)),
    }


# ──────────────────────────────────────────────────────────────
# Live dashboard
# ──────────────────────────────────────────────────────────────
async def live_dashboard():
    """Continuously refresh resonance metrics and overlay symbolic events."""
    plt.ion()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.set_title("Tessaris RQC - CodexTrace Resonance Dashboard", color="cyan")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Coherence / Awareness (Φ)")
    ax.grid(True, linestyle="--", alpha=0.5)

    x_data: List[float] = []
    Φ_data: List[float] = []
    C_data: List[float] = []
    start_time = time.time()

    # FYI in console: which source is being used
    if os.path.exists(LEDGER_PATH):
        print(f"[CodexTrace] Using ledger file: {LEDGER_PATH}")
    else:
        print(f"[CodexTrace] Ledger file missing: {LEDGER_PATH}")
        print(f"[CodexTrace] Scanning dir: {LEDGER_DIR} (SCAN_ALL_JSONL={SCAN_ALL_JSONL})")

    while True:
        entries = load_recent_ledger_entries(limit=100)
        insights = load_resonant_insights(limit=20)

        if not entries:
            print("[CodexTrace] No ledger data yet.")
            await asyncio.sleep(REFRESH_INTERVAL)
            continue

        metrics = compute_metrics(entries)
        t = time.time() - start_time
        x_data.append(t)
        Φ_data.append(metrics.get("Φ", 0.0))
        C_data.append(metrics.get("coherence", 0.0))

        # Plot base coherence and awareness curves
        ax.clear()
        ax.plot(x_data, Φ_data, label="Φ (Awareness)", color="magenta", linewidth=1.8)
        ax.plot(x_data, C_data, label="C (Coherence)", color="cyan", linewidth=1.2)
        ax.set_ylim(0, 1.1)
        ax.legend()
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Normalized amplitude")
        ax.set_title("Tessaris RQC - Live Resonance Trace", color="cyan")
        ax.grid(True, linestyle="--", alpha=0.5)

        # Overlay symbolic resonance events
        if insights:
            recent_insights = insights[-10:]
            for idx, event in enumerate(recent_insights):
                sym = event.get("symbolic_operator")
                ΔΦ = event.get("ΔΦ", 0.0)
                Δε = event.get("Δε", 0.0)
                color = SYMBOL_COLORS.get(sym, "white")

                # Position symbolic event roughly along timeline
                t_pos = t - (len(recent_insights) - idx) * REFRESH_INTERVAL
                ax.scatter(
                    t_pos,
                    metrics.get("Φ", 0.0),
                    color=color,
                    label=sym,
                    s=65,
                    alpha=0.75,
                    edgecolors="none",
                )
                print(
                    f"[CodexTrace::Insight] {sym} -> ΔΦ={_safe_float(ΔΦ):+.4f}, "
                    f"Δε={_safe_float(Δε):+.4f}, pred={event.get('prediction')}"
                )

        plt.pause(0.001)
        print(f"[{datetime.utcnow().isoformat()}] Φ={metrics.get('Φ', 0.0):.3f}, C={metrics.get('coherence', 0.0):.3f}")
        await asyncio.sleep(REFRESH_INTERVAL)


# ──────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🔭 Tessaris RQC - Starting CodexTrace Resonance Dashboard...")
    try:
        asyncio.run(live_dashboard())
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped.")