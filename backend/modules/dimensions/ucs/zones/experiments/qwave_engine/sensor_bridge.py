from __future__ import annotations

"""
Sensor Bridge
-------------
Thin abstraction for external / bench-side read channels.

Goals
- Provide a stable API for reading external coupling signals.
- Work in both real hardware mode and safe/simulated mode.
- Keep the interface simple so capture / A-B testing tools can use it directly.

Notes
- In safe_mode this now returns deterministic synthetic data by default.
- Wall-clock driven oscillation has been removed from the simulation path.
- A local seeded RNG plus an internal simulation tick are used instead.
- Replace the stub methods with real hardware reads as your bench setup evolves.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import math
import random
import time


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


@dataclass(slots=True)
class SensorSnapshot:
    timestamp: float
    pickup_voltage: float
    aux_adc_1: float
    aux_adc_2: float
    magnetometer_x: float
    magnetometer_y: float
    magnetometer_z: float
    temperature_c: float
    notes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "pickup_voltage": self.pickup_voltage,
            "aux_adc_1": self.aux_adc_1,
            "aux_adc_2": self.aux_adc_2,
            "magnetometer_x": self.magnetometer_x,
            "magnetometer_y": self.magnetometer_y,
            "magnetometer_z": self.magnetometer_z,
            "temperature_c": self.temperature_c,
            "notes": dict(self.notes),
        }


class SensorBridge:
    """
    Bench-side sensor abstraction.

    Real mode:
    - wire in ADC / I2C / SPI / serial device readers here.

    Safe mode:
    - emits a structured deterministic synthetic response influenced by the
      currently active emission profile.
    """

    def __init__(
        self,
        safe_mode: bool = True,
        seed: Optional[int] = 7,
    ):
        self.safe_mode = bool(safe_mode)
        self.random = random.Random(7 if seed is None else int(seed))
        self._last_profile: Optional[Dict[str, Any]] = None
        self._t0 = time.time()

        # deterministic simulation clock
        self._sim_tick = 0

    # ------------------------------------------------------------------
    # Internal deterministic helpers
    # ------------------------------------------------------------------
    def _advance_tick(self) -> int:
        self._sim_tick += 1
        return self._sim_tick

    def _sim_wave(self, scale: float, freq: float, phase: float = 0.0) -> float:
        return math.sin((self._sim_tick * freq) + phase) * scale

    # ------------------------------------------------------------------
    # Emission context hook
    # ------------------------------------------------------------------
    def update_emission_context(self, profile: Optional[Dict[str, Any]]) -> None:
        """
        Let the sensor bridge know what is currently being emitted so
        safe-mode can generate structured synthetic responses.
        """
        self._last_profile = profile

    # ------------------------------------------------------------------
    # Real hardware hooks (replace later)
    # ------------------------------------------------------------------
    def read_pickup_voltage(self) -> float:
        if self.safe_mode:
            return self._sim_pickup_voltage()
        return 0.0

    def read_aux_adc(self, channel: int) -> float:
        if self.safe_mode:
            return self._sim_aux_adc(channel)
        return 0.0

    def read_magnetometer(self) -> tuple[float, float, float]:
        if self.safe_mode:
            return self._sim_magnetometer()
        return (0.0, 0.0, 0.0)

    def read_temperature(self) -> float:
        if self.safe_mode:
            return self._sim_temperature()
        return 25.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def read_all(self) -> SensorSnapshot:
        if self.safe_mode:
            self._advance_tick()

        mx, my, mz = self.read_magnetometer()
        snapshot = SensorSnapshot(
            timestamp=time.time() if not self.safe_mode else float(self._sim_tick),
            pickup_voltage=self.read_pickup_voltage(),
            aux_adc_1=self.read_aux_adc(1),
            aux_adc_2=self.read_aux_adc(2),
            magnetometer_x=mx,
            magnetometer_y=my,
            magnetometer_z=mz,
            temperature_c=self.read_temperature(),
            notes={
                "mode": "safe" if self.safe_mode else "hardware",
                "has_emission_context": self._last_profile is not None,
                "sim_tick": self._sim_tick if self.safe_mode else None,
            },
        )
        return snapshot

    # ------------------------------------------------------------------
    # Safe-mode simulation
    # ------------------------------------------------------------------
    def _profile_terms(self) -> Dict[str, float]:
        """
        Convert current profile into a few synthetic observables.
        """
        if not self._last_profile:
            return {
                "phi": 0.0,
                "amplitude": 0.0,
                "frequency": 0.0,
                "harmonic_weight": 1.0,
                "interference_factor": 1.0,
                "duty_cycle": 0.5,
            }

        harmonics = self._last_profile.get("harmonics", [1]) or [1]
        harmonic_weight = sum(harmonics) / max(1, len(harmonics))

        return {
            "phi": float(self._last_profile.get("phi", 0.0)),
            "amplitude": float(self._last_profile.get("amplitude", 0.0)),
            "frequency": float(self._last_profile.get("frequency", 0.0)),
            "harmonic_weight": float(harmonic_weight),
            "interference_factor": float(self._last_profile.get("interference_factor", 1.0)),
            "duty_cycle": float(self._last_profile.get("duty_cycle", 0.5)),
        }

    def _sim_pickup_voltage(self) -> float:
        terms = self._profile_terms()

        phi = terms["phi"]
        amp = terms["amplitude"]
        freq = terms["frequency"]
        interference = terms["interference_factor"]
        harmonic_weight = terms["harmonic_weight"]
        duty_cycle = terms["duty_cycle"]

        base = 0.15 + (amp * 0.55) + (interference * 0.08)
        oscillation = self._sim_wave(
            scale=0.03,
            freq=0.11 + min(0.04, freq * 0.002),
            phase=phi * 0.07,
        )
        phase_bias = math.cos(phi) * 0.07
        harmonic_bias = min(0.08, harmonic_weight * 0.015)
        duty_bias = (duty_cycle - 0.5) * 0.06
        noise = self.random.uniform(-0.015, 0.015)

        return _clamp(
            base + oscillation + phase_bias + harmonic_bias + duty_bias + noise,
            0.0,
            3.3,
        )

    def _sim_aux_adc(self, channel: int) -> float:
        terms = self._profile_terms()
        phi = terms["phi"]
        amp = terms["amplitude"]
        interference = terms["interference_factor"]
        freq = terms["frequency"]

        noise = self.random.uniform(-0.01, 0.01)

        if channel == 1:
            value = (
                0.10
                + (amp * 0.25)
                + (math.sin(phi) * 0.05)
                + self._sim_wave(0.012, 0.09 + min(0.03, freq * 0.001), phase=0.3)
                + noise
            )
        else:
            value = (
                0.12
                + (interference * 0.10)
                + (math.cos(phi) * 0.04)
                + self._sim_wave(0.010, 0.07 + min(0.03, freq * 0.001), phase=0.8)
                + noise
            )

        return _clamp(value, 0.0, 3.3)

    def _sim_magnetometer(self) -> tuple[float, float, float]:
        terms = self._profile_terms()
        phi = terms["phi"]
        amp = terms["amplitude"]
        harmonic_weight = terms["harmonic_weight"]
        freq = terms["frequency"]

        nx = self.random.uniform(-0.005, 0.005)
        ny = self.random.uniform(-0.005, 0.005)
        nz = self.random.uniform(-0.005, 0.005)

        wobble_x = self._sim_wave(0.003, 0.05 + min(0.02, freq * 0.001), phase=0.1)
        wobble_y = self._sim_wave(0.003, 0.06 + min(0.02, freq * 0.001), phase=0.7)
        wobble_z = self._sim_wave(0.003, 0.08 + min(0.02, freq * 0.001), phase=1.3)

        x = (math.cos(phi) * 0.04) + (amp * 0.02) + wobble_x + nx
        y = (math.sin(phi) * 0.04) + (harmonic_weight * 0.003) + wobble_y + ny
        z = (amp * 0.015) + (math.cos(phi * 0.5) * 0.02) + wobble_z + nz
        return (x, y, z)

    def _sim_temperature(self) -> float:
        terms = self._profile_terms()
        amp = terms["amplitude"]
        harmonic_weight = terms["harmonic_weight"]
        freq = terms["frequency"]

        noise = self.random.uniform(-0.03, 0.03)
        drift = self._sim_wave(0.04, 0.02 + min(0.01, freq * 0.0005), phase=0.2)

        return 24.5 + (amp * 0.3) + (harmonic_weight * 0.02) + drift + noise