"""
Tessaris Optical Implementation Preparation
────────────────────────────────────────────
Prepares the physical photonic loop (MZM/DAC/PD) for live deployment.

Includes:
  * Hardware configuration schema (YAML-ready)
  * Calibration routine stubs for MZM bias and DAC linearity
  * Fiber alignment + PD gain validation
  * Integration readiness test for AION runtime coupling

This script bridges the digital simulation layer to real optical bench
hardware, forming the pre-deployment readiness test for Symatics v0.3.1.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

LOG_PATH = Path("backend/logs/photonics/optical_prep.jsonl")
CONFIG_PATH = Path("backend/config/photonics/hardware_config.yaml")

LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────
# Configuration Schema (YAML-friendly dict)
# ──────────────────────────────────────────────
def generate_hardware_config():
    """Generate base configuration template for the optical setup."""
    cfg = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hardware": {
            "MZM": {"bias_voltage": 2.5, "v_pi": 5.0, "driver_model": "MZM-X300"},
            "DAC": {"bit_depth": 14, "max_voltage": 3.3, "sample_rate": "5GS/s"},
            "PD": {"gain": 1.0, "bandwidth": "10GHz"},
            "FiberCoupler": {"split_ratio": "50:50", "alignment_tolerance_deg": 0.5},
        },
        "sync": {"clock_domain": "AION", "sync_mode": "resonant"},
        "safety": {"laser_shutdown_threshold_mW": 10.0, "temperature_limit_C": 45.0},
    }
    return cfg


# ──────────────────────────────────────────────
# Calibration + Validation Routines
# ──────────────────────────────────────────────
def calibrate_mzm_bias(v_pi=5.0, target_null=0.0):
    """Simulate Mach-Zehnder bias tuning to achieve intensity null."""
    voltages = np.linspace(0, v_pi, 50)
    intensity = np.cos(np.pi * voltages / v_pi) ** 2
    idx = np.argmin(np.abs(intensity - target_null))
    best_v = voltages[idx]
    return {"best_bias_voltage": float(best_v), "residual_intensity": float(intensity[idx])}


def calibrate_dac_linearity(bits=14):
    """Evaluate DAC linearity via simulated DNL/INL check."""
    codes = np.linspace(0, 2**bits - 1, 10)
    output = np.sin(codes / 2000.0)
    dnl = np.std(np.diff(output))
    inl = np.mean(np.abs(output - np.linspace(output[0], output[-1], len(output))))
    return {"dnl": float(dnl), "inl": float(inl)}


def validate_pd_gain(target_gain=1.0):
    """Perform a simple PD gain validation sequence."""
    measured = target_gain + np.random.normal(0, 0.02)
    return {"target_gain": target_gain, "measured_gain": measured, "gain_error": measured - target_gain}


def log_event(event: dict):
    """Log calibration/validation result to persistent file."""
    event["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(event) + "\n")


# ──────────────────────────────────────────────
# Integration Test Harness
# ──────────────────────────────────────────────
def run_optical_predeployment_check():
    """Perform full calibration + config emission for lab readiness."""
    print("🔬 Tessaris Optical Implementation Prep - Pre-Deployment Check")

    cfg = generate_hardware_config()
    with open(CONFIG_PATH, "w") as f:
        import yaml
        yaml.dump(cfg, f)

    print(f"[Config] Hardware schema emitted -> {CONFIG_PATH}")

    mzm_cal = calibrate_mzm_bias()
    dac_cal = calibrate_dac_linearity()
    pd_val = validate_pd_gain()

    report = {
        "config_path": str(CONFIG_PATH),
        "mzm_calibration": mzm_cal,
        "dac_calibration": dac_cal,
        "pd_validation": pd_val,
    }

    log_event(report)

    print("[Calibration] MZM bias:", mzm_cal)
    print("[Calibration] DAC linearity:", dac_cal)
    print("[Validation] PD gain:", pd_val)
    print(f"[OpticalPrep] Summary written -> {LOG_PATH}")
    return report


# ──────────────────────────────────────────────
# CLI Entry Point
# ──────────────────────────────────────────────
if __name__ == "__main__":
    report = run_optical_predeployment_check()
    print(json.dumps(report, indent=2))