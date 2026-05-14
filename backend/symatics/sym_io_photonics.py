"""
───────────────────────────────────────────────
Tessaris Symatics SDK v2.2
Module: sym_io_photonics.py
───────────────────────────────────────────────
Photonics experimental I/O bridge for Symatics.

Purpose:
    - Map μ ↔ optical tap ratio or detection efficiency
    - Map φ̇ ↔ modulation frequency or optical phase rate
    - Export/import JSON/CSV traces for lab or simulation data
    - Validate measured energy vs. SymTactics laws

Dependencies:
    - backend/modules/lean/sym_tactics.py
    - backend/modules/lean/sym_tactics_physics.py
───────────────────────────────────────────────
"""

from __future__ import annotations
import json, csv
import numpy as np
from pathlib import Path
from backend.modules.lean.sym_tactics import SymTactics
from backend.modules.lean.sym_tactics_physics import SymPhysics, C_LIGHT


class SymIOPhotonics:
    @staticmethod
    def generate_trace(freq_range, tap_ratios, k_phi=None):
        """
        Generate synthetic photonic trace for validation.

        Parameters
        ----------
        freq_range : array-like
            Optical frequency values (Hz)
        tap_ratios : array-like
            Detector tap ratios R (0-1)
        k_phi : float or None
            Optional phase-collapse constant (default c^2)

        Returns
        -------
        dict
            keys: 'phi_dot','mu','E_meas'
        """
        freq = np.asarray(freq_range, dtype=float)
        R = np.asarray(tap_ratios, dtype=float)
        assert freq.shape == R.shape, "freq and tap_ratios must match"

        mu = R  # μ ~ R
        phi_dot = 2 * np.pi * freq
        from backend.modules.lean.sym_tactics_physics import C_LIGHT

        E_meas = (k_phi or C_LIGHT**2) * phi_dot * mu
        return {"phi_dot": phi_dot, "mu": mu, "E_meas": E_meas}

    @staticmethod
    def export_trace(trace, path: str | Path):
        """Save trace dict to JSON or CSV based on extension."""
        path = Path(path)
        if path.suffix == ".json":
            with open(path, "w") as f:
                json.dump({k: list(map(float, np.ravel(v))) for k, v in trace.items()}, f, indent=2)
        elif path.suffix == ".csv":
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(trace.keys())
                for row in zip(*trace.values()):
                    writer.writerow(row)
        else:
            raise ValueError("Unsupported file type: use .json or .csv")

    @staticmethod
    def import_trace(path: str | Path):
        """Load trace dict from JSON or CSV."""
        path = Path(path)
        if path.suffix == ".json":
            with open(path) as f:
                data = json.load(f)
            return {k: np.array(v, dtype=float) for k, v in data.items()}
        elif path.suffix == ".csv":
            with open(path) as f:
                reader = csv.DictReader(f)
                cols = {k: [] for k in reader.fieldnames}
                for row in reader:
                    for k in cols:
                        cols[k].append(float(row[k]))
            return {k: np.array(v, dtype=float) for k, v in cols.items()}
        else:
            raise ValueError("Unsupported file type: use .json or .csv")

    @staticmethod
    def validate_trace(trace, tol=0.05):
        """
        Run SymTactics.energy_mass_equivalence on imported trace.
        Returns True if within tolerance.
        """
        return SymTactics.energy_mass_equivalence(trace["phi_dot"], trace["mu"], trace["E_meas"], tol=tol)