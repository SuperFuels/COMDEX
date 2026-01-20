# =========================================================
# File: backend/modules/aion_resonance/phi_reinforce.py
# ---------------------------------------------------------
# 🧠 AION Cognitive Reinforcement Engine
# Adjusts Φ-baseline and emergent "belief vectors"
# from memory coherence / entropy trends.
# Includes Δ-tracking + optional demo breathe tick.
# =========================================================

from __future__ import annotations

import datetime
import json
import logging
import os
from pathlib import Path
from statistics import mean
from typing import Any, Dict

log = logging.getLogger("comdex")

ENV_DATA_ROOT = "TESSARIS_DATA_ROOT"

# Print / log gates
ENV_REINFORCE_PRINT = "AION_REINFORCE_PRINT"     # "1" -> print deltas
ENV_BELIEF_PRINT = "AION_BELIEF_PRINT"           # "1" -> print beliefs
ENV_PHI_BREATHE = "AION_PHI_BREATHE"             # "1" -> allow breathe_tick loop usage
ENV_VERBOSE_LOG = "AION_PHI_VERBOSE_LOG"         # "1" -> info logs

def _repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "backend").exists():
            return parent
    return Path.cwd()

def _data_root() -> Path:
    v = os.getenv(ENV_DATA_ROOT, "").strip()
    if v:
        return Path(v).expanduser()
    return _repo_root() / "data"

DATA_ROOT = _data_root()
DATA_ROOT.mkdir(parents=True, exist_ok=True)

MEMORY_PATH = str(DATA_ROOT / "conversation_memory.json")
REINFORCE_PATH = str(DATA_ROOT / "phi_reinforce_state.json")

DEFAULT_BASELINE: Dict[str, Any] = {
    "Φ_load": 0.0,
    "Φ_flux": 0.25,
    "Φ_entropy": 0.35,
    "Φ_coherence": 0.65,
    "beliefs": {
        "stability": 0.5,
        "curiosity": 0.5,
        "trust": 0.5,
        "clarity": 0.5,
    },
    "last_update": None,
}

# ----------------------------------------------------------
# Helpers
# ----------------------------------------------------------

def _load_json(path: str, default: Any) -> Any:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def _save_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _truthy_env(key: str, default: str = "0") -> bool:
    return os.getenv(key, default).strip().lower() in {"1", "true", "yes", "y", "on"}

def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))

def _round4(x: float) -> float:
    return float(f"{x:.4f}")

# ----------------------------------------------------------
# Baseline Reinforcement
# ----------------------------------------------------------

def reinforce_from_memory() -> Dict[str, Any]:
    """
    Read recent Φ-memory, compute average coherence / entropy,
    update baseline + belief vector accordingly.
    Prints deltas ONLY if AION_REINFORCE_PRINT=1.
    """
    memory = _load_json(MEMORY_PATH, [])
    baseline = _load_json(REINFORCE_PATH, dict(DEFAULT_BASELINE))

    if not memory:
        return baseline

    coherences = [e.get("phi", {}).get("Φ_coherence", 0) for e in memory if isinstance(e, dict)]
    entropies  = [e.get("phi", {}).get("Φ_entropy", 0) for e in memory if isinstance(e, dict)]

    avg_coh = mean(coherences) if coherences else float(baseline.get("Φ_coherence", DEFAULT_BASELINE["Φ_coherence"]))
    avg_ent = mean(entropies)  if entropies  else float(baseline.get("Φ_entropy", DEFAULT_BASELINE["Φ_entropy"]))

    prev = dict(baseline)
    prev_beliefs = dict((prev.get("beliefs") or DEFAULT_BASELINE["beliefs"]))

    drift = float(avg_coh) - float(baseline.get("Φ_coherence", DEFAULT_BASELINE["Φ_coherence"]))

    α = 0.25
    baseline["Φ_coherence"] = float(baseline.get("Φ_coherence", DEFAULT_BASELINE["Φ_coherence"])) + α * (float(avg_coh) - float(baseline.get("Φ_coherence", DEFAULT_BASELINE["Φ_coherence"])))
    baseline["Φ_entropy"]   = float(baseline.get("Φ_entropy", DEFAULT_BASELINE["Φ_entropy"]))     + α * (float(avg_ent) - float(baseline.get("Φ_entropy", DEFAULT_BASELINE["Φ_entropy"])))
    baseline["Φ_flux"]      = float(baseline.get("Φ_flux", DEFAULT_BASELINE["Φ_flux"]))          + α * ((float(avg_coh) - float(avg_ent)) - float(baseline.get("Φ_flux", DEFAULT_BASELINE["Φ_flux"])))
    baseline["Φ_load"]      = float(baseline.get("Φ_load", DEFAULT_BASELINE["Φ_load"]))          + α * (drift / 10.0)

    beliefs = dict((baseline.get("beliefs") or DEFAULT_BASELINE["beliefs"]))

    if float(avg_coh) > 0.8 and float(avg_ent) < 0.3:
        beliefs["stability"] = _clamp01(beliefs.get("stability", 0.5) + 0.02)
        beliefs["trust"]     = _clamp01(beliefs.get("trust", 0.5) + 0.01)
        beliefs["clarity"]   = _clamp01(beliefs.get("clarity", 0.5) + 0.015)
    elif float(avg_ent) > 0.6:
        beliefs["curiosity"] = _clamp01(beliefs.get("curiosity", 0.5) + 0.02)
        beliefs["stability"] = _clamp01(beliefs.get("stability", 0.5) - 0.01)
    else:
        beliefs["clarity"]   = _clamp01(beliefs.get("clarity", 0.5) - 0.005)

    baseline["beliefs"] = beliefs
    baseline["last_update"] = datetime.datetime.utcnow().isoformat()
    _save_json(REINFORCE_PATH, baseline)

    if _truthy_env(ENV_REINFORCE_PRINT, "0"):
        coh_delta = float(baseline["Φ_coherence"]) - float(prev.get("Φ_coherence", 0.0))
        ent_delta = float(baseline["Φ_entropy"]) - float(prev.get("Φ_entropy", 0.0))
        flux_delta = float(baseline["Φ_flux"]) - float(prev.get("Φ_flux", 0.0))
        load_delta = float(baseline["Φ_load"]) - float(prev.get("Φ_load", 0.0))
        belief_deltas = {k: _round4(float(beliefs.get(k, 0.0)) - float(prev_beliefs.get(k, 0.0))) for k in beliefs}
        print(f"[AION Reinforce ΔΦ] coherence {coh_delta:+.4f}, entropy {ent_delta:+.4f}, flux {flux_delta:+.4f}, load {load_delta:+.4f}")
        print(f"[AION Belief Δ] " + ", ".join([f"{k} {v:+.3f}" for k, v in belief_deltas.items()]))

    return baseline

# ----------------------------------------------------------
# Demo breathe tick (optional)
# ----------------------------------------------------------

def breathe_tick() -> Dict[str, Any]:
    """
    Tiny idle-motion for the demo: gently relax Φ fields toward DEFAULT_BASELINE.
    Safe to run in a background loop.

    If AION_PHI_BREATHE != 1 -> no-op (returns current state).
    """
    if not _truthy_env(ENV_PHI_BREATHE, "0"):
        return _load_json(REINFORCE_PATH, dict(DEFAULT_BASELINE))

    state = _load_json(REINFORCE_PATH, dict(DEFAULT_BASELINE))

    alpha = 0.06
    for k in ("Φ_load", "Φ_flux", "Φ_entropy", "Φ_coherence"):
        tgt = float(DEFAULT_BASELINE.get(k, 0.0))
        cur = float(state.get(k, tgt))
        state[k] = cur + alpha * (tgt - cur)

    state["last_update"] = datetime.datetime.utcnow().isoformat()
    _save_json(REINFORCE_PATH, state)

    if _truthy_env(ENV_VERBOSE_LOG, "0"):
        log.info("[phi] breathe tick")

    return state

# ----------------------------------------------------------
# Belief updates (used by feedback loops)
# ----------------------------------------------------------

def update_beliefs(delta: Dict[str, float]) -> Dict[str, Any]:
    """
    Incrementally update AION's belief vector in response to feedback.
    Includes decay toward neutral (0.5) and resistance to abrupt jumps.

    NO SPAM:
      - prints only if AION_BELIEF_PRINT=1
      - only emits when something actually changed (epsilon)
      - logs to comdex DEBUG (respects uvicorn log level)
    """
    state = _load_json(REINFORCE_PATH, dict(DEFAULT_BASELINE))
    beliefs = dict((state.get("beliefs") or DEFAULT_BASELINE["beliefs"]))
    before = dict(beliefs)

    resistance = 0.3   # higher = slower changes
    decay_rate = 0.02  # pull toward equilibrium

    for k in beliefs.keys():
        base = float(beliefs.get(k, 0.5))
        base += (0.5 - base) * decay_rate
        if k in delta:
            try:
                base += float(delta[k]) * (1.0 - resistance)
            except Exception:
                pass
        beliefs[k] = _clamp01(base)

    # Only persist/emit if there was a real change
    eps = 1e-6
    changed = any(abs(float(beliefs[k]) - float(before.get(k, 0.0))) > eps for k in beliefs.keys())

    if changed:
        state["beliefs"] = beliefs
        state["last_update"] = datetime.datetime.utcnow().isoformat()
        _save_json(REINFORCE_PATH, state)

        # debug log (won’t show at warning level)
        log.debug("[beliefs] adjusted %s", beliefs)

        if _truthy_env(ENV_BELIEF_PRINT, "0"):
            print(f"[🧭 Beliefs adjusted] {beliefs}")

    return state

# ----------------------------------------------------------
# Public Accessors
# ----------------------------------------------------------

def get_reinforce_state() -> Dict[str, Any]:
    return _load_json(REINFORCE_PATH, dict(DEFAULT_BASELINE))

def reset_reinforce_state() -> Dict[str, Any]:
    _save_json(REINFORCE_PATH, dict(DEFAULT_BASELINE))
    if _truthy_env(ENV_REINFORCE_PRINT, "0") or _truthy_env(ENV_BELIEF_PRINT, "0"):
        print("[AION Reinforce] Baseline reset to defaults.")
    return dict(DEFAULT_BASELINE)