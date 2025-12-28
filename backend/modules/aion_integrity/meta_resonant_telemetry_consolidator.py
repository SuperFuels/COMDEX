#!/usr/bin/env python3
"""
Tessaris Phase 22 - Meta-Resonant Telemetry Consolidator (MRTC)

Aggregates and time-aligns live resonance telemetry across active subsystems.

CRITICAL FIX:
- Auto-detects the *real* data root (e.g. .runtime/COMDEX_MOVE/data)
- Reads inputs from that root
- Writes unified output to: <DATA_ROOT>/telemetry/meta_resonant_telemetry.jsonl

So SREL + RAL won’t stall waiting on a file that’s being written elsewhere.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# ----------------------------
# Data-root discovery
# ----------------------------

ENV_DATA_ROOT = "TESSARIS_DATA_ROOT"

KNOWN_SENTINELS = [
    "control/aqci_log.jsonl",
    "control/rqfs_feedback.jsonl",
    "learning/fusion_state.jsonl",
    "aion_field/resonant_heartbeat.jsonl",
    "analysis/resonant_optimizer.jsonl",
    "analysis/state_resonance_log.jsonl",
]

def pick_data_root() -> Path:
    # 1) explicit override
    env = Path(str(Path.cwd()))  # default
    if ENV_DATA_ROOT in __import__("os").environ:
        p = Path(__import__("os").environ[ENV_DATA_ROOT]).expanduser()
        if (p / "control").exists() or any((p / s).exists() for s in KNOWN_SENTINELS):
            return p

    # 2) prefer runtime-moved data if present
    candidates: List[Path] = []
    rt = Path(".runtime")
    if rt.exists():
        for d in rt.glob("*/data"):
            candidates.append(d)

    # 3) include local ./data
    candidates.append(Path("data"))

    def score(d: Path) -> Tuple[int, float]:
        hits = 0
        newest = 0.0
        for s in KNOWN_SENTINELS:
            f = d / s
            if f.exists():
                hits += 1
                try:
                    newest = max(newest, f.stat().st_mtime)
                except Exception:
                    pass
        return (hits, newest)

    best = None
    best_score = (-1, -1.0)
    for d in candidates:
        sc = score(d)
        if sc > best_score:
            best = d
            best_score = sc

    return best if best else Path("data")

DATA_ROOT = pick_data_root()

# ----------------------------
# Paths (relative to DATA_ROOT)
# ----------------------------

AQCI_LOG   = DATA_ROOT / "control" / "aqci_log.jsonl"
RQFS_FEED  = DATA_ROOT / "control" / "rqfs_feedback.jsonl"
FUSION_LOG = DATA_ROOT / "learning" / "fusion_state.jsonl"

AION_HEART = DATA_ROOT / "aion_field" / "resonant_heartbeat.jsonl"

# Optional extras if they exist in your stack
RFC_LOG    = DATA_ROOT / "learning" / "rfc_weights.jsonl"
RQFS_SYNC  = DATA_ROOT / "learning" / "rqfs_sync.jsonl"

PHOTO_DIR  = DATA_ROOT / "qqc_field" / "photo_output"

OUT_LOG    = DATA_ROOT / "telemetry" / "meta_resonant_telemetry.jsonl"
OUT_LOG.parent.mkdir(parents=True, exist_ok=True)

# ----------------------------
# Helpers
# ----------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def tail_jsonl(path: Path) -> Optional[Dict[str, Any]]:
    """Return last valid JSON object from a .jsonl file, or None."""
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        if not lines:
            return None
        return json.loads(lines[-1])
    except Exception:
        return None

def latest_photo_meta() -> Optional[Dict[str, Any]]:
    """Extract timestamp + pattern info from the newest .photo file."""
    if not PHOTO_DIR.exists():
        return None
    files = sorted(PHOTO_DIR.glob("*.photo"))
    if not files:
        return None
    try:
        with files[-1].open("r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "photo_file": files[-1].name,
            "pattern": data.get("pattern", {}),
            "timestamp": data.get("timestamp", ""),
        }
    except Exception:
        return None

def fget(d: Optional[Dict[str, Any]], k: str, default: float = 0.0) -> float:
    if not isinstance(d, dict):
        return float(default)
    v = d.get(k, default)
    try:
        return float(v)
    except Exception:
        return float(default)

# ----------------------------
# Core consolidator
# ----------------------------

def consolidate_once() -> bool:
    # Primary live sources (these exist in your runtime listing)
    aqci   = tail_jsonl(AQCI_LOG)
    rqfsfb = tail_jsonl(RQFS_FEED)
    fusion = tail_jsonl(FUSION_LOG)
    heart  = tail_jsonl(AION_HEART)

    # Optional sources (may/may not exist)
    rfc    = tail_jsonl(RFC_LOG)
    rqfss  = tail_jsonl(RQFS_SYNC)

    photo  = latest_photo_meta()

    if not any([aqci, rqfsfb, fusion, heart, rfc, rqfss, photo]):
        print(f"⚠️  No telemetry available yet... (DATA_ROOT={DATA_ROOT})")
        return False

    entry = {
        "type": "mrtc",
        "timestamp": now_iso(),
        "data_root": str(DATA_ROOT),

        # keep raw packets (don’t guess schema)
        "aqci": aqci,
        "rqfs_feedback": rqfsfb,
        "fusion": fusion,
        "aion_heartbeat": heart,

        # optional
        "rfc": rfc,
        "rqfs_sync": rqfss,

        "photo": photo,
    }

    with OUT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Print a stable summary from the fields we KNOW exist in your runtime:
    nu_bias  = fget(rqfsfb.get("state") if isinstance(rqfsfb, dict) else None, "nu_bias", 0.0)
    phi_bias = fget(rqfsfb.get("state") if isinstance(rqfsfb, dict) else None, "phi_bias", 0.0)
    amp_bias = fget(rqfsfb.get("state") if isinstance(rqfsfb, dict) else None, "amp_bias", 0.0)

    fusion_coh = fget(fusion, "fusion_coherence", 0.0)
    stab       = fget(fusion, "stability", 0.0)
    ent        = fget(fusion, "entropy", 0.0)

    print(
        f"📡 MRTC | ν_bias={nu_bias:+.4f} φ_bias={phi_bias:+.4f} amp_bias={amp_bias:+.4f} "
        f"| fusion={fusion_coh:.3f} S={stab:.3f} H(ent)={ent:.4f} "
        f"| out={OUT_LOG}"
    )
    return True

# ----------------------------
# Main loop
# ----------------------------

def main(interval: float = 2.0):
    print("📡 Starting Tessaris Meta-Resonant Telemetry Consolidator (MRTC)...")
    print(f"✅ DATA_ROOT = {DATA_ROOT}")
    print(f"✅ OUT_LOG   = {OUT_LOG}")
    while True:
        consolidate_once()
        time.sleep(interval)

if __name__ == "__main__":
    main()