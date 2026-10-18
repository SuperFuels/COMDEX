#!/usr/bin/env python3
"""Read-only structural probe for the pinned Isaac Lab beta2 authority."""
from __future__ import annotations

import argparse
import json

from isaaclab.app import AppLauncher


parser = argparse.ArgumentParser()
parser.add_argument("--task", default="Isaac-Lift-Cube-Franka-v0")
parser.add_argument("--recover-official-franka", action="store_true")
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
args.enable_cameras = True
launcher = AppLauncher(args)
app = launcher.app

import gymnasium as gym  # noqa: E402
import isaaclab_tasks  # noqa: F401,E402
from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402
from isaac_official_asset_recovery import recover_franka  # noqa: E402


def main() -> None:
    cfg = parse_env_cfg(args.task, device=args.device, num_envs=1)
    asset_recovery = recover_franka(cfg) if args.recover_official_franka else {
        "recovery_applied": False, "selected_url": str(cfg.scene.robot.spawn.usd_path)
    }
    entry = gym.spec(args.task)
    report = {
        "task": args.task,
        "entry_point": str(entry.entry_point),
        "kwargs": {key: str(value) for key, value in entry.kwargs.items()},
        "cfg_type": f"{type(cfg).__module__}:{type(cfg).__name__}",
        "scene_fields": sorted(key for key in vars(cfg.scene) if not key.startswith("_")),
        "action_fields": sorted(key for key in vars(cfg.actions) if not key.startswith("_")),
        "observation_groups": sorted(key for key in vars(cfg.observations) if not key.startswith("_")),
        "asset_recovery": asset_recovery,
    }
    env = gym.make(args.task, cfg=cfg)
    try:
        observation, _ = env.reset(seed=1701)
        robot = env.unwrapped.scene["robot"]
        report.update({
            "action_space": repr(env.action_space),
            "observation_space": repr(env.observation_space),
            "observation_keys": sorted(observation),
            "scene_keys": sorted(env.unwrapped.scene.keys()),
            "robot_joint_names": list(getattr(robot, "joint_names", [])),
            "robot_joint_shape": list(robot.data.joint_pos.shape),
            "device": str(env.unwrapped.device),
        })
    print("AION_ISAAC_STRUCTURE=" + json.dumps(report, sort_keys=True))
    env.close()
    app.close()


if __name__ == "__main__":
    main()
