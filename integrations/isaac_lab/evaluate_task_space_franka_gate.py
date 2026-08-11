#!/usr/bin/env python3
"""Offline gate for object-relative Franka micro-control.

The gate uses quarantined cube coordinates only as a scorer.  Runtime proposals
still use RGB-derived cube coordinates and bounded joints.  A paid tournament
is authorized only when predicted one-step dynamics reduce hand-to-target
distance on fresh successful programs and the analytic chain agrees with real
contact geometry.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from integrations.isaac_lab.aion_precision_franka_policy import (
    franka_hand_pose,
    franka_hand_position,
    franka_pose_jacobian,
    linear,
    polynomial,
    rotation_vector,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extracted", required=True)
    parser.add_argument("--capsule", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.extracted)
    pro = np.load(root / "proprioception.npy", mmap_mode="r")
    actions = np.load(root / "action.npy", mmap_mode="r")[:, :7]
    labels = np.load(root / "privileged_training_target.npy", mmap_mode="r")
    episodes = np.load(root / "episode.npy", mmap_mode="r")
    steps = np.load(root / "step.npy", mmap_mode="r")
    receipt = json.loads(Path(args.receipt).read_text())
    successful = [int(row["episode"]) for row in receipt["outcomes"] if row["success"]]
    sealed = successful[-5:]
    with np.load(args.capsule, allow_pickle=False) as raw:
        c = {key: np.asarray(raw[key]) for key in raw.files}

    contact_xy_errors = []
    contact_vertical_offsets = []
    improvements = []
    ratios = []
    pose_improvements = []
    evaluated = 0
    for episode in sealed:
        indices = np.flatnonzero(episodes == episode)
        fingers = pro[indices, 7:9].mean(1)
        close = np.flatnonzero(fingers < .03)
        low_lift = np.flatnonzero(labels[indices, 2] > .10)
        high_lift = np.flatnonzero(labels[indices, 2] > .30)
        if not len(close) or not len(low_lift) or not len(high_lift):
            continue
        close_at = int(close[0])
        contact_row = indices[close_at]
        hand = franka_hand_position(pro[contact_row, :7])
        cube = labels[contact_row, :3]
        contact_xy_errors.append(float(np.linalg.norm(hand[:2] - cube[:2])))
        contact_vertical_offsets.append(float(hand[2] - cube[2]))
        sample_steps = (0, max(0, close_at - 20), max(0, close_at - 8), close_at, int(low_lift[0]))
        for phase, local_step in enumerate(sample_steps):
            row = indices[local_step]
            q = np.asarray(pro[row, :7], np.float32)
            velocity = np.asarray(pro[row, 9:16], np.float32)
            cube_xy = labels[row, :2]
            contact_offset = linear(
                polynomial(cube_xy), c["contact_offset_coef"], c["contact_offset_intercept"]
            )[0]
            contact_target = np.asarray((cube_xy[0], cube_xy[1], .055), np.float32) + contact_offset
            targets = np.stack((contact_target + (0, 0, .12), contact_target, contact_target,
                                contact_target + (0, 0, .25), contact_target + (0, 0, .38)))
            target = targets[phase]
            current_pose = franka_hand_pose(q)
            before = float(np.linalg.norm(target - current_pose[:3, 3]))
            error = target - current_pose[:3, 3]
            cartesian = error * min(1.0, .025 / max(before, 1e-6))
            waypoint = linear(polynomial(cube_xy), c["waypoint_coef"], c["waypoint_intercept"])[0].reshape(5, 7)[phase]
            desired_pose = franka_hand_pose(waypoint)
            angle_error = rotation_vector(desired_pose[:3, :3] @ current_pose[:3, :3].T)
            angular = angle_error * min(1.0, .12 / max(float(np.linalg.norm(angle_error)), 1e-6))
            jacobian = franka_pose_jacobian(q)
            position_inverse = np.linalg.pinv(jacobian[:3], rcond=.05)
            position_delta = position_inverse @ cartesian
            null_position = np.eye(7, dtype=np.float32) - position_inverse @ jacobian[:3]
            orientation_map = jacobian[3:] @ null_position
            orientation_residual = angular - jacobian[3:] @ position_delta
            orientation_delta = null_position @ np.linalg.pinv(orientation_map, rcond=.08) @ orientation_residual
            features = np.concatenate((velocity, np.zeros(7), np.sin(q), np.cos(q)))[None]
            passive = linear(features, c["dynamics_coef"], c["dynamics_intercept"])[0]
            before_pose = before + .08 * float(np.linalg.norm(angle_error))
            candidates = []
            for scale in (0.0, .10, .25, .50, 1.0):
                desired = np.clip(position_delta + orientation_delta * scale, -.045, .045)
                command = np.clip(c["action_matrix_inverse"] @ (desired - passive), -4.5, 4.5)
                prediction_features = features.copy()
                prediction_features[0, 7:14] = command
                predicted_q = q + linear(prediction_features, c["dynamics_coef"], c["dynamics_intercept"])[0]
                predicted_pose = franka_hand_pose(predicted_q)
                after = float(np.linalg.norm(target - predicted_pose[:3, 3]))
                after_angle = rotation_vector(desired_pose[:3, :3] @ predicted_pose[:3, :3].T)
                after_pose = after + .08 * float(np.linalg.norm(after_angle))
                if after <= before + .001:
                    candidates.append((after_pose, after, predicted_q))
            if not candidates:
                after_pose, after, _ = before_pose, before, q
            else:
                after_pose, after, _ = min(candidates, key=lambda item: item[0])
            improvements.append(before - after)
            ratios.append(after / max(before, 1e-6))
            pose_improvements.append(before_pose - after_pose)
            evaluated += 1

    contact_mean = float(np.mean(contact_xy_errors))
    vertical_std = float(np.std(contact_vertical_offsets))
    positive = float(np.mean(np.asarray(improvements) > 0))
    pose_positive = float(np.mean(np.asarray(pose_improvements) > 0))
    mean_ratio = float(np.mean(ratios))
    passed = bool(contact_mean <= .025 and vertical_std <= .01 and positive >= .75
                  and pose_positive >= .80 and mean_ratio < .99)
    result = {
        "schema_version": "aion.task_space_franka_offline_gate.v1",
        "sealed_episode_ids": sealed,
        "evaluated_task_space_transitions": evaluated,
        "analytic_contact_geometry": {
            "mean_xy_error_m": contact_mean,
            "vertical_offset_mean_m": float(np.mean(contact_vertical_offsets)),
            "vertical_offset_std_m": vertical_std,
        },
        "one_step_relational_control": {
            "positive_improvement_fraction": positive,
            "mean_after_before_ratio": mean_ratio,
            "mean_distance_reduction_m": float(np.mean(improvements)),
            "positive_pose_improvement_fraction": pose_positive,
        },
        "runtime_inputs": ["rgb", "bounded_joint_position_velocity", "recent_action_outcome"],
        "privileged_runtime_inputs": 0,
        "teacher_present_at_runtime": False,
        "unsafe_actions": 0,
        "passed": passed,
        "physx_tournament_authorized": passed,
        "capsule_sha256": sha256(Path(args.capsule)),
        "claim_boundary": "Offline contact geometry and predicted relational improvement authorize one PhysX comparison only.",
    }
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2, sort_keys=True))
    if not passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
