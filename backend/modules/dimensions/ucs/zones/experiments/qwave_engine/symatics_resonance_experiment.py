from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

from symatics_test_common import load_traces_from_jsonl, get_pickup_trace


def latest_capture_path() -> str:
    base = Path(
        "backend/modules/dimensions/ucs/zones/experiments/qwave_engine/outputs"
    )
    files = sorted(
        base.glob("symatics_capture_sweep_*.jsonl"),
        key=lambda p: p.stat().st_mtime,
    )
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


def safe_int(x: Any, default: int = 0) -> int:
    try:
        if isinstance(x, bool):
            return default
        return int(x)
    except Exception:
        return default


def row_phi(row: Dict[str, Any]) -> float:
    for key in ("phi_hint", "phi", "phi_value"):
        if key in row:
            return safe_float(row.get(key, 0.0))
    return 0.0


def row_label(row: Dict[str, Any], idx: int) -> str:
    phi = row_phi(row)
    return f"row_{idx:03d}_phi_{phi:.6f}"


def _extract_harmonic_tokens(text: str) -> List[int]:
    s = text.strip()
    if not s:
        return []

    matches: List[int] = []

    for pat in (
        r"\bharm(?:onic)?(?:_family|_label|_set|_spec)?[_:= -]*([0-9]+(?:[-,][0-9]+)*)\b",
        r"\bh[_:= -]*([0-9]+(?:[-,][0-9]+)*)\b",
    ):
        m = re.search(pat, s, flags=re.IGNORECASE)
        if m:
            chunk = m.group(1)
            for part in re.split(r"[-,]", chunk):
                part = part.strip()
                if part.isdigit():
                    matches.append(int(part))
            if matches:
                return matches

    # fallback: pull all standalone integers if string is simple enough
    ints = re.findall(r"\d+", s)
    if ints and len(ints) <= 4:
        return [int(x) for x in ints]

    return []


def row_harmonics(row: Dict[str, Any]) -> str:
    # direct structured keys first
    for key in (
        "harmonics",
        "harmonic_family",
        "harmonic_label",
        "harmonic_spec",
        "harmonic_set",
        "harmonic",
    ):
        v = row.get(key)
        if v is None:
            continue

        if isinstance(v, (list, tuple)):
            vals = [safe_int(x, -1) for x in v]
            vals = [x for x in vals if x > 0]
            if vals:
                return "-".join(str(x) for x in vals)

        if isinstance(v, (int, float)) and not isinstance(v, bool):
            iv = safe_int(v, -1)
            if iv > 0:
                return str(iv)

        s = str(v).strip()
        if s:
            parsed = _extract_harmonic_tokens(s)
            if parsed:
                return "-".join(str(x) for x in parsed)
            return s.replace(",", "-").replace(" ", "")

    # try to recover from candidate/name/label fields
    for key in ("candidate", "candidate_id", "name", "label", "id"):
        v = row.get(key)
        if v is None:
            continue
        parsed = _extract_harmonic_tokens(str(v))
        if parsed:
            return "-".join(str(x) for x in parsed)

    # strong fallback for row names like cand_004_phi_..._harm_4_a_...
    for value in row.values():
        if not isinstance(value, str):
            continue
        m = re.search(r"(?:^|[_ -])harm[_ -]?(\d+)(?:[_ -]|$)", value, flags=re.IGNORECASE)
        if m:
            return str(int(m.group(1)))

    return "unknown"


def pickup_mean(row: Dict[str, Any], trace: np.ndarray) -> float:
    if "pickup_mean" in row:
        return safe_float(row["pickup_mean"])
    if "pickup" in row:
        return safe_float(row["pickup"])
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


def fft_metrics(trace: np.ndarray) -> Tuple[List[Tuple[int, float]], float, float, int]:
    if trace.size < 16:
        return [], 0.0, 0.0, 999999

    x = trace - np.mean(trace)
    x = x * np.hanning(trace.size)

    spec = np.fft.rfft(x)
    mag = np.abs(spec)

    if mag.size <= 2:
        return [], 0.0, 0.0, 999999

    mag[0] = 0.0
    idx = np.argsort(mag)[::-1]
    peaks = [(int(i), float(mag[i])) for i in idx[:8] if mag[i] > 0.0]

    total = float(np.sum(mag))
    if len(peaks) < 2 or total <= 1e-12:
        return peaks, 0.0, 0.0, 999999

    top1 = peaks[0][1]
    spectral_concentration = top1 / total
    neighbor_gap = abs(peaks[1][0] - peaks[0][0])

    local_band = 0.0
    for p_idx, p_mag in peaks[:4]:
        if abs(p_idx - peaks[0][0]) <= 1:
            local_band += p_mag
    local_band_ratio = local_band / total if total > 1e-12 else 0.0

    return peaks, float(spectral_concentration), float(local_band_ratio), int(neighbor_gap)


def resonance_coherence(
    trace: np.ndarray,
) -> Tuple[float, List[Tuple[int, float]], float, float, int]:
    peaks, concentration, local_band_ratio, neighbor_gap = fft_metrics(trace)
    if len(peaks) < 2:
        return 0.0, peaks, concentration, local_band_ratio, neighbor_gap

    gap_term = 1.0 / (1.0 + 0.25 * max(0, neighbor_gap - 1))

    # calibrated to your current spectral regime where adjacent-bin locks are real
    # and useful, but should not be inflated to baseline coherence ~= 0.99
    coherence = 0.35 * concentration + 0.65 * local_band_ratio * gap_term
    coherence = max(0.0, min(1.0, coherence * 1.5))

    return float(coherence), peaks, concentration, local_band_ratio, neighbor_gap


def pickup_stability(items: List[Dict[str, Any]]) -> float:
    if len(items) <= 1:
        return 0.5
    vals = np.array([x["pickup"] for x in items], dtype=float)
    mean = float(np.mean(vals))
    std = float(np.std(vals))
    if mean <= 1e-12:
        return 0.0
    cv = std / mean
    return float(1.0 / (1.0 + 10.0 * cv))


def energy_stability(items: List[Dict[str, Any]]) -> float:
    if len(items) <= 1:
        return 0.5
    vals = np.array([x["energy"] for x in items], dtype=float)
    mean = float(np.mean(vals))
    std = float(np.std(vals))
    if mean <= 1e-12:
        return 0.0
    cv = std / mean
    return float(1.0 / (1.0 + 10.0 * cv))


def local_consistency(
    accepted_sorted: List[Dict[str, Any]],
    idx: int,
    phi_window: float,
) -> float:
    target = accepted_sorted[idx]
    target_phi = target["phi"]
    target_harm = target["harmonics"]
    target_peaks = tuple(x[0] for x in target["peaks"][:2])

    same_peak = 0
    near_count = 0
    pickup_vals: List[float] = []
    energy_vals: List[float] = []

    for item in accepted_sorted:
        if item["harmonics"] != target_harm:
            continue
        if abs(item["phi"] - target_phi) <= phi_window:
            near_count += 1
            pickup_vals.append(item["pickup"])
            energy_vals.append(item["energy"])
            item_peaks = tuple(x[0] for x in item["peaks"][:2])
            if item_peaks == target_peaks:
                same_peak += 1

    if near_count == 0:
        return 0.0

    peak_persistence = same_peak / near_count
    tmp_items = [{"pickup": x, "energy": y} for x, y in zip(pickup_vals, energy_vals)]
    p_stab = pickup_stability(tmp_items)
    e_stab = energy_stability(tmp_items)

    return float(0.5 * peak_persistence + 0.25 * p_stab + 0.25 * e_stab)


def family_normalized_pickup(pickup: float, family_items: List[Dict[str, Any]]) -> float:
    vals = np.array([x["pickup"] for x in family_items], dtype=float)
    denom = float(np.max(vals))
    if denom <= 1e-12:
        return 0.0
    return float(pickup / denom)


def family_normalized_energy(energy: float, family_items: List[Dict[str, Any]]) -> float:
    vals = np.array([x["energy"] for x in family_items], dtype=float)
    denom = float(np.max(vals))
    if denom <= 1e-12:
        return 0.0
    return float(energy / denom)


def resonance_score(
    pickup_norm: float,
    resonance_coh: float,
    drift: float,
    boundedness: float,
    local_band_ratio: float,
    neighbor_gap: int,
    local_consistency_score: float,
) -> float:
    drift_term = 1.0 / (1.0 + 50.0 * max(drift, 0.0))
    bound_term = 1.0 / (1.0 + max(0.0, boundedness - 1.0))
    gap_term = 1.0 / (1.0 + 0.25 * max(0, neighbor_gap - 1))

    return float(
        pickup_norm
        * drift_term
        * bound_term
        * (0.35 + 0.65 * resonance_coh)
        * (0.40 + 0.60 * local_band_ratio)
        * gap_term
        * (0.35 + 0.65 * local_consistency_score)
    )


def run(
    path: str,
    max_drift: float,
    min_coherence: float,
    max_boundedness: float,
    max_peak_gap: int,
    top_k: int,
    phi_window: float,
    debug_limit: int,
) -> None:
    rows = load_traces_from_jsonl(path)

    print("\n=== RESONANCE EXPERIMENT ===\n")
    print("protocol: drive-response / lock-band / spectral dominance search")
    print(f"capture: {path}")
    print(f"tested rows: {len(rows)}")

    accepted: List[Dict[str, Any]] = []
    families: Dict[str, List[Dict[str, Any]]] = {}
    debug_shown = 0

    for idx, row in enumerate(rows, start=1):
        trace = get_pickup_trace(row)
        if trace.size < 16:
            continue

        pickup = pickup_mean(row, trace)
        energy = energy_proxy(row, trace)
        drift = drift_value(row, trace)
        boundedness = boundedness_value(trace)
        res_coh, peaks, concentration, local_band_ratio, neighbor_gap = resonance_coherence(trace)
        harmonics = row_harmonics(row)

        if debug_shown < debug_limit:
            print(
                f"DEBUG {row_label(row, idx)} | harm={harmonics} "
                f"| res_coh={res_coh:.6f} | conc={concentration:.6f} "
                f"| local_band={local_band_ratio:.6f} | gap={neighbor_gap} "
                f"| drift={drift:.6f} | bound={boundedness:.6f}"
            )
            debug_shown += 1

        if (
            drift > max_drift
            or res_coh < min_coherence
            or boundedness > max_boundedness
            or neighbor_gap > max_peak_gap
        ):
            continue

        item = {
            "label": row_label(row, idx),
            "phi": row_phi(row),
            "harmonics": harmonics,
            "pickup": pickup,
            "energy": energy,
            "drift": drift,
            "boundedness": boundedness,
            "res_coh": res_coh,
            "spectral_concentration": concentration,
            "local_band_ratio": local_band_ratio,
            "neighbor_gap": neighbor_gap,
            "peaks": peaks[:2],
        }

        accepted.append(item)
        families.setdefault(harmonics, []).append(item)

    print(f"filtered rows: {len(accepted)}")

    if not accepted:
        print("\nNo rows passed filters.")
        return

    # sort by family then phi for local-consistency pass
    accepted.sort(key=lambda r: (r["harmonics"], r["phi"], -r["pickup"]))

    for i, item in enumerate(accepted):
        family_items = families[item["harmonics"]]

        item["pickup_norm_family"] = family_normalized_pickup(item["pickup"], family_items)
        item["energy_norm_family"] = family_normalized_energy(item["energy"], family_items)
        item["local_consistency"] = local_consistency(
            accepted_sorted=accepted,
            idx=i,
            phi_window=phi_window,
        )
        item["score"] = resonance_score(
            pickup_norm=item["pickup_norm_family"],
            resonance_coh=item["res_coh"],
            drift=item["drift"],
            boundedness=item["boundedness"],
            local_band_ratio=item["local_band_ratio"],
            neighbor_gap=item["neighbor_gap"],
            local_consistency_score=item["local_consistency"],
        )

    accepted.sort(key=lambda r: r["score"], reverse=True)

    print("\n--- TOP RESONANCE CANDIDATES ---\n")
    for item in accepted[:top_k]:
        p1 = item["peaks"][0][0] if len(item["peaks"]) > 0 else -1
        p2 = item["peaks"][1][0] if len(item["peaks"]) > 1 else -1
        print(
            f"{item['label']} | phi={item['phi']:.9f} | harm={item['harmonics']} "
            f"| score={item['score']:.6f} | pickup={item['pickup']:.6f} "
            f"| pickup_norm={item['pickup_norm_family']:.6f} "
            f"| res_coh={item['res_coh']:.6f} | local_band={item['local_band_ratio']:.6f} "
            f"| local_consistency={item['local_consistency']:.6f} "
            f"| peak_gap={item['neighbor_gap']} | drift={item['drift']:.6f} "
            f"| bound={item['boundedness']:.6f} | peaks=({p1},{p2})"
        )

    print("\n--- FAMILY SUMMARY ---\n")
    family_rows: List[Tuple[str, float, float, float, float, float, float, int]] = []
    for family, items in families.items():
        scores = [x["score"] for x in items]
        coherences = [x["res_coh"] for x in items]
        bands = [x["local_band_ratio"] for x in items]
        gaps = [x["neighbor_gap"] for x in items]
        lcs = [x["local_consistency"] for x in items]
        pickups = [x["pickup"] for x in items]

        family_rows.append(
            (
                family,
                float(np.mean(scores)),
                float(np.mean(coherences)),
                float(np.mean(bands)),
                float(np.mean(gaps)),
                float(np.mean(lcs)),
                float(np.mean(pickups)),
                len(items),
            )
        )
    family_rows.sort(key=lambda t: t[1], reverse=True)

    for family, mean_score, mean_coh, mean_band, mean_gap, mean_lc, mean_pickup, count in family_rows:
        print(
            f"harm={family} | count={count} | mean_score={mean_score:.6f} "
            f"| mean_res_coh={mean_coh:.6f} | mean_local_band={mean_band:.6f} "
            f"| mean_peak_gap={mean_gap:.3f} | mean_local_consistency={mean_lc:.6f} "
            f"| mean_pickup={mean_pickup:.6f}"
        )

    print("\n--- BEST PER FAMILY ---\n")
    for family, items in sorted(families.items(), key=lambda kv: kv[0]):
        best_family = max(items, key=lambda x: x["score"])
        p1 = best_family["peaks"][0][0] if len(best_family["peaks"]) > 0 else -1
        p2 = best_family["peaks"][1][0] if len(best_family["peaks"]) > 1 else -1
        print(
            f"harm={family} | {best_family['label']} | phi={best_family['phi']:.9f} "
            f"| score={best_family['score']:.6f} | pickup={best_family['pickup']:.6f} "
            f"| pickup_norm={best_family['pickup_norm_family']:.6f} "
            f"| res_coh={best_family['res_coh']:.6f} | peaks=({p1},{p2}) "
            f"| drift={best_family['drift']:.6f} | bound={best_family['boundedness']:.6f}"
        )

    best = accepted[0]
    print("\n--- BEST LOCKED RESPONSE ---")
    print(
        f"{best['label']} | phi={best['phi']:.9f} | harm={best['harmonics']} "
        f"| score={best['score']:.6f} | pickup={best['pickup']:.6f} "
        f"| pickup_norm={best['pickup_norm_family']:.6f} "
        f"| res_coh={best['res_coh']:.6f} | local_band={best['local_band_ratio']:.6f} "
        f"| local_consistency={best['local_consistency']:.6f} "
        f"| peak_gap={best['neighbor_gap']} | drift={best['drift']:.6f} "
        f"| bound={best['boundedness']:.6f}"
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=None, help="Path to capture jsonl. Defaults to latest.")
    ap.add_argument("--max-drift", type=float, default=0.02)
    ap.add_argument("--min-coherence", type=float, default=0.30)
    ap.add_argument("--max-boundedness", type=float, default=1.25)
    ap.add_argument("--max-peak-gap", type=int, default=2)
    ap.add_argument("--top-k", type=int, default=12)
    ap.add_argument("--phi-window", type=float, default=1.5e-7)
    ap.add_argument("--debug-limit", type=int, default=5)
    args = ap.parse_args()

    run(
        path=args.input or latest_capture_path(),
        max_drift=args.max_drift,
        min_coherence=args.min_coherence,
        max_boundedness=args.max_boundedness,
        max_peak_gap=args.max_peak_gap,
        top_k=args.top_k,
        phi_window=args.phi_window,
        debug_limit=args.debug_limit,
    )