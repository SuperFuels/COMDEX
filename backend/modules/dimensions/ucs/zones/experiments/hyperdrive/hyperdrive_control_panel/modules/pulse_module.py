"""
🫀 Pulse Detection Module
-------------------------
* Detects resonance pulses and stability signatures.
* Auto-enables SQI when drift falls within threshold.
* Supports SQI lock, idle-state save, and stage-aware context.
"""

from datetime import datetime

# =========================
# 🫀 PULSE DETECTION & SQI AUTO-ENABLE
# =========================
def detect_pulse(engine):
    """
    Evaluate resonance drift for pulse stability and auto-enable SQI if conditions are met.
    Returns True if stable pulse is confirmed (for stage advancement triggers).
    """
    if len(engine.resonance_filtered) < getattr(engine, "stage_stability_window", 50):
        return False

    # 🔎 Drift window calculation
    window = engine.resonance_filtered[-engine.stage_stability_window:]
    drift = max(window) - min(window)

    # 🫀 Pulse signature detection
    if drift <= (engine.stability_threshold * 0.5):
        engine.log_event(f"🫀 Pulse detected: drift={drift:.4f} (stable signature)")

        # 🔓 Auto-enable SQI if not active
        if not engine.sqi_enabled:
            engine.log_event("🔓 Auto-enabling SQI: Pulse stability confirmed.")
            engine.sqi_enabled = True
            engine.pending_sqi_ticks = 10  # Kickstart SQI fine-tune

    # ✅ SQI Lock condition (ultra-low drift)
    if drift <= 0.05 and not getattr(engine, "sqi_locked", False):
        engine.sqi_locked = True
        engine.log_event(f"🔒 SQI LOCKED: Drift={drift:.4f}")
        _save_idle_state_if_available(engine)

    # Return True if fully stable (used for stage advance)
    return drift <= engine.stability_threshold


# =========================
# 💾 IDLE STATE SAVE (Optional Hook)
# =========================
def _save_idle_state_if_available(engine):
    """
    Auto-save engine state when SQI lock is achieved, if supported.
    """
    if hasattr(engine, "save_idle_state"):
        engine.save_idle_state(engine)
        engine.log_event(f"💾 SQI idle state saved (tick={engine.tick_count}).")


# =========================
# ✅ INLINE USAGE (Tick Integration)
# =========================
def tick_pulse_handler(engine):
    """
    Tick-level pulse handler.
    Called within tick orchestrator after harmonic & exhaust updates.
    """
    if detect_pulse(engine):
        engine.log_event("✅ Resonance stable -> eligible for stage advancement.")
        return True
    return False