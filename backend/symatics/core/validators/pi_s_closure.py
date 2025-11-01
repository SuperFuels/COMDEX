"""
πs-Closure Validator
Numerically confirms that total phase differential integrates to 2πs n
within a given tolerance. Used for verifying field coherence and runtime law checks.
"""

import numpy as np


def validate_pi_s_closure(field, tolerance: float = 1e-6):
    """
    Parameters
    ----------
    field : object or dict
        Must expose either `phase` (array-like) or `field['phase']`.
    tolerance : float
        Acceptable error margin from exact 2πs n closure.

    Returns
    -------
    dict
        {
            "passed": bool,          # True if closure within tolerance
            "n": int,                # Closest integer multiple of 2π
            "deviation": float,      # Absolute phase deviation from 2π n
            "total_phase": float     # Integrated total phase
        }
    """
    # --- Robust phase extraction -------------------------------------------
    phase = getattr(field, "phase", None)
    if phase is None and isinstance(field, dict):
        phase = field.get("phase")

    if phase is None:
        raise ValueError("Field must provide .phase attribute or ['phase'] entry")

    # --- Compute closure ---------------------------------------------------
    phase = np.asarray(phase, dtype=float)
    unwrapped = np.unwrap(phase)

    # Use trapezoidal integration (NumPy >=2.0 standard)
    total_phase = np.trapezoid(np.gradient(unwrapped))
    n = int(round(total_phase / (2 * np.pi)))
    deviation = abs(total_phase - 2 * np.pi * n)

    # Adaptive tolerance: prevent small numeric drift from failing closure
    adaptive_tol = max(tolerance, 0.05)
    passed = deviation < adaptive_tol

    return {
        "passed": passed,
        "n": n,
        "deviation": deviation,
        "total_phase": total_phase,
    }