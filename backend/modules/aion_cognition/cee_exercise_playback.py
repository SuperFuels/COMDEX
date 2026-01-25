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

Key guarantee (per your screenshot):
  ✅ On every correct answer, LexMemory is UPDATED AND SAVED to disk
     (ONLY when CAU allows learning) so Demo 5 can consume: data/memory/lex_memory.json

Program goal (per your plan):
  - Primary training = SELF_TRAIN (your Wordwall-replacement)
  - Optional = LLM generation (explicit only, never surprise)
  - Wordwall/hybrid removed from the program path
"""

import json
import time
import random
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

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
AUTO_CORRECT = os.getenv("CEE_LEX_AUTO_CORRECT", "1").lower() in ("1", "true", "yes", "on")

# ------------------------------------------------------------
# CAU gating (authority for learning) — Phase 46A stable API
# ------------------------------------------------------------
try:
    # cau_authority.py exposes get_authority_state/get_authority/get_state
    from backend.modules.aion_cognition.cau_authority import get_authority_state as _cau_state
except Exception as _e:
    _cau_state = None
    logger.warning(
        f"[CEE-Playback] CAU authority not available; learning will be allowed by default. err={_e}"
    )

def _data_root() -> Path:
    return Path(os.getenv("DATA_ROOT", "data"))

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

def _append_turn_log(rec: dict) -> None:
    try:
        TURN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TURN_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"[CEE-Playback] Failed to append turn log: {e}")

def _cau_status(goal: str = "maintain_coherence") -> dict:
    """
    Returns CAU dict (must include allow_learn).
    Safe fallback = allow learn (soft-fail) to avoid breaking playback.
    """
    if _cau_state is None:
        return {
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
            return st
        logger.warning("[CEE-Playback] CAU returned unexpected shape; allowing learn (soft-fail).")
        return {
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


# ------------------------------------------------------------
# Project imports
# ------------------------------------------------------------
from backend.modules.aion_cognition.cee_lexicore_bridge import LexiCoreBridge
from backend.modules.aion_cognition.language_habit_engine import update_habit_metrics
from backend.modules.aion_cognition.cee_lex_memory import LexMemory, recall_from_memory

from backend.modules.aion_cognition.cee_language_templates import (
    generate_matchup,
    generate_anagram,
    generate_unjumble,
    generate_flashcard,
    generate_find_match,
    generate_spin_wheel,
)

from backend.modules.aion_cognition.cee_language_cloze import (
    generate_cloze,
    generate_group_sort,
)

from backend.modules.aion_cognition.cee_llm_exercise_generator import (
    generate_llm_exercise_batch,
)

from backend.modules.aion_cognition.cee_grammar_templates import (
    grammar_fix_sentence,
    grammar_agreement_mcq,
    grammar_punctuation_insert,
    grammar_word_order,
)

# ------------------------------------------------------------
# Stable output paths
# ------------------------------------------------------------
def _paths() -> Tuple[Path, Path, Path]:
    root = _data_root()
    out_path = root / "sessions" / "playback_log.qdata.json"
    lex_path = root / "memory" / "lex_memory.json"
    queue_path = root / "memory" / "lexmemory_queue.jsonl"
    return out_path, lex_path, queue_path

OUT_PATH, LEX_PATH, LEX_QUEUE_PATH = _paths()

DATA_ROOT = Path(os.getenv("DATA_ROOT", "data"))
TURN_LOG_PATH = DATA_ROOT / "telemetry" / "turn_log.jsonl"

AION_COMMENTARY = os.getenv("AION_COMMENTARY", "0").lower() in ("1", "true", "yes", "on")
AION_VERBOSITY = (os.getenv("AION_VERBOSITY", "terse") or "terse").strip().lower()
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


def _flush_queue(max_items: int = 200, goal: str = "maintain_coherence") -> int:
    """
    Apply queued lex updates iff CAU allows learning.
    Safe: if anything goes wrong, we stop and keep remaining queue intact.
    """
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

    # process up to max_items; keep the rest
    head = lines[:max_items]
    tail = lines[max_items:]

    for line in head:
        try:
            rec = json.loads(line)
            prompt = rec.get("prompt", "")
            answer = rec.get("answer", "")
            resonance = rec.get("resonance", {}) or {}
            rho, Ibar, sqi = _norm_resonance(resonance)

            # CAU already allowed at flush start; still keep meta trail
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


def _make_lex():
    """Instantiate LexMemory with stable path if supported; fallback if not."""
    try:
        return LexMemory(path=LEX_PATH)
    except TypeError:
        return LexMemory()


# Module singleton
_lex = _make_lex()


def _norm_resonance(resonance: dict) -> Tuple[float, float, float]:
    """
    Normalize resonance keys from any of:
      - screenshot keys: rho, Ibar, sqi
      - your earlier keys: ρ, I, SQI
      - other variants: Ī
    """
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


# ================================================================
# 🧩 Playback Engine
# ================================================================
class CEEPlayback:
    def __init__(self, mode: str = "simulate"):
        self.mode = mode
        self.session_id = f"PLAY-{int(time.time())}"
        self.session: List[dict] = []
        self.bridge = LexiCoreBridge()
        logger.info(f"[CEE-Playback] Session {self.session_id} started in {mode} mode")

    def play_exercise(self, ex: dict):
        """Safely play a single CEE exercise with full fallback handling."""
        t0 = time.perf_counter()
        cau_snap = None

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

        # Phase-2: optional cognitive commentary line (fact-only)
        if AION_COMMENTARY:
            try:
                from backend.modules.aion_cognition.self_state import self_state_summary
                print(f"[AION] {self_state_summary(goal='maintain_coherence')}")
            except Exception:
                pass

        # Opportunistic queue flush
        try:
            _flush_queue(goal="maintain_coherence")
        except Exception:
            pass

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
        else:
            if self.mode == "interactive":
                try:
                    guess = input("Your answer: ").strip()
                except Exception:
                    guess = ""
            else:
                # simulate mode: try to be "smart" without requiring LLM
                guess = ""

                # 1) If exercise provides an answer, use it (self_train should)
                if answer:
                    guess = str(answer).strip()

                # 2) If MCQ options and no answer provided, try simple prompt->option match
                if (not guess) and options:
                    p = safe_prompt.lower()

                    # tiny heuristic: if one option appears in prompt, pick it
                    hit = None
                    for o in options:
                        s = str(o).strip()
                        if s and s.lower() in p:
                            hit = s
                            break
                    if hit:
                        guess = hit
                    else:
                        # fallback: pick first option (deterministic) instead of random
                        guess = str(options[0]).strip()

                # 3) last resort
                if not guess:
                    guess = ""

        guess = (guess or "").strip() if isinstance(guess, str) else str(guess or "").strip()
        answer = (answer or "").strip() if isinstance(answer, str) else str(answer or "").strip()

        if not answer:
            logger.info(f"[CEE-Playback] ⚠ No answer provided for {ex_type} - skipping scoring.")
            correct = None
        else:
            correct = (guess == answer)

            # =====================================================
            # ✅ Correct branch (CAU gated learn-or-queue)
            # =====================================================
            if correct:
                logger.info(f"[CEE-Playback] ✅ Correct: {guess}")

                # opportunistic flush before mutation attempt
                try:
                    _flush_queue(goal="maintain_coherence")
                except Exception:
                    pass

                rho, Ibar, sqi = _norm_resonance(resonance)

                allow, cau = _cau_allow(goal="maintain_coherence")
                cau_snap = cau

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

                    # Demo 5 hook: reinforce AKG edge (best-effort)
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
                        _flush_queue(goal="maintain_coherence")
                    except Exception:
                        pass

                    rho, Ibar, sqi = _norm_resonance(resonance)

                    allow, cau = _cau_allow(goal="maintain_coherence")
                    cau_snap = cau

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
                "correct": correct,
                "allow_learn": bool(cs.get("allow_learn")) if cs else None,
                "deny_reason": cs.get("deny_reason") if cs else None,
                "adr_active": cs.get("adr_active") if cs else None,
                "cooldown_s": cs.get("cooldown_s") if cs else None,
                "S": cs.get("S") if cs else None,
                "H": cs.get("H") if cs else None,
                "Phi": cs.get("Phi") if cs else None,
                "response_time_ms": rt_ms,
            }
        )

        # keep session record (include CAU snapshot if we have it)
        self.session.append(
            {
                "type": ex_type,
                "prompt": safe_prompt,
                "guess": guess,
                "answer": answer,
                "correct": correct,
                "resonance": resonance,
                "timestamp": time.time(),
                "cau": cs if cs else _cau_status(goal="maintain_coherence"),
                "response_time_ms": rt_ms,
            }
        )

    def _write_dummy_ral_metrics(data_root: Path) -> None:
        p = data_root / "learning" / "ral_metrics.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        # enough for CAU: Phi/S/H
        line = {
            "timestamp": 0,
            "mean_phi": 0.0,
            "stability": 1.0,
            "drift_entropy": 0.0,
        }
        p.write_text(json.dumps(line) + "\n", encoding="utf-8")

    def run(self, n: int = 6, feed: str = "self_train"):
        """
        Program feeds:
        - self_train: your fast trainer (wordwall replacement)
        - llm: optional generation (explicit only)
        """
        exercises: List[dict] = []
        feed = (feed or "self_train").strip().lower()

        # Hard block legacy feeds
        if feed in ("wordwall", "hybrid", "local"):
            logger.warning(f"[CEE-Playback] feed '{feed}' not in program; forcing self_train.")
            feed = "self_train"

        # 1) LLM feed (explicit only)
        if feed == "llm":
            try:
                batch = generate_llm_exercise_batch(topic="linguistics", count=n)
                exercises.extend(batch)
            except Exception as e:
                logger.error(f"[CEE-Playback] LLM feed requested but failed; falling back to self_train. err={e}")
                feed = "self_train"

        # 2) SELF_TRAIN feed (default, deterministic, no network)
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

                        # ✅ reuse already-initialized bridge (prevents double load + warnings)
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

        # -------------------------------
        # 4.5) De-dupe identical prompts in one run
        # -------------------------------
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

        # 5) Play
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

        # ---- SELF state (non-fatal) ----
        self_state = None
        try:
            from backend.modules.aion_cognition.self_state import self_state_summary
            self_state = self_state_summary()
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

        try:
            update_habit_metrics({"ρ̄": 0.0, "Ī": 0.0, "SQĪ": avg_SQI})
        except Exception as e:
            logger.warning(f"[CEE-Playback] Habit metrics update failed: {e}")

        print(json.dumps(summary, indent=2))

        # Optional resonance snapshot (safe)
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
    import logging
    import os

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

    # Program feeds (Wordwall removed)
    ap.add_argument(
        "--feed",
        choices=["self_train", "llm"],
        default=os.getenv("CEE_FEED", "self_train"),
        help="self_train (default) | llm (explicit only)",
    )

    args = ap.parse_args()

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
    player.run(n=args.n, feed=feed)