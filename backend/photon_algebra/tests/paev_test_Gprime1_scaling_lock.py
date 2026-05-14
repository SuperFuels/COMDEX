#!/usr/bin/env python3
"""
Test G′1 - Scaling Lock Calibration
Locks the model's unit system to physical constants using Λ or Planck reference.
"""

import json

# --- Choose reference (Lambda or Planck energy density) ---
REF_TYPE = "Lambda"  # or "Planck"
SIM_LAMBDA = 1.077e-04           # from G1
REAL_LAMBDA = 1.105e-52          # m^-2 (observed)
scale_factor = REAL_LAMBDA / SIM_LAMBDA

config = {
    "scale_ref": REF_TYPE,
    "scale_factor": scale_factor,
    "description": f"Locked scaling using {REF_TYPE} reference."
}

with open("backend/photon_algebra/config_physics_scale.json", "w") as f:
    json.dump(config, f, indent=4)

print("✅ Scaling locked successfully")
print(f"Reference: {REF_TYPE}")
print(f"scale_factor = {scale_factor:.3e}")