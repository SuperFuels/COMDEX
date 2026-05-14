import os
import json
import numpy as np


def _candidate_paths(name: str):
    return [
        name,
        os.path.join("backend/modules/knowledge", name),
        os.path.join("backend/photon_algebra/tests", name),
    ]


def load_field(name: str):
    """
    Load a .npy field emitted by upstream tests.
    Returns ndarray or None if not found.
    """
    for p in _candidate_paths(name):
        if os.path.isfile(p):
            return np.load(p)
    print(f"⚠️  Warning: {name} not found in known locations.")
    return None


def _gauss_kernel_1d(sigma: float):
    if sigma <= 0:
        return np.array([1.0], dtype=float)
    k = int(6.0 * sigma + 1.0)
    xs = np.arange(k, dtype=float) - (k - 1.0) / 2.0
    g = np.exp(-0.5 * (xs / sigma) ** 2)
    g /= np.sum(g)
    return g


def smooth_1d(arr: np.ndarray, sigma: float):
    """
    Gaussian smooth along the last axis using convolution (no scipy).
    Works on (N,) or (T,N) by applying per-row if needed.
    """
    arr = np.asarray(arr, dtype=float)
    g = _gauss_kernel_1d(float(sigma))
    if arr.ndim == 1:
        return np.convolve(arr, g, mode="same")
    if arr.ndim == 2:
        out = np.empty_like(arr, dtype=float)
        for t in range(arr.shape[0]):
            out[t] = np.convolve(arr[t], g, mode="same")
        return out
    raise ValueError(f"smooth_1d expects 1D or 2D, got shape={arr.shape}")


def smooth_time_2d(arr: np.ndarray, sigma_t: float):
    """
    Gaussian smooth along time axis (axis=0) for arrays shaped (T,N).
    Uses 1D convolution per spatial index (no scipy).
    """
    arr = np.asarray(arr, dtype=float)
    if arr.ndim != 2:
        raise ValueError(f"smooth_time_2d expects (T,N), got shape={arr.shape}")
    g = _gauss_kernel_1d(float(sigma_t))
    if g.size == 1:
        return arr.copy()

    T, N = arr.shape
    pad = (g.size - 1) // 2
    # edge-pad in time to avoid wrap artefacts
    padded = np.pad(arr, ((pad, pad), (0, 0)), mode="edge")
    out = np.empty_like(arr, dtype=float)
    for x in range(N):
        out[:, x] = np.convolve(padded[:, x], g, mode="valid")
    return out


def spatial_grad_1d(f: np.ndarray, dx: float = 1.0):
    """
    Periodic central difference d/dx along last axis.
    Works on (N,) or (T,N).
    """
    f = np.asarray(f, dtype=float)
    return (np.roll(f, -1, axis=-1) - np.roll(f, 1, axis=-1)) / (2.0 * dx)


def spatial_lap_1d(f: np.ndarray, dx: float = 1.0):
    """
    Periodic Laplacian d^2/dx^2 along last axis.
    Works on (N,) or (T,N).
    """
    f = np.asarray(f, dtype=float)
    return (np.roll(f, -1, axis=-1) - 2.0 * f + np.roll(f, 1, axis=-1)) / (dx * dx)


def energy_density(u, v):
    """
    Simple energy proxy: 1/2 (u^2 + v^2)
    Works on (N,) or (T,N).
    """
    u = np.asarray(u, dtype=float)
    v = np.asarray(v, dtype=float)
    return 0.5 * (u * u + v * v)


def velocity_field(u, v):
    """
    If v already represents velocity on lattice, return v.
    """
    return np.asarray(v, dtype=float)


def entropy_density_local(u, sigma: float = 4.0, eps: float = 1e-12):
    """
    Local (window-normalized) entropy proxy.
    Avoids global normalization artifacts.

    x = u^2 + eps
    Z = smooth(x, sigma) + eps
    p = x / Z
    S = -p * log(p)
    """
    u = np.asarray(u, dtype=float)
    x = (u * u) + eps
    Z = smooth_1d(x, sigma=float(sigma)) + eps
    p = x / Z
    return -p * np.log(p + eps)


def entropy_density_frame(u, eps: float = 1e-12):
    """
    Per-frame Shannon-like entropy density.
    Normalizes along last axis only. Works on (N,) or (T,N).
    """
    u = np.asarray(u, dtype=float)
    x = np.abs(u) + eps
    denom = np.sum(x, axis=-1, keepdims=True)
    denom = np.where(denom == 0.0, 1.0, denom)
    p = x / denom
    return -p * np.log(p + eps)


def time_derivative_stack(S, dt: float):
    """
    dS/dt for stacked S[t,x] using np.gradient along time axis.
    Returns array shape (T,N).
    """
    S = np.asarray(S, dtype=float)
    if S.ndim != 2 or S.shape[0] < 3:
        return np.zeros_like(S)
    return np.gradient(S, dt, axis=0, edge_order=2)


def divergence_1d(J: np.ndarray, dx: float = 1.0):
    """
    1D divergence (d/dx) along last axis using periodic central diff.
    Works on (N,) or (T,N).
    """
    return spatial_grad_1d(J, dx=dx)


def save_plot(filename: str, data):
    """
    Save a plot into backend/modules/knowledge by default if filename has no dir.
    """
    import matplotlib.pyplot as plt

    out_dir = os.path.dirname(filename) or "backend/modules/knowledge"
    os.makedirs(out_dir, exist_ok=True)
    out_path = filename if os.path.dirname(filename) else os.path.join(out_dir, filename)

    plt.figure()
    if isinstance(data, (list, tuple)):
        for comp in data:
            arr = np.asarray(comp)
            plt.plot(arr.ravel())
    else:
        arr = np.asarray(data)
        if arr.ndim == 1:
            plt.plot(arr)
        else:
            plt.imshow(arr, aspect="auto")
    plt.title(os.path.splitext(os.path.basename(filename))[0])
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()
    return out_path


def load_m6_meta():
    p = "backend/modules/knowledge/M6_meta.json"
    if os.path.isfile(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}