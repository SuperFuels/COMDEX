from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any

import numpy as np
import sounddevice as sd


def _tone_pair(
    sr: int,
    duration: float,
    f1: float,
    f2: float,
    phi: float,
    amp: float,
) -> np.ndarray:
    t = np.arange(int(sr * duration), dtype=np.float64) / sr
    x = amp * np.sin(2.0 * math.pi * f1 * t)
    y = amp * np.sin(2.0 * math.pi * f2 * t + phi)
    sig = x + y

    peak = np.max(np.abs(sig))
    if peak > 0.999:
        sig = sig / peak * 0.999
    return sig.astype(np.float32)


def _rms(x: np.ndarray) -> float:
    if x.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(x))))


def _dominant_peak_info(x: np.ndarray, sr: int) -> dict[str, Any]:
    if x.size < 32:
        return {"coherence": 0.0, "peak_1_hz": 0.0, "peak_2_hz": 0.0}

    x = x.astype(np.float64)
    x = x - np.mean(x)
    win = np.hanning(x.size)
    spec = np.fft.rfft(x * win)
    mag = np.abs(spec)
    freqs = np.fft.rfftfreq(x.size, d=1.0 / sr)

    if mag.size:
        mag[0] = 0.0

    idx = np.argsort(mag)[::-1][:2]
    if len(idx) == 0:
        return {"coherence": 0.0, "peak_1_hz": 0.0, "peak_2_hz": 0.0}

    top = mag[idx]
    denom = float(np.sum(top))
    coherence = float(np.max(top) / denom) if denom > 0 else 0.0

    peak_1 = float(freqs[idx[0]]) if len(idx) >= 1 else 0.0
    peak_2 = float(freqs[idx[1]]) if len(idx) >= 2 else 0.0

    return {
        "coherence": coherence,
        "peak_1_hz": peak_1,
        "peak_2_hz": peak_2,
    }


def _record_only(
    total_seconds: float,
    sr: int,
    input_device: int | None,
    channels: int = 1,
) -> np.ndarray:
    frames = int(sr * total_seconds)
    recorded = sd.rec(
        frames,
        samplerate=sr,
        channels=channels,
        dtype="float32",
        device=input_device,
        blocking=True,
    )
    return recorded[:, 0].copy()


def _play_only(
    signal: np.ndarray,
    sr: int,
    output_device: int | None,
) -> None:
    sd.play(
        signal.reshape(-1, 1),
        samplerate=sr,
        device=output_device,
        blocking=True,
    )
    sd.stop()


def _playrec_duplex(
    signal: np.ndarray,
    sr: int,
    input_device: int | None,
    output_device: int | None,
) -> np.ndarray:
    recorded = sd.playrec(
        signal.reshape(-1, 1),
        samplerate=sr,
        channels=1,
        dtype="float32",
        device=(input_device, output_device),
        blocking=True,
    )
    return recorded[:, 0].copy()


def _record_response(
    stimulus: np.ndarray,
    sr: int,
    pre_silence: float,
    post_silence: float,
    input_device: int | None,
    output_device: int | None,
    mode: str,
    sequential_gap: float,
) -> np.ndarray:
    pre = np.zeros(int(sr * pre_silence), dtype=np.float32)
    post = np.zeros(int(sr * post_silence), dtype=np.float32)
    out = np.concatenate([pre, stimulus, post])

    if mode == "duplex":
        return _playrec_duplex(
            signal=out,
            sr=sr,
            input_device=input_device,
            output_device=output_device,
        )

    total_seconds = pre_silence + len(stimulus) / sr + post_silence + sequential_gap

    rec = sd.InputStream(
        samplerate=sr,
        channels=1,
        dtype="float32",
        device=input_device,
    )
    rec.start()
    try:
        if sequential_gap > 0:
            time.sleep(sequential_gap / 2.0)

        _play_only(
            signal=out,
            sr=sr,
            output_device=output_device,
        )

        if sequential_gap > 0:
            time.sleep(sequential_gap / 2.0)

        available = rec.read(int(sr * total_seconds))[0][:, 0].copy()
    finally:
        rec.stop()
        rec.close()

    return available


def _print_devices() -> None:
    print("\n=== AUDIO DEVICES ===\n")
    for i, d in enumerate(sd.query_devices()):
        print(
            f"{i}: {d['name']} | "
            f"in={d['max_input_channels']} | out={d['max_output_channels']}"
        )


def main() -> None:
    ap = argparse.ArgumentParser(description="Mac acoustic phase-null test")
    ap.add_argument("--sr", type=int, default=48000)
    ap.add_argument("--duration", type=float, default=2.0)
    ap.add_argument("--pre-silence", type=float, default=0.15)
    ap.add_argument("--post-silence", type=float, default=0.15)
    ap.add_argument("--settle-seconds", type=float, default=0.30)
    ap.add_argument("--sequential-gap", type=float, default=0.20)
    ap.add_argument("--f1", type=float, default=440.0)
    ap.add_argument("--f2", type=float, default=440.0)
    ap.add_argument("--amp", type=float, default=0.20)
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--phis", nargs="+", type=float, required=True)
    ap.add_argument("--input-device", type=int, default=None)
    ap.add_argument("--output-device", type=int, default=None)
    ap.add_argument(
        "--mode",
        choices=["sequential", "duplex"],
        default="sequential",
        help="Use sequential play-then-record by default; duplex uses playrec().",
    )
    ap.add_argument(
        "--list-devices",
        action="store_true",
        help="Print audio devices and exit.",
    )
    ap.add_argument(
        "--out",
        type=str,
        default="backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs/mac_acoustic_phi_test.json",
    )
    args = ap.parse_args()

    if args.list_devices:
        _print_devices()
        return

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []

    print("\n=== MAC ACOUSTIC PHASE TEST ===\n")
    print(f"mode={args.mode}")
    print(f"sr={args.sr}")
    print(f"duration={args.duration}")
    print(f"f1={args.f1}")
    print(f"f2={args.f2}")
    print(f"repeats={args.repeats}")
    print(f"input_device={args.input_device}")
    print(f"output_device={args.output_device}")
    print()

    for phi in args.phis:
        phase_runs: list[dict[str, Any]] = []

        for rep in range(args.repeats):
            stim = _tone_pair(
                sr=args.sr,
                duration=args.duration,
                f1=args.f1,
                f2=args.f2,
                phi=phi,
                amp=args.amp,
            )

            rec = _record_response(
                stimulus=stim,
                sr=args.sr,
                pre_silence=args.pre_silence,
                post_silence=args.post_silence,
                input_device=args.input_device,
                output_device=args.output_device,
                mode=args.mode,
                sequential_gap=args.sequential_gap,
            )

            if args.mode == "duplex":
                start = int(args.sr * (args.pre_silence + args.settle_seconds))
                end = int(args.sr * (args.pre_silence + args.duration))
            else:
                start = int(args.sr * (args.sequential_gap + args.pre_silence + args.settle_seconds))
                end = int(args.sr * (args.sequential_gap + args.pre_silence + args.duration))

            start = max(0, min(start, rec.size))
            end = max(start, min(end, rec.size))
            segment = rec[start:end] if end > start else rec

            rms = _rms(segment)
            peaks = _dominant_peak_info(segment, args.sr)

            row = {
                "phi": phi,
                "repeat": rep + 1,
                "rms": rms,
                "coherence": peaks["coherence"],
                "peak_1_hz": peaks["peak_1_hz"],
                "peak_2_hz": peaks["peak_2_hz"],
                "segment_start": start,
                "segment_end": end,
            }
            phase_runs.append(row)

            print(
                f"phi={phi:.12f} rep={rep+1}/{args.repeats} "
                f"| rms={rms:.6f} | coherence={row['coherence']:.6f} "
                f"| peaks=({row['peak_1_hz']:.2f},{row['peak_2_hz']:.2f}) "
                f"| seg=[{start},{end})"
            )

            time.sleep(0.15)

        rms_vals = [r["rms"] for r in phase_runs]
        coh_vals = [r["coherence"] for r in phase_runs]

        summary = {
            "phi": phi,
            "mean_rms": float(np.mean(rms_vals)),
            "std_rms": float(np.std(rms_vals)),
            "mean_coherence": float(np.mean(coh_vals)),
            "std_coherence": float(np.std(coh_vals)),
            "runs": phase_runs,
        }
        results.append(summary)

    results.sort(key=lambda r: r["mean_rms"])
    best = results[0] if results else None

    payload = {
        "protocol": "mac_acoustic_phase_null_test",
        "mode": args.mode,
        "f1": args.f1,
        "f2": args.f2,
        "sr": args.sr,
        "duration": args.duration,
        "repeats": args.repeats,
        "input_device": args.input_device,
        "output_device": args.output_device,
        "results": results,
        "best": best,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("\n--- BEST PHASE ---")
    if best is not None:
        print(
            f"phi={best['phi']:.12f} | mean_rms={best['mean_rms']:.6f} "
            f"| std_rms={best['std_rms']:.6f} | mean_coherence={best['mean_coherence']:.6f}"
        )

    print(f"\nWrote: {out_path}")


if __name__ == "__main__":
    main()