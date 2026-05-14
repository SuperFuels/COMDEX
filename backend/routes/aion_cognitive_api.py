# backend/routes/aion_cognitive_api.py
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/aion", tags=["AION Cognitive"])

# Where the CLI bridge writes evidence:
DASHBOARD_LOG_PATH = Path("data/analysis/aion_live_dashboard.jsonl")
DASHBOARD_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────
# Shared writer (same schema as bridge)
# ─────────────────────────────────────────────────────────────
def _is_num(x: Any) -> bool:
    return isinstance(x, (int, float)) and x == x


def _pick(d: Dict[str, Any], *keys: str) -> Optional[float]:
    for k in keys:
        v = d.get(k)
        if _is_num(v):
            return float(v)
    return None


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _compute_equilibrium(metrics: Dict[str, Any]) -> Optional[float]:
    eq = _pick(metrics, "⟲", "res_eq", "equilibrium")
    if eq is not None:
        return _clamp01(eq)

    phi_c = _pick(metrics, "Φ_coherence", "Phi_coherence")
    phi_e = _pick(metrics, "Φ_entropy", "Phi_entropy")
    if phi_c is not None and phi_e is not None:
        return _clamp01(phi_c * (1.0 - phi_e))

    rho = _pick(metrics, "ρ", "rho")
    iota = _pick(metrics, "Ī", "iota", "I")
    if rho is not None and iota is not None:
        return _clamp01(rho * (1.0 - iota))

    return None


def _log_event(command: str, payload: Optional[Dict[str, Any]] = None, *, mode: str = "api", typ: str = "ui") -> None:
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
        "timestamp": time.time(),
        "command": command,
        "mode": mode,
        "type": typ,
        "SQI": sqi,
        "ρ": rho,
        "Ī": iota,
        "ΔΦ": dphi,
        "⟲": eq,
        "Θ_frequency": theta,
        # legacy aliases:
        "Φ_coherence": phi_c if phi_c is not None else rho,
        "Φ_entropy": phi_e if phi_e is not None else iota,
        # keep raw payload too (useful for UI / debugging):
        "payload": payload,
    }

    try:
        with open(DASHBOARD_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# Pydantic request models
# ─────────────────────────────────────────────────────────────
class TeachRequest(BaseModel):
    term: str = Field(..., min_length=1)
    level: int = Field(1, ge=1, le=9)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)


# ─────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────
@router.post("/teach")
def api_aion_teach(req: TeachRequest) -> Dict[str, Any]:
    """
    UI-triggered teaching. Runs the same CognitiveExerciseEngine
    and logs an event into aion_live_dashboard.jsonl.
    """
    from backend.modules.aion_cognition.cognitive_exercise_engine_dual import DualModeCEE as CognitiveExerciseEngine
    from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
    from backend.modules.aion_cognition.cee_lex_memory import update_lex_memory

    cee = CognitiveExerciseEngine()
    rmc = ResonantMemoryCache()
    rmc.load()

    term = req.term.strip()
    level = int(req.level)

    lesson = cee.generate_exercise(term, level=level)

    # keep it compatible with your CLI defaults
    resonance = {"ρ": 0.8, "Ī": 0.2, "SQI": 0.85, "ΔΦ": 0.0}

    # run questions; use expected answer as “demo ground truth”
    for q in (lesson.get("questions") or []):
        try:
            ans = cee.evaluate_answer(q, q.get("answer", ""))
        except Exception:
            ans = {}

        if _is_num(ans.get("SQI")):
            resonance["SQI"] = float(ans["SQI"])
        if _is_num(ans.get("ΔΦ")):
            resonance["ΔΦ"] = float(ans["ΔΦ"])

        try:
            update_lex_memory(q.get("prompt", ""), q.get("answer", ""), resonance)
        except Exception:
            pass

        try:
            rmc.update_from_photons([{"λ": term, "φ": resonance["ρ"], "μ": resonance["SQI"]}])
        except Exception:
            pass

    # best-effort persist learned concept
    try:
        rmc.cache[term.lower()] = {
            "definition": lesson.get("summary", f"Learned concept '{term}'"),
            "resonance": round(resonance.get("ρ", 0.8), 3),
            "intensity": round(1.0 - resonance.get("Ī", 0.2), 3),
            "SQI": round(resonance.get("SQI", 0.85), 3),
            "symbol": f"Q[{term}]",
            "stability": round(resonance.get("SQI", 0.85), 3),
        }
        rmc.last_update = time.time()
        rmc.save()
    except Exception:
        pass

    # ensure equilibrium present for UI
    eq = _compute_equilibrium(resonance)
    if eq is None:
        eq = _clamp01(float(resonance.get("ρ", 0.0)) * (1.0 - float(resonance.get("Ī", 0.0))))
    resonance["⟲"] = float(eq)

    _log_event("teach", {"term": term, "level": level, **resonance}, typ="train")

    return {
        "ok": True,
        "term": term,
        "level": level,
        "summary": lesson.get("summary"),
        "metrics": resonance,
        "ts": time.time(),
    }


@router.post("/ask")
def api_aion_ask(req: AskRequest) -> Dict[str, Any]:
    """
    UI-triggered question answering. Logs the question + answer
    to the dashboard feed.
    """
    from backend.modules.aion_cognition.cognitive_exercise_engine_dual import DualModeCEE as CognitiveExerciseEngine

    cee = CognitiveExerciseEngine()
    q = req.question.strip()

    try:
        a = cee.query(q)
    except Exception as e:
        a = f"[error] {e}"

    payload = {"question": q, "answer": a}
    _log_event("ask", payload, typ="cli")

    return {"ok": True, "question": q, "answer": a, "ts": time.time()}