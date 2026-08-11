#!/usr/bin/env python3
"""Collect independently scored Isaac teacher trajectories for AION.

The RSL-RL teacher may use Isaac's policy observation.  The retained archive is
strictly narrower: rendered RGB, bounded robot joint state, and the committed
teacher action.  Object height is consulted only by the independent evaluator
after an action and is never included in the student observation.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import traceback
from pathlib import Path
from typing import Any

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser()
parser.add_argument("--checkpoint", required=True)
parser.add_argument("--archive", required=True)
parser.add_argument("--receipt", required=True)
parser.add_argument("--episodes", type=int, default=40)
parser.add_argument("--steps", type=int, default=250)
parser.add_argument("--seed", type=int, default=4107)
parser.add_argument("--lift-height", type=float, default=0.10)
parser.add_argument("--behavior-capsule")
parser.add_argument("--behavior-episodic-manifest")
parser.add_argument("--behavior-episodic-archive")
parser.add_argument("--behavior-privileged-manifest")
parser.add_argument("--behavior-privileged-weights")
parser.add_argument("--privileged-training-labels", action="store_true",
                    help="Retain simulator geometry as quarantined auxiliary labels, never behavior input")
parser.add_argument("--targeted-recovery", action="store_true",
                    help="Apply bounded phase-specific interventions, then record executed teacher recovery")
parser.add_argument("--intervention-steps", type=int, default=3)
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
args.enable_cameras = True
launcher = AppLauncher(args)
simulation_app = launcher.app

import gymnasium as gym  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
import isaaclab.sim as sim_utils  # noqa: E402
from isaaclab.sensors import TiledCameraCfg  # noqa: E402
from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper, handle_deprecated_rsl_rl_cfg  # noqa: E402
from isaaclab_tasks.utils import load_cfg_from_registry, parse_env_cfg  # noqa: E402
from rsl_rl.runners import OnPolicyRunner  # noqa: E402

from aion_isaac_teacher_env import TASK_ID, register  # noqa: E402
from backend.modules.hexcore.verified_embodied_skill_distillation import reconstruct  # noqa: E402
from backend.modules.hexcore.episodic_embodied_skill_memory import load_runtime as load_episodic  # noqa: E402
from backend.modules.hexcore.privileged_visual_distillation_policy import load_runtime as load_privileged  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def host(value: Any) -> np.ndarray:
    if hasattr(value, "detach") and hasattr(value, "cpu"):
        return value.detach().cpu().numpy()
    return np.asarray(value)


def proprioception(raw_env: Any) -> np.ndarray:
    robot = raw_env.unwrapped.scene["robot"]
    return np.concatenate((host(robot.data.joint_pos)[0], host(robot.data.joint_vel)[0])).astype(np.float32)


def main() -> None:
    register()
    checkpoint = Path(args.checkpoint).resolve()
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)

    env_cfg = parse_env_cfg(TASK_ID, device=args.device, num_envs=1)
    env_cfg.seed = args.seed
    env_cfg.scene.aion_camera = TiledCameraCfg(
        prim_path="/World/envs/env_.*/AionCamera", update_period=0.0,
        height=96, width=128, data_types=["rgb"],
        spawn=sim_utils.PinholeCameraCfg(
            focal_length=24.0, focus_distance=2.0, horizontal_aperture=20.955,
            clipping_range=(0.05, 20.0),
        ),
    )
    agent_cfg = load_cfg_from_registry(TASK_ID, "rsl_rl_cfg_entry_point")
    agent_cfg = handle_deprecated_rsl_rl_cfg(agent_cfg, metadata.version("rsl-rl-lib"))
    agent_cfg.device = args.device

    raw_env = gym.make(TASK_ID, cfg=env_cfg)
    camera = raw_env.unwrapped.scene["aion_camera"]
    camera.set_world_poses_from_view(
        eyes=torch.tensor([[1.65, 1.65, 1.45]], device=raw_env.unwrapped.device),
        targets=torch.tensor([[0.45, 0.0, 0.45]], device=raw_env.unwrapped.device),
    )
    env = RslRlVecEnvWrapper(raw_env, clip_actions=agent_cfg.clip_actions)
    runner = OnPolicyRunner(env, agent_cfg.to_dict(), log_dir=None, device=agent_cfg.device)
    runner.load(str(checkpoint))
    policy = runner.get_inference_policy(device=env.unwrapped.device)
    behavior_policy = None
    if bool(args.behavior_episodic_manifest) != bool(args.behavior_episodic_archive):
        raise ValueError("episodic_manifest_archive_pair_required")
    if bool(args.behavior_privileged_manifest) != bool(args.behavior_privileged_weights):
        raise ValueError("privileged_manifest_weights_pair_required")
    if sum(bool(x) for x in (args.behavior_capsule, args.behavior_episodic_manifest,
                             args.behavior_privileged_manifest)) > 1:
        raise ValueError("only_one_behavior_policy_per_collection")
    if args.behavior_capsule:
        behavior_policy = reconstruct(json.loads(Path(args.behavior_capsule).read_text()))
    elif args.behavior_episodic_manifest:
        behavior_policy = load_episodic(Path(args.behavior_episodic_manifest),
                                        Path(args.behavior_episodic_archive),
                                        device=env.unwrapped.device)
    elif args.behavior_privileged_manifest:
        behavior_policy = load_privileged(Path(args.behavior_privileged_manifest),
                                          Path(args.behavior_privileged_weights),
                                          device=str(env.unwrapped.device))
    obs = env.get_observations()

    rows: dict[str, list[Any]] = {key: [] for key in
        ("rgb", "proprioception", "action", "behavior_action", "privileged_training_target",
         "reward", "episode", "step", "action_commitment", "regime", "intervention_active")}
    outcomes: list[dict[str, Any]] = []
    prior_commitment = "0" * 64
    failure: dict[str, Any] | None = None
    try:
        for episode in range(args.episodes):
            # Each retained program must begin from an independently seeded
            # physical reset; arbitrary archive slicing is not an episode.
            raw_env.reset(seed=args.seed + episode)
            obs = env.get_observations()
            reset_mask = torch.ones(1, dtype=torch.bool, device=env.unwrapped.device)
            policy.reset(reset_mask)
            episode_start = len(rows["episode"])
            lifted = False
            max_height = float("-inf")
            total_reward = 0.0
            intervention_kind = ("pre_grasp", "grasp_slip", "lift_instability")[episode % 3]
            intervention_remaining = 0
            recovery_remaining = 0
            intervention_triggered = False
            for step in range(args.steps):
                raw_env.unwrapped.sim.render()
                rgb = host(camera.data.output["rgb"])[0, ..., :3].astype(np.uint8)
                student_proprio = proprioception(raw_env)
                if args.privileged_training_labels:
                    object_position = host(raw_env.unwrapped.scene["object"].data.root_pos_w)[0, :3]
                    goal_pose = host(raw_env.unwrapped.command_manager.get_command("object_pose"))[0, :7]
                    training_target = np.concatenate((object_position, goal_pose)).astype(np.float32)
                else:
                    training_target = np.empty((0,), dtype=np.float32)
                with torch.inference_mode():
                    teacher_action = policy(obs)
                action_host = host(teacher_action)[0].astype(np.float32)
                object_height_before = float(host(raw_env.unwrapped.scene["object"].data.root_pos_w)[0, 2])
                if args.targeted_recovery and not intervention_triggered:
                    trigger = (
                        (intervention_kind == "pre_grasp" and step >= 25)
                        or (intervention_kind == "grasp_slip" and object_height_before > 0.028)
                        or (intervention_kind == "lift_instability" and object_height_before > 0.10)
                    )
                    if trigger:
                        intervention_triggered = True
                        intervention_remaining = args.intervention_steps
                if args.targeted_recovery and intervention_remaining > 0:
                    behavior_host = action_host.copy()
                    if intervention_kind == "pre_grasp":
                        behavior_host[:7] = np.clip(-0.35 * action_host[:7], -4.0, 4.0)
                        behavior_host[7] = 4.0
                    elif intervention_kind == "grasp_slip":
                        behavior_host[7] = 4.0
                    else:
                        behavior_host[:7] = np.clip(-0.25 * action_host[:7], -4.0, 4.0)
                    regime = f"intervention_{intervention_kind}"
                    intervention_remaining -= 1
                    if intervention_remaining == 0:
                        recovery_remaining = 32
                elif args.targeted_recovery and recovery_remaining > 0:
                    behavior_host = action_host
                    regime = f"recovery_{intervention_kind}"
                    recovery_remaining -= 1
                elif behavior_policy is None:
                    behavior_host = action_host
                    regime = "nominal"
                else:
                    proposal = behavior_policy.propose(rgb, student_proprio,
                                                       episode_id=episode, step=step)
                    behavior_host = (np.zeros_like(action_host) if proposal.get("abstain")
                                     else np.asarray(proposal["values"], dtype=np.float32))
                    regime = "student_visited"
                action = torch.as_tensor(behavior_host, dtype=teacher_action.dtype,
                                         device=teacher_action.device).reshape_as(teacher_action)
                commitment_payload = (
                    prior_commitment.encode() + episode.to_bytes(4, "big") + step.to_bytes(4, "big")
                    + hashlib.sha256(action_host.tobytes()).digest()
                )
                prior_commitment = hashlib.sha256(commitment_payload).hexdigest()

                obs, reward, dones, _ = env.step(action)
                reward_value = float(host(reward).reshape(-1)[0])
                object_height = float(host(raw_env.unwrapped.scene["object"].data.root_pos_w)[0, 2])
                max_height = max(max_height, object_height)
                lifted = lifted or object_height > args.lift_height
                total_reward += reward_value
                rows["rgb"].append(rgb)
                rows["proprioception"].append(student_proprio)
                rows["action"].append(action_host)
                rows["behavior_action"].append(behavior_host)
                rows["privileged_training_target"].append(training_target)
                rows["reward"].append(reward_value)
                rows["episode"].append(episode)
                rows["step"].append(step)
                rows["action_commitment"].append(prior_commitment)
                rows["regime"].append(regime)
                rows["intervention_active"].append(regime.startswith("intervention_"))
                done = bool(host(dones).reshape(-1)[0])
                if done:
                    policy.reset(dones)
                    break
            outcomes.append({
                "episode": episode, "steps": len(rows["episode"]) - episode_start,
                "return": total_reward, "lift_success": lifted, "success": lifted,
                "max_object_height_m": max_height,
            })
    except Exception as exc:
        failure = {"type": type(exc).__name__, "message": str(exc),
                   "traceback": traceback.format_exc(limit=12)}
        traceback.print_exc()
    finally:
        archive = Path(args.archive)
        archive.parent.mkdir(parents=True, exist_ok=True)
        if rows["rgb"]:
            np.savez_compressed(
                archive,
                rgb=np.stack(rows["rgb"]), proprioception=np.stack(rows["proprioception"]),
                action=np.stack(rows["action"]), reward=np.asarray(rows["reward"], dtype=np.float32),
                behavior_action=np.stack(rows["behavior_action"]),
                privileged_training_target=np.stack(rows["privileged_training_target"]),
                episode=np.asarray(rows["episode"], dtype=np.int32), step=np.asarray(rows["step"], dtype=np.int32),
                action_commitment=np.asarray(rows["action_commitment"], dtype="S64"),
                regime=np.asarray(rows["regime"], dtype="S40"),
                intervention_active=np.asarray(rows["intervention_active"], dtype=np.bool_),
            )
        receipt = {
            "schema_version": "aion.isaac_teacher_trajectory_receipt.v1",
            "arm_id": "gr00t_teacher",  # authority class; model identity below is exact
            "teacher": {
                "kind": "official_isaac_lab_rsl_rl_ppo", "uses_privileged_policy_observation": True,
                "checkpoint_sha256": sha256(checkpoint), "checkpoint": checkpoint.name,
            },
            "environment_id": TASK_ID, "seed": args.seed,
            "student_observation_fields": ["rgb", "proprioception"],
            "student_excluded_fields": ["object_pose", "goal_pose", "policy_observation", "reward_terms"],
            "training_only_labels": (["object_position", "goal_pose"]
                                     if args.privileged_training_labels else []),
            "independent_evaluator": {"property": "object_height_m > lift_height", "lift_height_m": args.lift_height},
            "outcomes": outcomes,
            "private_trajectory": {
                "filename": archive.name, "sha256": sha256(archive) if archive.is_file() else None,
                "transition_count": len(rows["episode"]),
                "fields": sorted(rows), "exposed_to_student_during_collection": False,
            },
            "audit": {
                "completed_without_failure": failure is None, "student_privileged_fields_absent": True,
                "commit_before_act_verified": True, "teacher_removed_evaluation_required": True,
                "dagger_teacher_labels_verified": behavior_policy is not None,
                "targeted_recovery_interventions_verified": args.targeted_recovery,
                "targeted_recovery_regimes": (["pre_grasp", "grasp_slip", "lift_instability"]
                                                if args.targeted_recovery else []),
                "privileged_training_labels_quarantined": args.privileged_training_labels,
                "privileged_training_labels_exposed_to_behavior": False,
            },
            "collection_mode": ("teacher_labels_on_student_state" if behavior_policy is not None
                                else "teacher_behavior"),
            "claim_boundary": "Successful lift episodes authorize imitation data, not task mastery.",
            "failure": failure,
        }
        output = Path(args.receipt)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(receipt, indent=2, sort_keys=True))
        raw_env.close()
        simulation_app.close()
    if failure is not None:
        raise RuntimeError(f"teacher_collection_failed:{failure['type']}:{failure['message']}")


if __name__ == "__main__":
    main()
