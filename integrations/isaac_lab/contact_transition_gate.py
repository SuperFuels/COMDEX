"""Fail-closed offline gate for learned Franka contact transitions."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

REQUIRED = {
    "proprioception", "action", "fingertip_touch", "object_height_post",
    "episode", "step", "arm",
}


def fit_capsule(path: str | Path, output: str | Path, *, arm: str = "aion_retained") -> dict:
    """Fit the frozen proposal-visible discriminator after the gate passes."""
    gate = assess_archive(path, arm=arm)
    if not gate["passed"]:
        raise RuntimeError(f"contact_transition_gate_not_passed:{gate['status']}")
    with np.load(path, allow_pickle=False) as archive:
        selected = np.asarray(archive["arm"]) == arm
        touch = np.asarray(archive["fingertip_touch"], np.float32)[selected]
        heights = np.asarray(archive["object_height_post"], np.float32)[selected]
        episodes = np.asarray(archive["episode"], np.int32)[selected]
        steps = np.asarray(archive["step"], np.int32)[selected]
        proprio = np.asarray(archive["proprioception"], np.float32)[selected]
    features, labels = [], []
    for index in range(3, len(touch) - 12):
        if episodes[index - 3] != episodes[index + 12] or steps[index] <= steps[index - 1]:
            continue
        history = np.log1p(np.clip(touch[index - 3:index + 1], 0, 250))
        features.append(np.concatenate((history.reshape(-1), np.diff(history, axis=0).reshape(-1),
                                        proprio[index, 7:9])))
        labels.append(float(np.max(heights[index + 1:index + 13]) - heights[index]) >= .02)
    x, y = np.asarray(features, np.float64), np.asarray(labels, dtype=bool)
    mean, scale = x.mean(0), x.std(0).clip(.05)
    z = (x - mean) / scale
    positive, negative = z[y], z[~y]
    direction = positive.mean(0) - negative.mean(0)
    midpoint = .5 * (positive.mean(0) + negative.mean(0))
    capsule = {"schema_version": "aion.contact_transition_capsule.v1", "history": 4,
               "horizon": 12, "feature_count": int(x.shape[1]), "mean": mean.tolist(),
               "scale": scale.tolist(), "direction": direction.tolist(), "midpoint": midpoint.tolist(),
               "gate": gate, "source_archive_sha256": gate["archive_sha256"]}
    capsule["capsule_sha256"] = hashlib.sha256(
        json.dumps(capsule, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    Path(output).write_text(json.dumps(capsule, indent=2, sort_keys=True))
    return capsule


def assess_archive(path: str | Path, *, arm: str = "aion_retained") -> dict:
    path = Path(path)
    with np.load(path, allow_pickle=False) as archive:
        missing = sorted(REQUIRED - set(archive.files))
        if missing:
            return {"passed": False, "status": "blocked_missing_real_fields", "missing": missing}
        selected = np.asarray(archive["arm"]) == arm
        touch = np.asarray(archive["fingertip_touch"], np.float32)[selected]
        heights = np.asarray(archive["object_height_post"], np.float32)[selected]
        episodes = np.asarray(archive["episode"], np.int32)[selected]
        steps = np.asarray(archive["step"], np.int32)[selected]
        actions = np.asarray(archive["action"], np.float32)[selected]
        proprio = np.asarray(archive["proprioception"], np.float32)[selected]
    if touch.ndim != 2 or touch.shape[1] != 2 or len(touch) < 100:
        return {"passed": False, "status": "blocked_insufficient_transitions",
                "transitions": int(len(touch))}

    features, labels, groups = [], [], []
    horizon = 12
    for index in range(3, len(touch) - horizon):
        if episodes[index - 3] != episodes[index + horizon] or steps[index] <= steps[index - 1]:
            continue
        history = np.log1p(np.clip(touch[index - 3:index + 1], 0, 250))
        # Proposal-visible history only: touch, gripper geometry, and actions.
        feature = np.concatenate((history.reshape(-1),
                                  np.diff(history, axis=0).reshape(-1),
                                  proprio[index, 7:9]))
        future_gain = float(np.max(heights[index + 1:index + horizon + 1]) - heights[index])
        features.append(feature)
        labels.append(future_gain >= .02)
        groups.append(episodes[index])
    x = np.asarray(features, np.float64)
    y = np.asarray(labels, np.int8)
    positives, negatives = int(y.sum()), int(len(y) - y.sum())
    if positives < 20 or negatives < 20 or len(np.unique(groups)) < 4:
        return {"passed": False, "status": "blocked_insufficient_independent_outcomes",
                "examples": int(len(y)), "positive": positives, "negative": negatives,
                "episodes": int(len(np.unique(groups)))}

    # Leave whole episodes out. A ridge linear discriminant is deliberately
    # small and replaceable; the gate measures transferable prediction rather
    # than training fit.
    predictions, truths = [], []
    groups = np.asarray(groups)
    for heldout in np.unique(groups):
        train, test = groups != heldout, groups == heldout
        mean, scale = x[train].mean(0), x[train].std(0).clip(.05)
        z = (x - mean) / scale
        pos, neg = z[train & (y == 1)], z[train & (y == 0)]
        direction = pos.mean(0) - neg.mean(0)
        midpoint = .5 * (pos.mean(0) + neg.mean(0))
        predictions.extend(((z[test] - midpoint) @ direction >= 0).tolist())
        truths.extend(y[test].tolist())
    predictions, truths = np.asarray(predictions), np.asarray(truths, dtype=bool)
    accuracy = float(np.mean(predictions == truths))
    recall = float(np.mean(predictions[truths]))
    specificity = float(np.mean(~predictions[~truths]))
    passed = accuracy >= .80 and recall >= .70 and specificity >= .70
    return {"passed": passed, "status": "passed" if passed else "failed_heldout_gate",
            "accuracy": accuracy, "recall": recall, "specificity": specificity,
            "examples": int(len(truths)), "positive": positives, "negative": negatives,
            "episodes": int(len(np.unique(groups))),
            "archive_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
