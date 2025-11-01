"""
───────────────────────────────────────────────
Tessaris Symatics SDK v2.2
Test Suite: Experimental Interface Layer
───────────────────────────────────────────────
Covers:
    * sym_io_photonics.py
    * sym_io_qubit.py
───────────────────────────────────────────────
"""

import numpy as np
from pathlib import Path
import tempfile
import json

from backend.symatics.sym_io_photonics import SymIOPhotonics
from backend.symatics.sym_io_qubit import SymIOQubit


def test_photonics_trace_generation_and_validation(tmp_path):
    """Validate photonics trace generation, export/import, and roundtrip integrity."""
    freq = np.linspace(1e14, 3e14, 100)
    R = np.linspace(0.01, 0.1, 100)

    # Generate trace and validate
    trace = SymIOPhotonics.generate_trace(freq, R)
    assert SymIOPhotonics.validate_trace(trace, tol=0.05)

    # Export -> Import -> Revalidate
    json_path = tmp_path / "trace.json"
    SymIOPhotonics.export_trace(trace, json_path)
    trace_loaded = SymIOPhotonics.import_trace(json_path)
    assert SymIOPhotonics.validate_trace(trace_loaded, tol=0.05)


def test_qubit_trace_validation():
    """Validate superconducting qubit trace generation and energy consistency."""
    omega_r = np.linspace(1e7, 5e7, 50)  # drive frequencies
    gamma_m = np.linspace(1e-5, 5e-5, 50)  # measurement coupling

    trace = SymIOQubit.generate_trace(omega_r, gamma_m)
    assert SymIOQubit.validate_trace(trace, tol=0.05)