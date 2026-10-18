#!/usr/bin/env python3
"""Calibrate recovery switching for asymmetric online utility, not F1."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import torch
from sklearn.ensemble import ExtraTreesClassifier

from backend.modules.hexcore.explicit_visual_action_chunk_memory import make_features
from backend.modules.hexcore.interruptible_recovery_option import (
    InterruptibleRecoveryOption,
    RecoveryOptionConfig,
)
from backend.modules.hexcore.recovery_visual_router import RGBObjectKeypoint
from integrations.isaac_lab.calibrate_temporal_recovery_router import temporal


def simulate(probability, target, episodes, config):
    selected = np.zeros(len(probability), dtype=bool)
    entries = 0
    state = InterruptibleRecoveryOption(config)
    previous_episode = None
    for index, (prob, episode) in enumerate(zip(probability, episodes, strict=True)):
        if previous_episode is None or episode != previous_episode:
            state.reset()
        use_recovery, mode = state.decide(float(prob))
        selected[index] = use_recovery
        entries += int(mode == "interruptible_recovery_enter")
        previous_episode = episode
    true_positive = int(np.sum(selected & target))
    false_positive = int(np.sum(selected & ~target))
    false_negative = int(np.sum(~selected & target))
    true_negative = int(np.sum(~selected & ~target))
    precision = true_positive / max(1, true_positive + false_positive)
    recall = true_positive / max(1, true_positive + false_negative)
    nominal_recall = true_negative / max(1, true_negative + false_positive)
    # A false hand-off is eight times as expensive as missing one recovery row;
    # each new switch also carries a small interruption cost.
    utility = true_positive - 8.0 * false_positive - 0.5 * entries
    return {
        "selected": selected,
        "entries": entries,
        "controlled_rows": int(selected.sum()),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": precision,
        "recovery_recall": recall,
        "nominal_recall": nominal_recall,
        "asymmetric_utility": utility,
    }


def public_metrics(metrics):
    return {key: value for key, value in metrics.items() if key != "selected"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True)
    parser.add_argument("--source-capsule", required=True)
    parser.add_argument("--source-result", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--capsule", required=True)
    parser.add_argument("--feature-cache")
    parser.add_argument("--device", choices=("cpu", "mps"), default="cpu")
    args = parser.parse_args()

    archive = np.load(args.archive)
    rgb = archive["rgb"]
    proprioception = archive["proprioception"]
    actions = archive["behavior_action"]
    episodes = archive["episode"]
    steps = archive["step"]
    target = np.char.startswith(archive["regime"].astype(str), "recovery_")
    source = joblib.load(args.source_capsule)
    source_result = json.loads(Path(args.source_result).read_text())

    cache_path = Path(args.feature_cache) if args.feature_cache else None
    if cache_path and cache_path.exists():
        cached = np.load(cache_path)
        points = cached["points"]
        features = cached["features"]
        base = cached["base"]
    else:
        device = torch.device(
            "mps" if args.device == "mps" and torch.backends.mps.is_available() else "cpu"
        )
        keypoint = RGBObjectKeypoint()
        keypoint.load_state_dict(source["keypoint_state_dict"])
        keypoint.to(device).eval()
        points = []
        with torch.inference_mode():
            for start in range(0, len(rgb), 256):
                batch = torch.from_numpy(rgb[start : start + 256]).to(device)
                points.append(keypoint(batch).cpu().numpy())
        points = np.concatenate(points)
        base = make_features(proprioception, points, steps)
        features = temporal(base, proprioception, points, actions, episodes)
        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(cache_path, points=points, base=base, features=features)
    training = episodes < 18
    development = (episodes >= 18) & (episodes < 24)
    sealed = episodes >= 24
    # The deployable router is fit only on the training episodes.  Reusing the
    # v28 train+development router here would make threshold selection on the
    # development episodes circular and overstate switching precision.
    router = ExtraTreesClassifier(
        n_estimators=256,
        min_samples_leaf=4,
        max_features=1.0,
        class_weight="balanced",
        n_jobs=-1,
        random_state=20260803,
    ).fit(features[training], target[training])
    probability = router.predict_proba(features)[:, 1]
    candidates = []
    all_candidates = []
    for enter in np.linspace(0.30, 0.99, 24):
        for exit_ratio in (0.50, 0.75):
            for sustained in (1, 2, 3):
                for burst in (1, 2, 3):
                    for cooldown in (0, 2):
                        config = RecoveryOptionConfig(
                            enter_threshold=float(enter),
                            exit_threshold=float(enter * exit_ratio),
                            sustained_observations=sustained,
                            max_burst_actions=burst,
                            cooldown_actions=cooldown,
                        )
                        metrics = simulate(
                            probability[development],
                            target[development],
                            episodes[development],
                            config,
                        )
                        all_candidates.append((config, metrics))
                        if (
                            metrics["precision"] < 0.90
                            or metrics["nominal_recall"] < 0.98
                            or metrics["recovery_recall"] < 0.30
                            or metrics["controlled_rows"] > 96
                        ):
                            continue
                        candidates.append(
                            (
                                -metrics["asymmetric_utility"],
                                -metrics["precision"],
                                metrics["false_positive"],
                                -metrics["recovery_recall"],
                                config,
                                metrics,
                            )
                        )
    development_gate_passed = bool(candidates)
    if candidates:
        candidates.sort(key=lambda item: item[:4])
        _, _, _, _, config, development_metrics = candidates[0]
    else:
        viable = [item for item in all_candidates if item[1]["recovery_recall"] > 0.0]
        config, development_metrics = sorted(
            viable,
            key=lambda item: (
                -item[1]["precision"],
                -item[1]["nominal_recall"],
                -item[1]["recovery_recall"],
                item[1]["controlled_rows"],
            ),
        )[0]
    sealed_metrics = simulate(
        probability[sealed], target[sealed], episodes[sealed], config
    )

    recovery_prediction = source["recovery_policy"].predict(base[sealed]).reshape(-1, 8, 8)
    selected = sealed_metrics["selected"]
    selected_true = selected & target[sealed]
    if selected_true.any():
        first_action_mae = float(
            np.mean(np.abs(recovery_prediction[selected_true, 0] - actions[sealed][selected_true]))
        )
    else:
        first_action_mae = None

    passed = bool(
        development_gate_passed
        and sealed_metrics["precision"] >= 0.90
        and sealed_metrics["nominal_recall"] >= 0.98
        and sealed_metrics["recovery_recall"] >= 0.30
        and sealed_metrics["controlled_rows"] <= 96
        and first_action_mae is not None
        and first_action_mae <= 0.35
    )
    payload = {
        **source,
        "router": router,
        "interruptible_recovery_config": config.__dict__,
        "router_objective": "asymmetric_switch_utility",
        "full_chunk_open_loop_authority": False,
    }
    capsule_path = Path(args.capsule)
    capsule_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(payload, capsule_path)
    result = {
        "schema_version": "aion.interruptible_recovery_option.v1",
        "router_training_episodes": "0-17 only",
        "source_gates": source_result["source_gates"],
        "selected_on_development": {
            "gate_passed": development_gate_passed,
            "config": config.__dict__,
            **public_metrics(development_metrics),
        },
        "sealed_option_gate": {
            "passed": passed,
            **public_metrics(sealed_metrics),
            "selected_true_recovery_first_action_mae": first_action_mae,
            "requirements": [
                "precision >= 0.90",
                "nominal recall >= 0.98",
                "recovery recall >= 0.30",
                "controlled rows <= 96/1500",
                "selected true-recovery first-action MAE <= 0.35",
            ],
        },
        "physx_probe_authorized": passed,
        "runtime_contract": {
            "actions_per_recovery_decision": 1,
            "maximum_burst_actions": config.max_burst_actions,
            "reobserve_before_continuation": True,
            "privileged_runtime_inputs": 0,
        },
        "capsule_sha256": hashlib.sha256(capsule_path.read_bytes()).hexdigest(),
        "claim_boundary": "A high-precision offline option gate authorizes only a tiny visual PhysX probe against protected v13.",
    }
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
