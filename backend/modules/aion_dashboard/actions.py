# backend/modules/aion_dashboard/actions.py
from __future__ import annotations

import json
import os
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Core engines (same as your CLI bridge uses)
from backend.AION.resonance.resonance_engine import update_resonance, get_resonance
from backend.modules.aion_cognition.cee_lex_memory import update_lex_memory
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.aion_cognition.cognitive_exercise_engine_dual import DualModeCEE as CognitiveExerciseEngine


# Paths (must match WS + dashboard)
DASHBOARD_LOG_PATH = Path(os.getenv("AION_DASHBOARD_JSONL", "data/analysis/aion_live_dashboard.jsonl"))
DASHBOARD_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

# Optional memory store
MEM_PATH = Path("data/aion/memory_store.json")

# Session id (stable-ish)
SESSION_ID = os.getenv("AION_SESSION_ID") or f"S{int(time.time())}_{random.randint(1000,9999)}"

# Global drift baseline (ΔΦ) if resonance engine doesn’t provide it
_LAST_EQ_FOR_DPHI: float | None = None


def _now() -> float:
    return time.time()


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _is_num(x: Any) -> bool:
    return isinstance(x, (int, float)) and x == x


def _pick(d: Dict[str, Any], *keys: str) -> Optional[float]:
    for k in keys:
        v = d.get(k)
        if _is_num(v):
            return float(v)
    return None


def _compute_equilibrium(metrics: Dict[str, Any]) -> Optional[float]:
    """
    Homeostasis headline score ⟲ (v2):

    Components (all clamped 0..1):
      - SQI   : learning/clarity score
      - ρ     : coherence
      - (1-Ī) : stability (low entropy)
      - drift : 1 - |ΔΦ|/ΔΦ_max   (penalize recent change)

    Output:
      geometric mean => only reaches ~1 when ALL components are high.
      0.975 is intentionally "near-perfect lock".
    """
    sqi = _pick(metrics, "SQI", "sqi", "sqi_checkpoint")
    rho = _pick(metrics, "ρ", "rho", "Φ_coherence", "Phi_coherence")
    iota = _pick(metrics, "Ī", "iota", "I", "Φ_entropy", "Phi_entropy")
    dphi = _pick(metrics, "ΔΦ", "dphi", "resonance_delta", "delta_phi")

    # Fallback raw equilibrium if needed (legacy)
    raw = _pick(metrics, "⟲", "res_eq", "equilibrium")

    # If we have rho+iota we can always compute a raw baseline
    if rho is not None and iota is not None:
        raw = _clamp01(float(rho) * (1.0 - float(iota))) if raw is None else _clamp01(float(raw))

    # If we have nothing except raw, return raw.
    if sqi is None and rho is None and iota is None and dphi is None:
        return _clamp01(float(raw)) if raw is not None else None

    # Defaults (conservative)
    sqi_v = _clamp01(float(sqi)) if sqi is not None else (0.0 if raw is None else _clamp01(float(raw)))
    rho_v = _clamp01(float(rho)) if rho is not None else (0.0 if raw is None else _clamp01(float(raw)))
    iota_v = _clamp01(float(iota)) if iota is not None else (1.0 - (0.0 if raw is None else _clamp01(float(raw))))

    stability = _clamp01(1.0 - iota_v)

    # Drift score: 1 when stable; falls to 0 when |ΔΦ| >= ΔΦ_max
    dphi_max = float(os.getenv("AION_HOMEOSTASIS_DPHI_MAX", "0.15"))
    if dphi is None or not _is_num(dphi):
        drift = 1.0
    else:
        drift = _clamp01(1.0 - (abs(float(dphi)) / max(1e-9, dphi_max)))

    # Geometric mean of 4 components
    prod = max(0.0, sqi_v * rho_v * stability * drift)
    return _clamp01(prod ** 0.25)


def _mk_lock_id() -> str:
    return f"HOMEOSTASIS_{int(_now())}_{random.randint(1000,9999)}"


def _tail_jsonl(path: Path, max_lines: int = 800, max_bytes: int = 512_000) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            end = f.tell()
            f.seek(max(0, end - max_bytes))
            chunk = f.read().decode("utf-8", errors="ignore")
        lines = [ln for ln in chunk.splitlines() if ln.strip()]
        for ln in lines[-max_lines:]:
            try:
                obj = json.loads(ln)
                if isinstance(obj, dict):
                    rows.append(obj)
            except Exception:
                continue
    except Exception:
        return []
    return rows


def _has_recent_checkpoint(window_s: int = 300) -> bool:
    now = _now()
    for r in reversed(_tail_jsonl(DASHBOARD_LOG_PATH, max_lines=1200)):
        if r.get("command") != "sqi_checkpoint":
            continue
        ts = r.get("timestamp")
        if isinstance(ts, (int, float)) and (now - float(ts)) <= window_s:
            return True
    return False


def log_event(
    command: str,
    payload: Optional[Dict[str, Any]] = None,
    *,
    mode: str = "aion_actions",
    typ: str = "api",
) -> Dict[str, Any]:
    """
    Canonical dashboard event writer (JSONL).
    Writes both canonical + legacy aliases.
    """
    payload = payload or {}

    rho = _pick(payload, "ρ", "rho")
    iota = _pick(payload, "Ī", "iota", "I")
    sqi = _pick(payload, "SQI", "sqi", "sqi_checkpoint")
    dphi = _pick(payload, "ΔΦ", "dphi", "resonance_delta", "delta_phi")
    phi_c = _pick(payload, "Φ_coherence", "Phi_coherence")
    phi_e = _pick(payload, "Φ_entropy", "Phi_entropy")
    theta = _pick(payload, "Θ_frequency", "theta_frequency", "Theta_frequency")

    eq = _compute_equilibrium(payload)

    entry: Dict[str, Any] = {
        "timestamp": _now(),
        "command": command,
        "mode": mode,
        "type": typ,
        # canonical metrics
        "SQI": sqi,
        "ρ": rho,
        "Ī": iota,
        "ΔΦ": dphi,
        "⟲": eq,
        "Θ_frequency": theta,
        # legacy aliases
        "Φ_coherence": phi_c if phi_c is not None else rho,
        "Φ_entropy": phi_e if phi_e is not None else iota,
    }

    # passthrough common transcript/meta
    for k in (
        "term",
        "session_id",
        "level",
        "question",
        "expected",
        "answer",
        "feedback",
        "summary",
        "text",
        "locked",
        "threshold",
        "lock_id",
        "reason",
        "E",
    ):
        if k in payload:
            entry[k] = payload[k]

    try:
        with open(DASHBOARD_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass

    return entry


def query_resonance(term: str) -> Dict[str, Any]:
    """
    Returns normalized resonance metrics and guarantees:
      - ⟲_raw : legacy/raw proxy (ρ*(1-Ī))
      - ⟲     : headline homeostasis score (via _compute_equilibrium v2)
      - ΔΦ    : drift (derived if engine doesn't provide it)
    """
    global _LAST_EQ_FOR_DPHI

    res = get_resonance(term)
    if not res:
        res = update_resonance(term)

    # Normalize
    out: Dict[str, Any] = {
        "SQI": res.get("SQI") or res.get("sqi"),
        "ρ": res.get("ρ") or res.get("rho"),
        "Ī": res.get("Ī") or res.get("iota") or res.get("I"),
        "ΔΦ": res.get("ΔΦ") or res.get("resonance_delta"),
        "E": res.get("E"),
        # legacy aliases (keep tools happy)
        "Φ_coherence": res.get("Φ_coherence") or res.get("Phi_coherence") or res.get("ρ") or res.get("rho"),
        "Φ_entropy": res.get("Φ_entropy") or res.get("Phi_entropy") or res.get("Ī") or res.get("iota") or res.get("I"),
    }

    # Always compute raw proxy (for debugging + stability baselines)
    rho0 = float(out.get("ρ") or 0.0)
    iota0 = float(out.get("Ī") or 0.0)
    raw = _clamp01(rho0 * (1.0 - iota0))
    out["⟲_raw"] = float(raw)

    # If engine provided explicit equilibrium, preserve it as an alternate raw hint
    # (but do NOT use it as headline unless _compute_equilibrium chooses to).
    if _is_num(res.get("⟲")):
        out["⟲_raw"] = _clamp01(float(res.get("⟲")))  # keep as raw channel only

    # Derive ΔΦ if missing: base it on RAW so "headline" changes don't fake drift
    if out.get("ΔΦ") is None:
        if _LAST_EQ_FOR_DPHI is None:
            out["ΔΦ"] = None
        else:
            out["ΔΦ"] = abs(float(out["⟲_raw"]) - float(_LAST_EQ_FOR_DPHI))

    # Headline metric ⟲: strict v2 (SQI + coherence + stability + drift)
    # Important: pass ⟲_raw in so _compute_equilibrium can use it as fallback.
    head = _compute_equilibrium({**out, "⟲": out["⟲_raw"]})
    out["⟲"] = float(head if head is not None else out["⟲_raw"])

    # Update drift baseline (RAW baseline)
    _LAST_EQ_FOR_DPHI = float(out["⟲_raw"])

    return out


def checkpoint(term: str = "homeostasis", *, typ: str = "checkpoint", mode: str = "aion_actions") -> Dict[str, Any]:
    t = (term or "homeostasis").strip() or "homeostasis"
    pulse = query_resonance(t)
    payload = {"term": t, **pulse, "text": f"checkpoint {t}", "session_id": SESSION_ID}
    ev = log_event("sqi_checkpoint", payload, typ=typ, mode=mode)
    return {"term": t, "metrics": pulse, "event": ev}


def homeostasis_lock(
    *,
    threshold: float = 0.975,
    window_s: int = 300,
    term: str = "homeostasis",
    typ: str = "homeostasis_lock",
    mode: str = "aion_actions",
) -> Dict[str, Any]:
    thr = float(threshold)
    win = int(window_s)
    t = (term or "homeostasis").strip() or "homeostasis"

    if not _has_recent_checkpoint(window_s=win):
        payload = {
            "term": t,
            "locked": False,
            "threshold": thr,
            "reason": f"no_recent_sqi_checkpoint (window_s={win})",
            "text": f"homeostasis thr={thr} window_s={win}",
            "session_id": SESSION_ID,
        }
        ev = log_event("homeostasis_lock", payload, typ=typ, mode=mode)
        return {"term": t, "locked": False, "threshold": thr, "window_s": win, "event": ev}

    pulse = query_resonance(t)
    eq = float(_compute_equilibrium(pulse) or 0.0)
    locked = bool(eq >= thr)
    lock_id = _mk_lock_id() if locked else None

    payload = {
        "term": t,
        **pulse,
        "⟲": eq,
        "locked": locked,
        "threshold": thr,
        "lock_id": lock_id,
        "text": f"homeostasis thr={thr} window_s={win}",
        "session_id": SESSION_ID,
    }
    ev = log_event("homeostasis_lock", payload, typ=typ, mode=mode)
    return {"term": t, "metrics": pulse, "locked": locked, "threshold": thr, "window_s": win, "lock_id": lock_id, "event": ev}


def teach(
    term: str,
    level: int = 1,
    *,
    typ: str = "train",
    mode: str = "aion_actions",
) -> Dict[str, Any]:
    """
    Runs a real CEE teaching session (same core behavior as your CLI bridge),
    and logs teach_q + teach_done events for the dashboard.
    """
    t = (term or "").strip()
    lvl = int(level or 1)
    if not t:
        raise ValueError("term is required")

    engine = CognitiveExerciseEngine()

    session_id = f"teach_{t}_{int(_now())}_{random.randint(1000,9999)}"
    log_event("teach_start", {"term": t, "level": lvl, "session_id": session_id, "text": f"teach {t} {lvl}"}, typ=typ, mode=mode)

    lesson = engine.generate_exercise(t, level=lvl)

    # baseline resonance (updated if engine returns SQI/ΔΦ per answer)
    resonance: Dict[str, Any] = {"ρ": 0.8, "Ī": 0.2, "SQI": 0.85, "ΔΦ": 0.0}

    # RMC update (matches your CLI intent)
    rmc = ResonantMemoryCache()
    try:
        rmc.load()
    except Exception:
        pass

    questions = lesson.get("questions", []) or []
    for q in questions:
        prompt = str(q.get("prompt", "") or "")
        expected = str(q.get("answer", "") or "")

        ans = engine.evaluate_answer(q, expected)
        feedback = str(ans.get("feedback", "") or "")

        if _is_num(ans.get("SQI")):
            resonance["SQI"] = float(ans["SQI"])
        if _is_num(ans.get("ΔΦ")):
            resonance["ΔΦ"] = float(ans["ΔΦ"])

        # persist learning (same as CLI)
        update_lex_memory(prompt, expected, resonance)
        try:
            rmc.update_from_photons([{"λ": t, "φ": resonance.get("ρ", 0.8), "μ": resonance.get("SQI", 0.85)}])
        except Exception:
            pass

        log_event(
            "teach_q",
            {
                "term": t,
                "level": lvl,
                "session_id": session_id,
                "question": prompt,
                "expected": expected,
                "feedback": feedback,
                "SQI": resonance.get("SQI"),
                "ΔΦ": resonance.get("ΔΦ"),
            },
            typ=typ,
            mode=mode,
        )

    try:
        rmc.save()
    except Exception:
        pass

    summary = str(lesson.get("summary", f"Learned concept '{t}'") or "")
    log_event(
        "teach_done",
        {"term": t, "level": lvl, "session_id": session_id, "summary": summary, "SQI": resonance.get("SQI"), "ΔΦ": resonance.get("ΔΦ")},
        typ=typ,
        mode=mode,
    )

    return {"term": t, "level": lvl, "session_id": session_id, "summary": summary, "resonance": resonance}


def ask(
    question: str,
    *,
    typ: str = "cli",
    mode: str = "aion_actions",
) -> Dict[str, Any]:
    q = (question or "").strip()
    if not q:
        raise ValueError("question is required")

    engine = CognitiveExerciseEngine()
    answer = engine.query(q)

    log_event(
        "ask",
        {"question": q, "answer": str(answer), "text": str(answer), "session_id": SESSION_ID},
        typ=typ,
        mode=mode,
    )

    return {"question": q, "answer": str(answer)}