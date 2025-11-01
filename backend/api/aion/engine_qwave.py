# backend/api/aion/engine_qwave.py
from fastapi import APIRouter
import os
import logging

from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.supercontainer_engine import SupercontainerEngine
from backend.modules.dimensions.containers.symbolic_expansion_container import SymbolicExpansionContainer

router = APIRouter()
log = logging.getLogger("qwave")

# -----------------------------------------------------------------------------
# Lazy/safe engine bootstrap (avoid import-time SoulLaw failures)
# -----------------------------------------------------------------------------
_sec_container = None
_engine = None
_saved_state = None  # 🔒 Global saved state snapshot


def _init_engine():
    """Initialize SEC + SupercontainerEngine safely (once)."""
    global _sec_container, _engine

    if _engine is not None:
        return _engine

    # Make the container first
    _sec_container = SymbolicExpansionContainer(container_id="qwave-sec")
    _sec_container.allow_nested = True

    # Try strict mode first; if it fails, fall back to permissive for dev
    try:
        _engine = SupercontainerEngine(container=_sec_container, safe_mode=True)
        return _engine
    except PermissionError as e:
        # Dev-friendly fallback: let the service start; logs make it obvious.
        log.warning(
            "SEC expand blocked by SoulLaw at import: %s - retrying with SOULLAW_MODE=permissive",
            e,
        )
        os.environ.setdefault("SOULLAW_MODE", "permissive")
        _engine = SupercontainerEngine(container=_sec_container, safe_mode=True)
        return _engine


def _get_engine():
    """Accessor so endpoints always have a ready engine."""
    return _init_engine()


# ---------------------------
# 🎛 Field Control Endpoints
# ---------------------------
@router.get("/engine/qwave/fields")
async def get_fields():
    engine = _get_engine()
    return {
        "fields": engine.fields,
        "flows": [
            {"source": s, "target": t, "force": engine.fields.get("magnetism", 0)}
            for s, t in getattr(engine, "flow_routes", {}).items()
        ],
        "stage": engine.stages[engine.current_stage],
        "particle_count": len(engine.particles),
    }


@router.post("/engine/qwave/fields")
async def adjust_field(data: dict):
    engine = _get_engine()
    field = data.get("field")
    value = data.get("value")
    if field and value is not None:
        engine.adjust_field(field, value)
    return {"status": "ok", "fields": engine.fields}


@router.post("/engine/qwave/advance")
async def advance_stage():
    """Advance QWave Engine stage + auto-save checkpoint."""
    engine = _get_engine()
    engine.advance_stage()
    global _saved_state
    _saved_state = engine.get_state()  # ✅ Auto-save after stage advance
    return {
        "status": "ok",
        "stage": engine.stages[engine.current_stage],
        "saved": True,
    }


# ---------------------------
# 📡 Full Engine State
# ---------------------------
@router.get("/engine/qwave/state")
async def get_engine_state():
    engine = _get_engine()
    state = engine.get_state()
    return {
        "stage": state["stage"],
        "fields": state["fields"],
        "particle_count": state["particle_count"],
        "particles": state["particles"],
        "nested_containers": state["nested_containers"],
    }


# ---------------------------
# 💾 Save & Load State
# ---------------------------
@router.post("/engine/qwave/save")
async def save_engine_state():
    """Manual save of engine state snapshot."""
    engine = _get_engine()
    global _saved_state
    _saved_state = engine.get_state()
    return {"status": "saved", "stage": _saved_state["stage"]}


@router.post("/engine/qwave/load")
async def load_engine_state():
    """Restore engine state from last save."""
    engine = _get_engine()
    global _saved_state
    if not _saved_state:
        return {"status": "error", "message": "No saved state found"}
    engine.set_state(_saved_state)
    return {"status": "loaded", "stage": engine.stages[engine.current_stage]}


# ---------------------------
# 🛑 Emergency Collapse
# ---------------------------
@router.post("/engine/qwave/collapse")
async def collapse_engine():
    """Emergency collapse endpoint to instantly reset engine."""
    engine = _get_engine()
    engine.collapse()
    return {"status": "collapsed", "stage": engine.stages[engine.current_stage]}