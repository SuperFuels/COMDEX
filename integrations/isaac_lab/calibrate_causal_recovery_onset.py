#!/usr/bin/env python3
"""Learn sparse causal recovery onset rather than persistent recovery state."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import ExtraTreesClassifier

from backend.modules.hexcore.interruptible_recovery_option import (
    InterruptibleRecoveryOption,
    RecoveryOptionConfig,
)


def onset_windows(regime: np.ndarray, episodes: np.ndarray, width: int = 4):
    recovery = np.char.startswith(regime.astype(str), "recovery_")
    onset = np.zeros(len(recovery), dtype=bool)
    windows = np.zeros(len(recovery), dtype=bool)
    event_id = np.full(len(recovery), -1, dtype=np.int64)
    next_event = 0
    for index in range(len(recovery)):
        prior_recovery = (
            index > 0 and episodes[index] == episodes[index - 1] and recovery[index - 1]
        )
        if recovery[index] and not prior_recovery:
            onset[index] = True
            stop = min(len(recovery), index + width)
            same_episode = episodes[index:stop] == episodes[index]
            valid = np.flatnonzero(same_episode) + index
            windows[valid] = True
            event_id[valid] = next_event
            next_event += 1
    return onset, windows, event_id


def evaluate(probability, windows, event_id, episodes, config):
    option = InterruptibleRecoveryOption(config)
    selected = np.zeros(len(probability), dtype=bool)
    entries = np.zeros(len(probability), dtype=bool)
    prior_episode = None
    for index, (prob, episode) in enumerate(zip(probability, episodes, strict=True)):
        if prior_episode is None or episode != prior_episode:
            option.reset()
        use_recovery, mode = option.decide(float(prob))
        selected[index] = use_recovery
        entries[index] = mode == "interruptible_recovery_enter"
        prior_episode = episode
    event_ids = sorted(set(event_id[event_id >= 0].tolist()))
    detected = sum(bool(np.any(selected[event_id == item])) for item in event_ids)
    true_entries = int(np.sum(entries & windows))
    false_entries = int(np.sum(entries & ~windows))
    event_recall = detected / max(1, len(event_ids))
    entry_precision = true_entries / max(1, true_entries + false_entries)
    false_controlled = int(np.sum(selected & ~windows))
    utility = 12.0 * detected - 16.0 * false_entries - 2.0 * false_controlled
    return {
        "selected": selected,
        "events": len(event_ids),
        "events_detected": detected,
        "event_recall": event_recall,
        "true_entries": true_entries,
        "false_entries": false_entries,
        "entry_precision": entry_precision,
        "controlled_rows": int(selected.sum()),
        "false_controlled_rows": false_controlled,
        "asymmetric_event_utility": utility,
    }


def public(metrics):
    return {key: value for key, value in metrics.items() if key != "selected"}


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
    regime = archive["regime"].astype(str)
    actions = archive["behavior_action"]
    _, windows, event_id = onset_windows(regime, episodes)
    training = episodes < 18
    development = (episodes >= 18) & (episodes < 24)
    sealed = episodes >= 24
    source = joblib.load(args.source_capsule)
    source_result = json.loads(Path(args.source_result).read_text())

    model_candidates = []
    for leaf in (1, 2, 4, 8):
        router = ExtraTreesClassifier(
            n_estimators=256,
            min_samples_leaf=leaf,
            max_features=1.0,
            class_weight="balanced",
            n_jobs=-1,
            random_state=20260803,
        ).fit(features[training], windows[training])
        probability = router.predict_proba(features)[:, 1]
        for enter in np.linspace(0.30, 0.99, 24):
            for sustained in (1, 2):
                for burst in (1, 2, 3):
                    for cooldown in (8, 16, 24):
                        config = RecoveryOptionConfig(
                            enter_threshold=float(enter),
                            exit_threshold=float(enter * 0.5),
                            sustained_observations=sustained,
                            max_burst_actions=burst,
                            cooldown_actions=cooldown,
                        )
                        metrics = evaluate(
                            probability[development],
                            windows[development],
                            event_id[development],
                            episodes[development],
                            config,
                        )
                        model_candidates.append((leaf, router, probability, config, metrics))

    eligible = [
        item
        for item in model_candidates
        if item[4]["entry_precision"] >= 0.90
        and item[4]["event_recall"] >= 0.50
        and item[4]["false_entries"] <= 1
        and item[4]["false_controlled_rows"] <= 3
    ]
    development_gate_passed = bool(eligible)
    pool = eligible or [item for item in model_candidates if item[4]["events_detected"]]
    leaf, router, probability, config, development_metrics = sorted(
        pool,
        key=lambda item: (
            -item[4]["asymmetric_event_utility"],
            -item[4]["entry_precision"],
            -item[4]["event_recall"],
            item[4]["false_entries"],
        ),
    )[0]
    sealed_metrics = evaluate(
        probability[sealed], windows[sealed], event_id[sealed], episodes[sealed], config
    )
    recovery = source["recovery_policy"].predict(base[sealed]).reshape(-1, 8, 8)
    selected_true = sealed_metrics["selected"] & windows[sealed]
    first_action_mae = (
        float(np.mean(np.abs(recovery[selected_true, 0] - actions[sealed][selected_true])))
        if selected_true.any()
        else None
    )
    passed = bool(
        development_gate_passed
        and sealed_metrics["entry_precision"] >= 0.90
        and sealed_metrics["event_recall"] >= 0.50
        and sealed_metrics["false_entries"] <= 1
        and sealed_metrics["false_controlled_rows"] <= 3
        and first_action_mae is not None
        and first_action_mae <= 0.35
    )
    payload = {
        **source,
        "router": router,
        "interruptible_recovery_config": config.__dict__,
        "router_target": "four-step causal recovery onset window",
        "full_chunk_open_loop_authority": False,
    }
    capsule_path = Path(args.capsule)
    capsule_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(payload, capsule_path)
    result = {
        "schema_version": "aion.causal_recovery_onset_option.v1",
        "router_training_episodes": "0-17 only",
        "target_revision": "sparse four-step recovery onset; not 32-step recovery occupancy",
        "source_gates": source_result["source_gates"],
        "selected_on_development": {
            "gate_passed": development_gate_passed,
            "min_samples_leaf": leaf,
            "config": config.__dict__,
            **public(development_metrics),
        },
        "sealed_onset_gate": {
            "passed": passed,
            **public(sealed_metrics),
            "selected_onset_first_action_mae": first_action_mae,
            "requirements": [
                "entry precision >=0.90",
                "event recall >=0.50",
                "false entries <=1",
                "false controlled rows <=3",
                "first recovery action MAE <=0.35",
            ],
        },
        "runtime_contract": {
            "actions_per_decision": 1,
            "maximum_burst_actions": config.max_burst_actions,
            "reobserve_before_continuation": True,
            "privileged_runtime_inputs": 0,
        },
        "physx_probe_authorized": passed,
        "capsule_sha256": hashlib.sha256(capsule_path.read_bytes()).hexdigest(),
        "claim_boundary": "Sparse causal onset detection authorizes only a tiny visual PhysX probe; it is not manipulation competence.",
    }
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

