#!/usr/bin/env python3
# docs/vol0_symatics_axioms/qfc/generate_axiom_stability_v0_v0_3.py

import json
import os
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).parent
OUT = HERE / "AXIOM_STABILITY_V0_v0_3.scene.json"

def build_scene() -> dict:
    # Best-effort lock hash: allow CI to inject it; otherwise "unknown"
    lock_hash = (
        os.getenv("GIT_COMMIT_HASH")
        or os.getenv("GITHUB_SHA")
        or os.getenv("CI_COMMIT_SHA")
        or "unknown"
    )

    return {
        "metadata": {
            "scene_id": "AXIOM_STABILITY_V0",
            "version": "0.3.0",
            "pillar": "SYMATICS",
            "paper_ref": "docs/vol0_symatics_axioms/vol0_symatics_axioms_v0_3.tex",
            "lock_hash": lock_hash,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
        },
        "logic_layer": {
            "axioms": ["S0", "E0"],
            "primary_equation": r"a \oplus b \Rightarrow b \oplus a \;\;\wedge\;\; a \leftrightarrow b \Rightarrow b \leftrightarrow a",
            "constants": {
                "seed": 1337,
                "n_samples": 256,
                "tolerance": 1e-6,
            },
        },
        "simulation_engine": {
            "input_stream": {
                "seed": 1337,
                "type": "STOCHASTIC",
                "params": {
                    "n_samples": 256,
                    "mix": [
                        {"expr": "a ⊕ b", "axiom": "S0"},
                        {"expr": "a ↔ b", "axiom": "E0"},
                    ],
                },
            },
            "controller": {
                "mode": "OPEN_LOOP",
                "target_invariant": "REWRITE_INVARIANCE_ERR",
            },
        },
        "telemetry_hud": {
            "primary_metric": {
                "label": "REWRITE_INVARIANCE_ERR",
                "key": "rewrite_invariance_err",
                "unit": "abs",
                "threshold": {"min": 0.0, "max": 1.0, "target": 1e-6},
            },
            "charts": [
                {"label": "Coherence Proxy", "keys": ["coherence_proxy_c"], "type": "line"},
            ],
        },
        "render_pipeline": {
            "shader_id": "QFCAxiomStability@v0.3",
            "geometry": {"type": "LATTICE_2D", "density": 128},
            "palette": {
                "primary": "#00FFFF",
                "secondary": "#FF00FF",
                "accent": "#FF0000",
            },
        },
        "audit_trail": {
            "pytest_anchor": "backend/photon/tests/test_axiom_stability_v0.py",
            "lean_obligation": "docs/vol0_symatics_axioms/lean/symatics_axioms_v0.lean",
            "expected_artifact": "docs/vol0_symatics_axioms/qfc/AXIOM_STABILITY_V0_v0_3.result.json",
        },
    }

def main() -> None:
    scene = build_scene()
    OUT.write_text(json.dumps(scene, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote: {OUT}")

if __name__ == "__main__":
    main()