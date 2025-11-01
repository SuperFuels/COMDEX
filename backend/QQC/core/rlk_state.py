"""
QQC Resonant Logic Kernel - Live State Controller
────────────────────────────────────────────────
Maintains dynamic RLK parameters (ε, audit interval) with persistence.
Restored automatically on boot to continue from last stable state.
"""

import json
from pathlib import Path
from datetime import datetime, timezone

STATE_PATH = Path("backend/state/qqc_rlk_state.json")

# Default baseline
RLK_STATE = {
    "tolerance": 1.0,
    "audit_interval": 10,
    "updated": datetime.now(timezone.utc).isoformat(),
}

def save_state():
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(RLK_STATE, f, indent=2)

def load_state():
    global RLK_STATE
    if STATE_PATH.exists():
        try:
            RLK_STATE = json.loads(STATE_PATH.read_text())
            print(f"[QQC::RLK_STATE] Restored persistent state -> ε={RLK_STATE['tolerance']:.4f}, "
                  f"N={RLK_STATE['audit_interval']}")
        except Exception as e:
            print(f"[QQC::RLK_STATE] ⚠ Failed to load state: {e}")
    else:
        save_state()
        print("[QQC::RLK_STATE] Initialized default state.")
    return RLK_STATE

def set_tolerance(eps: float):
    RLK_STATE["tolerance"] = eps
    RLK_STATE["updated"] = datetime.now(timezone.utc).isoformat()
    save_state()
    print(f"[QQC::RLK_STATE] ε updated -> {eps:.4f}")

def set_audit_interval(n: int):
    RLK_STATE["audit_interval"] = n
    RLK_STATE["updated"] = datetime.now(timezone.utc).isoformat()
    save_state()
    print(f"[QQC::RLK_STATE] Audit interval updated -> {n} beats")

def get_state():
    return RLK_STATE


# ──────────────────────────────────────────────
# Auto-restore at import
# ──────────────────────────────────────────────
load_state()