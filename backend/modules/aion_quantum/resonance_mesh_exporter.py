"""
Tessaris Resonance Mesh Exporter (RME)
Phase 11 - 4-D Cognitive Resonance Mesh Archival
------------------------------------------------
Captures harmonic surface evolution from Quantum Resonance Mapper (QRM)
and exports a .qrm file - JSON-encoded mesh representation of the
Φ-ν-ψ-t topology for replay or external rendering.

Author: Tessaris Symbolic Intelligence Lab, 2025
"""

import json
import gzip
import time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

# ---------------------------------------------------------
# 🧭 Configuration
# ---------------------------------------------------------
INPUT_FILE = Path("data/cognitive_field_resonance.jsonl")
OUTPUT_DIR = Path("data/qqc_field/mesh_exports")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EXPORT_INTERVAL = 120     # seconds between mesh exports
MAX_POINTS = 5000         # limit for each mesh slice
COMPRESS = True           # gzip-compress .qrm file

# ---------------------------------------------------------
# 🧮 Utility
# ---------------------------------------------------------
def load_records(limit=MAX_POINTS):
    """Load latest resonance data from log."""
    if not INPUT_FILE.exists():
        return []
    with open(INPUT_FILE) as f:
        lines = f.read().strip().splitlines()[-limit:]
    records = []
    for line in lines:
        try:
            records.append(json.loads(line))
        except Exception:
            continue
    return records


def build_mesh(records):
    """Construct mesh arrays for Φ, ν, ψ, and t."""
    if not records:
        return None

    t_vals = np.arange(len(records))
    phi_vals = [r.get("phi_state", 0.0) or 0.0 for r in records]
    psi_vals = [r.get("photon_pattern", {}).get("Δψ2", 0.0) or 0.0 for r in records]
    nu_vals = [r.get("spectrum_centroid", 0.0) or 0.0 for r in records]
    stab_vals = [r.get("stability", 1.0) or 1.0 for r in records]

    mesh = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dimensions": ["Φ_coh", "ψ2", "ν_centroid", "t"],
        "data": {
            "t": t_vals.tolist(),
            "Φ_coh": phi_vals,
            "ψ2": psi_vals,
            "ν_centroid": nu_vals,
            "stability": stab_vals,
        },
        "metadata": {
            "samples": len(records),
            "mean_stability": float(np.mean(stab_vals)),
            "var_stability": float(np.var(stab_vals)),
        },
    }
    return mesh


def export_mesh(mesh):
    """Write the mesh to a .qrm or .qrm.gz file."""
    if not mesh:
        return None

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_path = OUTPUT_DIR / f"resonance_{timestamp}.qrm"

    data = json.dumps(mesh, indent=2)
    if COMPRESS:
        out_path = out_path.with_suffix(".qrm.gz")
        with gzip.open(out_path, "wt", encoding="utf-8") as f:
            f.write(data)
    else:
        with open(out_path, "w") as f:
            f.write(data)

    print(f"🪶 Mesh exported -> {out_path.name}")
    return out_path


# ---------------------------------------------------------
# 🚀 Main loop
# ---------------------------------------------------------
def run_mesh_exporter():
    print("🧩 Starting Tessaris Resonance Mesh Exporter (RME)...")
    while True:
        try:
            records = load_records()
            mesh = build_mesh(records)
            out_file = export_mesh(mesh)
            if mesh:
                print(
                    f"   Samples={mesh['metadata']['samples']} "
                    f"MeanS={mesh['metadata']['mean_stability']:.3f} "
                    f"VarS={mesh['metadata']['var_stability']:.6f}"
                )
            time.sleep(EXPORT_INTERVAL)
        except KeyboardInterrupt:
            print("\n🪶 RME terminated by user.")
            break
        except Exception as e:
            print(f"⚠️ Mesh export error: {e}")
            time.sleep(EXPORT_INTERVAL)


# ---------------------------------------------------------
# Entry
# ---------------------------------------------------------
if __name__ == "__main__":
    run_mesh_exporter()