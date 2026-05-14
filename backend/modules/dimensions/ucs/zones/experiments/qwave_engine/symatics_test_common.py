from __future__ import annotations

from typing import List, Tuple
import json
import math
import numpy as np


def load_traces_from_jsonl(path: str) -> List[dict]:
    rows: List[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def row_label(row: dict, idx: int | None = None) -> str:
    if "label" in row and row["label"]:
        return str(row["label"])
    if "candidate_id" in row and row["candidate_id"]:
        return str(row["candidate_id"])

    phi = row.get("phi_hint")
    harmonics = row.get("harmonics") or row.get("harmonic_set") or row.get("harmonic")
    alpha = row.get("alpha")
    nu = row.get("nu")

    parts = []
    if idx is not None:
        parts.append(f"row_{idx + 1:03d}")
    else:
        parts.append("row")

    if phi is not None:
        parts.append(f"phi_{float(phi):.6f}")
    if harmonics is not None:
        if isinstance(harmonics, list):
            hs = "-".join(str(x) for x in harmonics)
        else:
            hs = str(harmonics).replace(",", "-")
        parts.append(f"harm_{hs}")
    if alpha is not None:
        parts.append(f"a_{float(alpha):.3f}")
    if nu is not None:
        parts.append(f"n_{float(nu):.3f}")

    return "_".join(parts)


def row_phi(row: dict) -> float:
    v = row.get("phi_hint")
    return float(v) if v is not None else float("nan")


def get_pickup_trace(row: dict) -> np.ndarray:
    candidates = [
        "pickup_trace",
        "pickup_samples",
        "pickup",
        "trace",
        "samples",
    ]
    for key in candidates:
        value = row.get(key)
        if isinstance(value, list) and value:
            return np.asarray(value, dtype=float)

    return np.asarray([], dtype=float)


def hann_window(x: np.ndarray) -> np.ndarray:
    if x.size == 0:
        return x
    return x * np.hanning(x.size)


def dominant_peaks_fft(x: np.ndarray, k: int = 5) -> List[Tuple[int, float]]:
    if x.size < 16:
        return []

    x = np.asarray(x, dtype=float)
    x = x - float(np.mean(x))
    xw = hann_window(x)

    fft = np.fft.rfft(xw)
    mag = np.abs(fft)
    if mag.size == 0:
        return []

    mag[0] = 0.0
    idx = np.argsort(mag)[::-1]
    peaks = [(int(i), float(mag[i])) for i in idx[:k] if mag[i] > 0]
    return peaks


def analytic_signal(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    n = x.size
    if n == 0:
        return np.asarray([], dtype=complex)

    X = np.fft.fft(x)
    h = np.zeros(n)

    if n % 2 == 0:
        h[0] = 1.0
        h[n // 2] = 1.0
        h[1:n // 2] = 2.0
    else:
        h[0] = 1.0
        h[1:(n + 1) // 2] = 2.0

    return np.fft.ifft(X * h)


def instantaneous_phase(x: np.ndarray) -> np.ndarray:
    if x.size == 0:
        return np.asarray([], dtype=float)
    z = analytic_signal(x)
    return np.unwrap(np.angle(z))


def phase_coherence(x: np.ndarray) -> float:
    if x.size < 8:
        return 0.0

    phase = instantaneous_phase(x)
    dphi = np.diff(phase)
    if dphi.size == 0:
        return 0.0

    return float(np.abs(np.mean(np.exp(1j * dphi))))


def phase_rate(x: np.ndarray) -> float:
    if x.size < 8:
        return 0.0

    phase = instantaneous_phase(x)
    dphi = np.diff(phase)
    if dphi.size == 0:
        return 0.0

    return float(np.mean(np.abs(dphi)))


def mean_energy(x: np.ndarray) -> float:
    if x.size == 0:
        return 0.0
    return float(np.mean(np.square(x)))


def trace_drift(x: np.ndarray) -> float:
    if x.size < 8:
        return 0.0

    q = max(1, x.size // 4)
    first = float(np.mean(x[:q]))
    last = float(np.mean(x[-q:]))
    return abs(last - first)


def boundedness_score(x: np.ndarray) -> float:
    if x.size < 8:
        return 0.0

    rms = math.sqrt(mean_energy(x))
    if rms <= 1e-12:
        return 0.0

    return float(np.std(x) / rms)


def safe_mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return float(np.mean(np.asarray(values, dtype=float)))


def safe_std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    return float(np.std(np.asarray(values, dtype=float)))