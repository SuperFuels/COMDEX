from __future__ import annotations

import argparse
import math
import struct
import wave
from pathlib import Path
from typing import List, Tuple


def _sine_sample(phase: float) -> float:
    return math.sin(phase)


def _clamp_audio(x: float) -> float:
    return max(-1.0, min(1.0, x))


def _phase_label(phi: float) -> str:
    if abs(phi - 0.0) < 1e-12:
        return "0"
    if abs(phi - (math.pi / 2.0)) < 1e-12:
        return "pi_over_2"
    if abs(phi - math.pi) < 1e-12:
        return "pi"
    if abs(phi - (3.0 * math.pi / 2.0)) < 1e-12:
        return "3pi_over_2"
    if abs(phi - (2.0 * math.pi)) < 1e-12:
        return "2pi"
    return f"{phi:.6f}".replace(".", "_").replace("-", "neg_")


def _get_phases(mode: str) -> List[float]:
    if mode == "broad":
        return [
            0.0,
            math.pi / 2.0,
            math.pi,
            3.0 * math.pi / 2.0,
            2.0 * math.pi,
        ]
    if mode == "micro-pi":
        return [
            3.141592990,
            3.141592995,
            3.141593000,
            3.141593005,
            3.141593010,
        ]
    if mode == "exaggerated-pi":
        return [
            math.pi - 0.2,
            math.pi - 0.1,
            math.pi,
            math.pi + 0.1,
            math.pi + 0.2,
        ]
    raise ValueError(f"Unknown phase mode: {mode}")


def build_phase_segments(
    sample_rate: int,
    carrier_hz: float,
    amplitude: float,
    segment_seconds: float,
    silence_seconds: float,
    marker_seconds: float,
    marker_hz: float,
    phases: List[float],
    *,
    continuous_phase: bool = True,
) -> Tuple[List[Tuple[str, float]], List[Tuple[float, float]]]:
    """
    Returns:
      timeline: [(label, duration_seconds), ...]
      stereo_samples: [(left, right), ...]

    Left channel is the reference waveform.
    Right channel is the phase-shifted waveform.
    """
    stereo_samples: List[Tuple[float, float]] = []
    timeline: List[Tuple[str, float]] = []

    phase_acc_left = 0.0
    phase_step = 2.0 * math.pi * carrier_hz / sample_rate

    marker_amp = min(0.95, amplitude * 0.85 + 0.1)
    marker_phase_step = 2.0 * math.pi * marker_hz / sample_rate

    def append_silence(seconds: float, label: str) -> None:
        n = int(round(seconds * sample_rate))
        if n <= 0:
            return
        stereo_samples.extend((0.0, 0.0) for _ in range(n))
        timeline.append((label, n / sample_rate))

    def append_marker(seconds: float, label: str) -> None:
        n = int(round(seconds * sample_rate))
        if n <= 0:
            return
        for i in range(n):
            x = marker_amp * _sine_sample(i * marker_phase_step)
            stereo_samples.append((x, x))
        timeline.append((label, n / sample_rate))

    def append_phase_segment(phi: float, seconds: float, label: str) -> None:
        nonlocal phase_acc_left

        n = int(round(seconds * sample_rate))
        if n <= 0:
            return

        local_phase_left = phase_acc_left if continuous_phase else 0.0
        right_phase_offset = phi

        for _ in range(n):
            left = amplitude * _sine_sample(local_phase_left)
            right = amplitude * _sine_sample(local_phase_left + right_phase_offset)
            stereo_samples.append((left, right))

            local_phase_left += phase_step
            if local_phase_left >= 2.0 * math.pi:
                local_phase_left %= 2.0 * math.pi

        if continuous_phase:
            phase_acc_left = local_phase_left

        timeline.append((label, n / sample_rate))

    append_silence(silence_seconds, "initial_silence")

    for idx, phi in enumerate(phases, start=1):
        tag = _phase_label(phi)
        append_marker(marker_seconds, f"marker_{idx}_{tag}")
        append_silence(silence_seconds, f"pre_phase_{idx}_{tag}")
        append_phase_segment(phi, segment_seconds, f"phase_{idx}_{tag}")
        append_silence(silence_seconds, f"post_phase_{idx}_{tag}")

    return timeline, stereo_samples


def write_wav(
    path: Path,
    stereo_samples: List[Tuple[float, float]],
    sample_rate: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)  # 16-bit PCM
        wf.setframerate(sample_rate)

        frames = bytearray()
        for left, right in stereo_samples:
            li = int(round(_clamp_audio(left) * 32767.0))
            ri = int(round(_clamp_audio(right) * 32767.0))
            frames.extend(struct.pack("<hh", li, ri))
        wf.writeframes(frames)


def write_manifest(
    path: Path,
    timeline: List[Tuple[str, float]],
    sample_rate: int,
    carrier_hz: float,
    amplitude: float,
    phases: List[float],
    mode: str,
) -> None:
    lines = [
        "# pi audio scope generator manifest",
        f"sample_rate={sample_rate}",
        f"carrier_hz={carrier_hz}",
        f"amplitude={amplitude}",
        f"mode={mode}",
        "phases_rad=" + ",".join(f"{p:.12f}" for p in phases),
        "",
        "timeline:",
    ]
    total = 0.0
    for label, dur in timeline:
        lines.append(f"  - {label}: {dur:.6f}s")
        total += dur
    lines.append("")
    lines.append(f"total_duration={total:.6f}s")
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a stereo WAV for oscilloscope verification of phase interference near pi."
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(".runtime/aion_field_control/pi_scope_test.wav"),
        help="Output WAV path",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(".runtime/aion_field_control/pi_scope_test_manifest.txt"),
        help="Output manifest path",
    )
    parser.add_argument("--sample-rate", type=int, default=48000)
    parser.add_argument("--carrier-hz", type=float, default=440.0)
    parser.add_argument("--amplitude", type=float, default=0.80)
    parser.add_argument("--segment-seconds", type=float, default=5.0)
    parser.add_argument("--silence-seconds", type=float, default=0.75)
    parser.add_argument("--marker-seconds", type=float, default=0.20)
    parser.add_argument("--marker-hz", type=float, default=1200.0)
    parser.add_argument(
        "--mode",
        choices=["broad", "micro-pi", "exaggerated-pi"],
        default="broad",
        help="Phase sweep mode",
    )
    parser.add_argument(
        "--micro-pi",
        action="store_true",
        help="Backward-compatible alias for --mode micro-pi",
    )
    parser.add_argument(
        "--exaggerated-pi",
        action="store_true",
        help="Use visibly shifted pi-neighbour phases for easier oscilloscope viewing",
    )
    parser.add_argument(
        "--restart-phase-each-segment",
        action="store_true",
        help="Restart the carrier phase at 0 for each segment instead of keeping a continuous reference phase",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    mode = args.mode
    if args.micro_pi:
        mode = "micro-pi"
    if args.exaggerated_pi:
        mode = "exaggerated-pi"

    phases = _get_phases(mode)

    timeline, stereo_samples = build_phase_segments(
        sample_rate=args.sample_rate,
        carrier_hz=args.carrier_hz,
        amplitude=args.amplitude,
        segment_seconds=args.segment_seconds,
        silence_seconds=args.silence_seconds,
        marker_seconds=args.marker_seconds,
        marker_hz=args.marker_hz,
        phases=phases,
        continuous_phase=not args.restart_phase_each_segment,
    )

    write_wav(args.out, stereo_samples, args.sample_rate)
    write_manifest(
        args.manifest,
        timeline,
        args.sample_rate,
        args.carrier_hz,
        args.amplitude,
        phases,
        mode,
    )

    print(f"Wrote WAV: {args.out}")
    print(f"Wrote manifest: {args.manifest}")
    print(f"Mode: {mode}")
    print("Phases:")
    for p in phases:
        print(f"  {p:.12f}")


if __name__ == "__main__":
    main()