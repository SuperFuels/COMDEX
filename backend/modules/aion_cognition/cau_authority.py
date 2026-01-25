#!/usr/bin/env python3
"""
Cognitive Authority Unification (CAU) — Authority Gate (Phase 46A)

Single source of truth for whether learning/reinforcement is permitted.

Reads:
  - RAL metrics tail:    data/learning/ral_metrics.jsonl
  - ADR repair log tail: data/feedback/drift_repair.log

Emits:
  - Canonical CAU status dict (for CEE + LexMemory gating)

Design goals:
  - Deterministic, auditable gate decisions.
  - No dependency on where RAL is computed: consume file artifacts only.
  - Cooldown after ADR to prevent oscillation.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# -------------------------
# Paths (DATA_ROOT aware)
# -------------------------
def _data_root() -> Path:
    return Path(os.getenv("DATA_ROOT", "data"))


def _paths() -> Tuple[Path, Path]:
    root = _data_root()
    return (
        root / "learning" / "ral_metrics.jsonl",
        root / "feedback" / "drift_repair.log",
    )


# -------------------------
# Env helpers (robust)
# -------------------------
def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


# -------------------------
# Gate Config (env-overridable via load)
# -------------------------
@dataclass(frozen=True)
class CAUConfig:
    # Permission thresholds
    S_min: float = 0.75
    H_max: float = 0.60

    # ADR cooldown (seconds). If ADR fired recently: deny learning.
    adr_cooldown_s: int = 30

    # If metrics are missing: default deny (safe) or allow (unsafe).
    default_allow_if_no_metrics: bool = False

    # Allow using fusion_* metrics as fallbacks if present
    use_fusion_fallbacks: bool = True


def load_cau_config() -> CAUConfig:
    """
    Reads env each time called.
    Note: in your normal usage you spawn a new python process per run,
    so env changes are reflected naturally.
    """
    return CAUConfig(
        S_min=_env_float("CAU_S_MIN", 0.75),
        H_max=_env_float("CAU_H_MAX", 0.60),
        adr_cooldown_s=_env_int("CAU_ADR_COOLDOWN_S", 30),
        default_allow_if_no_metrics=_env_bool("CAU_DEFAULT_ALLOW_IF_NO_METRICS", False),
        use_fusion_fallbacks=_env_bool("CAU_USE_FUSION_FALLBACKS", True),
    )


# keep for introspection/debug (loaded at import time)
DEFAULT_CONFIG = load_cau_config()


# -------------------------
# Helpers
# -------------------------
def _read_last_jsonl(path: Path) -> Optional[dict]:
    try:
        if not path.exists():
            return None
        txt = path.read_text(encoding="utf-8").strip()
        if not txt:
            return None
        return json.loads(txt.splitlines()[-1])
    except Exception:
        return None


def _now() -> float:
    return time.time()


def _parse_ts_any(v: Any) -> Optional[float]:
    # drift_repair.log in your stack is usually epoch float in "timestamp"
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except Exception:
            return None
    return None


# -------------------------
# Core: compute authority
# -------------------------
def compute_authority(
    goal: str = "maintain_coherence",
    config: Optional[CAUConfig] = None,
) -> Dict[str, Any]:
    """
    Source of truth: read last RAL metrics + ADR log and decide allow_learn.
    Returns dict containing at least: allow_learn (bool)
    """
    if config is None:
        config = load_cau_config()

    ral_path, adr_path = _paths()
    ral = _read_last_jsonl(ral_path) or {}
    adr = _read_last_jsonl(adr_path)

    # metrics (primary keys)
    Phi = ral.get("mean_phi", ral.get("Phi", None))
    S = ral.get("stability", ral.get("S", None))
    H = ral.get("drift_entropy", ral.get("H", None))

    # optional fusion fallbacks (if present)
    if config.use_fusion_fallbacks:
        if S is None and "fusion_stability_mean" in ral:
            S = ral.get("fusion_stability_mean")
        if H is None and "fusion_entropy_mean" in ral:
            H = ral.get("fusion_entropy_mean")

    # ADR cooldown
    adr_active = False
    cooldown_s = 0
    if isinstance(adr, dict):
        ts = _parse_ts_any(adr.get("timestamp"))
        if ts is not None:
            age = max(0.0, _now() - ts)
            if age <= float(config.adr_cooldown_s):
                adr_active = True
                cooldown_s = int(round(float(config.adr_cooldown_s) - age))

    deny_reason: Optional[str] = None

    # Metrics missing => default allow/deny (config)
    if S is None or H is None:
        allow = bool(config.default_allow_if_no_metrics)
        if not allow:
            deny_reason = "NO_RAL_METRICS"
    else:
        try:
            Sf = float(S)
            Hf = float(H)
        except Exception:
            Sf = None
            Hf = None

        if Sf is None or Hf is None:
            allow = bool(config.default_allow_if_no_metrics)
            if not allow:
                deny_reason = "NO_RAL_METRICS"
        else:
            # ADR override (hard deny)
            if adr_active:
                allow = False
                deny_reason = "ADR_COOLDOWN"
            else:
                if Sf < float(config.S_min):
                    allow = False
                    deny_reason = "LOW_STABILITY"
                elif Hf > float(config.H_max):
                    allow = False
                    deny_reason = "HIGH_ENTROPY"
                else:
                    allow = True
                    deny_reason = None

    st: Dict[str, Any] = {
        "t": _now(),
        "Phi": float(Phi) if Phi is not None else None,
        "S": float(S) if S is not None else None,
        "H": float(H) if H is not None else None,
        "allow_learn": bool(allow),
        "deny_reason": deny_reason,
        "adr_active": bool(adr_active),
        "cooldown_s": int(cooldown_s),
        "goal": str(goal),
        "paths": {"ral_metrics": str(ral_path), "adr_log": str(adr_path)},
        "config": asdict(config),
    }

    global LAST_STATE
    LAST_STATE = dict(st)
    return st


# Back-compat alias (some modules previously imported this name)
def compute_cau_status(
    config: Optional[CAUConfig] = None,
    goal: str = "maintain_coherence",
) -> Dict[str, Any]:
    return compute_authority(goal=goal, config=config)


# ---- stable public API (LexMemory / CEE probes these names) ----
LAST_STATE: Dict[str, Any] | None = None


def get_authority_state(goal: str = "maintain_coherence") -> Dict[str, Any]:
    return compute_authority(goal=goal)


def get_authority(goal: str = "maintain_coherence") -> Dict[str, Any]:
    return compute_authority(goal=goal)


def get_state(goal: str = "maintain_coherence") -> Dict[str, Any]:
    return compute_authority(goal=goal)


def main() -> None:
    print(json.dumps(get_authority_state(), indent=2))


if __name__ == "__main__":
    main()