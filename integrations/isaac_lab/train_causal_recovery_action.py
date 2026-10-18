#!/usr/bin/env python3
"""Learn the first corrective action specifically at detected recovery onset."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor

from integrations.isaac_lab.calibrate_causal_recovery_onset import onset_windows


def mae(model, features, actions, mask):
    return float(np.mean(np.abs(model.predict(features[mask]) - actions[mask])))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True)
    parser.add_argument("--feature-cache", required=True)
    parser.add_argument("--source-capsule", required=True)
    parser.add_argument("--source-result", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--capsule", required=True)
    args = parser.parse_args()

    archive = np.load(args.archive)
    cache = np.load(args.feature_cache)
    features = cache["features"]
    base = cache["base"]
    episodes = archive["episode"]
    actions = archive["behavior_action"]
    regime = archive["regime"].astype(str)
    onset, windows, _ = onset_windows(regime, episodes)
    training = (episodes < 18) & windows
    development = (episodes >= 18) & (episodes < 24) & onset
    sealed = (episodes >= 24) & onset
    source = joblib.load(args.source_capsule)
    source_result = json.loads(Path(args.source_result).read_text())

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
                ).fit(features[training], actions[training])
                candidates.append(
                    (mae(model, features, actions, development), kind, leaf, max_features, model)
                )
    candidates.sort(key=lambda item: item[:4])
    development_mae, kind, leaf, max_features, model = candidates[0]
    sealed_mae = mae(model, features, actions, sealed)
    inherited = source["recovery_policy"].predict(base[sealed]).reshape(-1, 8, 8)[:, 0]
    inherited_mae = float(np.mean(np.abs(inherited - actions[sealed])))
    improvement = (inherited_mae - sealed_mae) / inherited_mae
    passed = bool(
        source_result["sealed_onset_gate"]["entry_precision"] >= 0.90
        and source_result["sealed_onset_gate"]["event_recall"] >= 0.50
        and sealed_mae <= 0.35
        and improvement >= 0.20
    )
    payload = {
        **source,
        "onset_action_policy": model,
        "onset_action_contract": "one corrective action then mandatory re-observation",
        "full_chunk_open_loop_authority": False,
    }
    capsule_path = Path(args.capsule)
    capsule_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(payload, capsule_path)
    result = {
        "schema_version": "aion.causal_recovery_action.v1",
        "training_authority": "four onset-window rows from episodes 0-17 only",
        "selection_authority": "single onset row from episodes 18-23",
        "sealed_authority": "single onset row from episodes 24-29",
        "selected_model": {
            "kind": kind,
            "min_samples_leaf": leaf,
            "max_features": max_features,
            "development_mae": development_mae,
        },
        "sealed_action_gate": {
            "passed": passed,
            "mae": sealed_mae,
            "inherited_recovery_mae": inherited_mae,
            "improvement_over_inherited": improvement,
            "requirements": ["MAE <=0.35", ">=20% improvement over inherited recovery"],
        },
        "source_onset_gate": source_result["sealed_onset_gate"],
        "runtime_contract": {
            "corrective_actions_per_detection": 1,
            "reobserve_before_next_action": True,
            "privileged_runtime_inputs": 0,
        },
        "physx_probe_authorized": passed,
        "capsule_sha256": hashlib.sha256(capsule_path.read_bytes()).hexdigest(),
        "claim_boundary": "A sparse onset detector plus one-step corrective policy authorizes only a tiny visual PhysX probe.",
    }
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

