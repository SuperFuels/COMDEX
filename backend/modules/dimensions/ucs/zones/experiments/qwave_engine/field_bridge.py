"""
⚡ FieldBridge: Symatics / QWave Physical Output Bridge
------------------------------------------------------
Bridges the QWave / Symatics engine output to Raspberry Pi hardware:

    * PWM coil driving for resonance field output
    * Dual-coil phased output
    * Multi-harmonic stacking (base + overtone)
    * Pulse bursting for symbolic envelope intensification
    * Real-time feedback loop via ADC (coil voltage/current sensing)
    * Auto-calibration per emission tick
    * Legacy exhaust-wave compatibility
    * Symatics-native emission path:
        - phi controls symbolic phase-state / "word"
        - amplitude controls output intensity
        - frequency controls carrier
        - harmonic_signature controls overtone stack
        - duty_cycle controls pulse width
        - envelope controls burst behavior
    * Safe-mode simulation for bench testing

Key update
- Safe-mode is now deterministic by default.
- Wall-clock driven noise and module-global randomness have been removed
  from the simulation path.
- A local seeded RNG plus an internal simulation tick counter are used instead,
  so repeated runs with the same inputs produce stable, comparable outputs.
"""

from __future__ import annotations

import math
import random
import time
from typing import Optional

try:
    import RPi.GPIO as GPIO
    import spidev  # MCP3008 ADC
except ImportError:
    GPIO = None
    spidev = None
    print("⚠️ FieldBridge running in simulation mode (no GPIO detected).")


class FieldBridge:
    COIL_PIN_A = 18
    COIL_PIN_B = 19
    ADC_CHANNEL = 0

    def __init__(
        self,
        safe_mode: bool = False,
        dual_coil: bool = True,
        base_duty: float = 50.0,
        sim_seed: int = 7,
    ):
        self.safe_mode = bool(safe_mode)
        self.dual_coil = bool(dual_coil)
        self.base_duty = float(base_duty)

        self.pwm_a = None
        self.pwm_b = None
        self.spi = None

        # Simulated bridge state
        self.simulated_feedback = 1.0
        self.simulated_phase = 0.0
        self.simulated_amplitude = 0.0
        self.simulated_frequency = 0.0
        self.last_adjustment = 0.0
        self.last_mode = "idle"
        self.last_emit_timestamp = 0.0

        # Deterministic safe-mode state
        self._sim_tick = 0
        self._sim_rng = random.Random(sim_seed)

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
                self.spi.max_speed_hz = 1_350_000

        print(
            f"🔌 FieldBridge initialized "
            f"(dual_coil={self.dual_coil}, safe_mode={self.safe_mode})"
        )

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------
    @staticmethod
    def _clamp(value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))

    @staticmethod
    def _wrap_phase(phi: float) -> float:
        return float(phi) % (2.0 * math.pi)

    def _advance_sim_tick(self, steps: int = 1) -> int:
        self._sim_tick += max(1, int(steps))
        return self._sim_tick

    def _sim_sine(self, scale: float, freq: float, phase: float = 0.0) -> float:
        return math.sin((self._sim_tick * freq) + phase) * scale

    def _update_simulated_state(
        self,
        *,
        target_voltage: float,
        phi: float,
        amplitude: float,
        frequency: float,
    ) -> None:
        """
        Update safe-mode internal state so feedback behaves coherently.

        Deterministic simulation rules:
        - no wall-clock time
        - no module-global random state
        - only internal tick counter + local seeded RNG
        """
        phi = self._wrap_phase(phi)
        amplitude = max(0.0, float(amplitude))
        frequency = max(0.0, float(frequency))
        target_voltage = max(0.0, float(target_voltage))

        self._advance_sim_tick()

        # Gentle convergence toward target.
        blend = 0.18
        self.simulated_feedback += (target_voltage - self.simulated_feedback) * blend

        # Small deterministic oscillation + bounded seeded noise.
        osc = self._sim_sine(0.015, 0.07 + min(0.03, frequency * 0.01), phase=phi * 0.05)
        noise = self._sim_rng.uniform(-0.01, 0.01)
        self.simulated_feedback = self._clamp(self.simulated_feedback + osc + noise, 0.0, 3.3)

        # Track phase/frequency/amplitude for external readers if needed later.
        self.simulated_phase = phi
        self.simulated_amplitude = amplitude
        self.simulated_frequency = frequency
        self.last_emit_timestamp = float(self._sim_tick)

    # ---------------------------------------------------------
    # 🔥 Emit Waveform (basic / legacy)
    # ---------------------------------------------------------
    def emit_waveform(self, freq: float, duty: float) -> None:
        freq = max(1.0, float(freq))
        duty = self._clamp(float(duty), 0.0, 100.0)

        if self.safe_mode or GPIO is None:
            print(f"[SIM] PWM OUT: {freq:.2f} Hz @ {duty:.1f}% (dual={self.dual_coil})")
            return

        if self.pwm_a:
            self.pwm_a.ChangeFrequency(freq)
            self.pwm_a.ChangeDutyCycle(duty)

        if self.dual_coil and self.pwm_b:
            # Legacy fallback: inverse-duty pseudo phase split
            phase_shift_duty = self._clamp(100.0 - duty, 0.0, 100.0)
            self.pwm_b.ChangeFrequency(freq)
            self.pwm_b.ChangeDutyCycle(phase_shift_duty)

    # ---------------------------------------------------------
    # 🎶 Multi-Harmonic Wave Emission
    # ---------------------------------------------------------
    def emit_multi_harmonic(
        self,
        base_freq: float,
        duty: float,
        harmonics: int = 1,
        burst: bool = False,
    ) -> None:
        harmonics = max(1, int(harmonics))

        for h in range(1, harmonics + 1):
            freq = max(1.0, float(base_freq) * h)
            print(f"🎵 Harmonic {h}: {freq:.2f} Hz @ {duty:.1f}%")
            self.emit_waveform(freq, duty)
            if burst:
                self._pulse_burst(freq, duty)

    def _pulse_burst(
        self,
        freq: float,
        duty: float,
        bursts: int = 3,
        burst_delay: float = 0.02,
    ) -> None:
        for _ in range(max(1, int(bursts))):
            self.emit_waveform(freq, min(100.0, duty + 20.0))
            if not self.safe_mode:
                time.sleep(burst_delay)
            else:
                self._advance_sim_tick()

            self.emit_waveform(freq, duty)
            if not self.safe_mode:
                time.sleep(burst_delay)
            else:
                self._advance_sim_tick()

    # ---------------------------------------------------------
    # 🚀 Legacy Exhaust Emission
    # ---------------------------------------------------------
    def emit_exhaust_wave(
        self,
        phase: float,
        energy: float,
        target_voltage: float = 1.0,
        harmonics: int = 1,
        burst: bool = False,
    ) -> None:
        phase = self._wrap_phase(phase)
        energy = max(0.0, float(energy))
        base_freq = max(1.0, 200.0 + (energy * 5.0))

        # Legacy proxy: map energy to intended target voltage conservatively.
        emission_target_voltage = max(0.05, float(target_voltage) * min(2.0, 0.25 + energy))

        feedback = self.read_feedback()
        adjustment = self.auto_calibrate(emission_target_voltage)
        duty = self._clamp(self.base_duty + adjustment, 0.0, 100.0)

        if self.safe_mode:
            self._update_simulated_state(
                target_voltage=emission_target_voltage,
                phi=phase,
                amplitude=min(1.5, energy),
                frequency=base_freq / 100.0,
            )

        print(
            f"🎚 Exhaust Drive -> phase={phase:.4f}, "
            f"freq={base_freq:.2f}Hz, harmonics={harmonics}, "
            f"duty={duty:.1f}%, feedback={feedback:.2f}V"
        )

        self.last_mode = "exhaust"

        self.emit_multi_harmonic(
            base_freq=base_freq,
            duty=duty,
            harmonics=harmonics,
            burst=burst,
        )

    # ---------------------------------------------------------
    # ⟲ Symatics Emission
    # ---------------------------------------------------------
    def emit_symatics_wave(
        self,
        phi: float,
        amplitude: float,
        frequency: float,
        harmonic_signature: Optional[list[int]] = None,
        duty_cycle: float = 0.5,
        envelope: str = "steady",
        target_voltage: float = 1.0,
    ) -> None:
        """
        Emit an intentional Symatics waveform.

        Mapping:
        - phi controls the symbolic phase-state / word
        - amplitude controls output intensity
        - frequency controls base carrier
        - harmonic_signature controls overtone stack
        - duty_cycle controls pulse width
        - envelope controls burst behavior

        Hello World states:
        - phi = 0      -> constructive
        - phi = pi     -> destructive / cancellation probe
        - phi = pi / 2 -> beyond-Boolean probe
        """
        harmonic_signature = harmonic_signature or [1]
        harmonic_signature = [max(1, int(h)) for h in harmonic_signature]

        phi = self._wrap_phase(phi)
        amplitude = max(0.0, float(amplitude))
        frequency = max(0.001, float(frequency))
        duty = self._clamp(float(duty_cycle) * 100.0, 0.0, 100.0)

        # Symbolic phase meaning:
        # constructive (0)  -> 2.0
        # destructive (pi)  -> 0.0
        # pi/2              -> 1.0
        interference_factor = 1.0 + math.cos(phi)

        base_freq = max(1.0, frequency * 100.0)

        # Important fix:
        # - constructive should not explode upward
        # - destructive should not chase huge opposite values
        # - target stays bounded and physical
        if abs(phi - math.pi) < 1e-6:
            scaled_target_voltage = 0.05
        else:
            scaled_target_voltage = max(
                0.05,
                min(2.5, float(target_voltage) * max(0.05, amplitude)),
            )

        adjustment = self.auto_calibrate(target_voltage=scaled_target_voltage)
        tuned_duty = self._clamp(duty + adjustment, 0.0, 100.0)

        burst = envelope in {"burst", "pulsed", "ignite"}

        if self.safe_mode:
            self._update_simulated_state(
                target_voltage=scaled_target_voltage,
                phi=phi,
                amplitude=amplitude,
                frequency=frequency,
            )

        print(
            f"⟲ Symatics emission -> "
            f"phi={phi:.4f}, A={amplitude:.3f}, "
            f"f={base_freq:.2f}Hz, "
            f"harmonics={harmonic_signature}, "
            f"duty={tuned_duty:.1f}%, "
            f"factor={interference_factor:.3f}, "
            f"targetV={scaled_target_voltage:.3f}, "
            f"envelope={envelope}"
        )

        self.last_mode = "symatics"

        if self.dual_coil and self.pwm_a and self.pwm_b and not self.safe_mode and GPIO:
            self._emit_dual_phase_wave(
                base_freq=base_freq,
                duty=tuned_duty,
                phi=phi,
                harmonics=harmonic_signature,
                burst=burst,
            )
            return

        if self.dual_coil and self.safe_mode:
            self._emit_dual_phase_wave(
                base_freq=base_freq,
                duty=tuned_duty,
                phi=phi,
                harmonics=harmonic_signature,
                burst=burst,
            )
            return

        for h in harmonic_signature:
            freq = max(1.0, base_freq * h)
            print(f"🎵 Harmonic {h}: {freq:.2f} Hz @ {tuned_duty:.1f}%")
            self.emit_waveform(freq, tuned_duty)
            if burst:
                self._pulse_burst(freq, tuned_duty)

    def _emit_dual_phase_wave(
        self,
        base_freq: float,
        duty: float,
        phi: float,
        harmonics: list[int],
        burst: bool = False,
    ) -> None:
        """
        Dual-coil symbolic phase emission.

        Coil A and Coil B are biased according to phi.
        This is closer to the actual write-path than the legacy exhaust
        model, because phi now matters physically.
        """
        phase_mix = (1.0 + math.cos(phi)) / 2.0  # 0..1
        duty_a = self._clamp(duty * phase_mix, 0.0, 100.0)
        duty_b = self._clamp(duty * (1.0 - phase_mix), 0.0, 100.0)

        if self.safe_mode or GPIO is None:
            for h in harmonics:
                freq = max(1.0, base_freq * h)
                print(
                    f"[SIM] 🎵 Dual-phase harmonic h={h} "
                    f"freq={freq:.2f}Hz dutyA={duty_a:.1f}% dutyB={duty_b:.1f}% phi={phi:.4f}"
                )
                if burst:
                    self._advance_sim_tick()
            return

        for h in harmonics:
            freq = max(1.0, base_freq * h)

            if self.pwm_a:
                self.pwm_a.ChangeFrequency(freq)
                self.pwm_a.ChangeDutyCycle(duty_a)

            if self.pwm_b:
                self.pwm_b.ChangeFrequency(freq)
                self.pwm_b.ChangeDutyCycle(duty_b)

            print(
                f"🎵 Dual-phase harmonic h={h} "
                f"freq={freq:.2f}Hz dutyA={duty_a:.1f}% dutyB={duty_b:.1f}% phi={phi:.4f}"
            )

            if burst:
                time.sleep(0.01)

    # ---------------------------------------------------------
    # 🔎 Feedback (ADC Read)
    # ---------------------------------------------------------
    def read_feedback(self) -> float:
        if self.safe_mode or self.spi is None:
            return max(0.0, self.simulated_feedback)

        adc = self.spi.xfer2([1, (8 + self.ADC_CHANNEL) << 4, 0])
        value = ((adc[1] & 3) << 8) + adc[2]
        return (value * 3.3) / 1023.0

    def get_feedback_voltage(self) -> float:
        """
        Return smoothed simulated or actual feedback voltage.
        In safe mode this is deterministic and tied to the internal sim state.
        """
        if self.safe_mode:
            noise = self._sim_sine(0.01, 0.09, phase=self.simulated_phase * 0.03)
            noise += self._sim_rng.uniform(-0.005, 0.005)
            return max(0.0, min(3.3, self.simulated_feedback + noise))

        return self.read_feedback()

    # ---------------------------------------------------------
    # ⚖ Auto-Calibrate (Duty Bias)
    # ---------------------------------------------------------
    def auto_calibrate(self, target_voltage: float = 1.0) -> float:
        feedback = self.read_feedback()
        target_voltage = max(0.0, float(target_voltage))

        raw_adjustment = (target_voltage - feedback) * 10.0
        adjustment = self._clamp(raw_adjustment, -20.0, 20.0)
        self.last_adjustment = adjustment

        if self.safe_mode:
            self.simulated_feedback += (target_voltage - self.simulated_feedback) * 0.12
            self.simulated_feedback = self._clamp(self.simulated_feedback, 0.0, 3.3)

        print(f"⚖ Auto-calibrate: feedback={feedback:.2f}V adj={adjustment:+.2f}")
        return adjustment

    # ---------------------------------------------------------
    # 📴 Shutdown
    # ---------------------------------------------------------
    def shutdown(self) -> None:
        if GPIO and self.pwm_a:
            self.pwm_a.stop()

            if self.dual_coil and self.pwm_b:
                self.pwm_b.stop()

            GPIO.cleanup()

        if self.spi:
            self.spi.close()

        print("🔻 FieldBridge shut down.")