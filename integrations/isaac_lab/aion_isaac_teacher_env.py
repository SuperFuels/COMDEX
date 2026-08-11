"""Register a private Isaac teacher task with attested official asset recovery."""
from __future__ import annotations

import gymnasium as gym

from isaaclab.utils.configclass import configclass
from isaaclab_tasks.manager_based.manipulation.lift.config.franka.joint_pos_env_cfg import (
    FrankaCubeLiftEnvCfg,
)
from isaaclab_tasks.manager_based.manipulation.lift.config.franka.agents.rsl_rl_ppo_cfg import (
    LiftCubePPORunnerCfg,
)


OFFICIAL_FRANKA_5_1 = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/"
    "Isaac/IsaacLab/Robots/FrankaEmika/panda_instanceable.usd"
)
TASK_ID = "AION-Teacher-Lift-Cube-Franka-v0"


@configclass
class AionTeacherLiftCfg(FrankaCubeLiftEnvCfg):
    def __post_init__(self):
        super().__post_init__()
        self.scene.robot.spawn.usd_path = OFFICIAL_FRANKA_5_1


def register() -> list[str]:
    if TASK_ID not in gym.registry:
        gym.register(
            id=TASK_ID,
            entry_point="isaaclab.envs:ManagerBasedRLEnv",
            kwargs={
                "env_cfg_entry_point": f"{__name__}:AionTeacherLiftCfg",
                "rsl_rl_cfg_entry_point": f"{__name__}:LiftCubePPORunnerCfg",
            },
            disable_env_checker=True,
        )
    return []
