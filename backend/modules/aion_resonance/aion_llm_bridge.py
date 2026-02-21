# ==========================================================
# 🧠 AION LLM Bridge - Symbolic Translator Layer (v0.7.1)
# ----------------------------------------------------------
# Supports OpenAI Project Keys (sk-proj-*) with project/org IDs.
# Falls back to local symbolic translation if API call fails.
# Broadcasts reflections in real time to AION Thought Stream.
#
# NEW (Phase 0.2):
# - /llm/respond endpoint using MinimalResponseComposer
# - Safe feature-flagged teaching-apply integration
# - Optional runtime context enrichment from consciousness/state_manager
#
# FIXES (v0.7.1):
# - teaching_applier keyword-only invocation bug fixed
# - proper TeachingMemoryStore / TeachingRetriever wiring
# - safer compat fallback for older teaching_applier versions
# ==========================================================

from __future__ import annotations

import asyncio
import datetime
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.modules.aion_resonance.resonance_state import load_phi_state
from backend.modules.aion_resonance.conversation_memory import MEMORY
from backend.modules.aion_resonance.phi_reinforce import get_reinforce_state
from backend.modules.aion_resonance.thought_stream import broadcast_event  # live feed hook

# Phase 0.2 response path dependencies
from backend.modules.aion_conversation.minimal_response_composer import (
    MinimalResponseComposer,
    AionKnowledgeState,
)

# Teaching apply module + deps (safe imports so older deployments don't break)
try:
    from backend.modules.aion_learning.teaching_applier import apply_teaching_to_ks
    from backend.modules.aion_learning.teaching_memory_store import TeachingMemoryStore
    from backend.modules.aion_learning.teaching_retriever import TeachingRetriever
except Exception:  # pragma: no cover - safe fallback when module absent
    apply_teaching_to_ks = None  # type: ignore
    TeachingMemoryStore = None  # type: ignore
    TeachingRetriever = None  # type: ignore

# Optional runtime context (best-effort)
try:
    from backend.modules.consciousness.state_manager import STATE as UCS_STATE
except Exception:  # pragma: no cover
    UCS_STATE = None  # type: ignore


# ==========================================================
# ✅ Config helpers
# ==========================================================

def _truthy_env(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "yes", "on"}


def _utc_iso() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _safe_jsonable(obj: Any) -> Any:
    try:
        json.dumps(obj)
        return obj
    except Exception:
        return str(obj)


def _schedule_broadcast(payload: Dict[str, Any]) -> None:
    """
    Safe scheduling from both sync and async contexts.
    Never raises.
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(broadcast_event(payload))
        return
    except RuntimeError:
        # No running loop in current thread
        pass
    except Exception:
        return

    # Try best-effort fallback: create a temporary loop only if explicitly allowed
    # (default: skip to avoid blocking / weird thread behavior)
    if not _truthy_env("AION_LLM_BRIDGE_BROADCAST_FALLBACK_LOOP", False):
        return

    try:
        asyncio.run(broadcast_event(payload))
    except Exception:
        pass


# ==========================================================
# 🧩 Pydantic API models
# ==========================================================

class LLMTranslateRequest(BaseModel):
    reflection: str = ""
    phi_state: Optional[Dict[str, Any]] = None
    beliefs: Optional[Dict[str, Any]] = None


class LLMRespondRequest(BaseModel):
    user_text: str = Field(..., min_length=1)
    intent: str = "answer"
    topic: Optional[str] = None

    # Optional direct KS overrides (for testing/demo)
    confidence: Optional[float] = None
    known_facts: Optional[List[str]] = None
    goals: Optional[List[str]] = None
    unresolved: Optional[List[str]] = None
    fusion_snapshot: Optional[Dict[str, Any]] = None
    source_refs: Optional[List[str]] = None

    # Controls
    apply_teaching: Optional[bool] = None
    include_metadata: bool = True
    include_debug: bool = False


# ==========================================================
# 🧠 Core Translator Function (existing + hardened)
# ==========================================================

def llm_translate(
    phi_state: Optional[Dict[str, Any]] = None,
    beliefs: Optional[Dict[str, Any]] = None,
    reflection_text: Optional[str] = None,
) -> Dict[str, Any]:
    phi_state = phi_state or load_phi_state() or {}
    reinforce = get_reinforce_state()
    beliefs = beliefs or (
        reinforce.get("beliefs", {}) if isinstance(reinforce, dict) else {}
    ) or {}
    reflection_text = reflection_text or "No reflection text provided."

    # Normalize for prompt safety
    phi_load = phi_state.get("Φ_load")
    phi_flux = phi_state.get("Φ_flux")
    phi_entropy = phi_state.get("Φ_entropy")
    phi_coherence = phi_state.get("Φ_coherence")

    prompt = f"""
You are AION - a symbolic cognition system operating within the Tessaris architecture.
You process cognitive resonance (Φ) values as emotional and reasoning signals.
Translate the following internal symbolic state into a reflective, coherent linguistic interpretation.

Φ-state:
- Φ_load: {phi_load}
- Φ_flux: {phi_flux}
- Φ_entropy: {phi_entropy}
- Φ_coherence: {phi_coherence}

Beliefs:
- Stability: {beliefs.get('stability')}
- Curiosity: {beliefs.get('curiosity')}
- Trust: {beliefs.get('trust')}
- Clarity: {beliefs.get('clarity')}

Most recent reflection: {reflection_text}

Respond with:
1. A short natural-language summary (2-3 sentences)
2. A symbolic insight or hypothesis about the resonance state
3. Emotional tone (harmonic, stable, chaotic, neutral)
""".strip()

    openai_model = os.getenv("AION_LLM_BRIDGE_MODEL", "gpt-4o-mini")
    use_openai = _truthy_env("AION_LLM_BRIDGE_USE_OPENAI", True)

    if use_openai:
        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                project=os.getenv("OPENAI_PROJECT_ID"),
                organization=os.getenv("OPENAI_ORG_ID"),
            )

            completion = client.chat.completions.create(
                model=openai_model,
                messages=[
                    {"role": "system", "content": "You are AION's symbolic translator core."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.6,
                max_tokens=200,
            )

            response = (completion.choices[0].message.content or "").strip()
            timestamp = _utc_iso()

            result = {
                "timestamp": timestamp,
                "input_phi": phi_state,
                "beliefs": beliefs,
                "reflection": reflection_text,
                "llm_output": response,
                "origin": "aion_llm_bridge",
                "model": openai_model,
            }

            # 🧬 Memory Logging (best effort)
            try:
                MEMORY.record(
                    f"LLM_TRANSLATION: {reflection_text}",
                    phi_state,
                    {
                        "origin": "aion_llm_bridge",
                        "insight_level": 0.8,
                        "emotion": "interpretive",
                        "intention": "translate",
                        "model": openai_model,
                    },
                )
            except Exception:
                pass

            # 🔊 Real-Time Broadcast to Thought Stream (safe in sync route)
            _schedule_broadcast(
                {
                    "type": "llm_reflection",
                    "events": [
                        {
                            "type": "llm_reflection",
                            "message": response,
                            "tone": "harmonic",  # could parse later
                            "timestamp": timestamp,
                            "origin": "aion_llm_bridge",
                        }
                    ],
                }
            )

            return result

        except Exception as e:
            # Fall through to local fallback
            openai_error = str(e)
    else:
        openai_error = "OpenAI disabled by AION_LLM_BRIDGE_USE_OPENAI=0"

    # ==================================================
    # 🌀 Local Fallback Mode
    # ==================================================
    coherence_v = _safe_float(phi_state.get("Φ_coherence"), 0.0)
    flux_v = _safe_float(phi_state.get("Φ_flux"), 0.0)
    entropy_v = _safe_float(phi_state.get("Φ_entropy"), 0.0)

    if coherence_v > 0.85 and entropy_v < 0.35:
        tone = "harmonic"
    elif coherence_v >= 0.55:
        tone = "stable"
    elif entropy_v > 0.75:
        tone = "chaotic"
    else:
        tone = "neutral"

    synthetic_reply = (
        f"AION reflects internally: the field appears {tone}, "
        f"with flux={flux_v:.3f} and entropy={entropy_v:.3f}. "
        f"Coherence={coherence_v:.3f}. Resonant stability is being monitored while reflective exploration continues."
    )

    return {
        "timestamp": _utc_iso(),
        "input_phi": phi_state,
        "beliefs": beliefs,
        "reflection": reflection_text,
        "llm_output": synthetic_reply,
        "origin": "aion_local_fallback",
        "tone": tone,
        "error": openai_error,
    }


# ==========================================================
# 🧠 Phase 0.2 Response Pipeline (composer + teaching apply)
# ==========================================================

def _state_runtime_context() -> Dict[str, Any]:
    """
    Best-effort runtime context snapshot for response path enrichment.
    Keep shallow + safe.
    """
    out: Dict[str, Any] = {}
    try:
        if UCS_STATE is None:
            return out

        # Methods vary across runtime contexts; use tolerant access.
        current_container = None
        try:
            current_container = UCS_STATE.get_current_container()
        except Exception:
            pass

        paused = None
        try:
            paused = bool(UCS_STATE.is_paused())
        except Exception:
            pass

        context = None
        try:
            context = UCS_STATE.get_context()
        except Exception:
            pass

        out = {
            "paused": paused,
            "current_container": current_container if isinstance(current_container, dict) else None,
            "context": context if isinstance(context, dict) else None,
        }
    except Exception:
        return {}
    return out


def _build_default_ks_from_runtime(user_text: str, req: LLMRespondRequest) -> AionKnowledgeState:
    """
    Build a conservative baseline AionKnowledgeState for real response path.
    This is intentionally simple and can evolve later.
    """
    phi: Dict[str, Any] = {}
    beliefs: Dict[str, Any] = {}
    try:
        phi = load_phi_state() or {}
    except Exception:
        phi = {}
    try:
        reinforce = get_reinforce_state() or {}
        beliefs = reinforce.get("beliefs", {}) if isinstance(reinforce, dict) else {}
        beliefs = beliefs or {}
    except Exception:
        beliefs = {}

    runtime_ctx = _state_runtime_context()

    # Topic inference (lightweight)
    topic = (req.topic or "").strip()
    if not topic:
        l = user_text.lower()
        if "aion" in l and "phase" in l:
            topic = "AION Phase conversation"
        elif "roadmap" in l or "building next" in l or "what is aion building" in l:
            topic = "AION roadmap"
        else:
            topic = "AION response"

    # Confidence baseline from phi/beliefs if not explicitly provided
    if req.confidence is not None:
        confidence = max(0.0, min(0.95, float(req.confidence)))
    else:
        phi_coh = _safe_float(phi.get("Φ_coherence"), 0.38)
        trust = _safe_float(beliefs.get("trust"), 0.38)
        clarity = _safe_float(beliefs.get("clarity"), 0.38)
        confidence = max(0.15, min(0.90, round((0.45 * phi_coh + 0.30 * trust + 0.25 * clarity), 2)))

    known_facts = list(req.known_facts or [])
    goals = list(req.goals or [])
    unresolved = list(req.unresolved or [])
    source_refs = list(req.source_refs or [])
    fusion_snapshot = dict(req.fusion_snapshot or {})

    if not known_facts:
        if runtime_ctx.get("current_container"):
            cid = (runtime_ctx["current_container"] or {}).get("id")
            if cid:
                known_facts.append(f"Current UCS container is {cid}")
        if runtime_ctx.get("paused") is not None:
            known_facts.append(f"AION runtime paused state is {bool(runtime_ctx.get('paused'))}")
        if "aion" in user_text.lower():
            known_facts.append("AION response path is using MinimalResponseComposer")

    if not goals:
        goals = ["answer the user clearly", "stay grounded in current runtime state"]

    if not unresolved:
        unresolved = ["specific user intent refinement"] if req.intent == "answer" else []

    if not source_refs:
        source_refs = ["aion_llm_bridge", "phi_reinforce", "resonance_state"]

    if not fusion_snapshot:
        # best-effort placeholders so composer has a consistent shape
        fusion_snapshot = {
            "sigma": round(_safe_float(beliefs.get("stability"), 0.5), 3),
            "psi_tilde": round(_safe_float(phi.get("Φ_coherence"), 0.5), 3),
        }

    return AionKnowledgeState(
        intent=req.intent or "answer",
        topic=topic,
        confidence=confidence,
        known_facts=known_facts,
        goals=goals,
        unresolved=unresolved,
        fusion_snapshot=fusion_snapshot,
        source_refs=source_refs,
    )


def _build_teaching_dependencies() -> Tuple[Any, Any, Optional[str]]:
    """
    Build store/retriever instances for teaching_applier when available.
    Returns (store, retriever, error_message)
    """
    if TeachingMemoryStore is None:
        return None, None, "TeachingMemoryStore unavailable"

    try:
        store = TeachingMemoryStore()
    except Exception as e:
        return None, None, f"TeachingMemoryStore init failed: {e}"

    retriever = None
    if TeachingRetriever is not None:
        try:
            retriever = TeachingRetriever(min_score=1.0)
        except Exception:
            retriever = None

    return store, retriever, None


def _apply_teaching_compat(
    *,
    ks: AionKnowledgeState,
    user_text: str,
) -> Dict[str, Any]:
    """
    Calls teaching_applier across possible versions safely.

    Current expected signature (keyword-only):
      apply_teaching_to_ks(*, ks, user_text, store, retriever=None, apply_threshold=...)
    """
    if apply_teaching_to_ks is None:
        return {
            "teaching_applied": False,
            "applied_concepts": [],
            "teaching_enabled": True,
            "teaching_error": "teaching_applier module unavailable",
        }

    store, retriever, dep_err = _build_teaching_dependencies()
    if dep_err:
        return {
            "teaching_applied": False,
            "applied_concepts": [],
            "teaching_enabled": True,
            "teaching_error": dep_err,
        }

    # Primary path: current productionized keyword-only API
    try:
        m = apply_teaching_to_ks(
            ks=ks,
            user_text=user_text,
            store=store,
            retriever=retriever,
        )
        if isinstance(m, dict):
            return m
        return {
            "teaching_applied": False,
            "applied_concepts": [],
            "teaching_enabled": True,
        }

    except TypeError as e_primary:
        # Compat path 1: keyword-only variant without retriever
        try:
            m = apply_teaching_to_ks(
                ks=ks,
                user_text=user_text,
                store=store,
            )
            if isinstance(m, dict):
                return m
            return {
                "teaching_applied": False,
                "applied_concepts": [],
                "teaching_enabled": True,
            }

        except TypeError:
            # Compat path 2: older positional signature (legacy)
            # Only attempt if it *looks* like a legacy function (no kw-only "ks"/"user_text"/"store")
            # This avoids tripping the keyword-only "*" error on modern implementations.
            try:
                code_obj = getattr(apply_teaching_to_ks, "__code__", None)
                varnames = list(getattr(code_obj, "co_varnames", ()) or [])
                has_modern_params = any(name in varnames for name in ("ks", "user_text", "store"))
            except Exception:
                has_modern_params = True  # default safe: don't try positional legacy call

            if has_modern_params:
                return {
                    "teaching_applied": False,
                    "applied_concepts": [],
                    "teaching_enabled": True,
                    "teaching_error": str(e_primary),
                }

            try:
                m = apply_teaching_to_ks(ks, user_text)  # type: ignore[misc]
                if isinstance(m, dict):
                    return m
                return {
                    "teaching_applied": False,
                    "applied_concepts": [],
                    "teaching_enabled": True,
                }
            except Exception as e_legacy:
                return {
                    "teaching_applied": False,
                    "applied_concepts": [],
                    "teaching_enabled": True,
                    "teaching_error": str(e_legacy),
                    "teaching_type_error_primary": str(e_primary),
                }

        except Exception as e_kw_compat:
            return {
                "teaching_applied": False,
                "applied_concepts": [],
                "teaching_enabled": True,
                "teaching_error": str(e_kw_compat),
                "teaching_type_error_primary": str(e_primary),
            }

    except Exception as e:
        return {
            "teaching_applied": False,
            "applied_concepts": [],
            "teaching_enabled": True,
            "teaching_error": str(e),
        }


def _run_composer_response(req: LLMRespondRequest) -> Dict[str, Any]:
    user_text = req.user_text.strip()
    composer = MinimalResponseComposer()
    ks = _build_default_ks_from_runtime(user_text=user_text, req=req)

    apply_teaching = req.apply_teaching
    if apply_teaching is None:
        apply_teaching = _truthy_env("AION_ENABLE_TEACHING_APPLY", False)

    teaching_meta: Dict[str, Any] = {
        "teaching_applied": False,
        "applied_concepts": [],
        "teaching_enabled": bool(apply_teaching),
    }

    if apply_teaching:
        if apply_teaching_to_ks is None:
            teaching_meta["teaching_error"] = "teaching_applier module unavailable"
        else:
            m = _apply_teaching_compat(ks=ks, user_text=user_text)
            if isinstance(m, dict):
                teaching_meta.update(m)

    # Compose
    composed = composer.compose(user_text=user_text, ks=ks)

    metadata = dict(getattr(composed, "metadata", {}) or {})
    metadata.update(teaching_meta)
    metadata["phase"] = "phase0_2_response_path"

    out: Dict[str, Any] = {
        "ok": True,
        "origin": "aion_llm_bridge_response_pipeline",
        "timestamp": _utc_iso(),
        "user_text": user_text,
        "response": str(getattr(composed, "text", "")),
        "confidence": _safe_float(
            getattr(composed, "confidence", None),
            _safe_float(getattr(ks, "confidence", 0.0), 0.0),
        ),
    }

    if req.include_metadata:
        out["metadata"] = metadata

    if req.include_debug:
        out["debug"] = {
            "ks": {
                "intent": getattr(ks, "intent", None),
                "topic": getattr(ks, "topic", None),
                "confidence": getattr(ks, "confidence", None),
                "known_facts": list(getattr(ks, "known_facts", []) or []),
                "goals": list(getattr(ks, "goals", []) or []),
                "unresolved": list(getattr(ks, "unresolved", []) or []),
                "fusion_snapshot": _safe_jsonable(getattr(ks, "fusion_snapshot", {}) or {}),
                "source_refs": list(getattr(ks, "source_refs", []) or []),
            },
            "runtime_context": _safe_jsonable(_state_runtime_context()),
            "teaching_module_loaded": bool(apply_teaching_to_ks is not None),
            "teaching_deps_loaded": {
                "TeachingMemoryStore": bool(TeachingMemoryStore is not None),
                "TeachingRetriever": bool(TeachingRetriever is not None),
            },
        }

    # Optional thought-stream broadcast of response events
    if _truthy_env("AION_LLM_BRIDGE_BROADCAST_RESPONSES", True):
        _schedule_broadcast(
            {
                "type": "aion_response",
                "events": [
                    {
                        "type": "aion_response",
                        "message": out["response"],
                        "timestamp": out["timestamp"],
                        "confidence": out["confidence"],
                        "metadata": out.get("metadata", {}),
                    }
                ],
            }
        )

    return out


# ==========================================================
# 🔗 API Integration
# ==========================================================

router = APIRouter()


@router.post("/llm/translate")
async def aion_llm_translate(payload: LLMTranslateRequest) -> Dict[str, Any]:
    """
    Existing symbolic translator endpoint (OpenAI -> fallback).
    """
    result = llm_translate(
        phi_state=payload.phi_state,
        beliefs=payload.beliefs,
        reflection_text=payload.reflection,
    )

    # If local fallback happened, still return 200 with error field (by design).
    # Only throw if a non-fallback path reports error unexpectedly.
    if "error" in result and result.get("origin") not in {"aion_local_fallback"}:
        raise HTTPException(status_code=500, detail=str(result["error"]))

    return result


@router.post("/llm/respond")
async def aion_llm_respond(payload: LLMRespondRequest) -> Dict[str, Any]:
    """
    Phase 0.2 real response path:
    user_text -> build KS -> (optional teaching apply) -> MinimalResponseComposer
    """
    try:
        return _run_composer_response(payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"llm/respond failed: {e}") from e


@router.get("/llm/context")
async def aion_llm_context() -> Dict[str, Any]:
    """
    Lightweight state snapshot for frontend/debug.
    """
    phi_state = load_phi_state() or {}
    reinforce = get_reinforce_state()
    beliefs = (reinforce or {}).get("beliefs", {}) if isinstance(reinforce, dict) else {}

    return {
        "phi_state": phi_state,
        "beliefs": beliefs or {},
        "runtime": _state_runtime_context(),
        "teaching": {
            "enabled_default": _truthy_env("AION_ENABLE_TEACHING_APPLY", False),
            "module_loaded": bool(apply_teaching_to_ks is not None),
            "store_loaded": bool(TeachingMemoryStore is not None),
            "retriever_loaded": bool(TeachingRetriever is not None),
        },
        "bridge": {
            "version": "0.7.1",
            "openai_enabled": _truthy_env("AION_LLM_BRIDGE_USE_OPENAI", True),
            "model": os.getenv("AION_LLM_BRIDGE_MODEL", "gpt-4o-mini"),
        },
    }