# backend/api/aion/engine_qwave.py
from fastapi import APIRouter
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.supercontainer_engine import SupercontainerEngine
from backend.modules.dimensions.containers.symbolic_expansion_container import SymbolicExpansionContainer

router = APIRouter()

# ✅ Initialize SEC + Engine in Safe Mode by default
sec_container = SymbolicExpansionContainer(container_id="qwave-sec")
sec_container.allow_nested = True
engine = SupercontainerEngine(container=sec_container, safe_mode=True)
saved_state = None  # 🔒 Global saved state variable

# ---------------------------
# 🎛 Field Control Endpoints
# ---------------------------
@router.get("/engine/qwave/fields")
async def get_fields():
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
    field = data.get("field")
    value = data.get("value")
    if field and value is not None:
        engine.adjust_field(field, value)
    return {"status": "ok", "fields": engine.fields}

@router.post("/engine/qwave/advance")
async def advance_stage():
    """Advance QWave Engine stage + auto-save checkpoint."""
    engine.advance_stage()
    global saved_state
    saved_state = engine.get_state()  # ✅ Auto-save after stage advance
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
    global saved_state
    saved_state = engine.get_state()
    return {"status": "saved", "stage": saved_state["stage"]}

@router.post("/engine/qwave/load")
async def load_engine_state():
    """Restore engine state from last save."""
    global saved_state
    if not saved_state:
        return {"status": "error", "message": "No saved state found"}
    engine.set_state(saved_state)
    return {"status": "loaded", "stage": engine.stages[engine.current_stage]}

# ---------------------------
# 🛑 Emergency Collapse
# ---------------------------
@router.post("/engine/qwave/collapse")
async def collapse_engine():
    """Emergency collapse endpoint to instantly reset engine."""
    engine.collapse()
    return {"status": "collapsed", "stage": engine.stages[engine.current_stage]}