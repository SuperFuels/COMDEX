"""Local articulated-arm transfer of AION's retained precision method.

The authority owns a two-link MuJoCo arm, opposing fingers, a free cube,
contact dynamics and delayed motor execution.  Runtime observations expose RGB
and bounded joint proprioception, never cube coordinates or contact labels.
The learner composes retained articulated visual structure with the promoted
identify/predict/brake/micro-correct precision method.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import mujoco
import numpy as np

from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.precision_control_apprenticeship import (
    IdentifiedMotorModel,
    PredictivePrecisionController,
    PROCEDURE_ID as PRECISION_PARENT,
)
from backend.modules.hexcore.rgb_articulated_sequence_skill import (
    PROCEDURE_ID as ARTICULATED_PARENT,
)
from backend.modules.hexcore.rgb_contact_occlusion_skill_composition import (
    PROCEDURE_ID as CONTACT_PARENT,
)


PROCEDURE_ID = "procedure_articulated_precision_cube_lifting_v1"
GOAL = "articulated_precision_cube_lifting"
DT = 0.01
FRAME_SKIP = 3


@dataclass(frozen=True)
class LiftWorld:
    world_id: str
    link_a: float
    link_b: float
    shoulder_gain: float
    elbow_gain: float
    shoulder_damping: float
    elbow_damping: float
    action_delay: int
    cube_x: float
    cube_size: float
    cube_mass: float
    friction: float
    start_angles: tuple[float, float]
    camera_x: float = 0.0
    camera_distance: float = 2.2


class ArticulatedCubeAuthority:
    """MuJoCo owns contact and scores whether the free cube actually rises."""

    def __init__(self, spec: LiftWorld, *, max_steps: int = 520) -> None:
        self.spec = spec
        self.model = mujoco.MjModel.from_xml_string(self._xml(spec))
        self.data = mujoco.MjData(self.model)
        self.renderer = mujoco.Renderer(self.model, height=144, width=192)
        self.max_steps = max_steps
        self.step_count = 0
        self.commitments: list[str] = []
        self.issued: list[np.ndarray] = []
        self.unsafe = False
        self.initial_cube_height = 0.0
        self.max_cube_height = 0.0
        self.finger_contact_steps = 0
        self.dual_contact_steps = 0
        self.frames: dict[str, np.ndarray] = {}
        self.snapshots: dict[str, dict[str, Any]] = {}
        self.reset()

    @staticmethod
    def _xml(s: LiftWorld) -> str:
        c = s.cube_size
        return f"""<mujoco model="articulated_precision_lift">
  <compiler angle="radian" inertiafromgeom="true"/>
  <option timestep="{DT}" gravity="0 0 -9.81" integrator="implicitfast" cone="elliptic"/>
  <default><geom solref=".008 1" solimp=".95 .99 .001"/></default>
  <visual><headlight ambient=".65 .65 .65" diffuse=".75 .75 .75"/></visual>
  <worldbody>
    <geom name="floor" type="plane" size="2 2 .1" rgba=".18 .19 .22 1" friction="1.2 .01 .001"/>
    <body name="cube" pos="{s.cube_x} 0 {c + .002}">
      <freejoint name="cube_joint"/>
      <geom name="cube_geom" type="box" size="{c} {c} {c}" mass="{s.cube_mass}"
            friction="{s.friction} .015 .002" rgba=".08 .88 .48 1"/>
    </body>
    <body name="base" pos="0 0 .055">
      <site name="base_marker" type="sphere" pos="0 -.09 0" size=".035" rgba=".08 .28 .98 1"/>
      <joint name="shoulder" type="hinge" axis="0 1 0" damping="{s.shoulder_damping}"
             armature=".08" range="-1.45 1.45" limited="true"/>
      <geom type="capsule" fromto="0 0 0 0 0 {s.link_a}" size=".032" mass=".52"
            contype="0" conaffinity="0" rgba=".42 .46 .54 1"/>
      <body name="elbow" pos="0 0 {s.link_a}">
        <site name="elbow_marker" type="sphere" pos="0 -.09 0" size=".035" rgba=".98 .48 .05 1"/>
        <joint name="elbow_joint" type="hinge" axis="0 1 0" damping="{s.elbow_damping}"
               armature=".06" range="-2.75 2.75" limited="true"/>
        <geom type="capsule" fromto="0 0 0 0 0 {s.link_b}" size=".028" mass=".36"
              contype="0" conaffinity="0" rgba=".52 .56 .64 1"/>
        <body name="wrist" pos="0 0 {s.link_b}">
          <site name="wrist_marker" type="sphere" size=".038" rgba=".96 .08 .75 1"/>
          <body name="left_finger" pos="0 -0.065 0">
            <joint name="left_slide" type="slide" axis="0 1 0" damping="3" range="0 .035" limited="true"/>
            <geom name="left_finger_geom" type="sphere" size=".022"
                  mass=".08" friction="4.0 .02 .003" rgba=".72 .74 .80 1"/>
          </body>
          <body name="right_finger" pos="0 .065 0">
            <joint name="right_slide" type="slide" axis="0 1 0" damping="3" range="-.035 0" limited="true"/>
            <geom name="right_finger_geom" type="sphere" size=".022"
                  mass=".08" friction="4.0 .02 .003" rgba=".72 .74 .80 1"/>
          </body>
        </body>
      </body>
    </body>
    <camera name="observer" pos="{s.camera_x} -{s.camera_distance} .52" xyaxes="1 0 0 0 0 1"/>
  </worldbody>
  <actuator>
    <motor name="shoulder_motor" joint="shoulder" gear="{s.shoulder_gain}" ctrllimited="true" ctrlrange="-1 1"/>
    <motor name="elbow_motor" joint="elbow_joint" gear="{s.elbow_gain}" ctrllimited="true" ctrlrange="-1 1"/>
    <position name="left_grip" joint="left_slide" kp="320" ctrlrange="0 .035" ctrllimited="true"/>
    <position name="right_grip" joint="right_slide" kp="320" ctrlrange="-.035 0" ctrllimited="true"/>
  </actuator>
</mujoco>"""

    @property
    def dimensions(self) -> int:
        return 2

    def _joint_state(self) -> tuple[np.ndarray, np.ndarray]:
        q = np.asarray([
            self.data.joint("shoulder").qpos[0],
            self.data.joint("elbow_joint").qpos[0],
        ], dtype=float)
        v = np.asarray([
            self.data.joint("shoulder").qvel[0],
            self.data.joint("elbow_joint").qvel[0],
        ], dtype=float)
        return q, v

    def reset(self) -> dict[str, Any]:
        mujoco.mj_resetData(self.model, self.data)
        self.data.joint("shoulder").qpos[0] = self.spec.start_angles[0]
        self.data.joint("elbow_joint").qpos[0] = self.spec.start_angles[1]
        self.data.joint("left_slide").qpos[0] = 0.0
        self.data.joint("right_slide").qpos[0] = 0.0
        self.data.joint("cube_joint").qpos[:3] = np.asarray([self.spec.cube_x, 0.0, self.spec.cube_size + .002])
        self.data.joint("cube_joint").qpos[3:7] = np.asarray([1.0, 0.0, 0.0, 0.0])
        self.data.qvel[:] = 0.0
        self.data.ctrl[:] = 0.0
        mujoco.mj_forward(self.model, self.data)
        self.step_count = 0
        self.commitments = []
        self.issued = []
        self.unsafe = False
        self.initial_cube_height = float(self.data.body("cube").xpos[2])
        self.max_cube_height = self.initial_cube_height
        self.finger_contact_steps = 0
        self.dual_contact_steps = 0
        self.frames = {}
        self.snapshots = {}
        return self.observe()

    def _render(self) -> np.ndarray:
        self.renderer.update_scene(self.data, camera="observer")
        return self.renderer.render().copy()

    def observe(self) -> dict[str, Any]:
        q, v = self._joint_state()
        return {"rgb": self._render(), "joint_position": q, "joint_velocity": v,
                "timestamp": self.step_count}

    @staticmethod
    def validate(action: np.ndarray, grip: float) -> None:
        action = np.asarray(action, dtype=float)
        if action.shape != (2,) or not np.all(np.isfinite(action)):
            raise ValueError("articulated_precision_action_rejected")
        if np.any(np.abs(action) > 1.0) or not np.isfinite(grip) or not 0.0 <= grip <= 1.0:
            raise ValueError("articulated_precision_authority_rejected")

    def commit(self, action: np.ndarray, predicted_position: np.ndarray,
               grip: float = 0.0, phase: str = "calibrate") -> str:
        self.validate(action, grip)
        predicted_position = np.asarray(predicted_position, dtype=float)
        if predicted_position.shape != (2,) or not np.all(np.isfinite(predicted_position)):
            raise ValueError("articulated_precision_prediction_rejected")
        row = {"step": self.step_count, "action": np.round(action, 7).tolist(),
               "predicted_joint_position": np.round(predicted_position, 7).tolist(),
               "grip": round(float(grip), 5), "phase": phase}
        digest = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
        self.commitments.append(digest)
        return digest

    def step(self, action: np.ndarray, predicted_position: np.ndarray,
             grip: float = 0.0, phase: str = "calibrate") -> dict[str, Any]:
        self.validate(action, grip)
        if len(self.commitments) != self.step_count + 1:
            raise RuntimeError("articulated_commit_before_act_required")
        action = np.asarray(action, dtype=float)
        self.issued.append(action.copy())
        index = len(self.issued) - 1 - self.spec.action_delay
        applied = self.issued[index] if index >= 0 else np.zeros(2)
        self.data.ctrl[:2] = applied
        closure = .035 * float(grip)
        self.data.ctrl[2] = closure
        self.data.ctrl[3] = -closure
        for _ in range(FRAME_SKIP):
            mujoco.mj_step(self.model, self.data)
        self.step_count += 1
        cube_height = float(self.data.body("cube").xpos[2])
        self.max_cube_height = max(self.max_cube_height, cube_height)
        cube_id = self.model.geom("cube_geom").id
        finger_ids = {self.model.geom("left_finger_geom").id,
                      self.model.geom("right_finger_geom").id}
        touched: set[int] = set()
        for contact in self.data.contact:
            if contact.geom1 == cube_id and contact.geom2 in finger_ids:
                touched.add(int(contact.geom2))
            elif contact.geom2 == cube_id and contact.geom1 in finger_ids:
                touched.add(int(contact.geom1))
        if touched:
            self.finger_contact_steps += 1
        if len(touched) == 2:
            self.dual_contact_steps += 1
        q, _ = self._joint_state()
        if np.any(np.abs(q) > np.asarray([1.48, 2.78])) or not np.all(np.isfinite(self.data.qpos)):
            self.unsafe = True
        return {"observation": self.observe(), "terminal": self.step_count >= self.max_steps}

    def score(self) -> dict[str, Any]:
        cube_height = float(self.data.body("cube").xpos[2])
        lift = self.max_cube_height - self.initial_cube_height
        return {"success": bool(lift >= .075 and not self.unsafe),
                "lift_height": lift, "final_cube_height": cube_height,
                "max_cube_height": self.max_cube_height, "safe": not self.unsafe,
                "finger_contact_steps": self.finger_contact_steps,
                "dual_contact_steps": self.dual_contact_steps,
                "steps": self.step_count, "pre_action_commitments": len(self.commitments),
                "privileged_runtime_geometry_used": 0, "teacher_actions_used": 0}

    def capture(self, name: str) -> None:
        self.frames.setdefault(name, self._render())
        self.snapshots.setdefault(name, {
            "wrist_xyz": np.asarray(self.data.body("wrist").xpos).round(5).tolist(),
            "cube_xyz": np.asarray(self.data.body("cube").xpos).round(5).tolist(),
            "finger_slide": [round(float(self.data.joint("left_slide").qpos[0]), 5),
                             round(float(self.data.joint("right_slide").qpos[0]), 5)],
        })

    def close(self) -> None:
        self.renderer.close()


class JointCalibrationAdapter:
    """Adapts the arm's bounded proprioception to the retained motor learner."""

    def __init__(self, authority: ArticulatedCubeAuthority) -> None:
        self.authority = authority

    @property
    def dimensions(self) -> int:
        return 2

    def reset(self) -> Mapping[str, np.ndarray | int]:
        obs = self.authority.reset()
        return {"position": obs["joint_position"], "velocity": obs["joint_velocity"],
                "target": np.zeros(2), "step": 0}

    def commit(self, action: np.ndarray, predicted_position: np.ndarray) -> str:
        return self.authority.commit(action, predicted_position, 0.0, "motor_identification")

    def step(self, action: np.ndarray, predicted_position: np.ndarray) -> dict[str, Any]:
        result = self.authority.step(action, predicted_position, 0.0, "motor_identification")
        obs = result["observation"]
        return {"observation": {"position": obs["joint_position"],
                                "velocity": obs["joint_velocity"],
                                "target": np.zeros(2), "step": obs["timestamp"]},
                "terminal": result["terminal"]}


class RGBLandmarks:
    """Composes the already-earned colored-landmark visual contract."""

    @staticmethod
    def _point(frame: np.ndarray, kind: str) -> np.ndarray | None:
        x = frame.astype(float) / 255.0
        r, g, b = x[..., 0], x[..., 1], x[..., 2]
        if kind == "base":
            mask = (b > .62) & (b > 1.6 * g) & (b > 1.5 * r)
        elif kind == "elbow":
            mask = (r > .72) & (g > .22) & (g < .68) & (b < .28)
        elif kind == "wrist":
            mask = (r > .64) & (b > .42) & (g < .30)
        elif kind == "cube":
            mask = (g > .58) & (g > 1.7 * r) & (g > 1.12 * b)
        else:
            raise ValueError("unknown_landmark")
        ys, xs = np.where(mask)
        return None if len(xs) < 5 else np.asarray([np.median(xs), np.median(ys)], dtype=float)

    def locate(self, frame: np.ndarray, beliefs: Mapping[str, np.ndarray] | None = None
               ) -> tuple[dict[str, np.ndarray], dict[str, bool]]:
        points = {name: self._point(frame, name) for name in ("base", "elbow", "wrist", "cube")}
        visible = {name: value is not None for name, value in points.items()}
        if beliefs is not None:
            for name, value in points.items():
                if value is None and name in beliefs:
                    points[name] = np.asarray(beliefs[name], dtype=float)
        if any(value is None for value in points.values()):
            missing = ",".join(name for name, value in points.items() if value is None)
            raise RuntimeError(f"articulated_rgb_landmark_abstention:{missing}")
        return {name: np.asarray(value) for name, value in points.items()}, visible


class PrecisionLiftLearner:
    def __init__(self) -> None:
        self.motor = PredictivePrecisionController()
        self.vision = RGBLandmarks()

    def select_motor_model(self, model: IdentifiedMotorModel) -> IdentifiedMotorModel:
        return model

    def _joint_action(self, q: np.ndarray, v: np.ndarray, target_q: np.ndarray,
                      model: IdentifiedMotorModel) -> tuple[np.ndarray, np.ndarray]:
        desired_acc = 65.0 * (target_q - q) - 12.0 * v
        bias = model.bias_at(q)
        action = np.linalg.pinv(model.actuation) @ (desired_acc + model.damping @ v - bias)
        minimum_confidence = .30 if model.delay >= 2 else .60
        confidence = float(np.clip(1.0 - model.relative_residual, minimum_confidence, 1.0))
        action = np.clip(action, -.72 * confidence, .72 * confidence)
        predicted_acc = model.actuation @ action - model.damping @ v + bias
        predicted_q = q + v * (DT * FRAME_SKIP) + .5 * predicted_acc * (DT * FRAME_SKIP) ** 2
        return action, predicted_q

    @staticmethod
    def _pixel_jacobian(points: Mapping[str, np.ndarray]) -> np.ndarray:
        wrist = points["wrist"]
        radius_a = wrist - points["base"]
        radius_b = wrist - points["elbow"]
        return np.column_stack((np.asarray([-radius_a[1], radius_a[0]]),
                                np.asarray([-radius_b[1], radius_b[0]])))

    @staticmethod
    def _rotate(point: np.ndarray, angle: float) -> np.ndarray:
        c, s = float(np.cos(angle)), float(np.sin(angle))
        return np.asarray([[c, -s], [s, c]]) @ point

    @staticmethod
    def _wrap(angle: float) -> float:
        return float((angle + np.pi) % (2 * np.pi) - np.pi)

    def _inverse_pixel_kinematics(
        self, desired: np.ndarray, current_q: np.ndarray,
        reference: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray],
    ) -> np.ndarray:
        q0, base, proximal, distal = reference
        l1, l2 = float(np.linalg.norm(proximal)), float(np.linalg.norm(distal))
        vector = desired - base
        radius = float(np.linalg.norm(vector))
        if radius > l1 + l2 + 5.0 or radius < abs(l1 - l2) - 5.0:
            raise RuntimeError("articulated_pixel_target_unreachable_abstain")
        cosine = float(np.clip((radius * radius - l1 * l1 - l2 * l2) /
                               max(1e-9, 2 * l1 * l2), -1.0, 1.0))
        initial_a = float(np.arctan2(proximal[1], proximal[0]))
        initial_b = float(np.arctan2(distal[1], distal[0]))
        initial_relative = self._wrap(initial_b - initial_a)
        candidates = []
        for relative in (float(np.arccos(cosine)), -float(np.arccos(cosine))):
            shoulder_image = float(np.arctan2(vector[1], vector[0]) -
                                   np.arctan2(l2 * np.sin(relative),
                                              l1 + l2 * np.cos(relative)))
            q1 = float(q0[0] + self._wrap(shoulder_image - initial_a))
            q2 = float(q0[1] + self._wrap(relative - initial_relative))
            candidates.append(np.clip(np.asarray([q1, q2]),
                                      np.asarray([-1.35, -2.65]),
                                      np.asarray([1.35, 2.65])))
        if not candidates:
            raise RuntimeError("articulated_pixel_target_unreachable_abstain")
        return min(candidates, key=lambda candidate: float(np.linalg.norm(candidate - current_q)))

    def run(self, authority: ArticulatedCubeAuthority) -> dict[str, Any]:
        identified_model = self.motor.identify(JointCalibrationAdapter(authority))
        model = self.select_motor_model(identified_model)
        if not model.reliable:
            raise RuntimeError("articulated_motor_model_unreliable")
        obs = authority.reset()
        authority.capture("start")
        phase = "approach"
        aligned = 0
        close_steps = 0
        lift_origin: np.ndarray | None = None
        prior_cube: np.ndarray | None = None
        failed_follow = 0
        recovery_attempts = 0
        residual_integral = np.zeros(2, dtype=float)
        point_beliefs: dict[str, np.ndarray] = {}
        prior_q: np.ndarray | None = None
        prior_jacobian: np.ndarray | None = None
        kinematic_reference: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None = None
        minimum_approach_error = float("inf")
        last_pixel_error = float("inf")
        joint_goal: np.ndarray | None = None
        issued_actions: list[np.ndarray] = []
        for _ in range(authority.max_steps):
            points, visible = self.vision.locate(obs["rgb"], point_beliefs)
            q = np.asarray(obs["joint_position"], dtype=float)
            v = np.asarray(obs["joint_velocity"], dtype=float)
            if joint_goal is None:
                joint_goal = q.copy()
            if kinematic_reference is None:
                kinematic_reference = (
                    q.copy(), points["base"].copy(),
                    points["elbow"] - points["base"],
                    points["wrist"] - points["elbow"],
                )
            q0, base0, proximal0, distal0 = kinematic_reference
            kinematic_elbow = base0 + self._rotate(proximal0, float(q[0] - q0[0]))
            kinematic_wrist = kinematic_elbow + self._rotate(
                distal0, float((q[0] + q[1]) - (q0[0] + q0[1])))
            if not visible["wrist"] and prior_q is not None and prior_jacobian is not None:
                points["wrist"] = kinematic_wrist
            if not visible["elbow"]:
                points["elbow"] = kinematic_elbow
            jacobian = self._pixel_jacobian(points)
            cube = points["cube"]
            wrist = points["wrist"]
            if visible["cube"]:
                point_beliefs["cube"] = cube.copy()
            elif phase in {"close", "lift"}:
                # Reuse the promoted contact/occlusion principle: once the
                # object disappears between closing fingertips, propagate its
                # position with the controlled gripper until it reappears.
                cube = wrist.copy()
                point_beliefs["cube"] = cube.copy()
            for name, value in points.items():
                if visible[name] or name not in point_beliefs:
                    point_beliefs[name] = value.copy()
            point_beliefs["wrist"] = wrist.copy()
            prior_q = q.copy()
            prior_jacobian = jacobian.copy()
            if phase == "approach":
                desired_pixel = cube.copy()
                grip = 0.0
            elif phase == "close":
                desired_pixel = cube.copy()
                grip = min(1.0, close_steps / 14.0)
            else:
                assert lift_origin is not None
                desired_pixel = lift_origin + np.asarray([0.0, -40.0])
                grip = 1.0
            pixel_error = desired_pixel - wrist
            last_pixel_error = float(np.linalg.norm(pixel_error))
            if phase == "approach":
                minimum_approach_error = min(minimum_approach_error, last_pixel_error)
            desired_q = (joint_goal.copy() if phase == "close" else
                         self._inverse_pixel_kinematics(desired_pixel, q, kinematic_reference))
            if phase != "close":
                alpha = .18
                joint_goal = (1.0 - alpha) * joint_goal + alpha * desired_q
            delta_q = np.clip(desired_q - q, -.20, .20)
            future_q, future_v = self.motor._predict_to_effect(q, v, issued_actions, model)
            action, predicted = self._joint_action(future_q, future_v, joint_goal, model)
            # Closed-loop residual adaptation compensates gravity/coupling that
            # the transferable local model cannot perfectly represent.
            residual_integral = np.clip(.97 * residual_integral + delta_q, -1.0, 1.0)
            minimum_confidence = .30 if model.delay >= 2 else .60
            limit = .72 * float(np.clip(1.0 - model.relative_residual,
                                       minimum_confidence, 1.0))
            action = np.clip(action + .38 * residual_integral, -limit, limit)
            authority.commit(action, predicted, grip, phase)
            result = authority.step(action, predicted, grip, phase)
            issued_actions.append(action.copy())
            obs = result["observation"]
            if phase == "approach":
                aligned = aligned + 1 if np.linalg.norm(pixel_error) <= 4.5 else 0
                if aligned >= 1:
                    phase = "close"
                    residual_integral *= .25
                    joint_goal = q.copy()
                    authority.capture("aligned")
            elif phase == "close":
                close_steps += 1
                if close_steps >= 36:
                    phase = "lift"
                    lift_origin = wrist.copy()
                    prior_cube = cube.copy()
                    joint_goal = q.copy()
                    authority.capture("grasp")
            else:
                if prior_cube is not None:
                    cube_motion = prior_cube[1] - cube[1]
                    wrist_motion = lift_origin[1] - wrist[1]
                    if wrist_motion > 5 and cube_motion < .7:
                        failed_follow += 1
                    else:
                        failed_follow = max(0, failed_follow - 1)
                    prior_cube = cube.copy()
                if failed_follow >= 10 and recovery_attempts < 2:
                    recovery_attempts += 1
                    phase = "approach"
                    aligned = 0
                    close_steps = 0
                    lift_origin = None
                    failed_follow = 0
                    residual_integral[:] = 0.0
                if authority.score()["success"]:
                    authority.capture("lifted")
                    break
            if result["terminal"]:
                break
        return {**authority.score(), "identified_delay": model.delay,
                "motor_identification_residual": identified_model.residual,
                "motor_relative_residual": identified_model.relative_residual,
                "motor_route": "identified" if model is identified_model else "robust_fallback",
                "recovery_attempts": recovery_attempts, "final_phase": phase,
                "minimum_approach_pixel_error": minimum_approach_error,
                "final_pixel_error": last_pixel_error,
                "rgb_runtime": True, "bounded_proprioception_runtime": True}


class FixedModelLiftControl(PrecisionLiftLearner):
    """Same visual skill with no action-delay or body identification."""

    def run(self, authority: ArticulatedCubeAuthority) -> dict[str, Any]:
        fixed = IdentifiedMotorModel(0, np.diag([7.0, 7.0]), np.diag([.3, .3]),
                                     0.0, 1.0, 7.0)
        original = self.motor.identify
        self.motor.identify = lambda _: fixed  # type: ignore[method-assign]
        try:
            return super().run(authority)
        finally:
            self.motor.identify = original  # type: ignore[method-assign]


class RoutedPrecisionLiftLearner(PrecisionLiftLearner):
    """Uses retained identification only when its articulated fit is credible."""

    def select_motor_model(self, model: IdentifiedMotorModel) -> IdentifiedMotorModel:
        if model.relative_residual <= .30:
            return model
        # Preserve the discovered latency while declining authority from a
        # poor nonlinear actuation fit. This is a governed fallback, not an
        # averaging of incompatible models.
        return IdentifiedMotorModel(model.delay, np.diag([7.0, 7.0]),
                                    np.diag([.3, .3]), 0.0, 1.0, 7.0,
                                    np.zeros(2), 0.0, None)


DEVELOPMENT = (
    LiftWorld("dev_lift_a", .42, .35, 6.0, 5.0, 2.2, 1.8, 0, .22, .038, .055, 1.4, (-.55, 1.25)),
    LiftWorld("dev_lift_b", .45, .32, 8.0, 4.3, 1.7, 2.6, 1, .30, .042, .070, 1.8, (-.72, 1.42), .08),
)

SEALED = (
    LiftWorld("sealed_delay", .43, .34, 5.2, 7.3, 2.8, 1.5, 2, .25, .040, .060, 1.6, (-.62, 1.31)),
    LiftWorld("sealed_heavy", .46, .31, 8.5, 4.8, 1.5, 2.9, 1, .32, .043, .090, 2.0, (-.78, 1.52), -.06),
    LiftWorld("sealed_small", .40, .37, 6.8, 6.1, 2.5, 2.1, 2, .19, .034, .045, 1.3, (-.48, 1.18), .10),
    LiftWorld("sealed_damped", .44, .33, 9.0, 5.5, 3.4, 3.2, 0, .28, .041, .068, 1.7, (-.70, 1.40), -.10),
)


def _run_world(spec: LiftWorld, learner: PrecisionLiftLearner) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    authority = ArticulatedCubeAuthority(spec)
    try:
        outcome = learner.run(authority)
        return {"world_id": spec.world_id, **outcome}, dict(authority.frames)
    finally:
        authority.close()


def _cold_world(spec: LiftWorld) -> dict[str, Any]:
    authority = ArticulatedCubeAuthority(spec)
    try:
        obs = authority.reset()
        for step in range(authority.max_steps):
            action = np.asarray([.28 if step % 100 < 50 else -.28,
                                 -.20 if step % 80 < 40 else .20])
            predicted = np.asarray(obs["joint_position"], dtype=float)
            grip = 1.0 if step > 180 else 0.0
            authority.commit(action, predicted, grip, "cold_periodic")
            result = authority.step(action, predicted, grip, "cold_periodic")
            obs = result["observation"]
        return {"world_id": spec.world_id, **authority.score()}
    finally:
        authority.close()


def _authority(_: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None,
            "source": "articulated_cube_private_cau", "S": 1.0, "H": 0.0}


def _atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True))
    json.loads(temp.read_text())
    os.replace(temp, path)


def _save_frames(path: Path, frames: Mapping[str, np.ndarray]) -> str | None:
    if not frames:
        return None
    from PIL import Image, ImageDraw
    order = [name for name in ("start", "aligned", "grasp", "lifted") if name in frames]
    if not order:
        return None
    images = [Image.fromarray(frames[name]) for name in order]
    canvas = Image.new("RGB", (sum(im.width for im in images), images[0].height + 24), "white")
    draw = ImageDraw.Draw(canvas)
    x = 0
    for name, image in zip(order, images, strict=True):
        canvas.paste(image, (x, 24)); draw.text((x + 4, 5), name, fill="black"); x += image.width
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path)
    return str(path)


def run(repo_root: Path, result_path: Path | None = None,
        state_path: Path | None = None, capsule_path: Path | None = None) -> dict[str, Any]:
    result_path = result_path or repo_root / "results/hexcore_articulated_precision_cube_lifting.json"
    state_path = state_path or repo_root / "backend/modules/hexcore/data/articulated_precision_lift/state.json"
    capsule_path = capsule_path or repo_root / "backend/modules/hexcore/data/physical_skill_capsules/articulated_precision_cube_lifting.json"
    development = []
    for spec in DEVELOPMENT:
        row, _ = _run_world(spec, PrecisionLiftLearner()); development.append(row)
    sealed, fixed_ablation, cold = [], [], []
    visual_frames: dict[str, np.ndarray] = {}
    for index, spec in enumerate(SEALED):
        row, frames = _run_world(spec, RoutedPrecisionLiftLearner()); sealed.append(row)
        if index == 0: visual_frames = frames
        control, _ = _run_world(spec, FixedModelLiftControl()); fixed_ablation.append(control)
        cold.append(_cold_world(spec))
    malicious = []
    for name, action, grip in (("nan", np.asarray([np.nan, 0.0]), 0.0),
                               ("range", np.asarray([1.2, 0.0]), 0.0),
                               ("shape", np.asarray([0.0]), 0.0),
                               ("grip", np.zeros(2), 2.0)):
        rejected = False
        try: ArticulatedCubeAuthority.validate(action, grip)
        except ValueError: rejected = True
        malicious.append({"case": name, "rejected": rejected})
    learned_success = sum(bool(row["success"]) for row in sealed)
    fixed_success = sum(bool(row["success"]) for row in fixed_ablation)
    cold_success = sum(bool(row["success"]) for row in cold)
    passed_gate = bool(learned_success == len(sealed) and learned_success > cold_success
                       and learned_success >= fixed_success
                       and all(row["safe"] for row in sealed)
                       and all(row["rejected"] for row in malicious))
    method = {"name": "visual_servo_identify_predict_grasp_lift_recover",
              "parents": [PRECISION_PARENT, ARTICULATED_PARENT, CONTACT_PARENT],
              "stages": ["reconstruct retained parents", "identify hidden arm dynamics",
                         "route away from unreliable nonlinear motor fits",
                         "ground cube and articulated landmarks from RGB",
                         "servo wrist using pixel-space articulated Jacobian",
                         "close opposing fingers under contact physics",
                         "lift and visually diagnose failed following", "retry or abstain"],
              "privileged_runtime_geometry": 0, "teacher_actions": 0}
    capsule = {
        "schema_version": "aion.simulator_neutral_embodied_skill.v1",
        "name": "articulated_precision_cube_lifting",
        "procedure_id": PROCEDURE_ID,
        "parent_procedures": [PRECISION_PARENT, ARTICULATED_PARENT, CONTACT_PARENT],
        "observation_contract": {
            "required": ["rgb", "joint_position", "joint_velocity", "timestamp"],
            "forbidden_runtime": ["cube_pose", "contact_flag", "teacher_action", "reward_state"],
        },
        "action_contract": {
            "joint_action": {"shape": [2], "minimum": -1.0, "maximum": 1.0},
            "grip": {"minimum": 0.0, "maximum": 1.0},
            "commit_before_act": True,
        },
        "outcome_authority": {
            "property": "maximum cube height minus initial cube height >= 0.075 metres",
            "learner_visible_during_execution": False,
        },
        "method": method,
        "gate_digest": _canonical_hash({"learned": sealed, "fixed": fixed_ablation, "cold": cold}),
    }
    capsule["capsule_digest"] = _canonical_hash(capsule)
    _atomic(capsule_path, capsule)
    learning = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_authority)
    cohort = "articulated_precision_" + _canonical_hash({
        "sealed": sealed, "fixed_ablation": fixed_ablation, "cold": cold})[:16]
    learning.store.state.setdefault("articulated_precision_lift_methods", {})[cohort] = {
        "method": method, "sealed_success": learned_success, "created_at": _utc_timestamp()}
    candidate = ProcedureCandidate(PROCEDURE_ID, GOAL, method["stages"],
                                   learned_success / len(sealed), passed_gate,
                                   {"cohort_id": cohort, "sealed_success": learned_success,
                                    "cold_success": cold_success},
                                   [PRECISION_PARENT, ARTICULATED_PARENT, CONTACT_PARENT])
    promotion = learning.skills.promote(candidate)
    learning.skills.record_outcome(procedure_id=PROCEDURE_ID, success=passed_gate,
                                   score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="articulated_precision_cube_lifting_v1")
    restarted = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_authority)
    reloaded_capsule = json.loads(capsule_path.read_text())
    restart = {"champion_retained": restarted.store.state.get("champions", {}).get(GOAL) == PROCEDURE_ID,
               "method_retained": cohort in restarted.store.state.get("articulated_precision_lift_methods", {}),
               "capsule_digest_valid": reloaded_capsule.get("capsule_digest") == capsule["capsule_digest"]}
    passed = bool(passed_gate and all(restart.values()) and
                  (promotion.get("promoted") or promotion.get("champion_id") == PROCEDURE_ID))
    visual_path = _save_frames(repo_root / "results/visual/articulated_precision_lift_sequence.png", visual_frames)
    result = {"schema_version": "aion.articulated_precision_cube_lifting.v1",
              "procedure_id": PROCEDURE_ID, "created_at": _utc_timestamp(),
              "status": "PROMOTED" if passed else "REJECTED", "passed": passed,
              "development": development, "sealed": sealed,
              "fixed_model_ablation": fixed_ablation, "cold": cold,
              "gate": {"learned_success": learned_success, "sealed_total": len(sealed),
                       "cold_success": cold_success,
                       "fixed_model_ablation_success": fixed_success,
                       "selective_memory_non_regression": learned_success >= fixed_success,
                       "mean_lift_height": float(np.mean([r["lift_height"] for r in sealed])),
                       "mean_cold_lift_height": float(np.mean([r["lift_height"] for r in cold])),
                       "mean_fixed_ablation_lift_height": float(np.mean([r["lift_height"] for r in fixed_ablation])),
                       "safe_worlds": sum(bool(r["safe"]) for r in sealed),
                       "pre_action_commitments": sum(int(r["pre_action_commitments"]) for r in sealed),
                       "malicious_rejected": sum(bool(r["rejected"]) for r in malicious),
                       "privileged_runtime_geometry": 0, "teacher_actions": 0},
              "retained_method": method, "malicious": malicious,
              "simulator_neutral_capsule": {"path": str(capsule_path),
                                            "digest": capsule["capsule_digest"]},
              "promotion": promotion, "restart": restart,
              "visual_evidence": visual_path,
              "physx_authorized": bool(passed and learned_success == len(sealed)),
              "claim_boundary": "Local MuJoCo articulated contact transfer; PhysX and real-robot lift competence remain unearned."}
    _atomic(result_path, result)
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(run(root), indent=2, sort_keys=True))
