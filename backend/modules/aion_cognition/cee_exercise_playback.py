#!/usr/bin/env python3
# ================================================================
# 🎬 CEE Exercise Playback Engine (LexMemory persistence wired + CAU gating)
# ================================================================
"""
Plays back CEE-generated exercises in either:
  * simulate mode -> automatic answers (with LexMemory recall)
  * interactive mode -> user answers via console input

CAU guarantee:
  ✅ LexMemory reinforcement MUST be gated by CAU authority (RAL/SQI/ADR).
     No learning while injured / cooldown / ADR active.

Key guarantee:
  ✅ On every correct answer, LexMemory is UPDATED AND SAVED to disk
     (ONLY when CAU allows learning) so Demo 5 can consume: data/memory/lex_memory.json

Program goal:
  - Primary training = SELF_TRAIN (Wordwall replacement)
  - Optional = LLM generation (explicit only, never surprise)
  - Wordwall/hybrid removed from the program path
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running this file directly without PYTHONPATH (pytest subprocess / CLI)
_REPO_ROOT = Path(__file__).resolve().parents[3]  # .../backend/modules/aion_cognition -> repo root
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import json
import logging
import os
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from backend.modules.aion_cognition.correction_history import get_correction_history
from backend.modules.aion_cognition.goal_transitions import log_goal_transition
logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# Optional OpenAI key validation (only affects LLM feed)
# ------------------------------------------------------------
_api_key = os.getenv("OPENAI_API_KEY")
if not _api_key:
    logger.warning("[CEE-Playback] Missing OPENAI_API_KEY. LLM feed may be unavailable.")

# ------------------------------------------------------------
# LexMemory auto-correct (opt-in)
# ------------------------------------------------------------
AUTO_CORRECT = (os.getenv("CEE_LEX_AUTO_CORRECT", "1") or "1").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)

# ------------------------------------------------------------
# DATA_ROOT-aware paths
# ------------------------------------------------------------
def _data_root() -> Path:
    return Path(os.getenv("DATA_ROOT", "data"))


def _paths() -> Tuple[Path, Path, Path, Path, Path]:
    root = _data_root()
    out_path = root / "sessions" / "playback_log.qdata.json"
    lex_path = root / "memory" / "lex_memory.json"
    queue_path = root / "memory" / "lexmemory_queue.jsonl"
    turn_log_path = root / "telemetry" / "turn_log.jsonl"
    corr_log_path = root / "telemetry" / "correction_events.jsonl"
    return out_path, lex_path, queue_path, turn_log_path, corr_log_path


OUT_PATH, LEX_PATH, LEX_QUEUE_PATH, TURN_LOG_PATH, CORRECTION_LOG_PATH = _paths()

# ------------------------------------------------------------
# CAU gating (authority for learning) — Phase 46A stable API
# ------------------------------------------------------------
try:
    from backend.modules.aion_cognition.cau_authority import (
        get_authority_state as _cau_state,
    )
except Exception as _e:
    _cau_state = None
    logger.warning(
        f"[CEE-Playback] CAU authority not available; learning will be allowed by default. err={_e}"
    )


def _cau_status(goal: str = "maintain_coherence") -> dict:
    """
    Returns CAU dict (must include allow_learn).
    Safe fallback = allow learn (soft-fail) to avoid breaking playback.
    """
    if _cau_state is None:
        return {
            "t": time.time(),
            "allow_learn": True,
            "deny_reason": None,
            "adr_active": False,
            "cooldown_s": 0,
            "S": None,
            "H": None,
            "Phi": None,
            "goal": goal,
            "source": "CAU_IMPORT_FAIL",
        }
    try:
        st = _cau_state(goal=goal)
        if isinstance(st, dict) and "allow_learn" in st:
            st.setdefault("goal", goal)
            st.setdefault("source", "CAU:get_authority_state")
            st.setdefault("t", time.time())
            return st
        logger.warning("[CEE-Playback] CAU returned unexpected shape; allowing learn (soft-fail).")
        return {
            "t": time.time(),
            "allow_learn": True,
            "deny_reason": "cau_bad_shape",
            "adr_active": False,
            "cooldown_s": 0,
            "S": None,
            "H": None,
            "Phi": None,
            "goal": goal,
            "source": "CAU_BAD_SHAPE",
        }
    except Exception as e:
        logger.warning(f"[CEE-Playback] CAU compute failed; allowing learn. err={e}")
        return {
            "t": time.time(),
            "allow_learn": True,
            "deny_reason": "cau_compute_failed",
            "adr_active": False,
            "cooldown_s": 0,
            "S": None,
            "H": None,
            "Phi": None,
            "goal": goal,
            "source": "CAU_EXCEPTION",
        }


def _cau_allow(goal: str = "maintain_coherence") -> Tuple[bool, dict]:
    st = _cau_status(goal=goal)
    return bool(st.get("allow_learn", True)), st


def get_cognitive_status(goal: str = "maintain_coherence") -> dict:
    """
    Canonical cognitive status object (v0).
    For now: CAU is the source of truth.
    """
    st = _cau_status(goal=goal)
    return {
        "t": st.get("t", time.time()),
        "Phi": st.get("Phi"),
        "S": st.get("S"),
        "H": st.get("H"),
        "allow_learn": bool(st.get("allow_learn", False)),
        "adr_active": bool(st.get("adr_active", False)),
        "cooldown_s": int(st.get("cooldown_s", 0) or 0),
        "deny_reason": st.get("deny_reason"),
        "goal": st.get("goal", goal),
        "source": st.get("source"),
    }


# ------------------------------------------------------------
# Phase-2: commentary + verbosity gates (NO cached globals)
# ------------------------------------------------------------
def _env_truthy(name: str, default: str = "0") -> bool:
    v = os.getenv(name, default)
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def _verbosity_level() -> str:
    # off|minimal|terse|verbose (unknown -> terse)
    v = (os.getenv("AION_VERBOSITY", "off") or "off").strip().lower()
    if v not in ("off", "minimal", "terse", "verbose"):
        return "terse"
    return v


def _commentary_enabled() -> bool:
    # Hard rule: VERBOSITY=off disables commentary entirely
    if _verbosity_level() == "off":
        return False
    # Commentary is opt-in
    return _env_truthy("AION_COMMENTARY", "0")


def _emit_aion_commentary_line(goal: str = "maintain_coherence") -> None:
    """
    Emits exactly one stdout line prefixed [AION] when enabled.
    Always emits the tag (even if self_state fails) so pytest capture is deterministic.
    """
    if not _commentary_enabled():
        return

    msg: str
    try:
        from backend.modules.aion_cognition.self_state import self_state_summary
        msg = self_state_summary(goal=goal)
    except Exception:
        msg = "state unavailable"

    print(f"[AION] {msg}", flush=True)


def _infer_intent(ex_type: str, prompt: str = "") -> str:
    """
    Minimal intent classifier for per-turn telemetry.
    Keep stable strings (used for dashboards later).
    """
    t = (ex_type or "unknown").strip().lower()
    if t in ("flashcard", "matchup", "find_match"):
        return "recall"
    if t in ("anagram", "unjumble", "cloze"):
        return "solve"
    if t.startswith("grammar_") or t in ("grammar_fix", "grammar_agreement", "grammar_punctuation", "grammar_order"):
        return "edit"
    if t in ("spin_wheel", "group_sort"):
        return "associate"
    return "unknown"


def _coherence_from_cau(cs: dict | None) -> float | None:
    """
    Cheap coherence scalar for logs only.
    Not physics. Just a monotone-ish proxy based on CAU stability/entropy.
    """
    if not isinstance(cs, dict):
        return None
    S = cs.get("S")
    H = cs.get("H")
    try:
        if S is None or H is None:
            return None
        Sf = float(S)
        Hf = float(H)
        # map to 0..1-ish: higher S and lower H => higher coherence
        return max(0.0, min(1.0, 0.5 * Sf + 0.5 * (1.0 - Hf)))
    except Exception:
        return None

# ------------------------------------------------------------
# Phase-2 per-turn telemetry (DATA_ROOT aware)
# ------------------------------------------------------------

TURN_LOG_SCHEMA_V1 = {
    "schema": "AION.TurnLog.v1",
    "required": [
        "ts","session","mode","type","prompt",
        "intent","coherence","correct",
        "allow_learn","deny_reason","adr_active","cooldown_s",
        "S","H","Phi",
        "response_time_ms",
    ],
    "optional": ["guess", "answer"],
}

def _validate_turn_log(rec: dict) -> dict:
    rec = dict(rec or {})
    rec.setdefault("schema", TURN_LOG_SCHEMA_V1["schema"])
    for k in TURN_LOG_SCHEMA_V1["required"]:
        rec.setdefault(k, None)
    for k in TURN_LOG_SCHEMA_V1.get("optional", []):
        rec.setdefault(k, None)
    return rec

def _append_turn_log(rec: dict) -> None:
    try:
        rec = _validate_turn_log(rec)
        TURN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TURN_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"[CEE-Playback] Failed to append turn log: {e}")

CORRECTION_SCHEMA_V1 = {
    "schema": "AION.CorrectionEvent.v1",
    "required": [
        "ts", "session", "prompt",
        "from_answer", "to_answer",
        "cause", "allow_learn", "deny_reason",
    ],
}

def _append_correction_event(rec: dict) -> None:
    try:
        rec = dict(rec or {})
        rec.setdefault("schema", CORRECTION_SCHEMA_V1["schema"])
        for k in CORRECTION_SCHEMA_V1["required"]:
            rec.setdefault(k, None)

        CORRECTION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CORRECTION_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"[CEE-Playback] Failed to append correction event: {e}")

# ------------------------------------------------------------
# Project imports
# ------------------------------------------------------------
from backend.modules.aion_cognition.cee_lexicore_bridge import LexiCoreBridge
from backend.modules.aion_cognition.cee_lex_memory import LexMemory, recall_from_memory
from backend.modules.aion_cognition.language_habit_engine import update_habit_metrics

from backend.modules.aion_cognition.cee_language_templates import (
    generate_anagram,
    generate_find_match,
    generate_flashcard,
    generate_matchup,
    generate_spin_wheel,
    generate_unjumble,
)

from backend.modules.aion_cognition.cee_language_cloze import (
    generate_cloze,
    generate_group_sort,
)

from backend.modules.aion_cognition.cee_llm_exercise_generator import (
    generate_llm_exercise_batch,
)

from backend.modules.aion_cognition.cee_grammar_templates import (
    grammar_agreement_mcq,
    grammar_fix_sentence,
    grammar_punctuation_insert,
    grammar_word_order,
)

# ------------------------------------------------------------
# LexMemory queue-on-deny (Phase 46A)
# ------------------------------------------------------------
def _append_queue(rec: dict) -> None:
    try:
        LEX_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LEX_QUEUE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"[CEE-Playback] Failed to append lex queue: {e}")


def _make_lex():
    """Instantiate LexMemory with stable path if supported; fallback if not."""
    try:
        return LexMemory(path=LEX_PATH)
    except TypeError:
        return LexMemory()


_lex = _make_lex()


def _norm_resonance(resonance: dict) -> Tuple[float, float, float]:
    if not isinstance(resonance, dict):
        resonance = {}

    rho = resonance.get("rho", resonance.get("ρ", 0.6))
    Ibar = resonance.get("Ibar", resonance.get("Ī", resonance.get("I", 0.6)))
    sqi = resonance.get("sqi", resonance.get("SQI", 0.6))

    try:
        rho = float(rho)
    except Exception:
        rho = 0.6
    try:
        Ibar = float(Ibar)
    except Exception:
        Ibar = 0.6
    try:
        sqi = float(sqi)
    except Exception:
        sqi = 0.6

    return rho, Ibar, sqi


def _flush_queue(max_items: int = 200, goal: str = "maintain_coherence") -> int:
    allow, cau = _cau_allow(goal=goal)
    if not allow:
        return 0
    if not LEX_QUEUE_PATH.exists():
        return 0

    try:
        lines = LEX_QUEUE_PATH.read_text(encoding="utf-8").splitlines()
    except Exception:
        return 0
    if not lines:
        return 0

    applied = 0
    remaining: List[str] = []

    head = lines[:max_items]
    tail = lines[max_items:]

    for line in head:
        try:
            rec = json.loads(line)
            prompt = rec.get("prompt", "")
            answer = rec.get("answer", "")
            resonance = rec.get("resonance", {}) or {}
            rho, Ibar, sqi = _norm_resonance(resonance)

            _lex.update(
                prompt,
                answer,
                rho=rho,
                Ibar=Ibar,
                sqi=sqi,
                meta={"queued": True, "queued_reason": rec.get("reason")},
            )
            applied += 1
        except Exception:
            remaining.append(line)

    remaining.extend(tail)

    try:
        _lex.save()
    except Exception as e:
        logger.warning(f"[CEE-Playback] LexMemory save failed during flush: {e}")
        return 0

    try:
        if remaining:
            LEX_QUEUE_PATH.write_text("\n".join(remaining) + "\n", encoding="utf-8")
        else:
            try:
                LEX_QUEUE_PATH.unlink()
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"[CEE-Playback] Queue rewrite failed (non-fatal): {e}")

    if applied:
        logger.info(
            f"[CEE-Playback] ✅ Flushed {applied} queued LexMemory updates (CAU allowed). "
            f"deny_reason={cau.get('deny_reason')} adr_active={cau.get('adr_active')} cooldown_s={cau.get('cooldown_s')}"
        )
    return applied


def _compute_goal_from_cau(cs: dict | None, current_goal: str) -> str:
    if not isinstance(cs, dict):
        return current_goal or "maintain_coherence"

    # CAU denial gates learning, but SHOULD NOT override the active goal.
    # Keep goal stable to avoid thrash.
    allow = cs.get("allow_learn")
    if allow is False:
        return current_goal or "maintain_coherence"

    # If we're in conflict resolution, do not auto-promote to improve_accuracy.
    if (current_goal or "").strip() == "resolve_conflict":
        return "resolve_conflict"

    S = cs.get("S")
    H = cs.get("H")
    try:
        if S is not None and H is not None:
            Sf = float(S)
            Hf = float(H)
            if Sf >= 0.85 and Hf <= 0.15:
                return "improve_accuracy"
    except Exception:
        pass

    return current_goal or "maintain_coherence"

def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)) or str(default))
    except Exception:
        return default

# ================================================================
# 🧩 Playback Engine
# ================================================================
class CEEPlayback:
    def __init__(self, mode: str = "simulate"):
        self.mode = mode
        self.session_id = f"PLAY-{int(time.time())}"
        self.session: List[dict] = []
        self.bridge = LexiCoreBridge()
        self.goal = "maintain_coherence"
        self._recent_correct: List[bool] = []

        # Phase 5: last observed actuals (used to forecast next)
        self._last_rho: float = 0.6
        self._last_sqi: float = 0.6

        # Phase 5: last emitted forecast (used for predicted-vs-actual comparison)
        self._last_forecast_rho: float = 0.6
        self._last_forecast_sqi: float = 0.6
        self._last_forecast_conf: float = 0.2

        logger.info(f"[CEE-Playback] Session {self.session_id} started in {mode} mode")

    def play_exercise(self, ex: dict):
        """Safely play a single CEE exercise with full fallback handling."""
        t0 = time.perf_counter()

        ex_type = ex.get("type", "unknown")

        prompt = ex.get("prompt")
        if not isinstance(prompt, str):
            prompt = str(prompt or "").strip()
        safe_prompt = prompt if prompt else "[no prompt provided]"

        options = ex.get("options", [])
        answer = ex.get("answer")

        resonance = ex.get("resonance", {"rho": 0.6, "Ibar": 0.6, "sqi": 0.6})
        if not isinstance(resonance, dict):
            resonance = {"rho": 0.6, "Ibar": 0.6, "sqi": 0.6}

        print(f"\n▶ {ex_type} - {safe_prompt}")
        if options:
            print(f"Options: {', '.join(str(o) for o in options if o)}")

        # --- CAU snapshot once per turn (so goal can transition even if no learn path runs) ---
        _, cau_snap = _cau_allow(goal=self.goal)

        # --- Phase 4 starter: compute + log goal transition ---
        new_goal = _compute_goal_from_cau(cau_snap, self.goal)
        if new_goal != self.goal:
            log_goal_transition(
                ts=time.time(),
                from_goal=self.goal,
                to_goal=new_goal,
                cause="cau_update",
                session=self.session_id,
            )
            self.goal = new_goal

            # refresh CAU snapshot under the new goal (keeps telemetry consistent)
            _, cau_snap = _cau_allow(goal=self.goal)

        # --- Phase 5: Forecast (read-only) + persist last-forecast fields ---
        try:
            from backend.modules.aion_cognition.forecast_report import append_forecast

            # confidence from CAU if present, else low confidence
            conf = 0.2
            if isinstance(cau_snap, dict):
                S = cau_snap.get("S")
                H = cau_snap.get("H")
                try:
                    if S is not None and H is not None:
                        Sf = float(S)
                        Hf = float(H)
                        conf = max(0.0, min(1.0, 0.5 * Sf + 0.5 * (1.0 - Hf)))
                except Exception:
                    conf = 0.2

            # Forecast = "next" predicted values (stub: carry-forward last observed)
            rho_next = float(getattr(self, "_last_rho", 0.6))
            sqi_next = float(getattr(self, "_last_sqi", 0.6))

            append_forecast(
                ts=time.time(),
                session=self.session_id,
                goal=self.goal,
                rho_next=rho_next,
                sqi_next=sqi_next,
                confidence=conf,
            )

            # store what we just forecasted (for predicted-vs-actual on the NEXT turn)
            self._last_forecast_rho = float(rho_next)
            self._last_forecast_sqi = float(sqi_next)
            self._last_forecast_conf = float(conf)
        except Exception:
            pass

        # Phase-2: optional cognitive commentary line (fact-only) — uses current goal
        _emit_aion_commentary_line(goal=self.goal)

        # --- Phase 5: Risk awareness (read-only; gated by confidence) ---
        try:
            from backend.modules.aion_cognition.risk_awareness import (
                append_risk_awareness,
                compute_risk_from_cau,
            )

            min_conf = float(os.getenv("AION_RISK_MIN_CONF", "0.6") or "0.6")
            min_score = float(os.getenv("AION_RISK_MIN_SCORE", "0.65") or "0.65")

            topic = _infer_intent(ex_type, safe_prompt)
            risk = compute_risk_from_cau(cau_snap if isinstance(cau_snap, dict) else {}, conf)

            if conf >= min_conf and risk >= min_score:
                S = cau_snap.get("S") if isinstance(cau_snap, dict) else None
                H = cau_snap.get("H") if isinstance(cau_snap, dict) else None
                append_risk_awareness(
                    ts=time.time(),
                    session=self.session_id,
                    goal=self.goal,
                    topic=topic,
                    risk=risk,
                    confidence=conf,
                    S=None if S is None else float(S),
                    H=None if H is None else float(H),
                    cause="risk_awareness",
                )
        except Exception:
            pass

        # Opportunistic queue flush — uses current goal
        try:
            _flush_queue(goal=self.goal)
        except Exception:
            pass

        # Defaults (avoid UnboundLocalError)
        guess = ""
        correct: Optional[bool] = None

        # -------------------------
        # LexMemory recall
        # -------------------------
        memory_hit = recall_from_memory(prompt)
        if memory_hit and memory_hit.get("answer"):
            guess = memory_hit["answer"]
            logger.info(f"[CEE-Playback] 🧠 Recall -> {prompt} -> {guess}")

            if guess and answer and str(guess).strip() != str(answer).strip():
                logger.warning(
                    f"[LexMemory] ⚠ Recall mismatch for '{prompt}': "
                    f"recalled '{guess}', expected '{answer}'"
                )

                # --- Phase 5 (stub): contradiction -> resolve_conflict ---
                # Deterministic: only when recalled answer conflicts with provided answer.
                if self.goal != "resolve_conflict":
                    try:
                        log_goal_transition(
                            ts=time.time(),
                            from_goal=self.goal,
                            to_goal="resolve_conflict",
                            cause="contradiction",
                            session=self.session_id,
                        )
                        self.goal = "resolve_conflict"
                        # refresh CAU snapshot under new goal (keeps rest-of-turn consistent)
                        _, cau_snap = _cau_allow(goal=self.goal)
                    except Exception:
                        pass
        else:
            if self.mode == "interactive":
                try:
                    guess = input("Your answer: ").strip()
                except Exception:
                    guess = ""
            else:
                guess = ""
                if answer:
                    guess = str(answer).strip()

                if (not guess) and options:
                    p = safe_prompt.lower()
                    hit = None
                    for o in options:
                        s = str(o).strip()
                        if s and s.lower() in p:
                            hit = s
                            break
                    guess = hit if hit else str(options[0]).strip()

                if not guess:
                    guess = ""

        guess = (guess or "").strip() if isinstance(guess, str) else str(guess or "").strip()
        answer = (answer or "").strip() if isinstance(answer, str) else str(answer or "").strip()

        # --- Phase 5: update last observed values (actuals for next forecast) ---
        # Do this once per turn, regardless of correct/wrong/denied.
        try:
            rho_obs, _, sqi_obs = _norm_resonance(resonance)
            self._last_rho = float(rho_obs)
            self._last_sqi = float(sqi_obs)
        except Exception:
            pass

        # --- Phase 5: predicted vs actual + prediction miss event (read-only) ---
        try:
            rho_actual = float(getattr(self, "_last_rho", 0.6))
            sqi_actual = float(getattr(self, "_last_sqi", 0.6))

            rho_pred = float(getattr(self, "_last_forecast_rho", 0.6))
            sqi_pred = float(getattr(self, "_last_forecast_sqi", 0.6))
            conf_pred = float(getattr(self, "_last_forecast_conf", 0.2))

            rho_err = abs(rho_actual - rho_pred)
            sqi_err = abs(sqi_actual - sqi_pred)

            # thresholds (stable defaults; env-overridable for tests)
            TH_CONF = float(os.getenv("AION_FORECAST_MIN_CONF", "0.6") or "0.6")
            TH_RHO = float(os.getenv("AION_FORECAST_RHO_ERR", "0.25") or "0.25")
            TH_SQI = float(os.getenv("AION_FORECAST_SQI_ERR", "0.25") or "0.25")

            if conf_pred >= TH_CONF and (rho_err >= TH_RHO or sqi_err >= TH_SQI):
                from backend.modules.aion_cognition.prediction_miss import append_prediction_miss

                append_prediction_miss(
                    ts=time.time(),
                    session=self.session_id,
                    goal=self.goal,
                    rho_pred=rho_pred,
                    sqi_pred=sqi_pred,
                    rho_actual=rho_actual,
                    sqi_actual=sqi_actual,
                    rho_err=rho_err,
                    sqi_err=sqi_err,
                    confidence=conf_pred,
                    thresholds={"min_conf": TH_CONF, "rho_err": TH_RHO, "sqi_err": TH_SQI},
                    cause="prediction_miss",
                )
        except Exception:
            pass

        if not answer:
            logger.info(f"[CEE-Playback] ⚠ No answer provided for {ex_type} - skipping scoring.")
            correct = None
        else:
            correct = (guess == answer)

            # --- Phase 4: repeated-error trigger (local, deterministic) ---
            if isinstance(correct, bool):
                self._recent_correct.append(bool(correct))
                if len(self._recent_correct) > 6:
                    self._recent_correct = self._recent_correct[-6:]

                wrongs = sum(1 for v in self._recent_correct if v is False)
                # 3 wrong in last 6 -> improve_accuracy
                if wrongs >= 3 and self.goal != "improve_accuracy":
                    log_goal_transition(
                        ts=time.time(),
                        from_goal=self.goal,
                        to_goal="improve_accuracy",
                        cause="repeated_errors",
                        session=self.session_id,
                    )
                    self.goal = "improve_accuracy"
                    _, cau_snap = _cau_allow(goal=self.goal)

            # =====================================================
            # ✅ Correct branch (CAU gated learn-or-queue)
            # =====================================================
            if correct:
                logger.info(f"[CEE-Playback] ✅ Correct: {guess}")

                try:
                    _flush_queue(goal=self.goal)
                except Exception:
                    pass

                rho, Ibar, sqi = _norm_resonance(resonance)

                allow = bool(cau_snap.get("allow_learn", True)) if isinstance(cau_snap, dict) else True
                cau = cau_snap or {}

                if allow:
                    _lex.update(
                        prompt,
                        answer,
                        rho=rho,
                        Ibar=Ibar,
                        sqi=sqi,
                        meta={"source": "cee_playback_correct", "session": self.session_id, "type": ex_type},
                    )
                    _lex.save()

                    try:
                        from backend.modules.aion_cognition.akg_singleton import reinforce_answer_is
                        reinforce_answer_is(prompt, answer, hit=1.0)
                    except Exception:
                        pass

                    logger.info(
                        f"[CAU] ALLOW_LEARN S={cau.get('S')} H={cau.get('H')} Phi={cau.get('Phi')} "
                        f"deny_reason={cau.get('deny_reason')} adr_active={cau.get('adr_active')} cooldown_s={cau.get('cooldown_s')}"
                    )
                else:
                    _append_queue(
                        {
                            "t": time.time(),
                            "prompt": prompt,
                            "answer": answer,
                            "resonance": resonance,
                            "cau": cau,
                            "reason": "correct_but_cau_denied",
                            "session": self.session_id,
                            "type": ex_type,
                        }
                    )
                    logger.warning(
                        f"[CEE-Playback] 🧯 CAU denied; queued LexMemory update. "
                        f"deny_reason={cau.get('deny_reason')} S={cau.get('S')} H={cau.get('H')} cooldown_s={cau.get('cooldown_s')}"
                    )
            # =====================================================
            # ❌ Wrong branch (optional auto-correct; CAU gated)
            # =====================================================
            else:
                logger.info(f"[CEE-Playback] ❌ Wrong (expected {answer}): {guess}")

                if memory_hit and answer and AUTO_CORRECT:
                    try:
                        _flush_queue(goal=self.goal)
                    except Exception:
                        pass

                    rho, Ibar, sqi = _norm_resonance(resonance)

                    # use the per-turn CAU snapshot
                    allow = bool(cau_snap.get("allow_learn", True)) if isinstance(cau_snap, dict) else True
                    cau = cau_snap or {}

                    if allow:
                        _lex.update(
                            prompt,
                            answer,
                            rho=rho,
                            Ibar=Ibar,
                            sqi=sqi,
                            meta={
                                "auto_correct": True,
                                "source": "cee_playback",
                                "session": self.session_id,
                                "type": ex_type,
                            },
                        )
                        _lex.save()

                        # ✅ Phase-3 correction event (persisted)
                        _append_correction_event(
                            {
                                "ts": time.time(),
                                "session": self.session_id,
                                "prompt": safe_prompt,
                                "from_answer": guess,
                                "to_answer": answer,
                                "cause": "auto_correct",
                                "allow_learn": True,
                                "deny_reason": None,
                            }
                        )

                        logger.info(f"[LexMemory] 🔧 Auto-corrected memory for '{prompt}' -> {answer}")
                    else:
                        _append_queue(
                            {
                                "t": time.time(),
                                "prompt": prompt,
                                "answer": answer,
                                "resonance": resonance,
                                "cau": cau,
                                "reason": "auto_correct_but_cau_denied",
                                "session": self.session_id,
                                "type": ex_type,
                            }
                        )

                        # ✅ Phase-3 correction event (denied, queued)
                        _append_correction_event(
                            {
                                "ts": time.time(),
                                "session": self.session_id,
                                "prompt": safe_prompt,
                                "from_answer": guess,
                                "to_answer": answer,
                                "cause": "auto_correct_denied_queued",
                                "allow_learn": False,
                                "deny_reason": cau.get("deny_reason"),
                            }
                        )

                        logger.warning(
                            f"[CEE-Playback] 🧯 CAU denied; queued auto-correct. "
                            f"deny_reason={cau.get('deny_reason')} S={cau.get('S')} H={cau.get('H')} cooldown_s={cau.get('cooldown_s')}"
                        )

        # ---- turn telemetry (Phase-2) ----
        rt_ms = int(round((time.perf_counter() - t0) * 1000.0))
        cs = cau_snap or {}
        _append_turn_log(
            {
                "ts": time.time(),
                "session": self.session_id,
                "mode": self.mode,
                "type": ex_type,
                "prompt": safe_prompt,
                "intent": _infer_intent(ex_type, safe_prompt),
                "coherence": _coherence_from_cau(cs),
                "correct": correct,
                "guess": guess,
                "answer": answer,
                "goal": self.goal,
                "allow_learn": cs.get("allow_learn") if cs else None,
                "deny_reason": cs.get("deny_reason") if cs else None,
                "adr_active": cs.get("adr_active") if cs else None,
                "cooldown_s": cs.get("cooldown_s") if cs else None,
                "S": cs.get("S") if cs else None,
                "H": cs.get("H") if cs else None,
                "Phi": cs.get("Phi") if cs else None,
                "response_time_ms": rt_ms,
            }
        )

        self.session.append(
            {
                "type": ex_type,
                "prompt": safe_prompt,
                "guess": guess,
                "answer": answer,
                "correct": correct,
                "resonance": resonance,
                "timestamp": time.time(),
                "cau": cs if cs else _cau_status(goal=self.goal),
                "goal": self.goal,
                "response_time_ms": rt_ms,
            }
        )

    def run(self, n: int = 6, feed: str = "self_train", gens_csv: str = ""):
        """
        Program feeds:
        - self_train: deterministic trainer (default)
        - llm: optional generation (explicit only)
        """
        exercises: List[dict] = []
        feed = (feed or "self_train").strip().lower()

        seed = _env_int("CEE_SEED", 0)
        if seed:
            random.seed(seed)

        # ✅ Important for tests: emit one commentary line at run start (if enabled),
        # even if n=0 or generator fails (so stdout capture is deterministic).
        _emit_aion_commentary_line(goal=self.goal)

        if feed in ("wordwall", "hybrid", "local"):
            logger.warning(f"[CEE-Playback] feed '{feed}' not in program; forcing self_train.")
            feed = "self_train"

        if feed == "llm":
            try:
                batch = generate_llm_exercise_batch(topic="linguistics", count=n)
                exercises.extend(batch)
            except Exception as e:
                logger.error(f"[CEE-Playback] LLM feed requested but failed; falling back to self_train. err={e}")
                feed = "self_train"

        if feed == "self_train":
            gens = [
                generate_matchup,
                generate_anagram,
                generate_unjumble,
                generate_flashcard,
                generate_find_match,
                generate_spin_wheel,
                generate_cloze,
                generate_group_sort,
                grammar_fix_sentence,
                grammar_agreement_mcq,
                grammar_punctuation_insert,
                grammar_word_order,
            ]

            name_to_gen = {g.__name__: g for g in gens}

            forced: List[str] = []
            if gens_csv:
                forced = [s.strip() for s in gens_csv.split(",") if s.strip()]

            for i in range(n):
                if forced:
                    gname = forced[i % len(forced)]
                    gen = name_to_gen.get(gname)
                    if gen is None:
                        logger.warning(f"[CEE-Playback] Unknown gen '{gname}', falling back to random.")
                        gen = random.choice(gens)
                else:
                    gen = random.choice(gens)

            for _ in range(n):
                gen = random.choice(gens)
                try:
                    if gen.__name__ == "generate_cloze":
                        sentence = random.choice(
                            [
                                "The sun rises in the ____.",
                                "She plays the ____ beautifully.",
                                "Water freezes at zero ____.",
                                "He is reading a ____ book.",
                            ]
                        )
                        if "sun rises" in sentence:
                            missing_word = "east"
                        elif "plays the" in sentence:
                            missing_word = "piano"
                        elif "freezes" in sentence:
                            missing_word = "degrees"
                        else:
                            missing_word = "interesting"
                        ex = gen(sentence, missing_word, bridge=self.bridge)

                    elif gen.__name__ == "generate_group_sort":
                        groups = {"Fruits": ["apple", "banana"], "Animals": ["dog", "cat"]}
                        ex = gen(groups)

                    else:
                        ex = gen()

                    if not isinstance(ex, dict):
                        ex = ex.to_dict()

                    exercises.append(ex)

                except Exception as e:
                    logger.warning(f"[CEE-Playback] Error running {gen.__name__}: {e}")

        # De-dupe identical prompts in one run
        seen = set()
        deduped: List[dict] = []
        for ex in exercises:
            if not isinstance(ex, dict):
                continue
            key = (
                (ex.get("type") or "unknown"),
                (str(ex.get("prompt") or "").strip().lower()),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(ex)
        exercises = deduped

        for ex in exercises:
            try:
                self.play_exercise(ex)
            except Exception as e:
                logger.warning(f"[CEE-Playback] Error playing exercise: {e}")

        return self.finalize()

    def finalize(self):
        """Compute metrics, export session summary, snapshot resonance."""
        if not self.session:
            logger.warning("[CEE-Playback] No exercises played.")
            return None

        valid_corrects = [e["correct"] for e in self.session if isinstance(e["correct"], bool)]
        perf = round(sum(valid_corrects) / len(valid_corrects), 3) if valid_corrects else 0.0

        def _get_sqi(e):
            r = e.get("resonance", {}) if isinstance(e.get("resonance", {}), dict) else {}
            return r.get("sqi", r.get("SQI", 0.0))

        avg_SQI = round(sum(float(_get_sqi(e) or 0.0) for e in self.session) / len(self.session), 3)

        self_state = None
        try:
            from backend.modules.aion_cognition.self_state import self_state_summary
            self_state = self_state_summary(goal=self.goal)
            logger.info(f"[SELF] {self_state}")
        except Exception as e:
            logger.warning(f"[CEE-Playback] self_state_summary failed (non-fatal): {e}")

        summary = {
            "timestamp": time.time(),
            "session": self.session_id,
            "mode": self.mode,
            "entries": len(self.session),
            "performance": perf,
            "avg_SQI": avg_SQI,
            "self_state": self_state,
            "schema": "CEEPlayback.v1",
        }

        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        logger.info(f"[CEE-Playback] Exported playback log -> {OUT_PATH}")

        # --- Phase 5: end-of-run forecast rollup ---
        try:
            from backend.modules.aion_cognition.forecast_summary import write_forecast_report_summary
            write_forecast_report_summary(session=self.session_id, ts=time.time())
        except Exception as e:
            logger.warning(f"[CEE-Playback] forecast_report summary failed (non-fatal): {e}")

        try:
            update_habit_metrics({"ρ̄": 0.0, "Ī": 0.0, "SQĪ": avg_SQI})
        except Exception as e:
            logger.warning(f"[CEE-Playback] Habit metrics update failed: {e}")

        print(json.dumps(summary, indent=2))

        try:
            from backend.modules.aion_cognition.cee_resonance_analytics import snapshot_memory
            snapshot_memory(tag=self.session_id)
        except Exception as e:
            logger.warning(f"[CEE-Playback] snapshot_memory failed (non-fatal): {e}")
        else:
            logger.info(f"[CEE-Playback] Logged resonance snapshot for {self.session_id}")

        return summary


# ================================================================
# 🚀 Entry Point (non-interactive friendly)
# ================================================================
if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)

    ap = argparse.ArgumentParser(description="CEE Exercise Playback (CAU-gated LexMemory)")
    ap.add_argument(
        "--mode",
        choices=["simulate", "interactive"],
        default=os.getenv("CEE_MODE", "simulate"),
        help="simulate = auto-run; interactive = console input",
    )
    ap.add_argument(
        "--n",
        type=int,
        default=int(os.getenv("CEE_N", "6")),
        help="number of exercises to run",
    )
    ap.add_argument(
        "--feed",
        choices=["self_train", "llm"],
        default=os.getenv("CEE_FEED", "self_train"),
        help="self_train (default) | llm (explicit only)",
    )

    # Phase 3: correction history query (CLI)
    ap.add_argument(
        "--history",
        type=str,
        default="",
        help="print correction history for a prompt and exit",
    )
    ap.add_argument(
        "--history_n",
        type=int,
        default=int(os.getenv("AION_HISTORY_N", "20")),
        help="max history events (default 20)",
    )
    ap.add_argument(
        "--since_ts",
        type=float,
        default=None,
        help="Only return events with t >= since_ts (float seconds; e.g. 1769339264.05)",
    )
    ap.add_argument(
        "--until_ts",
        type=float,
        default=None,
        help="Only return events with t <= until_ts (float seconds; use +0.5/+1.0 for whole-second windows)",
    )
    ap.add_argument(
        "--gens",
        type=str,
        default=os.getenv("CEE_GENS", ""),
        help="Comma-separated generator names to use in order (overrides random selection).",
    )

    args = ap.parse_args()

    # Phase 3: history mode exits early
    if args.history:
        try:
            evs = get_correction_history(
                args.history,
                limit=args.history_n,
                since_ts=getattr(args, "since_ts", None),
                until_ts=getattr(args, "until_ts", None),
            )
        except Exception as e:
            logging.getLogger(__name__).warning(f"[CEE-Playback] history query failed: {e}")
            evs = []
        print(
            json.dumps(
                {"prompt": args.history, "events": evs, "schema": "AION.CorrectionHistory.v1"},
                indent=2,
                ensure_ascii=False,
            )
        )
        raise SystemExit(0)

    mode = (args.mode or "simulate").strip().lower()
    if mode not in ("simulate", "interactive"):
        mode = "simulate"

    feed = (args.feed or "self_train").strip().lower()
    if feed in ("wordwall", "hybrid", "local"):
        logging.getLogger(__name__).warning(
            f"[CEE-Playback] feed '{feed}' is not part of the program; forcing self_train."
        )
        feed = "self_train"

    if feed == "llm" and not os.getenv("OPENAI_API_KEY"):
        logging.getLogger(__name__).warning("[CEE-Playback] OPENAI_API_KEY missing; forcing self_train.")
        feed = "self_train"

    player = CEEPlayback(mode=mode)
    player.run(n=args.n, feed=feed, gens_csv=args.gens)