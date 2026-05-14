from __future__ import annotations

import argparse
import math
import struct
import wave
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from backend.tools.field_programs import (
    FieldProgram,
    canonical_field_programs,
    micro_pi_programs,
)


def _sine_sample(phase: float) -> float:
    return math.sin(phase)


def _clamp_audio(x: float) -> float:
    return max(-1.0, min(1.0, x))


def _phase_tag(phi: float) -> str:
    return f"{phi:.12f}".replace(".", "_")


def build_samples_for_programs(
    programs: Sequence[FieldProgram],
    sample_rate: int,
) -> Tuple[List[Tuple[str, float]], List[Tuple[float, float]]]:
    stereo_samples: List[Tuple[float, float]] = []
    timeline: List[Tuple[str, float]] = []

    phase_acc_left = 0.0

    def append_silence(seconds: float, label: str) -> None:
        n = int(round(seconds * sample_rate))
        if n <= 0:
            return
        stereo_samples.extend((0.0, 0.0) for _ in range(n))
        timeline.append((label, n / sample_rate))

    def append_marker(seconds: float, label: str, marker_hz: float, amp: float) -> None:
        n = int(round(seconds * sample_rate))
        if n <= 0:
            return
        step = 2.0 * math.pi * marker_hz / sample_rate
        marker_amp = min(0.9, amp * 0.85 + 0.1)
        for i in range(n):
            x = marker_amp * _sine_sample(i * step)
            stereo_samples.append((x, x))
        timeline.append((label, n / sample_rate))

    def append_phase_segment(program: FieldProgram, label: str) -> None:
        nonlocal phase_acc_left
        n = int(round(program.segment_seconds * sample_rate))
        if n <= 0:
            return
        step = 2.0 * math.pi * program.carrier_hz / sample_rate
        for _ in range(n):
            left = program.amplitude * _sine_sample(phase_acc_left)
            right = program.amplitude * _sine_sample(phase_acc_left + program.phase_rad)
            stereo_samples.append((left, right))
            phase_acc_left += step
            if phase_acc_left >= 2.0 * math.pi:
                phase_acc_left %= 2.0 * math.pi
        timeline.append((label, n / sample_rate))

    append_silence(0.75, "initial_silence")
    for idx, program in enumerate(programs, start=1):
        tag = _phase_tag(program.phase_rad)
        append_marker(program.marker_seconds, f"marker_{idx}_{program.program_id}_{tag}", program.marker_hz, program.amplitude)
        append_silence(program.silence_seconds, f"pre_{idx}_{program.program_id}")
        append_phase_segment(program, f"phase_{idx}_{program.program_id}_{program.label}")
        append_silence(program.silence_seconds, f"post_{idx}_{program.program_id}")

    return timeline, stereo_samples


def write_wav(path: Path, stereo_samples: Iterable[Tuple[float, float]], sample_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        frames = bytearray()
        for left, right in stereo_samples:
            li = int(round(_clamp_audio(left) * 32767.0))
            ri = int(round(_clamp_audio(right) * 32767.0))
            frames.extend(struct.pack("<hh", li, ri))
        wf.writeframes(frames)


def write_manifest(
    path: Path,
    programs: Sequence[FieldProgram],
    timeline: Sequence[Tuple[str, float]],
    sample_rate: int,
) -> None:
    lines: List[str] = [
        "# field program wav manifest",
        f"sample_rate={sample_rate}",
        "",
        "programs:",
    ]
    for p in programs:
        lines.extend(
            [
                f"- program_id={p.program_id}",
                f"  label={p.label}",
                f"  phase_rad={p.phase_rad:.12f}",
                f"  carrier_hz={p.carrier_hz}",
                f"  amplitude={p.amplitude}",
                f"  expected_state={p.expected_state}",
                f"  expected_scope_behavior={p.expected_scope_behavior}",
                f"  expected_pickup_behavior={p.expected_pickup_behavior}",
            ]
        )

    lines.extend(["", "timeline:"])
    total = 0.0
    for label, dur in timeline:
        lines.append(f"  - {label}: {dur:.6f}s")
        total += dur
    lines.append("")
    lines.append(f"total_duration={total:.6f}s")
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate repeatable field-program WAV files.")
    parser.add_argument("--sample-rate", type=int, default=48000)
    parser.add_argument("--carrier-hz", type=float, default=440.0)
    parser.add_argument("--amplitude", type=float, default=0.65)
    parser.add_argument("--segment-seconds", type=float, default=5.0)
    parser.add_argument("--silence-seconds", type=float, default=0.75)
    parser.add_argument("--marker-seconds", type=float, default=0.2)
    parser.add_argument("--marker-hz", type=float, default=1200.0)
    parser.add_argument("--micro-pi", action="store_true")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(".runtime/aion_field_control/field_program_wavs"),
    )
    parser.add_argument(
        "--combined-name",
        type=str,
        default="field_program_sequence.wav",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    factory = micro_pi_programs if args.micro_pi else canonical_field_programs
    programs = factory(
        carrier_hz=args.carrier_hz,
        amplitude=args.amplitude,
        segment_seconds=args.segment_seconds,
        silence_seconds=args.silence_seconds,
        marker_seconds=args.marker_seconds,
        marker_hz=args.marker_hz,
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)

    combined_timeline, combined_samples = build_samples_for_programs(programs, args.sample_rate)
    combined_wav = args.out_dir / args.combined_name
    combined_manifest = args.out_dir / f"{Path(args.combined_name).stem}_manifest.txt"
    write_wav(combined_wav, combined_samples, args.sample_rate)
    write_manifest(combined_manifest, programs, combined_timeline, args.sample_rate)

    for program in programs:
        tline, samples = build_samples_for_programs([program], args.sample_rate)
        wav_path = args.out_dir / f"{program.program_id}_{program.label}.wav"
        manifest_path = args.out_dir / f"{program.program_id}_{program.label}_manifest.txt"
        write_wav(wav_path, samples, args.sample_rate)
        write_manifest(manifest_path, [program], tline, args.sample_rate)

    print(f"Wrote combined WAV: {combined_wav}")
    print(f"Wrote combined manifest: {combined_manifest}")
    print("Programs:")
    for p in programs:
        print(f"  {p.program_id} | {p.label} | phase={p.phase_rad:.12f} | expected={p.expected_state}")


if __name__ == "__main__":
    main()