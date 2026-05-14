#!/usr/bin/env python3
# ================================================================
# 🧠 CEE LexMemory - Resonant Knowledge Reinforcement Engine
# Phase 45G.13/14 - Atomic Persistent Symbolic Resonance Memory
# ================================================================
"""
Stores and recalls resonance-weighted associations learned during
language and reasoning exercises.

Upgrades in this version:
  ✅ Atomic + validated writes + .bak backups + auto-recovery
  ✅ Versioned on-disk schema (stable forward/backward compatibility)
  ✅ Migration from legacy "prompt↔answer" keyed file format
  ✅ Class API (LexMemory) + backwards-compatible function API
  ✅ Fuzzy recall weighted by SQI
  ✅ **CAU Authority Gate**: reinforcement/maintenance ONLY runs when allow_learn=true

Memory file:
    ${DATA_ROOT:-data}/memory/lex_memory.json
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import tempfile
import time
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SCHEMA_VERSION = 2  # v2 = {"version":2, "alpha":..., "entries":[LexEntry...]}

# ================================================================
# 📁 DATA_ROOT (single source of truth)
# ================================================================
def _data_root() -> Path:
    return Path(os.getenv("DATA_ROOT", "data"))

def _memory_path() -> Path:
    return _data_root() / "memory" / "lex_memory.json"

# ================================================================
# 🛡️ CAU Authority Gate (robust import + safe fallback)
# ================================================================
CAU_ENABLED = os.getenv("CAU_ENABLED", "1").lower() in ("1", "true", "yes", "on")
CAU_DEFAULT_GOAL = os.getenv("CAU_DEFAULT_GOAL", "maintain_coherence")

def _safe_call(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except Exception:
        return None

def _get_cau_state(goal: str | None = None) -> Dict[str, Any]:
    """
    Returns a dict like:
      { "allow_learn": bool, "deny_reason": str|None, "S": float, "H": float, "Phi": float, "cooldown_s": int, ... }
    Defensive: tries multiple function names to avoid hard coupling to one CAU API.
    """
    if not CAU_ENABLED:
        return {
            "allow_learn": True,
            "deny_reason": None,
            "S": None,
            "H": None,
            "Phi": None,
            "cooldown_s": 0,
            "adr_active": False,
            "goal": goal or CAU_DEFAULT_GOAL,
            "source": "CAU_DISABLED",
        }

    try:
        import backend.modules.aion_cognition.cau_authority as cau  # type: ignore

        for name in (
            "get_authority",
            "get_authority_state",
            "get_state",
            "authority_state",
            "compute_authority",
            "compute",
            "read_authority",
        ):
            fn = getattr(cau, name, None)
            if callable(fn):
                out = _safe_call(fn, goal=goal or CAU_DEFAULT_GOAL)
                if isinstance(out, dict) and "allow_learn" in out:
                    out.setdefault("source", f"CAU:{name}")
                    return out
                if isinstance(out, dict) and ("allow" in out or "permit" in out):
                    out["allow_learn"] = bool(out.get("allow", out.get("permit")))
                    out.setdefault("source", f"CAU:{name}")
                    return out

        for name in ("LAST", "LAST_STATE", "STATE", "AUTHORITY"):
            maybe = getattr(cau, name, None)
            if isinstance(maybe, dict) and "allow_learn" in maybe:
                maybe = dict(maybe)
                maybe.setdefault("source", f"CAU:{name}")
                return maybe

        logger.warning("[CAU] cau_authority imported but no authority state function found; allowing learn (soft-fail).")
        return {
            "allow_learn": True,
            "deny_reason": None,
            "S": None,
            "H": None,
            "Phi": None,
            "cooldown_s": 0,
            "adr_active": False,
            "goal": goal or CAU_DEFAULT_GOAL,
            "source": "CAU_SOFT_FAIL_NO_FN",
        }

    except Exception as e:
        logger.warning(f"[CAU] Could not import cau_authority ({e}); allowing learn (soft-fail).")
        return {
            "allow_learn": True,
            "deny_reason": None,
            "S": None,
            "H": None,
            "Phi": None,
            "cooldown_s": 0,
            "adr_active": False,
            "goal": goal or CAU_DEFAULT_GOAL,
            "source": "CAU_SOFT_FAIL_IMPORT",
        }

def _cau_allow(goal: str | None = None) -> Tuple[bool, Dict[str, Any]]:
    st = _get_cau_state(goal=goal)
    allow = bool(st.get("allow_learn", True))
    return allow, st

# ================================================================
# 🧩 Safe I/O Utilities (atomic + validated + backup)
# ================================================================
def _safe_val(v: Any) -> Any:
    if isinstance(v, (int, float, str, bool)) or v is None:
        return v
    if isinstance(v, (list, tuple)):
        return [_safe_val(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _safe_val(val) for k, val in v.items()}
    return str(v)

def _atomic_write_json(path: Path, data: dict) -> None:
    """
    Safely write JSON with validation before replacing the original.
    NOTE: mkdir happens here (write-time), NOT at import-time.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    backup = path.with_suffix(".bak")
    if path.exists():
        try:
            backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        except Exception as e:
            logger.warning(f"[LexMemory] Backup write failed (non-fatal): {e}")

    tmp = tempfile.NamedTemporaryFile("w", delete=False, dir=path.parent, suffix=".tmp", encoding="utf-8")
    try:
        json.dump(_safe_val(data), tmp, ensure_ascii=False, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()

        json.loads(Path(tmp.name).read_text(encoding="utf-8"))  # validation
        os.replace(tmp.name, path)
        logger.info(f"[LexMemory] ✅ Atomic save verified -> {path}")
    except Exception as e:
        logger.error(f"[LexMemory] ❌ Atomic write failed: {e}")
        try:
            os.unlink(tmp.name)
        except Exception:
            pass
        raise

def _auto_recover_json(path: Path, fallback: dict) -> dict:
    """
    Auto-repair loader for JSON memory files.
      - Missing -> create new.
      - Corrupt -> move to .corrupt, restore from .bak if present, else clean.
    """
    if not path.exists():
        logger.warning(f"[Recovery] Missing {path.name}, creating new.")
        _atomic_write_json(path, fallback)
        return fallback

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"[Recovery] ⚠ Corruption in {path.name}: {e}")

        corrupt = path.with_suffix(".corrupt")
        backup = path.with_suffix(".bak")

        try:
            os.replace(path, corrupt)
            logger.warning(f"[Recovery] Renamed bad file -> {corrupt}")
        except Exception:
            pass

        if backup.exists():
            try:
                data = json.loads(backup.read_text(encoding="utf-8"))
                _atomic_write_json(path, data)
                logger.info(f"[Recovery] ✅ Restored from backup -> {backup}")
                return data
            except Exception as e2:
                logger.warning(f"[Recovery] Backup restore failed: {e2}")

        logger.warning("[Recovery] No usable backup; creating clean file.")
        _atomic_write_json(path, fallback)
        return fallback

# ================================================================
# 🧠 Normalization / Tokenization
# ================================================================
def _norm_text(s: str) -> str:
    s = (s or "").strip()
    return " ".join(s.split())

def _normalize_prompt(text: str) -> str:
    text = (text or "").lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def _tokenize(text: str) -> set:
    n = _normalize_prompt(text)
    return set(n.split()) if n else set()

# ================================================================
# 📦 Schema (v2)
# ================================================================
@dataclass
class LexEntry:
    prompt: str
    answer: str
    count: int = 0
    rho: float = 0.0
    Ibar: float = 0.0
    sqi: float = 0.0
    last_ts: float = 0.0
    meta: Dict[str, Any] = None

    def to_json(self) -> Dict[str, Any]:
        d = asdict(self)
        if d.get("meta") is None:
            d["meta"] = {}
        return d

# ================================================================
# 🧠 LexMemory Core
# ================================================================
class LexMemory:
    def __init__(self, path: Optional[Path] = None, alpha: float = 0.35, cau_goal: str = CAU_DEFAULT_GOAL):
        self.path = Path(path) if path is not None else _memory_path()
        self.alpha = float(alpha)
        self.cau_goal = str(cau_goal or CAU_DEFAULT_GOAL)
        self.entries: Dict[str, LexEntry] = {}
        self._load()

    # ----------------------------
    # CAU gate
    # ----------------------------
    def _allow_mutation(self, reason: str, meta: Optional[Dict[str, Any]] = None) -> Tuple[bool, Dict[str, Any]]:
        allow, st = _cau_allow(goal=self.cau_goal)
        if allow:
            return True, st

        deny_reason = st.get("deny_reason") or "cau_deny"
        logger.warning(
            f"[CAU] DENY LexMemory mutation ({reason}) | "
            f"deny_reason={deny_reason} S={st.get('S')} H={st.get('H')} Phi={st.get('Phi')} cooldown_s={st.get('cooldown_s')}"
        )

        if isinstance(meta, dict):
            meta.setdefault("cau", {})
            try:
                meta["cau"].update(
                    {
                        "allow_learn": False,
                        "deny_reason": deny_reason,
                        "S": st.get("S"),
                        "H": st.get("H"),
                        "Phi": st.get("Phi"),
                        "cooldown_s": st.get("cooldown_s", 0),
                        "adr_active": st.get("adr_active", False),
                        "source": st.get("source"),
                    }
                )
            except Exception:
                pass

        return False, st

    # ----------------------------
    # Load / Save
    # ----------------------------
    def _empty_payload(self) -> dict:
        return {"version": SCHEMA_VERSION, "saved_ts": time.time(), "alpha": self.alpha, "entries": []}

    def _load(self) -> None:
        raw = _auto_recover_json(self.path, self._empty_payload())

        # v2
        if isinstance(raw, dict) and raw.get("version") == SCHEMA_VERSION and isinstance(raw.get("entries"), list):
            self.alpha = float(raw.get("alpha", self.alpha))
            self.entries = {}
            for e in raw["entries"]:
                if not isinstance(e, dict):
                    continue
                le = LexEntry(
                    prompt=_norm_text(e.get("prompt", "")),
                    answer=_norm_text(e.get("answer", "")),
                    count=int(e.get("count", 0)),
                    rho=float(e.get("rho", 0.0)),
                    Ibar=float(e.get("Ibar", 0.0)),
                    sqi=float(e.get("sqi", 0.0)),
                    last_ts=float(e.get("last_ts", 0.0)),
                    meta=dict(e.get("meta") or {}),
                )
                if le.prompt:
                    self.entries[_normalize_prompt(le.prompt)] = le
            return

        # v1-ish {"version":1, "entries":[...]}
        if isinstance(raw, dict) and isinstance(raw.get("entries"), list):
            self.entries = {}
            for e in raw["entries"]:
                if not isinstance(e, dict):
                    continue
                le = LexEntry(
                    prompt=_norm_text(e.get("prompt", "")),
                    answer=_norm_text(e.get("answer", "")),
                    count=int(e.get("count", 0)),
                    rho=float(e.get("rho", e.get("ρ", 0.0) or 0.0)),
                    Ibar=float(e.get("Ibar", e.get("I", e.get("Ī", 0.0)) or 0.0)),
                    sqi=float(e.get("sqi", e.get("SQI", 0.0) or 0.0)),
                    last_ts=float(e.get("last_ts", e.get("last_update", 0.0) or 0.0)),
                    meta=dict(e.get("meta") or {}),
                )
                if le.prompt:
                    self.entries[_normalize_prompt(le.prompt)] = le
            self.save()
            return

        # legacy map
        if isinstance(raw, dict):
            self.entries = self._migrate_legacy_map(raw)
            self.save()
            logger.info(f"[LexMemory] Migrated legacy map -> v{SCHEMA_VERSION} ({len(self.entries)} prompts)")
            return

        self.entries = {}

    def save(self) -> None:
        payload = {
            "version": SCHEMA_VERSION,
            "saved_ts": time.time(),
            "alpha": self.alpha,
            "entries": [e.to_json() for e in self.entries.values()],
        }
        _atomic_write_json(self.path, payload)

    def _migrate_legacy_map(self, raw: Dict[str, Any]) -> Dict[str, LexEntry]:
        grouped: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
        for k, v in raw.items():
            if not isinstance(k, str) or "↔" not in k or not isinstance(v, dict):
                continue
            p, a = k.split("↔", 1)
            p = _norm_text(p)
            a = _norm_text(a)
            if not p:
                continue
            grouped.setdefault(_normalize_prompt(p), []).append((a, v))

        out: Dict[str, LexEntry] = {}
        for p_norm, variants in grouped.items():
            best = None
            for a, v in variants:
                sqi = float(v.get("SQI", v.get("sqi", 0.0)) or 0.0)
                cnt = int(v.get("count", 0) or 0)
                ts = float(v.get("last_update", v.get("last_ts", 0.0)) or 0.0)
                score = (sqi, cnt, ts)
                if best is None or score > best[0]:
                    best = (score, a, v)

            if best is None:
                continue

            _, a_best, v_best = best
            le = LexEntry(
                prompt=p_norm,
                answer=a_best,
                count=int(v_best.get("count", 0) or 0),
                rho=float(v_best.get("ρ", v_best.get("rho", 0.0)) or 0.0),
                Ibar=float(v_best.get("I", v_best.get("Ibar", v_best.get("Ī", 0.0))) or 0.0),
                sqi=float(v_best.get("SQI", v_best.get("sqi", 0.0)) or 0.0),
                last_ts=float(v_best.get("last_update", v_best.get("last_ts", 0.0)) or 0.0),
                meta={"migrated_from": "legacy_prompt_arrow_answer"},
            )
            out[p_norm] = le

        return out

    # ----------------------------
    # Update / Reinforcement (CAU-gated)
    # ----------------------------
    def update(
        self,
        prompt: str,
        answer: str,
        rho: float,
        Ibar: float,
        sqi: float,
        meta: Optional[Dict[str, Any]] = None,
        require_cau: bool = True,
    ) -> Optional[LexEntry]:
        if meta is None:
            meta = {}

        if require_cau:
            ok, cau = self._allow_mutation(reason="update", meta=meta)
            if not ok:
                return None
            meta.setdefault("cau", {})
            meta["cau"].update(
                {
                    "allow_learn": True,
                    "S": cau.get("S"),
                    "H": cau.get("H"),
                    "Phi": cau.get("Phi"),
                    "cooldown_s": cau.get("cooldown_s", 0),
                    "adr_active": cau.get("adr_active", False),
                    "source": cau.get("source"),
                }
            )

        now = time.time()
        p_raw = _norm_text(prompt)
        a_raw = _norm_text(answer)
        p_norm = _normalize_prompt(p_raw)
        if not p_norm:
            raise ValueError("prompt is empty after normalization")

        e = self.entries.get(p_norm)
        if e is None:
            e = LexEntry(prompt=p_norm, answer=a_raw, count=0, rho=0.0, Ibar=0.0, sqi=0.0, last_ts=0.0, meta={})
            self.entries[p_norm] = e

        e.count += 1
        e.last_ts = now
        e.answer = a_raw

        a = self.alpha
        e.rho = round((1 - a) * float(e.rho) + a * float(rho), 3)
        e.Ibar = round((1 - a) * float(e.Ibar) + a * float(Ibar), 3)
        e.sqi = round((1 - a) * float(e.sqi) + a * float(sqi), 3)

        if e.meta is None:
            e.meta = {}
        if meta:
            e.meta.update(_safe_val(meta))

        return e

    # ----------------------------
    # Recall
    # ----------------------------
    def recall_exact(self, prompt: str) -> Optional[LexEntry]:
        return self.entries.get(_normalize_prompt(prompt))

    def recall_fuzzy(self, prompt: str, threshold: float = 0.25) -> Optional[Tuple[LexEntry, float]]:
        if not prompt:
            return None
        p_norm = _normalize_prompt(prompt)
        p_tokens = _tokenize(prompt)

        best_e: Optional[LexEntry] = None
        best_score = 0.0

        for e in self.entries.values():
            base_norm = e.prompt
            base_tokens = _tokenize(base_norm)

            ratio = SequenceMatcher(None, base_norm, p_norm).ratio()
            overlap = len(p_tokens & base_tokens) / max(len(p_tokens), 1)

            sqi_w = float(e.sqi) if e.sqi is not None else 1.0
            coherence = (0.6 * ratio + 0.4 * overlap) * (sqi_w if sqi_w > 0 else 1.0)

            if coherence > best_score:
                best_score = coherence
                best_e = e

        if best_e and best_score >= threshold:
            return best_e, float(best_score)
        return None

    # ----------------------------
    # Decay / Maintenance (CAU-gated)
    # ----------------------------
    def decay(self, half_life_hours: float = 48.0, require_cau: bool = True) -> bool:
        if require_cau:
            ok, _ = self._allow_mutation(reason="decay", meta=None)
            if not ok:
                return False

        now = time.time()
        decay_rate = math.log(2) / (half_life_hours * 3600.0)
        for e in self.entries.values():
            age = max(0.0, now - float(e.last_ts or now))
            factor = math.exp(-decay_rate * age)
            e.rho = round(float(e.rho) * factor, 3)
            e.Ibar = round(float(e.Ibar) * factor, 3)
            e.sqi = round(float(e.sqi) * factor, 3)

        self.save()
        return True

    def reinforce_field(
        self,
        prompt: str,
        rho: float,
        Ibar: float,
        sqi: float,
        overlap_threshold: float = 0.4,
        require_cau: bool = True,
    ) -> int:
        if require_cau:
            ok, _ = self._allow_mutation(reason="reinforce_field", meta=None)
            if not ok:
                return 0

        p_tokens = _tokenize(prompt)
        if not p_tokens:
            return 0

        reinforced = 0
        for e in self.entries.values():
            base_tokens = _tokenize(e.prompt)
            overlap = len(p_tokens & base_tokens) / max(len(p_tokens), 1)
            if overlap >= overlap_threshold:
                e.rho = round(float(e.rho) + float(rho) * 0.05, 3)
                e.Ibar = round(float(e.Ibar) + float(Ibar) * 0.05, 3)
                e.sqi = round(float(e.sqi) + float(sqi) * 0.05, 3)
                e.last_ts = time.time()
                reinforced += 1

        if reinforced:
            self.save()
        return reinforced

# ================================================================
# ✅ Lazy singleton for function API (NO import-time IO)
# ================================================================
_LEX_SINGLETON: Optional[LexMemory] = None

def get_lex() -> LexMemory:
    global _LEX_SINGLETON
    if _LEX_SINGLETON is None:
        _LEX_SINGLETON = LexMemory(path=_memory_path(), alpha=0.35, cau_goal=CAU_DEFAULT_GOAL)
    return _LEX_SINGLETON

# ================================================================
# ✅ Backwards-compatible function API (existing calls)
# ================================================================
def update_lex_memory(prompt: str, answer: str, resonance: Dict[str, float]) -> None:
    rho = float(resonance.get("ρ", resonance.get("rho", 0.0)) or 0.0)
    Ibar = float(resonance.get("I", resonance.get("Ī", resonance.get("Ibar", 0.0))) or 0.0)
    sqi = float(resonance.get("SQI", resonance.get("sqi", 0.0)) or 0.0)

    e = get_lex().update(
        prompt=prompt,
        answer=answer,
        rho=rho,
        Ibar=Ibar,
        sqi=sqi,
        meta={"api": "update_lex_memory"},
        require_cau=True,
    )
    if e is None:
        logger.info("[LexMemory] CAU denied update_lex_memory -> no write")
        return

    get_lex().save()
    logger.info(f"[LexMemory] Reinforced '{e.prompt}' -> SQI={e.sqi}, count={e.count}")

def store_concept_definition(term: str, definition: str, resonance: Dict[str, float]) -> None:
    rho = float(resonance.get("ρ", resonance.get("rho", 0.75)) or 0.75)
    Ibar = float(resonance.get("I", resonance.get("Ī", resonance.get("Ibar", 0.8))) or 0.8)
    sqi = float(resonance.get("SQI", resonance.get("sqi", 0.85)) or 0.85)

    e = get_lex().update(
        prompt=term,
        answer=definition,
        rho=rho,
        Ibar=Ibar,
        sqi=sqi,
        meta={"concept": True, "api": "store_concept_definition"},
        require_cau=True,
    )
    if e is None:
        logger.info("[LexMemory] CAU denied store_concept_definition -> no write")
        return

    get_lex().save()
    logger.info(f"[LexMemory] 📘 Stored concept '{term}' -> '{definition}' (SQI={e.sqi})")

def recall_from_memory(prompt: str) -> Dict[str, Any]:
    if not prompt:
        return {}

    e = get_lex().recall_exact(prompt)
    if e:
        return {
            "prompt": prompt,
            "answer": e.answer,
            "resonance": {"ρ": e.rho, "I": e.Ibar, "SQI": e.sqi, "count": e.count, "last_update": e.last_ts},
            "confidence": 1.0,
        }

    hit = get_lex().recall_fuzzy(prompt, threshold=0.0)
    if not hit:
        return {}

    e2, score = hit

    min_conf = float(os.getenv("CEE_LEX_MIN_CONF", "0.72"))
    min_overlap = float(os.getenv("CEE_LEX_MIN_OVERLAP", "0.20"))

    try:
        p_tokens = _tokenize(prompt)
        e_tokens = _tokenize(e2.prompt)
        overlap = len(p_tokens & e_tokens) / max(len(p_tokens), 1)
    except Exception:
        overlap = 0.0

    if float(score) < min_conf or float(overlap) < min_overlap:
        return {}

    logger.info(f"[LexMemory] 🔍 Recall OK ({score:.2f}, overlap={overlap:.2f}) -> {e2.answer}")
    return {
        "prompt": prompt,
        "answer": e2.answer,
        "resonance": {"ρ": e2.rho, "I": e2.Ibar, "SQI": e2.sqi, "count": e2.count, "last_update": e2.last_ts},
        "confidence": round(float(score), 2),
    }

def decay_memory(half_life_hours: float = 48.0) -> None:
    ok = get_lex().decay(half_life_hours=half_life_hours, require_cau=True)
    if ok:
        logger.info(f"[LexMemory] Applied decay (half-life={half_life_hours}h)")
    else:
        logger.info("[LexMemory] CAU denied decay -> no write")

def reinforce_field(prompt: str, answer: str, resonance: Dict[str, float]) -> None:
    rho = float(resonance.get("ρ", resonance.get("rho", 0.0)) or 0.0)
    Ibar = float(resonance.get("I", resonance.get("Ī", resonance.get("Ibar", 0.0))) or 0.0)
    sqi = float(resonance.get("SQI", resonance.get("sqi", 0.0)) or 0.0)

    n = get_lex().reinforce_field(
        prompt=prompt,
        rho=rho,
        Ibar=Ibar,
        sqi=sqi,
        overlap_threshold=0.4,
        require_cau=True,
    )
    if n:
        logger.info(f"[LexMemory] 🔄 Field resonance reinforced for {n} entries")
    else:
        logger.info("[LexMemory] 🔄 Field resonance: none reinforced (or CAU denied)")

# ================================================================
# Back-compat helpers for older analytics modules
# ================================================================
def _load_memory(path: Optional[Path] = None) -> dict:
    """
    Older modules import this symbol.
    Return the raw JSON payload (auto-recovered).
    """
    p = Path(path) if path is not None else _memory_path()
    tmp = {"version": SCHEMA_VERSION, "saved_ts": time.time(), "alpha": 0.35, "entries": []}
    return _auto_recover_json(p, tmp)

# ================================================================
# 🧪 Self-Test
# ================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    update_lex_memory("The sun rises in the", "east", {"ρ": 0.82, "I": 0.9, "SQI": 0.86})
    update_lex_memory("Happy", "joyful", {"ρ": 0.88, "I": 0.92, "SQI": 0.9})

    res = recall_from_memory("The sun rises in")
    print(json.dumps(res, indent=2, ensure_ascii=False))

    decay_memory(half_life_hours=48.0)