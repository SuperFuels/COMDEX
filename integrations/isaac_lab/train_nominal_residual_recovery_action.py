#!/usr/bin/env python3
"""Learn a sparse correction to protected v13 at causal recovery onset."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import torch
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor

from backend.modules.hexcore.episodic_embodied_skill_memory import load_runtime
from integrations.isaac_lab.calibrate_causal_recovery_onset import onset_windows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True)
    parser.add_argument("--feature-cache", required=True)
    parser.add_argument("--source-capsule", required=True)
    parser.add_argument("--source-result", required=True)
    parser.add_argument("--nominal-manifest", required=True)
    parser.add_argument("--nominal-archive", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--capsule", required=True)
    args = parser.parse_args()

    archive = np.load(args.archive)
    features = np.load(args.feature_cache)["features"]
    episodes = archive["episode"]
    actions = archive["behavior_action"]
    regime = archive["regime"].astype(str)
    onset, windows, _ = onset_windows(regime, episodes)
    relevant = onset
    nominal = np.zeros_like(actions, dtype=np.float32)
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    runtime = load_runtime(
        Path(args.nominal_manifest), Path(args.nominal_archive), device=device
    )
    for index in np.flatnonzero(relevant):
        proposal = runtime.propose(
            archive["rgb"][index],
            archive["proprioception"][index],
            episode_id=int(episodes[index]),
            step=int(archive["step"][index]),
        )
        nominal[index] = np.asarray(proposal["values"], dtype=np.float32)
    residual = actions - nominal

    training = (episodes < 18) & onset
    development = (episodes >= 18) & (episodes < 24) & onset
    sealed = (episodes >= 24) & onset
    candidates = []
    for kind in ("extra", "forest"):
        for leaf in (1, 2, 4):
            for max_features in (0.5, 1.0):
                cls = ExtraTreesRegressor if kind == "extra" else RandomForestRegressor
                model = cls(
                    n_estimators=256,
                    min_samples_leaf=leaf,
                    max_features=max_features,
                    n_jobs=-1,
                    random_state=20260803,
                ).fit(features[training], residual[training])
                corrected = nominal[development] + model.predict(features[development])
                error = float(np.mean(np.abs(corrected - actions[development])))
                candidates.append((error, kind, leaf, max_features, model))
    candidates.sort(key=lambda item: item[:4])
    development_mae, kind, leaf, max_features, model = candidates[0]
    corrected = nominal[sealed] + model.predict(features[sealed])
    sealed_mae = float(np.mean(np.abs(corrected - actions[sealed])))
    nominal_mae = float(np.mean(np.abs(nominal[sealed] - actions[sealed])))
    improvement = (nominal_mae - sealed_mae) / max(nominal_mae, 1e-9)
    source = joblib.load(args.source_capsule)
    source_result = json.loads(Path(args.source_result).read_text())
    passed = bool(
        source_result["sealed_onset_gate"]["entry_precision"] >= 0.90
        and source_result["sealed_onset_gate"]["event_recall"] >= 0.50
        and sealed_mae <= 0.35
        and improvement >= 0.20
    )
    payload = {
        **source,
        "onset_residual_policy": model,
        "onset_action_contract": "protected nominal plus one correction then reobserve",
        "full_chunk_open_loop_authority": False,
    }
    capsule_path = Path(args.capsule)
    capsule_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(payload, capsule_path)
    result = {
        "schema_version": "aion.nominal_residual_recovery_action.v1",
        "selected_model": {
            "kind": kind,
            "min_samples_leaf": leaf,
            "max_features": max_features,
            "development_mae": development_mae,
        },
        "sealed_action_gate": {
            "passed": passed,
            "corrected_mae": sealed_mae,
            "protected_nominal_mae": nominal_mae,
            "improvement_over_nominal": improvement,
            "requirements": ["corrected MAE <=0.35", ">=20% improvement over nominal"],
        },
        "source_onset_gate": source_result["sealed_onset_gate"],
        "runtime_contract": {
            "protected_nominal_preserved": True,
            "corrective_actions_per_detection": 1,
            "reobserve_before_next_action": True,
            "privileged_runtime_inputs": 0,
        },
        "physx_probe_authorized": passed,
        "capsule_sha256": hashlib.sha256(capsule_path.read_bytes()).hexdigest(),
        "claim_boundary": "A sparse correction to protected v13 authorizes only a tiny visual PhysX probe.",
    }
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
