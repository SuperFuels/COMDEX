from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

from symatics_test_common import load_traces_from_jsonl, get_pickup_trace


def latest_capture_path() -> str:
    base = Path(
        "backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs"
    )
    files = sorted(base.glob("symatics_capture_sweep_*.jsonl"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise FileNotFoundError(f"No capture files found in {base}")
    return str(files[-1])


def safe_float(x: Any, default: float = 0.0) -> float:
    try:
        y = float(x)
        if math.isfinite(y):
            return y
    except Exception:
        pass
    return default


def row_phi(row: Dict[str, Any]) -> float:
    return safe_float(row.get("phi_hint", 0.0))


def row_alpha(row: Dict[str, Any]) -> float:
    for key in ("alpha", "alpha_hint", "drive_alpha"):
        if key in row:
            return safe_float(row.get(key, 0.0))
    return 0.0


def row_nu(row: Dict[str, Any]) -> float:
    for key in ("nu", "nu_hint", "drive_nu"):
        if key in row:
            return safe_float(row.get(key, 0.0))
    return 0.0


def row_label(row: Dict[str, Any], idx: int) -> str:
    return f"row_{idx:03d}_phi_{row_phi(row):.6f}"


def row_harmonics(row: Dict[str, Any]) -> str:
    for key in ("harmonics", "harmonic_family", "harmonic_label", "harmonic_spec", "harmonic_set"):
        v = row.get(key)
        if v is not None:
            if isinstance(v, (list, tuple)):
                return "-".join(str(int(x)) for x in v)
            s = str(v).strip()
            if s:
                return s.replace(",", "-")
    return "unknown"


def pickup_mean(row: Dict[str, Any], trace: np.ndarray) -> float:
    if "pickup_mean" in row:
        return safe_float(row["pickup_mean"])
    if trace.size == 0:
        return 0.0
    return float(np.mean(np.abs(trace)))


def energy_proxy(row: Dict[str, Any], trace: np.ndarray) -> float:
    if "energy_proxy" in row:
        return safe_float(row["energy_proxy"])
    if trace.size == 0:
        return 0.0
    return float(np.mean(trace * trace))


def drift_value(row: Dict[str, Any], trace: np.ndarray) -> float:
    if "drift" in row:
        return safe_float(row["drift"])
    if trace.size < 8:
        return float("inf")
    n = max(4, trace.size // 16)
    head = float(np.mean(trace[:n]))
    tail = float(np.mean(trace[-n:]))
    return abs(tail - head)


def boundedness_value(trace: np.ndarray) -> float:
    if trace.size == 0:
        return float("inf")
    rms = float(np.sqrt(np.mean(trace * trace)))
    if rms <= 1e-12:
        return float("inf")
    return float(np.max(np.abs(trace)) / rms)


def fft_metrics(trace: np.ndarray) -> Tuple[List[Tuple[int, float]], float, float]:
    if trace.size < 16:
        return [], 0.0, 0.0

    x = trace - np.mean(trace)
    x = x * np.hanning(trace.size)

    spec = np.fft.rfft(x)
    mag = np.abs(spec)

    if mag.size <= 2:
        return [], 0.0, 0.0

    mag[0] = 0.0
    idx = np.argsort(mag)[::-1]
    peaks = [(int(i), float(mag[i])) for i in idx[:8] if mag[i] > 0.0]

    total = float(np.sum(mag))
    if not peaks or total <= 1e-12:
        return peaks, 0.0, 0.0

    concentration = peaks[0][1] / total

    local_band = 0.0
    for p_idx, p_mag in peaks[:4]:
        if abs(p_idx - peaks[0][0]) <= 1:
            local_band += p_mag
    local_band_ratio = local_band / total

    return peaks, float(concentration), float(local_band_ratio)


def resonance_coherence(trace: np.ndarray) -> Tuple[float, List[Tuple[int, float]], float, float]:
    peaks, concentration, local_band_ratio = fft_metrics(trace)
    if len(peaks) < 2:
        return 0.0, peaks, concentration, local_band_ratio
    coherence = 0.35 * concentration + 0.65 * local_band_ratio
    coherence = max(0.0, min(1.0, coherence * 1.5))
    return float(coherence), peaks, concentration, local_band_ratio


def level_spacing(values: List[float]) -> Tuple[List[float], float, float]:
    vals = sorted(values)
    if len(vals) < 2:
        return [], 0.0, 0.0
    diffs = [vals[i + 1] - vals[i] for i in range(len(vals) - 1)]
    mean_diff = float(np.mean(diffs))
    std_diff = float(np.std(diffs))
    return diffs, mean_diff, std_diff


def cluster_plateaus(values: List[float], tol: float) -> List[List[float]]:
    vals = sorted(values)
    if not vals:
        return []
    groups: List[List[float]] = [[vals[0]]]
    for v in vals[1:]:
        if abs(v - groups[-1][-1]) <= tol:
            groups[-1].append(v)
        else:
            groups.append([v])
    return groups


def run(
    path: str,
    max_drift: float,
    min_coherence: float,
    max_boundedness: float,
    plateau_tol: float,
    min_plateau_size: int,
) -> None:
    rows = load_traces_from_jsonl(path)

    print("\n=== H EXPERIMENT ===\n")
    print("protocol: quantized plateau / level-spacing search on locked resonance surface")
    print(f"capture: {path}")
    print(f"tested rows: {len(rows)}")

    accepted: List[Dict[str, Any]] = []

    for idx, row in enumerate(rows, start=1):
        trace = get_pickup_trace(row)
        if trace.size < 16:
            continue

        pickup = pickup_mean(row, trace)
        energy = energy_proxy(row, trace)
        drift = drift_value(row, trace)
        boundedness = boundedness_value(trace)
        res_coh, peaks, conc, local_band = resonance_coherence(trace)

        if drift > max_drift or res_coh < min_coherence or boundedness > max_boundedness:
            continue

        accepted.append(
            {
                "label": row_label(row, idx),
                "phi": row_phi(row),
                "alpha": row_alpha(row),
                "nu": row_nu(row),
                "harm": row_harmonics(row),
                "pickup": pickup,
                "energy": energy,
                "drift": drift,
                "bound": boundedness,
                "res_coh": res_coh,
                "conc": conc,
                "local_band": local_band,
                "peak_1": peaks[0][0] if len(peaks) > 0 else -1,
                "peak_2": peaks[1][0] if len(peaks) > 1 else -1,
            }
        )

    print(f"accepted rows: {len(accepted)}")

    if not accepted:
        print("\nNo rows passed locked-surface filters.")
        return

    by_family: Dict[str, List[Dict[str, Any]]] = {}
    for item in accepted:
        by_family.setdefault(item["harm"], []).append(item)

    print("\n--- FAMILY LEVEL-SPACING SUMMARY ---\n")

    any_plateau = False

    for family, items in sorted(by_family.items()):
        pickups = [x["pickup"] for x in items]
        energies = [x["energy"] for x in items]
        coherences = [x["res_coh"] for x in items]

        p_diffs, p_mean, p_std = level_spacing(pickups)
        e_diffs, e_mean, e_std = level_spacing(energies)
        c_diffs, c_mean, c_std = level_spacing(coherences)

        pickup_plateaus = cluster_plateaus(pickups, plateau_tol)
        energy_plateaus = cluster_plateaus(energies, plateau_tol)
        coh_plateaus = cluster_plateaus(coherences, plateau_tol)

        strong_pickup = [g for g in pickup_plateaus if len(g) >= min_plateau_size]
        strong_energy = [g for g in energy_plateaus if len(g) >= min_plateau_size]
        strong_coh = [g for g in coh_plateaus if len(g) >= min_plateau_size]

        if strong_pickup or strong_energy or strong_coh:
            any_plateau = True

        print(
            f"harm={family} | count={len(items)} "
            f"| pickup_spacing_mean={p_mean:.9f} | pickup_spacing_std={p_std:.9f} "
            f"| energy_spacing_mean={e_mean:.9f} | energy_spacing_std={e_std:.9f} "
            f"| coh_spacing_mean={c_mean:.9f} | coh_spacing_std={c_std:.9f}"
        )

        if strong_pickup:
            print("  pickup plateaus:")
            for g in strong_pickup:
                print(
                    f"    size={len(g)} | min={min(g):.9f} | max={max(g):.9f} | center={float(np.mean(g)):.9f}"
                )

        if strong_energy:
            print("  energy plateaus:")
            for g in strong_energy:
                print(
                    f"    size={len(g)} | min={min(g):.9f} | max={max(g):.9f} | center={float(np.mean(g)):.9f}"
                )

        if strong_coh:
            print("  coherence plateaus:")
            for g in strong_coh:
                print(
                    f"    size={len(g)} | min={min(g):.9f} | max={max(g):.9f} | center={float(np.mean(g)):.9f}"
                )

    if not any_plateau:
        print("\nNo strong plateaus detected under current tolerance.")
        print("Interpretation: the surface is ordered, but not yet quantized enough to claim h-like spacing.")
        return

    print("\nInterpretation: candidate plateau structure exists. Next step is denser alpha sweeps within winning families.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=None, help="Path to capture jsonl. Defaults to latest.")
    ap.add_argument("--max-drift", type=float, default=0.02)
    ap.add_argument("--min-coherence", type=float, default=0.26)
    ap.add_argument("--max-boundedness", type=float, default=1.25)
    ap.add_argument("--plateau-tol", type=float, default=5e-4)
    ap.add_argument("--min-plateau-size", type=int, default=3)
    args = ap.parse_args()

    run(
        path=args.input or latest_capture_path(),
        max_drift=args.max_drift,
        min_coherence=args.min_coherence,
        max_boundedness=args.max_boundedness,
        plateau_tol=args.plateau_tol,
        min_plateau_size=args.min_plateau_size,
    )