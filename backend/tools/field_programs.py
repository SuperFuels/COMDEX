from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class FieldProgram:
    program_id: str
    label: str
    phase_rad: float
    carrier_hz: float
    amplitude: float
    segment_seconds: float
    silence_seconds: float
    marker_seconds: float
    marker_hz: float
    expected_state: str
    expected_scope_behavior: str
    expected_pickup_behavior: str
    harmonic_family: int = 1
    envelope: str = "steady"


def canonical_field_programs(
    *,
    carrier_hz: float = 440.0,
    amplitude: float = 0.65,
    segment_seconds: float = 5.0,
    silence_seconds: float = 0.75,
    marker_seconds: float = 0.2,
    marker_hz: float = 1200.0,
) -> List[FieldProgram]:
    return [
        FieldProgram(
            program_id="FP_0",
            label="constructive_0",
            phase_rad=0.0,
            carrier_hz=carrier_hz,
            amplitude=amplitude,
            segment_seconds=segment_seconds,
            silence_seconds=silence_seconds,
            marker_seconds=marker_seconds,
            marker_hz=marker_hz,
            expected_state="S1_constructive",
            expected_scope_behavior="high amplitude, channels aligned",
            expected_pickup_behavior="strong induced response",
        ),
        FieldProgram(
            program_id="FP_1",
            label="intermediate_pos",
            phase_rad=math.pi / 2.0,
            carrier_hz=carrier_hz,
            amplitude=amplitude,
            segment_seconds=segment_seconds,
            silence_seconds=silence_seconds,
            marker_seconds=marker_seconds,
            marker_hz=marker_hz,
            expected_state="S2_intermediate",
            expected_scope_behavior="reduced/intermediate amplitude",
            expected_pickup_behavior="moderate induced response",
        ),
        FieldProgram(
            program_id="FP_2",
            label="null_pi",
            phase_rad=math.pi,
            carrier_hz=carrier_hz,
            amplitude=amplitude,
            segment_seconds=segment_seconds,
            silence_seconds=silence_seconds,
            marker_seconds=marker_seconds,
            marker_hz=marker_hz,
            expected_state="S4_destructive",
            expected_scope_behavior="near-flat / null collapse",
            expected_pickup_behavior="minimum induced response",
        ),
        FieldProgram(
            program_id="FP_3",
            label="intermediate_neg",
            phase_rad=3.0 * math.pi / 2.0,
            carrier_hz=carrier_hz,
            amplitude=amplitude,
            segment_seconds=segment_seconds,
            silence_seconds=silence_seconds,
            marker_seconds=marker_seconds,
            marker_hz=marker_hz,
            expected_state="S2_intermediate",
            expected_scope_behavior="reduced/intermediate amplitude",
            expected_pickup_behavior="moderate induced response",
        ),
        FieldProgram(
            program_id="FP_4",
            label="constructive_wrap",
            phase_rad=2.0 * math.pi,
            carrier_hz=carrier_hz,
            amplitude=amplitude,
            segment_seconds=segment_seconds,
            silence_seconds=silence_seconds,
            marker_seconds=marker_seconds,
            marker_hz=marker_hz,
            expected_state="S1_constructive",
            expected_scope_behavior="high amplitude restored",
            expected_pickup_behavior="strong induced response",
        ),
    ]


def micro_pi_programs(
    *,
    carrier_hz: float = 440.0,
    amplitude: float = 0.65,
    segment_seconds: float = 5.0,
    silence_seconds: float = 0.75,
    marker_seconds: float = 0.2,
    marker_hz: float = 1200.0,
) -> List[FieldProgram]:
    phases = [
        3.141592990,
        3.141592995,
        3.141593000,
        3.141593005,
        3.141593010,
    ]
    out: List[FieldProgram] = []
    for idx, phase in enumerate(phases):
        out.append(
            FieldProgram(
                program_id=f"PI_MICRO_{idx}",
                label=f"micro_pi_{idx}",
                phase_rad=phase,
                carrier_hz=carrier_hz,
                amplitude=amplitude,
                segment_seconds=segment_seconds,
                silence_seconds=silence_seconds,
                marker_seconds=marker_seconds,
                marker_hz=marker_hz,
                expected_state="micro_pi_probe",
                expected_scope_behavior="compare null depth around pi",
                expected_pickup_behavior="compare induced null depth around pi",
            )
        )
    return out