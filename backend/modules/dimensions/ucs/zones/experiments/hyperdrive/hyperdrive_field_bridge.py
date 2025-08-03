# File: backend/modules/dimensions/ucs/zones/experiments/hyperdrive/hyperdrive_field_bridge.py

"""
⚡ FieldBridge: Physical Exhaust Bridge (Hyperdrive)
-----------------------------------------------------
Bridges the Hyperdrive engine exhaust to Raspberry Pi hardware:
    • PWM coil driving for resonance field output
    • Dual-coil phased output (0° / 180°)
    • Multi-harmonic stacking (base + overtone)
    • Pulse bursting for exhaust phase intensification
    • Real-time feedback loop via ADC (coil voltage/current sensing)
    • Auto-calibration per exhaust tick
    • Safe-mode simulation for bench testing
"""

import time
import random
import math

try:
    import RPi.GPIO as GPIO
    import spidev  # For MCP3008 ADC
except ImportError:
    GPIO = None
    spidev = None
    print("⚠️ FieldBridge running in simulation mode (no GPIO detected).")


class FieldBridge:
    COIL_PIN_A = 18
    COIL_PIN_B = 19
    ADC_CHANNEL = 0

    def __init__(self, safe_mode: bool = False, dual_coil: bool = True, base_duty: float = 50.0):
        self.safe_mode = safe_mode
        self.dual_coil = dual_coil
        self.base_duty = base_duty
        self.pwm_a = None
        self.pwm_b = None
        self.spi = None
        self.simulated_feedback = 1.0
        self.last_adjustment = 0.0

        if GPIO:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.COIL_PIN_A, GPIO.OUT)
            self.pwm_a = GPIO.PWM(self.COIL_PIN_A, 100)
            self.pwm_a.start(0)

            if self.dual_coil:
                GPIO.setup(self.COIL_PIN_B, GPIO.OUT)
                self.pwm_b = GPIO.PWM(self.COIL_PIN_B, 100)
                self.pwm_b.start(0)

            if not self.safe_mode and spidev:
                self.spi = spidev.SpiDev()
                self.spi.open(0, 0)
                self.spi.max_speed_hz = 1350000

        print(f"🔌 FieldBridge initialized (dual_coil={self.dual_coil}, safe_mode={self.safe_mode})")

    # ---------------------------------------------------------
    # 🔥 Emit Waveform (Supports Dual-Coil)
    # ---------------------------------------------------------
    def emit_waveform(self, freq: float, duty: float):
        if self.safe_mode or GPIO is None:
            print(f"[SIM] PWM OUT: {freq:.2f} Hz @ {duty:.1f}% (dual={self.dual_coil})")
            return

        self.pwm_a.ChangeFrequency(freq)
        self.pwm_a.ChangeDutyCycle(duty)

        if self.dual_coil and self.pwm_b:
            phase_shift = max(0, min(100, 100 - duty))
            self.pwm_b.ChangeFrequency(freq)
            self.pwm_b.ChangeDutyCycle(phase_shift)

    # ---------------------------------------------------------
    # 🎶 Multi-Harmonic Wave Emission
    # ---------------------------------------------------------
    def emit_multi_harmonic(self, base_freq: float, duty: float, harmonics: int = 1, burst: bool = False):
        for h in range(1, harmonics + 1):
            freq = base_freq * h
            print(f"🎵 Harmonic {h}: {freq:.2f} Hz @ {duty:.1f}%")
            self.emit_waveform(freq, duty)
            if burst:
                self._pulse_burst(freq, duty)

    def _pulse_burst(self, freq: float, duty: float, bursts: int = 3, burst_delay: float = 0.02):
        for _ in range(bursts):
            self.emit_waveform(freq, min(100, duty + 20))
            time.sleep(burst_delay)
            self.emit_waveform(freq, duty)
            time.sleep(burst_delay)

    # ---------------------------------------------------------
    # 🚀 Exhaust Emission with Auto-Calibrate & Harmonics
    # ---------------------------------------------------------
    def emit_exhaust_wave(self, phase: float, energy: float, target_voltage: float = 1.0, harmonics: int = 1, burst: bool = False):
        base_freq = 200 + (energy * 5)
        feedback = self.read_feedback()
        adjustment = self.auto_calibrate(target_voltage)
        duty = max(0, min(100, self.base_duty + adjustment))

        print(f"🎚 Exhaust Drive → freq={base_freq:.2f}Hz, harmonics={harmonics}, duty={duty:.1f}%, feedback={feedback:.2f}V")
        self.emit_multi_harmonic(base_freq, duty, harmonics=harmonics, burst=burst)

    # ---------------------------------------------------------
    # 🔎 Feedback (ADC Read)
    # ---------------------------------------------------------
    def read_feedback(self) -> float:
        if self.safe_mode or self.spi is None:
            return random.uniform(0.2, 1.2)
        adc = self.spi.xfer2([1, (8 + self.ADC_CHANNEL) << 4, 0])
        value = ((adc[1] & 3) << 8) + adc[2]
        return (value * 3.3) / 1023

    def get_feedback_voltage(self) -> float:
        """Returns smoothed simulated or actual feedback voltage."""
        if self.safe_mode:
            noise = (math.sin(time.time() * 2.0) * 0.05) + (random.uniform(-0.02, 0.02))
            return self.simulated_feedback + noise
        return self.read_feedback()

    # ---------------------------------------------------------
    # ⚖ Auto-Calibrate (Duty)
    # ---------------------------------------------------------
    def auto_calibrate(self, target_voltage: float = 1.0) -> float:
        feedback = self.read_feedback()
        adjustment = (target_voltage - feedback) * 10
        self.last_adjustment = adjustment

        if self.safe_mode:
            self.simulated_feedback += adjustment * 0.05  # Simulate gradual tuning

        print(f"⚖ Auto-calibrate: feedback={feedback:.2f}V adj={adjustment:+.2f}")
        return adjustment

    # ---------------------------------------------------------
    # 📴 Shutdown
    # ---------------------------------------------------------
    def shutdown(self):
        if GPIO and self.pwm_a:
            self.pwm_a.stop()
            if self.dual_coil and self.pwm_b:
                self.pwm_b.stop()
            GPIO.cleanup()
        if self.spi:
            self.spi.close()
        print("🔻 FieldBridge shut down.")