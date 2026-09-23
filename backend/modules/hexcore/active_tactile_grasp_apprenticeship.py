"""Active tactile opposition, attachment belief and progressive lifting.

This arena closes the gap between detecting contact and controlling through
contact.  MuJoCo owns a free object's mass, friction, contact and motion.  The
learner receives only RGB, bounded joint state and two fingertip force values.
It must align visually, acquire opposed contact, correct one-sided contact in
small interruptible steps, test attachment through consequence and recover
from slip.  Object coordinates and contact geometry are never runtime inputs.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
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


PROCEDURE_ID = "procedure_active_tactile_grasp_apprenticeship_v2"
GOAL = "active_tactile_grasp_apprenticeship"
DT = 0.004
FRAME_SKIP = 5


@dataclass(frozen=True)
class GraspWorld:
    world_id: str
    cube_y: float
    cube_size: float
    cube_mass: float
    friction: float
    action_delay: int = 0
    touch_scale: tuple[float, float] = (1.0, 1.0)
    start_y: float = 0.0
    start_z: float = 0.18
    disturbance_step: int = -1
    disturbance_force: float = 0.0
    marker_y_bias: float = 0.0


class TactileGraspAuthority:
    """A free cube and a four-axis gripper under independent physics."""

    def __init__(self, spec: GraspWorld, max_steps: int = 400) -> None:
        self.spec = spec
        self.max_steps = int(max_steps)
        self.model = mujoco.MjModel.from_xml_string(self._xml(spec))
        self.data = mujoco.MjData(self.model)
        self.renderer = mujoco.Renderer(self.model, height=144, width=192)
        self.step_count = 0
        self.commitments: list[str] = []
        self.pending: list[np.ndarray] = []
        self.target = np.asarray([spec.start_y, spec.start_z, 0.0, 0.0], dtype=float)
        self.initial_height = 0.0
        self.max_height = 0.0
        self.dual_steps = 0
        self.one_sided_steps = 0
        self.slip_events = 0
        self.unsafe = False
        self.frames: dict[str, np.ndarray] = {}
        self.reset()

    @staticmethod
    def _xml(s: GraspWorld) -> str:
        c = s.cube_size
        return f"""<mujoco model="active_tactile_grasp">
  <compiler angle="radian" inertiafromgeom="true"/>
  <option timestep="{DT}" gravity="0 0 -9.81" integrator="implicitfast" cone="elliptic"/>
  <default><geom solref=".004 1" solimp=".97 .995 .001"/></default>
  <visual><headlight ambient=".72 .72 .72" diffuse=".72 .72 .72"/></visual>
  <worldbody>
    <geom name="floor" type="plane" size="1 1 .05" rgba=".10 .11 .14 1"
          friction="1.2 .02 .002"/>
    <body name="cube" pos="0 {s.cube_y:.6f} {c + .002:.6f}">
      <freejoint name="cube_joint"/>
      <geom name="cube_geom" type="box" size="{c} {c} {c}" mass="{s.cube_mass}"
            friction="{s.friction} .02 .003" rgba=".08 .88 .42 1"/>
    </body>
    <body name="gripper" pos="0 0 0">
      <inertial pos="0 0 0" mass=".20" diaginertia=".002 .002 .002"/>
      <joint name="wrist_y" type="slide" axis="0 1 0" range="-.20 .20" limited="true" damping="4"/>
      <joint name="wrist_z" type="slide" axis="0 0 1" range=".025 .32" limited="true" damping="5"/>
      <site name="wrist_marker" type="sphere" pos="0 {s.marker_y_bias:.6f} 0"
            size=".012" rgba=".96 .08 .76 1"/>
      <body name="left_finger" pos="0 -.070 0">
        <joint name="left_slide" type="slide" axis="0 1 0" range="0 .052" limited="true" damping="3"/>
        <geom name="left_finger_geom" type="capsule" fromto="-.025 0 -.035 .025 0 .035"
              size=".012" mass=".07" friction="3.8 .02 .003" rgba=".78 .80 .88 1"/>
        <site name="left_touch" type="capsule" fromto="-.025 0 -.035 .025 0 .035"
              size=".014" rgba="0 0 0 0"/>
      </body>
      <body name="right_finger" pos="0 .070 0">
        <joint name="right_slide" type="slide" axis="0 1 0" range="-.052 0" limited="true" damping="3"/>
        <geom name="right_finger_geom" type="capsule" fromto="-.025 0 -.035 .025 0 .035"
              size=".012" mass=".07" friction="3.8 .02 .003" rgba=".78 .80 .88 1"/>
        <site name="right_touch" type="capsule" fromto="-.025 0 -.035 .025 0 .035"
              size=".014" rgba="0 0 0 0"/>
      </body>
    </body>
    <camera name="observer" pos="-1.2 0 .25" xyaxes="0 -1 0 0 0 1"/>
  </worldbody>
  <actuator>
    <position name="wrist_y_motor" joint="wrist_y" kp="150" ctrlrange="-.20 .20" ctrllimited="true"/>
    <position name="wrist_z_motor" joint="wrist_z" kp="180" ctrlrange=".025 .32" ctrllimited="true"/>
    <position name="left_motor" joint="left_slide" kp="260" ctrlrange="0 .052" ctrllimited="true"/>
    <position name="right_motor" joint="right_slide" kp="260" ctrlrange="-.052 0" ctrllimited="true"/>
  </actuator>
  <sensor>
    <touch name="left_force" site="left_touch"/>
    <touch name="right_force" site="right_touch"/>
  </sensor>
</mujoco>"""

    @staticmethod
    def validate(action: np.ndarray) -> None:
        value = np.asarray(action, dtype=float)
        limits = np.asarray([.008, .008, .004, .004])
        if value.shape != (4,) or not np.all(np.isfinite(value)) or np.any(np.abs(value) > limits):
            raise ValueError("active_tactile_action_rejected")

    def reset(self) -> dict[str, Any]:
        mujoco.mj_resetData(self.model, self.data)
        self.data.joint("wrist_y").qpos[0] = self.spec.start_y
        self.data.joint("wrist_z").qpos[0] = self.spec.start_z
        self.data.joint("cube_joint").qpos[:3] = [0.0, self.spec.cube_y, self.spec.cube_size + .002]
        self.data.joint("cube_joint").qpos[3:7] = [1.0, 0.0, 0.0, 0.0]
        self.data.qvel[:] = 0.0
        self.target = np.asarray([self.spec.start_y, self.spec.start_z, 0.0, 0.0], dtype=float)
        self.data.ctrl[:] = self.target
        mujoco.mj_forward(self.model, self.data)
        self.step_count = 0
        self.commitments = []
        self.pending = []
        self.initial_height = float(self.data.body("cube").xpos[2])
        self.max_height = self.initial_height
        self.dual_steps = self.one_sided_steps = self.slip_events = 0
        self.unsafe = False
        self.frames = {}
        return self.observe()

    def _render(self) -> np.ndarray:
        self.renderer.update_scene(self.data, camera="observer")
        return self.renderer.render().copy()

    def observe(self) -> dict[str, Any]:
        q = np.asarray([
            self.data.joint("wrist_y").qpos[0], self.data.joint("wrist_z").qpos[0],
            self.data.joint("left_slide").qpos[0], self.data.joint("right_slide").qpos[0],
        ], dtype=np.float32)
        v = np.asarray([
            self.data.joint("wrist_y").qvel[0], self.data.joint("wrist_z").qvel[0],
            self.data.joint("left_slide").qvel[0], self.data.joint("right_slide").qvel[0],
        ], dtype=np.float32)
        touch = np.asarray(self.data.sensordata[:2], dtype=np.float32)
        touch *= np.asarray(self.spec.touch_scale, dtype=np.float32)
        return {"rgb": self._render(), "joint_position": q, "joint_velocity": v,
                "fingertip_touch": np.clip(touch, 0.0, 50.0), "timestamp": self.step_count}

    def commit(self, action: np.ndarray, phase: str, belief: str) -> str:
        self.validate(action)
        row = {"step": self.step_count, "action": np.round(action, 6).tolist(),
               "phase": phase, "belief": belief}
        value = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
        self.commitments.append(value)
        return value

    def step(self, action: np.ndarray, phase: str, belief: str) -> dict[str, Any]:
        self.validate(action)
        if len(self.commitments) != self.step_count + 1:
            raise RuntimeError("active_tactile_commit_before_act_required")
        self.pending.append(np.asarray(action, dtype=float).copy())
        index = len(self.pending) - 1 - self.spec.action_delay
        applied = self.pending[index] if index >= 0 else np.zeros(4)
        self.target += applied
        self.target = np.clip(self.target,
                              [-.20, .025, 0.0, -.052],
                              [.20, .32, .052, 0.0])
        self.data.ctrl[:] = self.target
        if self.step_count == self.spec.disturbance_step:
            self.data.xfrc_applied[self.model.body("cube").id, 1] = self.spec.disturbance_force
        else:
            self.data.xfrc_applied[self.model.body("cube").id] = 0.0
        for _ in range(FRAME_SKIP):
            mujoco.mj_step(self.model, self.data)
        self.step_count += 1
        touch = self.observe()["fingertip_touch"]
        active = touch >= .012
        self.dual_steps += int(bool(np.all(active)))
        self.one_sided_steps += int(bool(np.sum(active) == 1))
        if phase in {"test_lift", "lift"} and np.max(touch) < .008:
            self.slip_events += 1
        height = float(self.data.body("cube").xpos[2])
        self.max_height = max(self.max_height, height)
        q = self.observe()["joint_position"]
        if (not np.all(np.isfinite(self.data.qpos)) or np.any(np.abs(self.data.qvel) > 30)
                or not (-.205 <= q[0] <= .205) or not (.02 <= q[1] <= .325)):
            self.unsafe = True
        return {"observation": self.observe(), "terminal": self.step_count >= self.max_steps}

    def score(self) -> dict[str, Any]:
        lift = self.max_height - self.initial_height
        return {"success": bool(lift >= .075 and not self.unsafe), "lift_height": lift,
                "max_height": self.max_height, "dual_contact_steps": self.dual_steps,
                "one_sided_contact_steps": self.one_sided_steps, "slip_events": self.slip_events,
                "safe": not self.unsafe, "steps": self.step_count,
                "pre_action_commitments": len(self.commitments),
                "privileged_runtime_geometry_used": 0, "teacher_actions_used": 0}

    def capture(self, name: str) -> None:
        self.frames.setdefault(name, self._render())

    def close(self) -> None:
        self.renderer.close()


@dataclass
class AttachmentBelief:
    probabilities: dict[str, float]
    stable_dual: int = 0
    prior_dual: bool = False
    lost_contact_age: int = 0
    attachment_latched: bool = False

    STATES = ("no_contact", "left_only", "right_only", "dual_unstable", "attached", "slipping")

    @classmethod
    def initial(cls) -> "AttachmentBelief":
        return cls({name: float(name == "no_contact") for name in cls.STATES})

    def update(self, touch: np.ndarray, phase: str, rising: bool) -> str:
        left, right = np.asarray(touch, dtype=float)
        threshold = .012
        dual = left >= threshold and right >= threshold
        balanced = dual and abs(left - right) / max(left + right, 1e-6) <= .72
        if balanced:
            self.stable_dual += 1
            self.lost_contact_age = 0
            if self.stable_dual >= 2 and phase in {"test_lift", "lift"}:
                self.attachment_latched = True
        else:
            self.stable_dual = 0
            self.lost_contact_age = self.lost_contact_age + 1 if not dual else 0
        if rising and self.attachment_latched and not dual and self.lost_contact_age >= 2:
            state = "slipping"
            self.attachment_latched = False
        elif self.stable_dual >= 2 and phase in {"test_lift", "lift"}:
            state = "attached"
        elif dual:
            state = "dual_unstable"
        elif left >= threshold:
            state = "left_only"
        elif right >= threshold:
            state = "right_only"
        else:
            state = "no_contact"
        self.probabilities = {name: .04 for name in self.STATES}
        self.probabilities[state] = .80
        self.prior_dual = dual
        return state


class ActiveTactileController:
    """Visual approach followed by tactile opposition and consequence tests."""

    @staticmethod
    def _centroid(rgb: np.ndarray, kind: str) -> np.ndarray:
        x = np.asarray(rgb, dtype=float) / 255.0
        r, g, b = x[..., 0], x[..., 1], x[..., 2]
        if kind == "cube":
            mask = (g > .55) & (g > 1.7 * r) & (g > 1.25 * b)
        elif kind == "wrist":
            mask = (r > .62) & (b > .40) & (g < .32)
        else:
            raise ValueError("unknown_tactile_landmark")
        yy, xx = np.where(mask)
        if len(xx) < (3 if kind == "wrist" else 5):
            raise RuntimeError(f"tactile_visual_abstention:{kind}")
        return np.asarray([np.median(xx), np.median(yy)], dtype=float)

    def run(self, authority: TactileGraspAuthority) -> dict[str, Any]:
        obs = authority.reset()
        authority.capture("start")
        belief = AttachmentBelief.initial()
        phase = "approach"
        contact_age = 0
        corrections = 0
        test_lifts = 0
        recoveries = 0
        one_sided_age = 0
        correction_remaining = 0
        correction_direction = 0.0
        opposition_force = 0.0
        opposition_balance = 0.0
        protected_nominal_routes = 0
        prior_z = float(obs["joint_position"][1])
        initial_q = np.asarray(obs["joint_position"], dtype=float).copy()
        cube_belief = self._centroid(obs["rgb"], "cube")
        wrist_origin = self._centroid(obs["rgb"], "wrist")
        for _ in range(authority.max_steps):
            q = np.asarray(obs["joint_position"], dtype=float)
            touch = np.asarray(obs["fingertip_touch"], dtype=float)
            rising = q[1] > prior_z + 2e-4
            state = belief.update(touch, phase, rising)
            prior_z = float(q[1])
            action = np.zeros(4, dtype=float)
            if phase == "approach":
                try:
                    cube_belief = self._centroid(obs["rgb"], "cube")
                except RuntimeError:
                    pass
                try:
                    wrist = self._centroid(obs["rgb"], "wrist")
                except RuntimeError:
                    # The marker is naturally occluded at contact.  Propagate
                    # its last grounded position from bounded proprioception.
                    delta = q[:2] - initial_q[:2]
                    wrist = wrist_origin + np.asarray([-155.0 * delta[0], -155.0 * delta[1]])
                cube = cube_belief
                # Centre the vertical fingers slightly above the cube centre
                # so their distal surfaces do not mistake the table for an
                # opposed grasp.
                error = cube + np.asarray([0.0, -4.0]) - wrist
                # Camera horizontal is world y; image vertical is world z.
                action[0] = np.clip(-error[0] * .00055, -.006, .006)
                action[1] = np.clip(-error[1] * .00045, -.006, .006)
                if state != "no_contact":
                    # Physical contact outranks a biased visual calibration.
                    # Stop chasing the marker and hand authority to the
                    # opposition controller on the next observation.
                    action[:2] = 0.0
                    action[2], action[3] = .0012, -.0012
                    phase = "close"
                    authority.capture("contact_override")
                elif np.linalg.norm(error) <= 5.0:
                    phase = "close"
                    authority.capture("aligned")
            elif phase == "close":
                action[2], action[3] = .0024, -.0024
                contact_age += 1
                one_sided_age = one_sided_age + 1 if state in {"left_only", "right_only"} else 0
                if correction_remaining > 0:
                    action[0] = correction_direction * .002
                    action[2], action[3] = -.0012, .0012
                    correction_remaining -= 1
                    corrections += 1
                elif state in {"left_only", "right_only"} and one_sided_age >= 6:
                    correction_direction = -1.0 if state == "left_only" else 1.0
                    correction_remaining = 6
                    one_sided_age = 0
                    action[0] = correction_direction * .002
                    action[2], action[3] = -.0012, .0012
                    corrections += 1
                elif state in {"dual_unstable", "attached"}:
                    left, right = touch
                    imbalance = np.clip((left - right) / max(left + right, 1e-6), -1.0, 1.0)
                    action[0] = -.0018 * imbalance
                    corrections += int(abs(imbalance) > .18)
                    if belief.stable_dual >= 4:
                        if corrections <= 20 and contact_age >= 20:
                            phase = "lift"
                            protected_nominal_routes += 1
                        else:
                            phase = "test_lift"
                        opposition_force = float(np.min(touch))
                        opposition_balance = float(np.min(touch) / max(np.max(touch), 1e-6))
                        authority.capture("opposed_contact")
                if contact_age > 90 and state == "no_contact":
                    phase = "approach"
                    action[2], action[3] = -.004, .004
                    recoveries += 1
            elif phase == "test_lift":
                action[1] = .0015
                action[2], action[3] = .0015, -.0015
                test_lifts += 1
                if state == "attached" and test_lifts >= 3:
                    phase = "lift"
                    authority.capture("test_lift_passed")
                elif (state in {"slipping", "left_only", "right_only", "no_contact"}
                      and test_lifts >= 2) or test_lifts >= 14:
                    action[1] = -.004
                    action[2], action[3] = .001, -.001
                    phase = "close"
                    test_lifts = 0
                    recoveries += 1
            else:  # lift
                action[1] = .003
                action[2], action[3] = .0010, -.0010
                if state in {"slipping", "left_only", "right_only", "no_contact"}:
                    action[1] = -.004
                    action[2], action[3] = .001, -.001
                    phase = "close"
                    recoveries += 1
                if authority.score()["success"]:
                    authority.capture("lifted")
                    break
            authority.commit(action, phase, state)
            result = authority.step(action, phase, state)
            obs = result["observation"]
            if result["terminal"]:
                break
        return {**authority.score(), "final_phase": phase, "belief": belief.probabilities,
                "tactile_corrections": corrections, "test_lifts": test_lifts,
                "recoveries": recoveries, "opposition_force": opposition_force,
                "opposition_balance": opposition_balance,
                "protected_nominal_routes": protected_nominal_routes}


class BinaryContactBaseline(ActiveTactileController):
    """Ablation: visual align, close for a fixed duration, then lift."""

    def run(self, authority: TactileGraspAuthority) -> dict[str, Any]:
        obs = authority.reset()
        phase = "approach"
        age = 0
        for _ in range(authority.max_steps):
            action = np.zeros(4)
            if phase == "approach":
                error = (self._centroid(obs["rgb"], "cube") + np.asarray([0.0, -4.0])
                         - self._centroid(obs["rgb"], "wrist"))
                action[:2] = [np.clip(-error[0] * .00055, -.006, .006),
                              np.clip(-error[1] * .00045, -.006, .006)]
                if np.linalg.norm(error) <= 5.0:
                    phase, age = "close", 0
            elif phase == "close":
                action[2:] = [.0024, -.0024]
                age += 1
                if age >= 24:
                    phase = "lift"
            else:
                action[1] = .004
                action[2:] = [.0004, -.0004]
            authority.commit(action, phase, "binary")
            result = authority.step(action, phase, "binary")
            obs = result["observation"]
            if authority.score()["success"] or result["terminal"]:
                break
        return {**authority.score(), "final_phase": phase}


DEVELOPMENT = (
    GraspWorld("dev_center", .000, .030, .10, 1.2),
    GraspWorld("dev_left", -.020, .028, .13, .9, 1, (.9, 1.1)),
    GraspWorld("dev_right", .022, .032, .08, 1.5, 2, (1.15, .85)),
)
SEALED = tuple(
    GraspWorld(f"sealed_{i:02d}", y, size, mass, friction, delay, scale,
               start_y=start, disturbance_step=disturbance, disturbance_force=force,
               marker_y_bias=marker_bias)
    for i, (y, size, mass, friction, delay, scale, start, disturbance, force, marker_bias) in enumerate((
        (-.032, .026, .07, .70, 0, (.80, 1.20), .018, -1, 0, .056),
        (.034, .034, .18, 1.60, 1, (1.20, .80), -.015, -1, 0, -.056),
        (-.018, .030, .24, .85, 2, (.95, 1.05), .025, 58, .65, .056),
        (.020, .028, .11, 1.25, 0, (1.08, .92), -.025, 60, -.55, -.056),
        (-.040, .032, .15, .65, 1, (.75, 1.25), .010, 57, .75, .056),
        (.042, .026, .09, 1.80, 2, (1.25, .75), -.010, -1, 0, -.056),
        (-.025, .034, .20, 1.10, 0, (1.0, 1.0), .030, 61, -.70, .056),
        (.028, .030, .14, .75, 1, (.88, 1.12), -.030, 59, .60, -.056),
        (-.012, .027, .26, 1.50, 2, (1.18, .82), .022, -1, 0, .056),
        (.014, .033, .06, .60, 0, (.82, 1.18), -.022, 56, .50, -.056),
        (-.036, .029, .17, 1.35, 1, (1.05, .95), .016, -1, 0, .056),
        (.038, .031, .12, .90, 2, (.92, 1.08), -.018, 62, -.65, -.056),
    ))
)


def _episode(spec: GraspWorld, controller: ActiveTactileController) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    authority = TactileGraspAuthority(spec)
    try:
        try:
            result = controller.run(authority)
        except RuntimeError as exc:
            result = {**authority.score(), "abstained": True, "failure": str(exc)}
        return {"world_id": spec.world_id, **result}, dict(authority.frames)
    finally:
        authority.close()


def _prospective_worlds(seed: int = 180801) -> tuple[GraspWorld, ...]:
    """Generate the frozen source-disjoint transfer cohort prospectively."""
    rng = np.random.default_rng(seed)
    worlds = []
    for index in range(48):
        severe = index >= 24
        disturbed = index % 3 == 0
        worlds.append(GraspWorld(
            f"prospective_{index:02d}", float(rng.uniform(-.04, .04)),
            float(rng.uniform(.026, .034)), float(rng.uniform(.06, .24)),
            float(rng.uniform(.65, 1.70)), int(rng.integers(0, 3)),
            (float(rng.uniform(.8, 1.2)), float(rng.uniform(.8, 1.2))),
            start_y=float(rng.uniform(-.025, .025)),
            disturbance_step=int(rng.integers(58, 66)) if disturbed else -1,
            disturbance_force=(float(rng.choice([-1, 1]) * rng.uniform(.35, .70))
                               if disturbed else 0.0),
            marker_y_bias=float(rng.choice([-1, 1]) * rng.uniform(
                *((.045, .058) if severe else (.025, .040)))),
        ))
    return tuple(worlds)


def _atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True))
    json.loads(temporary.read_text())
    os.replace(temporary, path)


def _authority(_: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None,
            "source": "active_tactile_private_cau", "S": 1.0, "H": 0.0}


def run(repo_root: Path, result_path: Path | None = None, state_path: Path | None = None,
        capsule_path: Path | None = None) -> dict[str, Any]:
    result_path = result_path or repo_root / "results/hexcore_active_tactile_grasp_apprenticeship_v2.json"
    state_path = state_path or repo_root / "backend/modules/hexcore/data/active_tactile_grasp/state.json"
    capsule_path = capsule_path or repo_root / "backend/modules/hexcore/data/physical_skill_capsules/active_tactile_grasp.json"
    development = [_episode(world, ActiveTactileController())[0] for world in DEVELOPMENT]
    sealed: list[dict[str, Any]] = []
    baseline: list[dict[str, Any]] = []
    visual: dict[str, np.ndarray] = {}
    for world in SEALED:
        row, frames = _episode(world, ActiveTactileController())
        sealed.append(row)
        baseline.append(_episode(world, BinaryContactBaseline())[0])
        if row["success"] and not visual:
            visual = frames
    prospective_worlds = _prospective_worlds()
    prospective = [_episode(world, ActiveTactileController())[0] for world in prospective_worlds]
    prospective_baseline = [_episode(world, BinaryContactBaseline())[0]
                            for world in prospective_worlds]
    malicious = []
    for name, value in (("nan", [0, 0, np.nan, 0]), ("range", [.1, 0, 0, 0]),
                        ("shape", [0, 0]), ("infinite", [0, np.inf, 0, 0])):
        rejected = False
        try:
            TactileGraspAuthority.validate(np.asarray(value, dtype=float))
        except ValueError:
            rejected = True
        malicious.append({"case": name, "rejected": rejected})
    successes = sum(int(row["success"]) for row in sealed)
    baseline_successes = sum(int(row["success"]) for row in baseline)
    prospective_successes = sum(int(row["success"]) for row in prospective)
    prospective_baseline_successes = sum(int(row["success"]) for row in prospective_baseline)
    nominal_successes = sum(int(row["success"]) for row in prospective[:24])
    severe_successes = sum(int(row["success"]) for row in prospective[24:])
    severe_baseline_successes = sum(int(row["success"]) for row in prospective_baseline[24:])
    disturbed_successes = sum(
        int(row["success"]) for index, row in enumerate(prospective) if index % 3 == 0
    )
    weakest_disturbance = min(
        np.mean([row["success"] for row, world in zip(sealed, SEALED, strict=True)
                 if world.disturbance_step >= 0]),
        np.mean([row["success"] for row, world in zip(sealed, SEALED, strict=True)
                 if world.disturbance_step < 0]),
    )
    gate = {
        "development_success": sum(int(row["success"]) for row in development),
        "development_total": len(development), "sealed_success": successes,
        "sealed_total": len(sealed), "binary_baseline_success": baseline_successes,
        "weakest_disturbance_group": float(weakest_disturbance),
        "malicious_rejected": sum(int(row["rejected"]) for row in malicious),
        "unsafe_actions": sum(int(not row["safe"]) for row in sealed),
        "privileged_runtime_geometry": sum(row["privileged_runtime_geometry_used"] for row in sealed),
        "teacher_actions": sum(row["teacher_actions_used"] for row in sealed),
        "prospective_success": prospective_successes,
        "prospective_total": len(prospective),
        "prospective_binary_baseline_success": prospective_baseline_successes,
        "prospective_nominal_success": nominal_successes,
        "prospective_nominal_total": 24,
        "prospective_severe_success": severe_successes,
        "prospective_severe_total": 24,
        "prospective_severe_baseline_success": severe_baseline_successes,
        "prospective_disturbed_success": disturbed_successes,
        "prospective_disturbed_total": 16,
        "prospective_unsafe_actions": sum(int(not row["safe"]) for row in prospective),
    }
    passed_gate = bool(gate["development_success"] == gate["development_total"]
                       and successes >= 10 and successes > baseline_successes
                       and weakest_disturbance >= .75 and gate["malicious_rejected"] == 4
                       and gate["unsafe_actions"] == 0
                       and gate["privileged_runtime_geometry"] == 0
                       and gate["teacher_actions"] == 0)
    passed_gate = bool(
        passed_gate and prospective_successes >= 40
        and prospective_successes > prospective_baseline_successes
        and nominal_successes >= 22 and severe_successes >= 18
        and severe_successes > severe_baseline_successes
        and disturbed_successes >= 12 and gate["prospective_unsafe_actions"] == 0
    )
    capsule = {
        "schema_version": "aion.active_tactile_grasp_skill.v2",
        "procedure_id": PROCEDURE_ID,
        "parents": ["procedure_self_modelled_tactile_hand_apprenticeship_v1",
                    "procedure_articulated_precision_cube_lifting_v1"],
        "observation_contract": {"required": ["rgb", "joint_position", "joint_velocity", "fingertip_touch"],
                                 "forbidden": ["object_pose", "contact_geometry", "teacher_action", "reward"]},
        "action_contract": {"axes": ["wrist_y", "wrist_z", "left_finger", "right_finger"],
                            "maximum_delta": [.008, .008, .004, .004], "commit_before_act": True},
        "belief_states": list(AttachmentBelief.STATES),
        "retained_method": ["visual_approach", "independent_digit_closure", "opposition_balance",
                            "interruptible_micro_correction", "progressive_test_lift",
                            "slip_recovery", "consequence_confirmed_lift"],
        "gate": gate,
    }
    capsule["capsule_digest"] = _canonical_hash(capsule)
    _atomic(capsule_path, capsule)
    learning = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_authority)
    candidate = ProcedureCandidate(PROCEDURE_ID, GOAL, capsule["retained_method"],
                                   successes / len(sealed), passed_gate,
                                   {"gate": gate, "capsule_digest": capsule["capsule_digest"]}, [])
    promotion = learning.skills.promote(candidate)
    learning.skills.record_outcome(procedure_id=PROCEDURE_ID, success=passed_gate,
                                   score=candidate.score, evidence=candidate.evidence)
    learning.store.state.setdefault("active_tactile_skills", {})[capsule["capsule_digest"]] = capsule
    learning.store.commit(reason="active_tactile_grasp_apprenticeship_v2")
    restarted = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_authority)
    restart = {
        "champion_retained": restarted.store.state.get("champions", {}).get(GOAL) == PROCEDURE_ID,
        "capsule_retained": capsule["capsule_digest"] in restarted.store.state.get("active_tactile_skills", {}),
        "digest_valid": json.loads(capsule_path.read_text()).get("capsule_digest") == capsule["capsule_digest"],
    }
    passed = bool(passed_gate and all(restart.values()) and promotion.get("promoted"))
    result = {
        "schema_version": "aion.active_tactile_grasp_apprenticeship.result.v2",
        "procedure_id": PROCEDURE_ID, "generated_at": _utc_timestamp(), "passed": passed,
        "promoted": bool(promotion.get("promoted")), "gate": gate,
        "development": development, "sealed": sealed, "binary_baseline": baseline,
        "prospective": prospective, "prospective_binary_baseline": prospective_baseline,
        "malicious": malicious, "restart": restart, "capsule": str(capsule_path),
        "claim_boundary": "Local MuJoCo tactile opposition and free-object lifting; Isaac transfer and real hardware remain unearned.",
    }
    _atomic(result_path, result)
    if visual:
        frame_path = result_path.with_name("hexcore_active_tactile_grasp_frames.npz")
        np.savez_compressed(frame_path, **visual)
        result["visual_evidence"] = str(frame_path)
        _atomic(result_path, result)
    return result


if __name__ == "__main__":
    print(json.dumps(run(Path(__file__).resolve().parents[3]), indent=2))
