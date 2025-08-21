from datetime import datetime
import os, json
from typing import Dict, Any
from copy import deepcopy
from backend.modules.lean.lean_utils import is_lean_container

def get_state(engine) -> Dict[str, Any]:
    """Returns current engine state snapshot with harmonics and SQI context."""
    return {
        "stage": engine.stages[engine.current_stage],
        "fields": engine.fields,
        "particle_count": len(engine.particles),
        "nested_containers": engine.nested_containers,
        "particles": [
            {k: round(v, 3) if isinstance(v, float) else v for k, v in p.items()}
            for p in engine.particles
        ],
        "resonance_phase": getattr(engine, "resonance_phase", 0.0),
        "harmonic_coherence": getattr(engine, "last_harmonic_coherence", None),
        "sqi_enabled": engine.sqi_enabled,
        "last_sqi_adjustments": getattr(engine, "last_sqi_adjustments", {}),
        "tick_count": getattr(engine, "tick_count", 0),
    }

def set_state(engine, state: Dict[str, Any]):
    """Restores engine state from a snapshot with harmonic validation and container sync."""
    # ✅ Field/Stage restore
    engine.fields = state.get("fields", engine.fields)
    stage_name = state.get("stage", engine.stages[0])
    if stage_name in engine.stages:
        engine.current_stage = engine.stages.index(stage_name)

    # ✅ Core state restore
    engine.nested_containers = state.get("nested_containers", [])
    engine.particles = state.get("particles", [])
    engine.resonance_phase = state.get("resonance_phase", 0.0)
    engine.sqi_enabled = state.get("sqi_enabled", False)
    engine.last_sqi_adjustments = state.get("last_sqi_adjustments", {})
    engine.tick_count = state.get("tick_count", 0)

    # ✅ Container sync
    engine.container.nested = engine.nested_containers
    engine.container.expand(avatar_state=engine.safe_mode_avatar if engine.safe_mode else None)

    # ✅ Reset logs
    engine.resonance_log.clear()
    engine.resonance_filtered.clear()
    engine.pending_sqi_ticks = 20

    # 🎼 Harmonic resync if coherence missing or drift detected
    if "harmonic_coherence" in state and state["harmonic_coherence"] is not None:
        engine.last_harmonic_coherence = state["harmonic_coherence"]
    else:
        print("🎼 Harmonic coherence missing in snapshot → Triggering resync...")
        if hasattr(engine, "_resync_harmonics"):
            engine._resync_harmonics()

    print(f"✅ Engine state restored: {stage_name} ({len(engine.particles)} particles)")

def compute_score(engine):
    """Calculates stability score: drift, exhaust, SQI, harmonic weight."""
    drift_window = engine.resonance_filtered[-10:]
    drift_penalty = (max(drift_window) - min(drift_window)) if drift_window else 0.0
    exhaust_penalty = sum(e.get("impact_speed", 0) for e in engine.exhaust_log[-5:]) / max(len(engine.exhaust_log[-5:]), 1)

    # SQI bonus if drift improves
    sqi_bonus = 0.0
    if getattr(engine, "last_sqi_adjustments", {}):
        prev_drift = getattr(engine, "_prev_drift_for_score", drift_penalty)
        if drift_penalty < prev_drift:
            sqi_bonus = 0.3
        engine._prev_drift_for_score = drift_penalty

    # Harmonic coherence bonus
    coherence = getattr(engine, "last_harmonic_coherence", 1.0)
    harmonic_bonus = (coherence - 0.7) * 0.5 if coherence else 0.0

    drift_penalty = min(drift_penalty, 5.0)
    exhaust_penalty = min(exhaust_penalty, 10.0)

    score = -(drift_penalty * 1.5 + exhaust_penalty) + sqi_bonus + harmonic_bonus
    print(f"🏆 [Score] Drift={drift_penalty:.3f}, Exhaust={exhaust_penalty:.2f}, SQI Bonus={sqi_bonus:.2f}, Harmonic Bonus={harmonic_bonus:.2f} → Score={score:.4f}")

    if engine.best_score is None or score > engine.best_score:
        engine.best_score = score
        engine.best_fields = deepcopy(engine.fields)
        engine.best_particles = deepcopy(engine.particles)

    return score

def export_best_state(engine):
    """Exports best engine state snapshot (with harmonics)."""
    os.makedirs(engine.LOG_DIR, exist_ok=True)
    best_path = os.path.join(engine.LOG_DIR, "qwave_best_state.json")
    data = {
        "fields": engine.best_fields,
        "particles": deepcopy(engine.best_particles),
        "score": engine.best_score,
        "sqi_enabled": engine.sqi_enabled,
        "last_sqi_adjustments": getattr(engine, "last_sqi_adjustments", {}),
        "harmonic_coherence": getattr(engine, "last_harmonic_coherence", None),
        "timestamp": datetime.now().isoformat()
    }
    with open(best_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"💾 Best state exported: {best_path}")

# ===============================
# 🧠 Class Wrapper (StateManager)
# ===============================
class StateManager:
    @staticmethod
    def get_active_universal_container_system(engine):
        return get_state(engine)

    @staticmethod
    def restore_universal_container_system(engine, state):
        return set_state(engine, state)

    @staticmethod
    def compute_engine_score(engine):
        return compute_score(engine)

    @staticmethod
    def export_best_snapshot(engine):
        return export_best_state(engine)

    @staticmethod
    def get_current_container():
        """Stub to satisfy ContainerRuntime contract — unused in CreativeCore."""
        return None

    @staticmethod
    def get_current_container_id() -> str:
        """Stub to satisfy ContainerRuntime contract — static test ID."""
        return "atom_electrons_test"

    @staticmethod
    def set_current_container(container_id: str):
        """Stub — no runtime container switching in this context."""
        pass