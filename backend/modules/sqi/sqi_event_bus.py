# File: backend/modules/sqi/sqi_event_bus.py
"""
SQI Event Bus
=============
Manages emission of SQI (Symbolic Quantum Interface) events to GPIO pins or simulated outputs.
Integrates with Raspberry Pi GPIO for hardware signaling, while providing a fallback simulation
mode when running off-Pi (e.g., dev environment).

Features:
    • GPIO-based pulse signaling for SQI events (if RPi.GPIO is available)
    • Simulation mode with console logging (non-Pi environments)
    • Event listener registration for custom SQI hooks
    • Integrated safety shutdown/cleanup for GPIO
"""

import os
import time
import threading

# Attempt GPIO import (only works on Raspberry Pi)
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)  # BCM pin numbering
    GPIO_AVAILABLE = True
    print("✅ SQI: Raspberry Pi GPIO detected, hardware mode enabled.")
except ImportError:
    GPIO_AVAILABLE = False
    print("⚠️ SQI: No GPIO detected, running in simulation mode.")

# Default SQI pin mapping (BCM numbers)
DEFAULT_PINS = {
    "container_growth": 17,
    "glyph_injection": 27,
    "entropy_pulse": 22,
    "heartbeat": 5,
}

# Event listeners registry
event_listeners = {}


def register_event_listener(event_type: str, callback):
    """Register a listener function for a given SQI event."""
    if event_type not in event_listeners:
        event_listeners[event_type] = []
    event_listeners[event_type].append(callback)
    print(f"🔗 SQI listener registered for event: {event_type}")


def _pulse_pin(pin: int, duration: float = 0.1):
    """Pulse a GPIO pin high for a short duration."""
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH)
    time.sleep(duration)
    GPIO.output(pin, GPIO.LOW)


def emit_sqi_event(event_type: str, payload: dict = None):
    """
    Emit an SQI event, pulsing GPIO (if available) and notifying listeners.

    Args:
        event_type: The type of event (e.g., 'container_growth', 'glyph_injection').
        payload: Optional dictionary payload containing event metadata.
    """
    print(f"[SQI Event] {event_type} | Payload: {payload}")

    # Trigger GPIO pulse if hardware is available
    if GPIO_AVAILABLE and event_type in DEFAULT_PINS:
        pin = DEFAULT_PINS[event_type]
        threading.Thread(target=_pulse_pin, args=(pin,), daemon=True).start()
    elif not GPIO_AVAILABLE:
        print(f"⚠️ SQI simulated pulse → Event: {event_type}")

    # Notify any registered listeners
    if event_type in event_listeners:
        for callback in event_listeners[event_type]:
            try:
                callback(payload or {})
            except Exception as e:
                print(f"⚠️ SQI listener error for {event_type}: {e}")


def emit_heartbeat(interval: float = 5.0):
    """
    Emit periodic heartbeat pulses over SQI to confirm system is alive.
    Runs on a separate thread.
    """
    def _heartbeat_loop():
        while True:
            emit_sqi_event("heartbeat", {"timestamp": time.time()})
            time.sleep(interval)

    threading.Thread(target=_heartbeat_loop, daemon=True).start()
    print(f"💓 SQI heartbeat started (interval: {interval}s)")


def cleanup_sqi():
    """Clean up GPIO pins on shutdown."""
    if GPIO_AVAILABLE:
        GPIO.cleanup()
        print("🧹 SQI GPIO cleaned up.")


# Auto-start heartbeat if enabled
if os.getenv("SQI_HEARTBEAT", "true").lower() == "true":
    emit_heartbeat()