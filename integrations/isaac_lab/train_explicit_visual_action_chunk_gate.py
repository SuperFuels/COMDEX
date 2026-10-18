#!/usr/bin/env python3
"""Freeze an RGB keypoint + recovery chunk policy through a sealed episode split."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np

from backend.modules.hexcore.explicit_visual_action_chunk_memory import (
    ActionChunkMemory, ChromaKeypoint, feature_weights, make_features,
)
from backend.modules.hexcore.object_centric_action_chunk_policy import project_world


def eligible(episode: np.ndarray, step: np.ndarray, episodes: np.ndarray, chunk: int) -> np.ndarray:
    return np.flatnonzero(np.isin(episode, episodes) & (step <= 250 - chunk))


def chunks(actions: np.ndarray, indices: np.ndarray, length: int) -> np.ndarray:
    return np.stack([actions[index:index + length] for index in indices])


def score(memory: ActionChunkMemory, features: np.ndarray, target: np.ndarray) -> dict:
    predicted = memory.predict(features)
    repeated = np.repeat(predicted[:, :1], predicted.shape[1], axis=1)
    error = float(np.abs(predicted - target).mean())
    baseline = float(np.abs(repeated - target).mean())
    return {
        "chunk_action_mae": error,
        "retrieved_one_step_repeated_mae": baseline,
        "improvement_over_repeated_step": float(1.0 - error / max(baseline, 1e-8)),
        "temporal_std_ratio": float(predicted.std(1).mean() / (target.std(1).mean() + 1e-8)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--capsule", required=True)
    args = parser.parse_args()
    data = np.load(args.archive)
    rgb = data["rgb"]
    proprio = data["proprioception"]
    action = data["action"]
    labels = data["privileged_training_target"]
    episode = data["episode"]
    step = data["step"]
    train_ep = np.arange(0, 10)
    development_ep = np.arange(10, 14)
    sealed_ep = np.arange(14, 20)

    calibration_indices = np.flatnonzero(np.isin(episode, train_ep))[::5]
    detector = ChromaKeypoint.fit(rgb[calibration_indices], labels[calibration_indices, :3])
    detected_uv = detector.detect(rgb)
    truth_uv, _ = project_world(labels[:, :3])

    configurations = []
    # A compact development search avoids turning sealed evaluation into a
    # compute contest. Extremes test whether each state family matters.
    grid = (.5, 2.0)
    for length in (8, 12, 16):
        train = eligible(episode, step, train_ep, length)
        development = eligible(episode, step, development_ep, length)
        train_feature = make_features(proprio[train], detected_uv[train], step[train])
        development_feature = make_features(proprio[development], detected_uv[development], step[development])
        mean = train_feature.mean(0)
        scale = train_feature.std(0)
        scale[scale < 1e-4] = 1.0
        train_chunks = chunks(action, train, length)
        development_chunks = chunks(action, development, length)
        for groups in itertools.product(grid, repeat=4):
            weights = feature_weights(groups)
            for neighbours in (1, 3, 5):
                memory = ActionChunkMemory(train_feature, train_chunks, weights, mean, scale, neighbours)
                result = score(memory, development_feature, development_chunks)
                configurations.append((result["chunk_action_mae"], -result["improvement_over_repeated_step"],
                                       length, groups, neighbours, result))
    configurations.sort(key=lambda item: item[:2])
    _, _, length, groups, neighbours, development_result = configurations[0]

    train = eligible(episode, step, np.concatenate((train_ep, development_ep)), length)
    sealed = eligible(episode, step, sealed_ep, length)
    train_feature = make_features(proprio[train], detected_uv[train], step[train])
    sealed_feature = make_features(proprio[sealed], detected_uv[sealed], step[sealed])
    mean = train_feature.mean(0)
    scale = train_feature.std(0)
    scale[scale < 1e-4] = 1.0
    train_chunks = chunks(action, train, length)
    sealed_chunks = chunks(action, sealed, length)
    weights = feature_weights(groups)
    memory = ActionChunkMemory(train_feature, train_chunks, weights, mean, scale, neighbours)
    sealed_result = score(memory, sealed_feature, sealed_chunks)
    pixel_error = np.linalg.norm(detected_uv[sealed] - truth_uv[sealed], axis=1)
    geometry = {
        "mean_pixel_error": float(pixel_error.mean()),
        "median_pixel_error": float(np.median(pixel_error)),
        "p90_pixel_error": float(np.quantile(pixel_error, .9)),
        "passed": bool(pixel_error.mean() <= 5.0 and np.quantile(pixel_error, .9) <= 7.0),
        "requirement": "mean <=5 px and p90 <=7 px on six unseen student-visited resets",
    }
    action_gate = bool(sealed_result["chunk_action_mae"] <= .35 and
                       sealed_result["improvement_over_repeated_step"] >= .20 and
                       sealed_result["temporal_std_ratio"] >= .35)
    capsule = {
        "schema_version": "aion.explicit_visual_action_chunk_capsule.v1",
        "detector": detector.state_dict(),
        "retrieval": {"chunk_length": length, "group_weights": list(groups),
                      "neighbours": neighbours, "mean": mean.tolist(), "scale": scale.tolist(),
                      "features": train_feature.tolist(), "chunks": train_chunks.tolist()},
    }
    capsule_path = Path(args.capsule)
    capsule_path.parent.mkdir(parents=True, exist_ok=True)
    capsule_path.write_text(json.dumps(capsule, separators=(",", ":")))
    result = {
        "schema_version": "aion.explicit_visual_action_chunk_gate.v1",
        "authority": "student-visited DAgger states; privileged geometry used only for offline calibration/scoring",
        "split": {"train": train_ep.tolist(), "development": development_ep.tolist(), "sealed": sealed_ep.tolist()},
        "selected_on_development": {"chunk_length": length, "group_weights": list(groups),
                                    "neighbours": neighbours, "result": development_result},
        "geometry_gate": geometry,
        "action_chunk_gate": {"passed": action_gate, "sealed": sealed_result,
                              "requirement": "MAE <=0.35, >=20% improvement, >=0.35 temporal ratio"},
        "runtime_inputs": ["rgb", "bounded_proprioception", "mission_lift_cube"],
        "privileged_runtime_inputs": 0,
        "capsule_sha256": hashlib.sha256(capsule_path.read_bytes()).hexdigest(),
        "physx_authorized": bool(geometry["passed"] and action_gate),
        "claim_boundary": "Passing offline gates authorizes one sealed PhysX challenger; it is not manipulation success.",
    }
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
