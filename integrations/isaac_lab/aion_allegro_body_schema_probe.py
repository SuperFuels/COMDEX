#!/usr/bin/env python3
"""Teacher-free Allegro body-schema discovery and coordinated manipulation.

The development phase identifies the action-to-joint map from paired physical
interventions at several amplitudes and horizons.  A disjoint intervention is
then used to reconstruct every learned mapping.  Only a passing body schema is
allowed to generate coordinated manipulation programs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import traceback
from pathlib import Path

from isaaclab.app import AppLauncher

p = argparse.ArgumentParser()
p.add_argument("--output", required=True)
p.add_argument("--seed", type=int, required=True)
AppLauncher.add_app_launcher_args(p)
args = p.parse_args()
args.enable_cameras = False
app = AppLauncher(args).app

import gymnasium as gym
import numpy as np
import torch
import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils import parse_env_cfg


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def find_asset(raw, names, scene_group):
    for name in names:
        value = getattr(raw, name, None)
        if value is not None:
            return value
    scene = getattr(raw, "scene", None)
    if scene is not None:
        group = getattr(scene, scene_group, {})
        for name in names:
            try:
                return group[name.lstrip("_")]
            except Exception:
                pass
    raise RuntimeError(f"authority_not_found:{names[0]}")


def maximum_assignment(scores):
    """Exact maximum-weight bipartite assignment without an extra dependency."""
    n = int(scores.shape[0])
    states = {0: (0.0, ())}
    for row in range(n):
        nxt = {}
        for mask, (value, path) in states.items():
            for col in range(n):
                bit = 1 << col
                if mask & bit:
                    continue
                candidate = value + float(scores[row, col])
                old = nxt.get(mask | bit)
                if old is None or candidate > old[0]:
                    nxt[mask | bit] = (candidate, path + (col,))
        states = nxt
    return list(states[(1 << n) - 1][1])


def quat_distance(a, b):
    # q and -q describe the same orientation.
    similarity = float(np.clip(abs(np.dot(a, b)), 0.0, 1.0))
    return float(2.0 * np.arccos(similarity))


out = Path(args.output)
out.parent.mkdir(parents=True, exist_ok=True)
receipt = {
    "schema_version": "aion.allegro_embodied_schema.v3",
    "seed": args.seed,
    "environment_id": "Isaac-Repose-Cube-Allegro-Direct-v0",
    "teacher_actions": 0,
    "privileged_object_state_used_by_policy": 0,
    "ambient_authority_expansion": 0,
}
env = None
try:
    cfg = parse_env_cfg(receipt["environment_id"], device=args.device, num_envs=1)
    cfg.seed = args.seed
    # Body-schema learning must measure the hand rather than a random collision
    # between the hand and the reset cube.  Remove joint reset noise and move
    # the cube away only during schema interventions.  Manipulation below uses
    # the environment's ordinary in-hand reset.
    cfg.reset_dof_pos_noise = 0.0
    cfg.reset_dof_vel_noise = 0.0
    env = gym.make(receipt["environment_id"], cfg=cfg)
    raw = env.unwrapped
    robot = find_asset(raw, ("hand", "_hand", "robot", "_robot"), "articulations")
    obj = find_asset(raw, ("object", "_object"), "rigid_objects")
    env.reset(seed=args.seed)
    action_shape = tuple(int(v) for v in env.action_space.shape)
    action_dim = int(action_shape[-1])
    joint_names = list(getattr(robot, "joint_names", []))
    q0 = robot.data.joint_pos.detach().cpu().numpy()[0].copy()
    if action_dim != len(q0) or action_dim < 16:
        raise RuntimeError(f"unexpected_allegro_contract:{action_dim}:{len(q0)}")

    def deterministic_reset(seed):
        # Direct-task randomization draws from Torch as well as Gymnasium.  Seed
        # both authorities so paired interventions really share one origin.
        torch.manual_seed(seed)
        np.random.seed(seed)
        env.reset(seed=seed)

    def reset_free_hand(seed):
        deterministic_reset(seed)
        pose = obj.data.root_pose_w.detach().clone()
        pose[:, 0] += 2.0
        obj.write_root_pose_to_sim(pose)
        # One zero-control step commits the isolated physical state.
        env.step(torch.zeros(action_shape, dtype=torch.float32, device=raw.device))

    # Discovery: estimate a robust causal derivative over different physical
    # scales. Identical resets and +/- actions cancel shared relaxation.
    trials = []
    commitments = []
    amplitudes = (0.08, 0.25, 0.60)
    horizons = (1, 3, 7)
    derivatives = np.zeros((action_dim, len(amplitudes) * len(horizons), len(q0)), dtype=np.float32)
    for channel in range(action_dim):
        sample = 0
        for amplitude in amplitudes:
            for horizon in horizons:
                consequences = []
                for sign in (1.0, -1.0):
                    reset_free_hand(args.seed)
                    origin = robot.data.joint_pos.detach().cpu().numpy()[0].copy()
                    action = torch.zeros(action_shape, dtype=torch.float32, device=raw.device)
                    action.reshape(-1, action_dim)[0, channel] = amplitude * sign
                    commitment = {
                        "phase": "schema_discovery",
                        "channel": channel,
                        "amplitude": amplitude * sign,
                        "horizon": horizon,
                        "prior_joint_sha256": hashlib.sha256(origin.tobytes()).hexdigest(),
                    }
                    commitments.append(digest(commitment))
                    for _ in range(horizon):
                        env.step(action)
                    consequences.append(robot.data.joint_pos.detach().cpu().numpy()[0].copy())
                derivative = (consequences[0] - consequences[1]) / (2.0 * amplitude)
                derivatives[channel, sample] = derivative
                trials.append({"channel": channel, "amplitude": amplitude, "horizon": horizon,
                               "response": derivative.round(7).tolist()})
                sample += 1

    robust_response = np.median(derivatives, axis=1)
    score_matrix = np.median(np.abs(derivatives), axis=1)
    assignment = maximum_assignment(score_matrix)

    # Fresh, previously unused intervention parameters test whether the map can
    # reconstruct the affected joint rather than merely fit discovery trials.
    heldout_amplitude, heldout_horizon = 0.42, 5
    effects = []
    heldout_passes = 0
    for channel, assigned_joint in enumerate(assignment):
        consequences = []
        for sign in (1.0, -1.0):
            reset_free_hand(args.seed + 101)
            action = torch.zeros(action_shape, dtype=torch.float32, device=raw.device)
            action.reshape(-1, action_dim)[0, channel] = heldout_amplitude * sign
            commitments.append(digest({"phase": "heldout_reconstruction", "channel": channel,
                                       "value": heldout_amplitude * sign,
                                       "horizon": heldout_horizon, "seed": args.seed + 101}))
            for _ in range(heldout_horizon):
                env.step(action)
            consequences.append(robot.data.joint_pos.detach().cpu().numpy()[0].copy())
        response = (consequences[0] - consequences[1]) / (2.0 * heldout_amplitude)
        magnitude = float(abs(response[assigned_joint]))
        rank = int(np.sum(np.abs(response) > magnitude) + 1)
        discovery_sign = float(np.sign(robust_response[channel, assigned_joint]))
        heldout_sign = float(np.sign(response[assigned_joint]))
        # The semantic body-schema claim is which joint a channel controls.
        # Transient displacement direction may reverse across horizons in an
        # under-damped joint, so sign is retained as a diagnostic—not falsely
        # treated as part of anatomical identity.
        passed = magnitude >= 0.005 and rank == 1
        heldout_passes += int(passed)
        alternatives = np.delete(score_matrix[channel], assigned_joint)
        effects.append({
            "action_channel": channel,
            "joint_index": assigned_joint,
            "joint_name": joint_names[assigned_joint],
            "discovery_strength": float(score_matrix[channel, assigned_joint]),
            "assignment_margin": float(score_matrix[channel, assigned_joint] - np.max(alternatives)),
            "heldout_strength": magnitude,
            "heldout_rank": rank,
            "sign_consistent": discovery_sign == heldout_sign,
            "heldout_passed": passed,
        })

    schema_passed = len(set(assignment)) == action_dim and heldout_passes == action_dim

    manipulation = {"attempted": False, "passed": False, "reason": "body_schema_gate_failed"}
    if schema_passed:
        # Construct finger groups from learned consequences and public joint
        # names. Names identify anatomy, never the action channel mapping.
        groups = {}
        for channel, joint_index in enumerate(assignment):
            name = joint_names[joint_index].lower()
            finger = next((f for f in ("thumb", "index", "middle", "ring") if f in name), "unknown")
            groups.setdefault(finger, []).append(channel)

        # Each candidate is a coordinated, teacher-free hand program. It uses
        # only the discovered schema. Object pose is read after execution solely
        # as the independent outcome authority.
        candidate_specs = []
        for partner in ("index", "middle", "ring"):
            for direction in (1.0, -1.0):
                candidate_specs.append({"thumb": direction, partner: -direction})
                candidate_specs.append({"thumb": direction, partner: direction})

        def run_program(seed, spec, phase):
            deterministic_reset(seed)
            q_before = obj.data.root_quat_w.detach().cpu().numpy()[0].copy()
            p_before = obj.data.root_pos_w.detach().cpu().numpy()[0].copy()
            total_reward = 0.0
            for step in range(24):
                wave = 1.0 if step < 12 else -0.35
                action = torch.zeros(action_shape, dtype=torch.float32, device=raw.device)
                flat = action.reshape(-1, action_dim)[0]
                for finger, direction in spec.items():
                    channels = groups.get(finger, [])
                    for depth, channel in enumerate(channels):
                        flat[channel] = float(np.clip(direction * wave * (0.45 + 0.10 * depth), -0.8, 0.8))
                commitments.append(digest({"phase": phase, "seed": seed, "step": step,
                                           "action": action.detach().cpu().numpy().round(5).tolist()}))
                _, reward, terminated, truncated, _ = env.step(action)
                total_reward += float(reward.detach().cpu().reshape(-1)[0])
                if bool(torch.as_tensor(terminated).reshape(-1)[0]) or bool(torch.as_tensor(truncated).reshape(-1)[0]):
                    break
            q_after = obj.data.root_quat_w.detach().cpu().numpy()[0].copy()
            p_after = obj.data.root_pos_w.detach().cpu().numpy()[0].copy()
            return {"rotation_radians": quat_distance(q_before, q_after),
                    "translation_metres": float(np.linalg.norm(p_after - p_before)),
                    "height_change_metres": float(p_after[2] - p_before[2]),
                    "reward_sum": total_reward, "steps": step + 1}

        development = []
        for index, spec in enumerate(candidate_specs):
            result = run_program(args.seed + 200, spec, f"manipulation_development_{index}")
            development.append({"program": spec, "outcome": result})
        # Prefer object rotation but reject programs that simply throw/drop it.
        viable = [r for r in development if r["outcome"]["translation_metres"] <= 0.30]
        selected = max(viable or development, key=lambda r: r["outcome"]["rotation_radians"])
        sealed = run_program(args.seed + 303, selected["program"], "manipulation_sealed")
        cold = run_program(args.seed + 303, {}, "manipulation_cold")
        manipulation = {
            "attempted": True,
            "candidate_count": len(candidate_specs),
            "selected_program": selected["program"],
            "development_outcome": selected["outcome"],
            "sealed_outcome": sealed,
            "cold_outcome": cold,
            "rotation_lift_vs_cold": float(sealed["rotation_radians"] - cold["rotation_radians"]),
            "passed": sealed["rotation_radians"] >= 0.10
                      and sealed["rotation_radians"] >= cold["rotation_radians"] + 0.05
                      and sealed["translation_metres"] <= 0.30,
        }

    receipt.update({
        "action_shape": action_shape,
        "joint_names": joint_names,
        "joint_count": len(q0),
        "discovery": {"amplitudes": amplitudes, "horizons": horizons,
                      "trial_count": len(trials), "assignment": assignment,
                      "effects": effects, "unique_assigned_joints": len(set(assignment)),
                      "heldout_reconstruction_passes": heldout_passes,
                      "passed": schema_passed},
        "manipulation": manipulation,
        "pre_action_commitments": len(commitments),
        "commitment_chain_sha256": digest(commitments),
        "passed": schema_passed and manipulation["passed"],
        "runtime": {"physics": "PhysX", "host": platform.node(),
                    "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none"},
        "failure": None,
    })
except Exception as exc:
    receipt.update({"passed": False, "failure": {"type": type(exc).__name__,
                    "message": str(exc), "traceback": traceback.format_exc(limit=8)}})
finally:
    if env is not None:
        env.close()
    receipt["receipt_sha256"] = digest(receipt)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True))
    app.close()
