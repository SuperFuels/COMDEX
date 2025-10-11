import numpy as np

def compute_visibility(intensity_1d):
    Imax = np.max(intensity_1d)
    Imin = np.min(intensity_1d)
    return (Imax - Imin) / (Imax + Imin + 1e-12)

def project_with_pi(frame_stack, pi_spatial=1, pi_temporal=1):
    """
    Symatics π projection — spatial & temporal coherence collapse.
    """
    arr = np.asarray(frame_stack, dtype=float)
    if arr.ndim == 2:
        arr = arr[None, :, :]

    # Temporal coherence projection
    if pi_temporal > 1:
        T = arr.shape[0]
        k = T // pi_temporal
        arr = arr[:k * pi_temporal]
        arr = arr.reshape(k, pi_temporal, *arr.shape[1:]).mean(axis=1)

    field = arr.mean(axis=0)

    # Spatial coherence projection — low-pass in Fourier domain
    if pi_spatial > 1:
        H, W = field.shape
        fy, fx = np.fft.fftfreq(H), np.fft.fftfreq(W)
        FX, FY = np.meshgrid(fx, fy)
        radius = np.sqrt(FX**2 + FY**2)

        # π cutoff (smaller = stronger filtering)
        cutoff = 0.03 / (pi_spatial ** 1.4)
        mask = np.exp(-((radius / cutoff) ** 6))
        F = np.fft.fft2(field)
        field = np.real(np.fft.ifft2(F * mask))

    field -= field.min()
    field /= field.max() + 1e-12
    return field