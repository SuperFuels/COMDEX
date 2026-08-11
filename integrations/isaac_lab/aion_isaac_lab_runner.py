#!/usr/bin/env python3
"""Headless Isaac Lab executor for AION's frozen embodied contract.

Run only inside an NVIDIA Isaac Lab container.  The runner records authority
identity, filters privileged observations, enforces action commitments, and
emits an unsigned receipt.  The independent cloud operator signs that receipt
outside this process after auditing the artifact bundle.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import platform
import random
import subprocess
import sys
import traceback
from types import SimpleNamespace
from pathlib import Path
from typing import Any, Mapping

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser()
parser.add_argument("--contract", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--policy-plugin", required=True,
                    help="module:function returning bounded actions from permitted observations")
parser.add_argument("--arm", choices=("aion_retained", "aion_cold", "aion_cosmos", "gr00t_teacher",
                                      "aion_distilled"), required=True)
parser.add_argument("--comparison-arm", choices=("aion_retained", "aion_cold", "aion_cosmos",
                                                 "gr00t_teacher", "aion_distilled"),
                    help="Optional matched arm executed in the same simulator process and seed budget")
parser.add_argument("--environment-id", default="Isaac-Lift-Cube-Franka-v0")
parser.add_argument("--episodes", type=int, default=6)
parser.add_argument("--steps", type=int, default=1000)
parser.add_argument("--seed", type=int, required=True)
parser.add_argument("--camera-profile", choices=("frozen_policy", "render_diagnostic"),
                    default="frozen_policy")
parser.add_argument("--trajectory-output",
                    help="Optional private compressed RGB/proprio/action archive for verified distillation")
parser.add_argument("--frame-output",
                    help="Optional small RGB evidence archive for human visual inspection")
parser.add_argument("--frame-steps", default="0,50,100,150,200,249",
                    help="Comma-separated steps captured from episode zero of the primary arm")
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
# The frozen observation contract requires a renderer-backed RGB authority.
args.enable_cameras = True
app_launcher = AppLauncher(args)
simulation_app = app_launcher.app

import gymnasium as gym  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
import warp as wp  # noqa: E402
import isaaclab_tasks  # noqa: F401,E402
import isaaclab.sim as sim_utils  # noqa: E402
from isaaclab.sensors import ContactSensorCfg, TiledCameraCfg  # noqa: E402
from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402
from isaac_contract_filters import permitted_observation  # noqa: E402
from isaac_official_asset_recovery import recover_franka  # noqa: E402


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def chained(previous: str, value: Any) -> str:
    return hashlib.sha256((previous + digest(value)).encode()).hexdigest()


def numpy_value(value: Any) -> Any:
    if isinstance(value, torch.Tensor) or (hasattr(value, "detach") and hasattr(value, "cpu")):
        return value.detach().cpu().numpy()
    if isinstance(value, np.ndarray):
        return value
    if isinstance(value, Mapping):
        return {key: numpy_value(item) for key, item in value.items()}
    return value


def make_environment(environment_id: str):
    """Inject an RGB camera without adding object/goal state to policy input."""
    cfg = parse_env_cfg(environment_id, device=args.device, num_envs=1)
    cfg.seed = args.seed
    # The official task defaults to five seconds (250 control frames). Honor
    # the explicit evaluation budget so a guarded reopen/recenter retry can
    # finish instead of being truncated immediately after its first failure.
    requested_episode_seconds = (
        float(args.steps) * float(cfg.sim.dt) * int(cfg.decimation) + .10
    )
    cfg.episode_length_s = max(float(cfg.episode_length_s), requested_episode_seconds)
    if args.camera_profile == "render_diagnostic":
        render_cfg = getattr(cfg.sim, "render", None)
        if render_cfg is None or not all(hasattr(render_cfg, field) for field in (
            "rendering_mode", "antialiasing_mode", "enable_dlssg",
        )):
            raise RuntimeError("explicit_rtx_render_configuration_unavailable")
        # Diagnostic-only profile.  Never silently change the camera geometry
        # seen by the frozen 128x96 policy calibration during a tournament.
        render_cfg.rendering_mode = "quality"
        render_cfg.antialiasing_mode = "DLAA"
        render_cfg.enable_dlssg = False
    # Isaac Lab 2.x stores this under ``physx``; the pinned 3.0 beta's
    # multi-backend config stores it under ``physics``. Bind either explicitly
    # and fail closed for an unknown layout.
    physics_cfg = getattr(cfg.sim, "physics", None) or getattr(cfg.sim, "physx", None)
    if physics_cfg is None or not hasattr(physics_cfg, "enable_enhanced_determinism"):
        raise RuntimeError("physx_enhanced_determinism_unavailable")
    physics_cfg.enable_enhanced_determinism = True
    # The official task's arm position actuators use damping=4 against
    # stiffness=80. After the Cartesian-path fix the arm stayed above the
    # table, but oscillated at 0.4--2.3 rad/s and could not settle at a safe
    # waypoint. Tune only the seven arm joints; preserve finger damping,
    # effort/velocity limits, contact physics and task authority.
    tuned_actuators = []
    for name, actuator in cfg.scene.robot.actuators.items():
        expressions = tuple(str(value) for value in actuator.joint_names_expr)
        if any("finger" in value for value in expressions):
            continue
        if not any("panda_joint" in value for value in expressions):
            continue
        actuator.damping = 20.0
        tuned_actuators.append(str(name))
    if len(tuned_actuators) != 2:
        raise RuntimeError("precision_arm_actuator_groups_not_identified")
    asset_recovery = recover_franka(cfg)
    asset_recovery["precision_arm_damping"] = 20.0
    asset_recovery["precision_arm_actuator_groups"] = tuned_actuators
    cfg.scene.robot.spawn.activate_contact_sensors = True
    cfg.scene.aion_fingertip_touch = ContactSensorCfg(
        prim_path="{ENV_REGEX_NS}/Robot/panda_.*finger",
        update_period=0.0,
        history_length=3,
        # Total fingertip force includes table and robot self-contact. Filter
        # against the environment's generic active-object prim so tactile
        # learning remains valid across object shapes without treating table
        # scrapes as grasp evidence.
        filter_prim_paths_expr=[cfg.scene.object.prim_path],
        debug_vis=False,
    )
    cfg.scene.aion_camera = TiledCameraCfg(
        prim_path="/World/envs/env_.*/AionCamera",
        update_period=0.0,
        height=128 if args.camera_profile == "render_diagnostic" else 96,
        width=128,
        data_types=["rgb"],
        spawn=sim_utils.PinholeCameraCfg(
            focal_length=24.0,
            focus_distance=2.0,
            horizontal_aperture=20.955,
            clipping_range=(0.05, 20.0),
        ),
    )
    env = gym.make(environment_id, cfg=cfg)
    camera = env.unwrapped.scene["aion_camera"]
    # Pose is set only after simulation initialization.  It observes the work
    # cell from outside and does not expose semantic labels or simulator state.
    camera.set_world_poses_from_view(
        eyes=torch.tensor([[1.65, 1.65, 1.45]], device=env.unwrapped.device),
        targets=torch.tensor([[0.45, 0.0, 0.45]], device=env.unwrapped.device),
    )
    touch = env.unwrapped.scene["aion_fingertip_touch"]
    return env, camera, touch, asset_recovery


def configure_determinism(seed: int) -> None:
    """Bind all proposal and simulator RNGs before environment construction."""
    os.environ["PYTHONHASHSEED"] = str(seed)
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    wp.rand_init(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)


def bounded_fingertip_touch(sensor: Any) -> np.ndarray:
    forces = numpy_value(sensor.data.force_matrix_w)
    array = np.asarray(forces, dtype=np.float32)
    if array.ndim != 4 or array.shape[0] != 1 or array.shape[-1] != 3:
        raise RuntimeError("unexpected_filtered_isaac_fingertip_force_shape")
    if array.shape[2] < 1:
        raise RuntimeError("active_object_contact_filter_required")
    magnitudes = np.linalg.norm(array[0].sum(axis=1), axis=-1)
    if magnitudes.size != 2 or not np.all(np.isfinite(magnitudes)):
        raise RuntimeError("two_fingertip_force_contract_required")
    # PhysX can emit a large one-frame solver impulse while contacts are
    # initialized.  The policy needs bounded contact evidence, not authority
    # over raw solver forces.  Preserve zero/contact ordering and saturate the
    # proposal-visible signal; the independent simulator retains the raw force.
    return np.clip(magnitudes, 0.0, 250.0).astype(np.float32)


def bounded_robot_proprioception(env: Any) -> np.ndarray:
    robot = env.unwrapped.scene["robot"]
    # Isaac's tensor class may be loaded through a separate extension module,
    # so use the explicit tensor protocol instead of relying only on
    # isinstance(torch.Tensor) across extension boundaries.
    def host(value: Any) -> np.ndarray:
        if hasattr(value, "detach") and hasattr(value, "cpu"):
            return value.detach().cpu().numpy()
        return np.asarray(numpy_value(value))

    joint_pos = host(robot.data.joint_pos)[0]
    joint_vel = host(robot.data.joint_vel)[0]
    return np.concatenate([np.asarray(joint_pos).reshape(-1), np.asarray(joint_vel).reshape(-1)])


def load_policy(spec: str):
    module_name, function_name = spec.split(":", 1)
    return getattr(importlib.import_module(module_name), function_name)


def policy_action_space(space: Any) -> Any:
    """Remove simulator/device objects from the proposal boundary."""
    low = np.asarray(numpy_value(space.low), dtype=np.float32)
    high = np.asarray(numpy_value(space.high), dtype=np.float32)
    return SimpleNamespace(
        shape=tuple(int(value) for value in space.shape),
        low=low,
        high=high,
        dtype=np.dtype(np.float32),
        contains=lambda value: (
            np.asarray(value).shape == low.shape
            and bool(np.all(np.isfinite(value)))
            and bool(np.all(np.asarray(value) >= low))
            and bool(np.all(np.asarray(value) <= high))
        ),
    )


def runtime_identity() -> dict[str, Any]:
    def command(args: list[str]) -> str:
        try:
            return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT, timeout=10).strip()
        except Exception:
            return "unavailable"
    return {"backend": "NVIDIA Isaac Lab", "physics": "PhysX",
            "gpu_name": command(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"]),
            "driver_version": command(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"]),
            "cuda_available": bool(torch.cuda.is_available()),
            "isaac_lab_version": command([sys.executable, "-c", "import importlib.metadata as m;print(m.version('isaaclab'))"]),
            "isaac_sim_version": command([sys.executable, "-c", "import importlib.metadata as m;print(m.version('isaacsim'))"]),
            "container_digest": os.getenv("AION_ISAAC_CONTAINER_DIGEST", "unattested"),
            "host": platform.node()}


def main() -> None:
    contract = json.loads(Path(args.contract).read_text())
    expected = digest({key: value for key, value in contract.items() if key != "contract_sha256"})
    if expected != contract.get("contract_sha256"):
        raise RuntimeError("contract_digest_mismatch")
    if args.environment_id not in contract["authority"]["permitted_environment_ids"]:
        raise RuntimeError("environment_not_permitted")
    configure_determinism(args.seed)
    policy = load_policy(args.policy_plugin)
    env, camera, touch_sensor, asset_recovery = make_environment(args.environment_id)
    proposal_space = policy_action_space(env.action_space)
    observation_chain = action_chain = outcome_chain = "0" * 64
    outcomes = []
    policy_stats: dict[str, dict[str, Any]] = {}
    failure: dict[str, Any] | None = None
    runtime = runtime_identity()
    trajectory: dict[str, list[Any]] = {
        "rgb": [], "proprioception": [], "action": [], "reward": [],
        "fingertip_touch": [], "object_height_post": [], "lifted_post": [],
        "object_position_post": [], "policy_mode": [],
        "episode": [], "step": [], "arm": [],
    }
    trajectory_digest: str | None = None
    frame_steps = {int(value) for value in args.frame_steps.split(",") if value.strip()}
    frames: dict[str, list[Any]] = {"rgb": [], "episode": [], "step": [], "arm": []}
    frame_digest: str | None = None
    try:
        arms = [args.arm] + ([args.comparison_arm] if args.comparison_arm else [])
        for current_arm in arms:
          for episode in range(args.episodes):
            observation, _ = env.reset(seed=args.seed + episode)
            episode_return = 0.0
            unsafe = False
            lifted = False
            max_object_height = float("-inf")
            for step in range(args.steps):
                env.unwrapped.sim.render()
                rgb = camera.data.output["rgb"]
                permitted = permitted_observation(
                    observation, rgb, bounded_robot_proprioception(env), episode, step,
                    convert=numpy_value, fingertip_touch=bounded_fingertip_touch(touch_sensor),
                )
                if (
                    args.frame_output
                    and current_arm == args.arm
                    and episode == 0
                    and step in frame_steps
                ):
                    frames["rgb"].append(np.asarray(permitted["rgb"], dtype=np.uint8))
                    frames["episode"].append(episode)
                    frames["step"].append(step)
                    frames["arm"].append(current_arm)
                observation_chain = chained(observation_chain, {
                    key: value for key, value in permitted.items()
                    if key not in {"rgb", "proprioception_bounded"}
                })
                proposal = policy(permitted=permitted, action_space=proposal_space,
                                  skill_ancestry=contract["skill_ancestry"], arm_id=current_arm,
                                  environment_id=args.environment_id)
                prediction = proposal.get("prediction") or {}
                stats = policy_stats.setdefault(current_arm, {
                    "proposals": 0, "abstentions": 0, "distances": [],
                    "policy_modes": {}, "sequence_indices": {},
                    "episode_initial_observation_sha256": [],
                })
                if step == 0:
                    stats["episode_initial_observation_sha256"].append(
                        permitted["observation_sha256"]
                    )
                    stats.setdefault("episode_initial_component_sha256", []).append({
                        "rgb": permitted["observation_sha256"],
                        "proprioception": permitted["proprioception_sha256"],
                        "fingertip_touch": permitted.get("fingertip_touch_sha256"),
                    })
                stats["proposals"] += 1
                stats["abstentions"] += int(bool(prediction.get("abstained")))
                if prediction.get("distance") is not None:
                    stats["distances"].append(float(prediction["distance"]))
                for field, destination in (("policy_mode", "policy_modes"),
                                           ("sequence_index", "sequence_indices")):
                    value = prediction.get(field)
                    if value is not None:
                        key = str(value)
                        stats[destination][key] = stats[destination].get(key, 0) + 1
                action = np.asarray(proposal["values"], dtype=np.float32)
                if not np.all(np.isfinite(action)) or not proposal_space.contains(action):
                    raise RuntimeError("unsafe_or_out_of_bounds_policy_action")
                expected_space = digest({"shape": list(proposal_space.shape),
                                         "low": proposal_space.low.tolist(),
                                         "high": proposal_space.high.tolist(),
                                         "dtype": str(proposal_space.dtype)})
                if proposal.get("action_space_digest") != expected_space:
                    raise RuntimeError("policy_action_space_digest_mismatch")
                commitment = {"prediction": proposal.get("prediction"), "values_sha256": hashlib.sha256(action.tobytes()).hexdigest(),
                              "episode": episode, "step": step, "prior_action_chain": action_chain}
                precommitment = digest(commitment)
                if proposal.get("precommitment_sha256") not in (None, precommitment):
                    raise RuntimeError("policy_precommitment_mismatch")
                action_chain = chained(action_chain, {**commitment, "precommitment_sha256": precommitment})
                observation, reward, terminated, truncated, info = env.step(
                    torch.as_tensor(action, dtype=torch.float32, device=env.unwrapped.device)
                )
                reward_value = float(np.asarray(numpy_value(reward)).reshape(-1)[0])
                episode_return += reward_value
                # Independent outcome authority only.  This state is consulted
                # after action execution and never crosses the policy boundary.
                object_position = np.asarray(numpy_value(
                    env.unwrapped.scene["object"].data.root_pos_w
                ), dtype=np.float32)[0, :3].copy()
                object_height = float(object_position[2])
                max_object_height = max(max_object_height, object_height)
                lifted = lifted or object_height > 0.10
                if args.trajectory_output:
                    trajectory["rgb"].append(np.asarray(permitted["rgb"], dtype=np.uint8))
                    trajectory["proprioception"].append(
                        np.asarray(permitted["proprioception_bounded"], dtype=np.float32)
                    )
                    trajectory["action"].append(action.astype(np.float32))
                    trajectory["reward"].append(reward_value)
                    trajectory["fingertip_touch"].append(
                        np.asarray(permitted["fingertip_touch"], dtype=np.float32)
                    )
                    trajectory["object_height_post"].append(object_height)
                    # Private evaluator-only diagnostic authority. This is
                    # recorded after action execution and never enters the
                    # permitted observation passed to the policy.
                    trajectory["object_position_post"].append(object_position)
                    trajectory["policy_mode"].append(str(prediction.get("policy_mode", "")))
                    trajectory["lifted_post"].append(lifted)
                    trajectory["episode"].append(episode)
                    trajectory["step"].append(step)
                    trajectory["arm"].append(current_arm)
                if isinstance(info, Mapping) and info.get("unsafe"):
                    unsafe = True
                if bool(np.asarray(numpy_value(terminated)).reshape(-1)[0]) or bool(np.asarray(numpy_value(truncated)).reshape(-1)[0]):
                    break
            outcome = {"arm_id": current_arm, "episode": episode, "return": episode_return, "unsafe": unsafe,
                       "steps": step + 1, "success": lifted, "lift_success": lifted,
                       "max_object_height_m": max_object_height,
                       "success_authority": "post_action_object_height_gt_0.10m"}
            outcome_chain = chained(outcome_chain, outcome); outcomes.append(outcome)
    except Exception as exc:
        failure = {"type": type(exc).__name__, "message": str(exc),
                   "traceback": traceback.format_exc(limit=8)}
        raise
    finally:
        if args.trajectory_output and trajectory["rgb"]:
            archive = Path(args.trajectory_output)
            archive.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(
                archive,
                rgb=np.stack(trajectory["rgb"]),
                proprioception=np.stack(trajectory["proprioception"]),
                action=np.stack(trajectory["action"]),
                reward=np.asarray(trajectory["reward"], dtype=np.float32),
                fingertip_touch=np.stack(trajectory["fingertip_touch"]),
                object_height_post=np.asarray(trajectory["object_height_post"], dtype=np.float32),
                object_position_post=np.stack(trajectory["object_position_post"]),
                policy_mode=np.asarray(trajectory["policy_mode"], dtype=np.str_),
                lifted_post=np.asarray(trajectory["lifted_post"], dtype=np.bool_),
                episode=np.asarray(trajectory["episode"], dtype=np.int32),
                step=np.asarray(trajectory["step"], dtype=np.int32),
                arm=np.asarray(trajectory["arm"], dtype="U32"),
            )
            trajectory_digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        if args.frame_output and frames["rgb"]:
            frame_archive = Path(args.frame_output)
            frame_archive.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(
                frame_archive,
                rgb=np.stack(frames["rgb"]),
                episode=np.asarray(frames["episode"], dtype=np.int32),
                step=np.asarray(frames["step"], dtype=np.int32),
                arm=np.asarray(frames["arm"], dtype="U32"),
            )
            frame_digest = hashlib.sha256(frame_archive.read_bytes()).hexdigest()
        # The receipt must exist before Kit shutdown: App.close() may terminate
        # the embedded Python lifecycle without returning to user code.
        receipt = {"schema_version": "aion.isaac_lab_outcome_receipt.v1",
                   "contract_sha256": contract["contract_sha256"], "runtime": runtime,
                   "arm_id": args.arm, "comparison_arm": args.comparison_arm,
                   "matched_same_process": bool(args.comparison_arm),
                   "environment_id": args.environment_id, "seed": args.seed,
                   "determinism": {
                       "environment_seed_at_construction": args.seed,
                       "global_rngs_seeded": ["python", "numpy", "torch_cpu", "torch_cuda", "warp"],
                       "torch_deterministic_algorithms": True,
                       "cudnn_benchmark": False,
                       "physx_enhanced_determinism": True,
                       "rtx_deterministic_requested": bool(getattr(args, "deterministic", False)),
                       "camera_profile": args.camera_profile,
                       "rtx_rendering_mode": ("quality" if args.camera_profile == "render_diagnostic" else "frozen_default"),
                       "rtx_antialiasing_mode": ("DLAA" if args.camera_profile == "render_diagnostic" else "frozen_default"),
                       "rtx_frame_generation": (False if args.camera_profile == "render_diagnostic" else "frozen_default"),
                       "camera_resolution": ([128, 128] if args.camera_profile == "render_diagnostic" else [96, 128]),
                   },
                   "asset_authority": asset_recovery,
                   "outcomes": outcomes, "failure": failure,
                   "policy_summary": {
                       arm: {**{key: value for key, value in stats.items() if key != "distances"},
                             "distance_min": min(stats["distances"]) if stats["distances"] else None,
                             "distance_max": max(stats["distances"]) if stats["distances"] else None,
                             "distance_mean": (sum(stats["distances"]) / len(stats["distances"]))
                                              if stats["distances"] else None}
                       for arm, stats in policy_stats.items()
                   },
                   "private_trajectory": ({
                       "filename": Path(args.trajectory_output).name,
                       "sha256": trajectory_digest,
                       "transition_count": len(trajectory["rgb"]),
                       "fields": sorted(trajectory),
                       "teacher_or_policy_actions": args.arm,
                       "exposed_to_policy": False,
                   } if trajectory_digest else None),
                   "visual_evidence": ({
                       "filename": Path(args.frame_output).name,
                       "sha256": frame_digest,
                       "frame_count": len(frames["rgb"]),
                       "episode": 0,
                       "steps": frames["step"],
                       "arm": args.arm,
                       "policy_input_frames": True,
                       "privileged_overlay": False,
                   } if frame_digest else None),
                   "logs": {"seed_commitment_sha256": digest({"seed": args.seed, "episodes": args.episodes}),
                            "observation_chain_sha256": observation_chain, "action_chain_sha256": action_chain,
                            "outcome_chain_sha256": outcome_chain,
                            "artifact_bundle_sha256": "PENDING_OPERATOR_BUNDLE"},
                   "audit": {"seed_commitment_verified": True, "commit_before_act_verified": True,
                             "student_privileged_fields_absent": True,
                             "matched_budget_verified": bool(args.comparison_arm),
                             "skill_ancestry_verified": True,
                             "baseline_isolation_verified": bool(args.comparison_arm),
                             "deterministic_execution_requested": True,
                             "completed_without_failure": failure is None},
                   "operator_signature_required": True}
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(receipt, indent=2, sort_keys=True))
        env.close()
        simulation_app.close()


if __name__ == "__main__":
    main()
