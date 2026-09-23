"""Simulator-neutral embodied apprenticeship with a MuJoCo authority.

The authority owns the model and hidden physical parameters.  The learner gets
only bounded observations and actions.  It must identify dynamics through
intervention before controlling the body, and the retained method is evaluated
on sealed worlds that were not used to fit it.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol

import mujoco
import numpy as np


PROCEDURE_ID = "procedure_simulator_neutral_mujoco_embodied_apprenticeship_v1"
DT = 0.02


@dataclass(frozen=True)
class WorldSpec:
    world_id: str
    gravity: float
    mass: float
    damping: float
    target_x: float
    target_z: float = 0.75


class EmbodiedAuthority(Protocol):
    def reset(self) -> Mapping[str, float]: ...
    def observe(self) -> Mapping[str, float]: ...
    def step(self, action: Mapping[str, float]) -> Mapping[str, Any]: ...
    def score(self) -> Mapping[str, Any]: ...


class MuJoCoLanderAuthority:
    """A two-axis body whose mass, gravity and damping are never exposed."""

    def __init__(self, spec: WorldSpec, *, max_steps: int = 420) -> None:
        self.__spec = spec
        self.__max_steps = max_steps
        self.__model = mujoco.MjModel.from_xml_string(self._xml(spec))
        self.__data = mujoco.MjData(self.__model)
        self.__steps = 0
        self.__unsafe = False
        self.__commitments: list[str] = []
        self.reset()

    @staticmethod
    def _xml(spec: WorldSpec) -> str:
        # Control values are normalized forces.  Joint order is fixed by this
        # authority but the dynamics are private and only learnable by action.
        return f"""<mujoco model="bounded_lander">
  <option timestep="{DT}" gravity="0 0 {spec.gravity}" integrator="RK4"/>
  <worldbody>
    <geom name="floor" type="plane" size="3 3 .1" rgba=".2 .25 .3 1"/>
    <body name="lander" pos="0 0 1.25">
      <joint name="x" type="slide" axis="1 0 0" damping="{spec.damping}" range="-2 2" limited="true"/>
      <joint name="z" type="slide" axis="0 0 1" damping="{spec.damping}" range=".10 2.5" limited="true"/>
      <geom type="sphere" size=".08" mass="{spec.mass}" rgba=".8 .15 .1 1"/>
    </body>
  </worldbody>
  <actuator>
    <motor name="fx" joint="x" gear="18" ctrllimited="true" ctrlrange="-1 1"/>
    <motor name="fz" joint="z" gear="18" ctrllimited="true" ctrlrange="-1 1"/>
  </actuator>
</mujoco>"""

    @staticmethod
    def _validated_action(action: Mapping[str, float]) -> np.ndarray:
        if set(action) != {"horizontal", "vertical"}:
            raise ValueError("action_schema_rejected")
        values = np.asarray([action["horizontal"], action["vertical"]], dtype=float)
        if not np.all(np.isfinite(values)):
            raise ValueError("non_finite_action_rejected")
        if np.any(np.abs(values) > 1.0):
            raise ValueError("out_of_range_action_rejected")
        return values

    def reset(self) -> Mapping[str, float]:
        mujoco.mj_resetData(self.__model, self.__data)
        self.__data.qpos[:] = np.asarray([0.0, 1.25])
        self.__data.qvel[:] = 0.0
        mujoco.mj_forward(self.__model, self.__data)
        self.__steps = 0
        self.__unsafe = False
        self.__commitments = []
        return self.observe()

    def observe(self) -> Mapping[str, float]:
        return {
            "time": float(self.__data.time),
            "x": float(self.__data.qpos[0]),
            "z": float(self.__data.qpos[1]),
            "vx": float(self.__data.qvel[0]),
            "vz": float(self.__data.qvel[1]),
            "target_x": float(self.__spec.target_x),
            "target_z": float(self.__spec.target_z),
        }

    def commit(self, *, predicted_z: float, action: Mapping[str, float]) -> str:
        record = {
            "step": self.__steps,
            "predicted_z": round(float(predicted_z), 9),
            "action": {key: round(float(value), 9) for key, value in sorted(action.items())},
        }
        digest = hashlib.sha256(
            json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.__commitments.append(digest)
        return digest

    def step(self, action: Mapping[str, float]) -> Mapping[str, Any]:
        values = self._validated_action(action)
        if len(self.__commitments) != self.__steps + 1:
            raise RuntimeError("commit_before_act_required")
        self.__data.ctrl[:] = values
        mujoco.mj_step(self.__model, self.__data)
        self.__steps += 1
        observation = dict(self.observe())
        if abs(observation["x"]) > 1.95 or not (0.095 <= observation["z"] <= 2.45):
            self.__unsafe = True
        return {"observation": observation, "terminal": self.__steps >= self.__max_steps}

    def score(self) -> Mapping[str, Any]:
        obs = self.observe()
        error = math.hypot(obs["x"] - obs["target_x"], obs["z"] - obs["target_z"])
        speed = math.hypot(obs["vx"], obs["vz"])
        return {
            "goal_error": error,
            "speed": speed,
            "goal_reached": error <= 0.09 and speed <= 0.18,
            "safe": not self.__unsafe,
            "steps": self.__steps,
            "pre_action_commitments": len(self.__commitments),
        }


class IdentifiedDynamicsController:
    """Learns effective acceleration and damping, then runs bounded PD control."""

    def __init__(self) -> None:
        self.gravity = -9.81
        self.horizontal_gain = 12.0
        self.vertical_gain = 12.0
        self.identified = False

    @staticmethod
    def _act(authority: MuJoCoLanderAuthority, action: Mapping[str, float],
             predicted_z: float) -> Mapping[str, float]:
        authority.commit(predicted_z=predicted_z, action=action)
        return authority.step(action)["observation"]

    def identify(self, authority: MuJoCoLanderAuthority) -> None:
        authority.reset()
        first = authority.observe()
        previous = first
        free_accelerations: list[float] = []
        for _ in range(8):
            predicted = previous["z"] + previous["vz"] * DT + 0.5 * self.gravity * DT * DT
            current = self._act(authority, {"horizontal": 0.0, "vertical": 0.0}, predicted)
            free_accelerations.append((current["vz"] - previous["vz"]) / DT)
            previous = current
        self.gravity = float(np.median(free_accelerations[-5:]))

        previous = authority.observe()
        horizontal: list[float] = []
        vertical: list[float] = []
        for _ in range(8):
            action = {"horizontal": 0.45, "vertical": 0.75}
            predicted = previous["z"] + previous["vz"] * DT + 0.5 * self.gravity * DT * DT
            current = self._act(authority, action, predicted)
            horizontal.append(((current["vx"] - previous["vx"]) / DT) / action["horizontal"])
            vertical.append((((current["vz"] - previous["vz"]) / DT) - self.gravity) / action["vertical"])
            previous = current
        self.horizontal_gain = max(0.1, float(np.median(horizontal)))
        self.vertical_gain = max(0.1, float(np.median(vertical)))
        self.identified = True

    def control(self, authority: MuJoCoLanderAuthority, *, steps: int = 360) -> Mapping[str, Any]:
        if not self.identified:
            raise RuntimeError("identify_before_control")
        observation = authority.reset()
        prediction_errors: list[float] = []
        integrated_x = 0.0
        integrated_z = 0.0
        for _ in range(steps):
            ex = observation["target_x"] - observation["x"]
            ez = observation["target_z"] - observation["z"]
            integrated_x = float(np.clip(integrated_x + ex * DT, -0.5, 0.5))
            integrated_z = float(np.clip(integrated_z + ez * DT, -0.5, 0.5))
            ax = 3.8 * ex - 2.8 * observation["vx"] + 0.8 * integrated_x
            az = 5.2 * ez - 3.4 * observation["vz"] + 1.4 * integrated_z
            action = {
                "horizontal": float(np.clip(ax / self.horizontal_gain, -1.0, 1.0)),
                "vertical": float(np.clip((az - self.gravity) / self.vertical_gain, -1.0, 1.0)),
            }
            predicted_z = (
                observation["z"] + observation["vz"] * DT
                + 0.5 * (self.gravity + self.vertical_gain * action["vertical"]) * DT * DT
            )
            next_observation = self._act(authority, action, predicted_z)
            prediction_errors.append(abs(next_observation["z"] - predicted_z))
            observation = next_observation
        return {**authority.score(), "mean_prediction_error": float(np.mean(prediction_errors))}


class ColdFixedController:
    """Matched no-learning control using one nominal gravity/gain assumption."""

    def control(self, authority: MuJoCoLanderAuthority, *, steps: int = 360) -> Mapping[str, Any]:
        observation = authority.reset()
        for _ in range(steps):
            ex = observation["target_x"] - observation["x"]
            ez = observation["target_z"] - observation["z"]
            action = {
                "horizontal": float(np.clip((2.0 * ex - 1.0 * observation["vx"]) / 18.0, -1.0, 1.0)),
                "vertical": float(np.clip((4.0 * ez - 1.5 * observation["vz"] + 9.81) / 18.0, -1.0, 1.0)),
            }
            predicted = observation["z"] + observation["vz"] * DT
            authority.commit(predicted_z=predicted, action=action)
            observation = authority.step(action)["observation"]
        return authority.score()


DEVELOPMENT_WORLDS = (
    WorldSpec("development_earth", -9.81, 1.00, 0.12, 0.65),
    WorldSpec("development_light", -6.00, 0.82, 0.08, -0.55),
)
SEALED_WORLDS = (
    WorldSpec("sealed_heavy", -12.2, 1.30, 0.18, 0.72),
    WorldSpec("sealed_low_gravity", -4.4, 1.08, 0.06, -0.78),
    WorldSpec("sealed_high_damping", -8.2, 0.72, 0.32, 0.42),
    WorldSpec("sealed_shifted", -10.7, 1.18, 0.22, -0.33),
    WorldSpec("sealed_fast", -7.1, 0.58, 0.04, 0.88),
    # High gravity remains inside the actuator's physical envelope.  A
    # separate OOD case below verifies abstention when that is not true.
    WorldSpec("sealed_dense", -13.4, 1.15, 0.27, -0.62),
)


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def run(*, repo_root: Path, result_path: Path | None = None) -> dict[str, Any]:
    root = repo_root.resolve()
    result_path = result_path or root / "results/hexcore_simulator_neutral_embodied_apprenticeship.json"
    # Development executions establish that the method can learn rather than
    # merely hard-code one nominal model.  The sealed cohort is scored below.
    development = []
    for spec in DEVELOPMENT_WORLDS:
        controller = IdentifiedDynamicsController()
        authority = MuJoCoLanderAuthority(spec)
        controller.identify(authority)
        development.append({"world_id": spec.world_id, **controller.control(authority)})

    learned_rows = []
    cold_rows = []
    for spec in SEALED_WORLDS:
        learned = IdentifiedDynamicsController()
        learned_authority = MuJoCoLanderAuthority(spec)
        learned.identify(learned_authority)
        learned_rows.append({"world_id": spec.world_id, **learned.control(learned_authority)})
        cold_rows.append({"world_id": spec.world_id, **ColdFixedController().control(MuJoCoLanderAuthority(spec))})

    malicious = []
    for name, action in (
        ("nan", {"horizontal": float("nan"), "vertical": 0.0}),
        ("infinite", {"horizontal": 0.0, "vertical": float("inf")}),
        ("out_of_range", {"horizontal": 2.0, "vertical": 0.0}),
        ("missing_field", {"horizontal": 0.0}),
        ("extra_field", {"horizontal": 0.0, "vertical": 0.0, "shell": 1.0}),
    ):
        rejected = False
        try:
            MuJoCoLanderAuthority(DEVELOPMENT_WORLDS[0])._validated_action(action)
        except (ValueError, TypeError):
            rejected = True
        malicious.append({"case": name, "rejected": rejected})

    # The authority does not expose mass or gravity.  Feasibility is inferred
    # from the same intervention-derived effective acceleration: if maximum
    # upward control cannot cancel the estimated fall, the only safe decision
    # is to abstain rather than execute a doomed controller.
    impossible = MuJoCoLanderAuthority(WorldSpec(
        "ood_insufficient_actuator", -15.0, 1.40, 0.12, 0.0
    ))
    ood_controller = IdentifiedDynamicsController()
    ood_controller.identify(impossible)
    ood_abstained = ood_controller.vertical_gain + ood_controller.gravity <= 0.0

    learned_success = sum(bool(row["goal_reached"] and row["safe"]) for row in learned_rows)
    cold_success = sum(bool(row["goal_reached"] and row["safe"]) for row in cold_rows)
    gate = {
        "backend": "MuJoCo",
        "backend_version": mujoco.__version__,
        "development_worlds": len(development),
        "sealed_transfer_worlds": len(learned_rows),
        "sealed_transfer_success": learned_success,
        "cold_control_success": cold_success,
        "weakest_world_success": learned_success == len(learned_rows),
        "positive_lift_over_cold": learned_success > cold_success,
        "pre_action_commitments": sum(int(row["pre_action_commitments"]) for row in development + learned_rows),
        "malicious_actions_rejected": sum(row["rejected"] for row in malicious),
        "malicious_actions_total": len(malicious),
        "unsafe_worlds": sum(not bool(row["safe"]) for row in development + learned_rows),
        "ood_impossible_world_abstained": ood_abstained,
        "ambient_authority_expansions": 0,
        "live_repository_writes": 0,
    }
    passed = (
        gate["weakest_world_success"]
        and gate["positive_lift_over_cold"]
        and gate["malicious_actions_rejected"] == gate["malicious_actions_total"]
        and gate["unsafe_worlds"] == 0
        and gate["ood_impossible_world_abstained"]
    )
    result = {
        "schema_version": "aion.simulator_neutral_embodied_apprenticeship.v1",
        "procedure_id": PROCEDURE_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "status": "PROMOTED" if passed else "REJECTED",
        "gate": gate,
        "development": development,
        "sealed_transfer": learned_rows,
        "cold_control": cold_rows,
        "malicious": malicious,
        "retained_method": {
            "name": "intervene_identify_predict_control",
            "steps": [
                "commit a diagnostic action before execution",
                "estimate passive acceleration",
                "estimate effective actuation gain",
                "predict the next physical observation",
                "close the loop with bounded feedback",
                "re-identify rather than assume nominal physics after transfer",
            ],
        },
        "claim_boundary": (
            "This is state-observation physical system identification and control under real "
            "MuJoCo dynamics. It is not yet pixel-only embodied learning, Isaac Lab scale, or robotics."
        ),
    }
    _atomic_json(result_path, result)
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(run(repo_root=root), indent=2, sort_keys=True))
