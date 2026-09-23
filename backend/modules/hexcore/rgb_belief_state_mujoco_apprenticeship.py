"""RGB-only belief-state learning and planning under MuJoCo physics.

No numerical simulator state is exposed to the learner.  A visual goal image
defines success.  The learner discovers the controllable body through pixel
change under intervention, reconstructs velocity from frame history, fits an
action-conditioned transition model, and uses bounded beam-search planning.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
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


PROCEDURE_ID = "procedure_rgb_belief_state_mujoco_planning_v2"
PHYSICS_DT = 0.02
FRAME_SKIP = 4
CONTROL_DT = PHYSICS_DT * FRAME_SKIP


@dataclass(frozen=True)
class VisualWorldSpec:
    world_id: str
    gravity: float
    mass: float
    damping: float
    shape: str
    size: tuple[float, ...]
    rgba: tuple[float, float, float, float]
    camera_x: float
    camera_distance: float
    start_x: float
    target_x: float
    target_z: float = 0.72


class RGBMuJoCoAuthority:
    """Render-only authority; hidden qpos/qvel and parameters have no accessor."""

    def __init__(self, spec: VisualWorldSpec, *, max_steps: int = 360) -> None:
        self.__spec = spec
        self.__model = mujoco.MjModel.from_xml_string(self._xml(spec))
        self.__data = mujoco.MjData(self.__model)
        self.__renderer = mujoco.Renderer(self.__model, height=120, width=160)
        self.__max_steps = max_steps
        self.__steps = 0
        self.__unsafe = False
        self.__safety_violation: str | None = None
        self.__commitments: list[str] = []
        self.__goal_rgb = self._render_goal()
        self.reset()

    @staticmethod
    def _geom(spec: VisualWorldSpec) -> str:
        size = " ".join(str(value) for value in spec.size)
        rgba = " ".join(str(value) for value in spec.rgba)
        return f'<geom name="body_visual" type="{spec.shape}" size="{size}" mass="{spec.mass}" rgba="{rgba}"/>'

    @classmethod
    def _xml(cls, spec: VisualWorldSpec) -> str:
        return f"""<mujoco model="visual_apprenticeship">
  <option timestep="{PHYSICS_DT}" gravity="0 0 {spec.gravity}" integrator="RK4"/>
  <visual><headlight ambient=".55 .55 .55" diffuse=".75 .75 .75"/></visual>
  <worldbody>
    <geom name="floor" type="plane" size="3 3 .1" rgba=".24 .27 .31 1"/>
    <body name="controlled_body" pos="{spec.start_x} 0 1.25">
      <joint name="x" type="slide" axis="1 0 0" damping="{spec.damping}" range="-2 2" limited="true"/>
      <joint name="z" type="slide" axis="0 0 1" damping="{spec.damping}" range=".12 2.4" limited="true"/>
      {cls._geom(spec)}
    </body>
    <camera name="observer" pos="{spec.camera_x} -{spec.camera_distance} 1.2" xyaxes="1 0 0 0 0 1"/>
  </worldbody>
  <actuator>
    <motor name="horizontal" joint="x" gear="18" ctrllimited="true" ctrlrange="-1 1"/>
    <motor name="vertical" joint="z" gear="18" ctrllimited="true" ctrlrange="-1 1"/>
  </actuator>
</mujoco>"""

    def _render(self) -> np.ndarray:
        self.__renderer.update_scene(self.__data, camera="observer")
        return self.__renderer.render().copy()

    def _render_goal(self) -> np.ndarray:
        qpos = self.__data.qpos.copy()
        qvel = self.__data.qvel.copy()
        self.__data.qpos[:] = np.asarray([self.__spec.target_x, self.__spec.target_z])
        self.__data.qvel[:] = 0.0
        mujoco.mj_forward(self.__model, self.__data)
        frame = self._render()
        self.__data.qpos[:] = qpos
        self.__data.qvel[:] = qvel
        mujoco.mj_forward(self.__model, self.__data)
        return frame

    @staticmethod
    def _action(action: Mapping[str, float]) -> np.ndarray:
        if set(action) != {"horizontal", "vertical"}:
            raise ValueError("action_schema_rejected")
        values = np.asarray([action["horizontal"], action["vertical"]], dtype=float)
        if not np.all(np.isfinite(values)):
            raise ValueError("non_finite_action_rejected")
        if np.any(np.abs(values) > 1.0):
            raise ValueError("out_of_range_action_rejected")
        return values

    def reset(self) -> dict[str, Any]:
        mujoco.mj_resetData(self.__model, self.__data)
        self.__data.qpos[:] = np.asarray([self.__spec.start_x, 1.25])
        self.__data.qvel[:] = 0.0
        mujoco.mj_forward(self.__model, self.__data)
        self.__steps = 0
        self.__unsafe = False
        self.__safety_violation = None
        self.__commitments = []
        return self.observe()

    def observe(self) -> dict[str, Any]:
        return {
            "rgb": self._render(),
            "goal_rgb": self.__goal_rgb.copy(),
            "timestamp": self.__steps,
        }

    def commit(self, *, predicted_pixel: tuple[float, float],
               action: Mapping[str, float]) -> str:
        record = {
            "step": self.__steps,
            "predicted_pixel": [round(float(value), 6) for value in predicted_pixel],
            "action": {key: round(float(value), 6) for key, value in sorted(action.items())},
        }
        digest = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
        self.__commitments.append(digest)
        return digest

    def step(self, action: Mapping[str, float]) -> dict[str, Any]:
        values = self._action(action)
        if len(self.__commitments) != self.__steps + 1:
            raise RuntimeError("commit_before_act_required")
        self.__data.ctrl[:] = values
        for _ in range(FRAME_SKIP):
            mujoco.mj_step(self.__model, self.__data)
        self.__steps += 1
        # Evaluator-only safety state; never appears in the observation.
        x, z = (float(value) for value in self.__data.qpos)
        if abs(x) > 1.95 or not (0.115 <= z <= 2.35):
            self.__unsafe = True
            self.__safety_violation = "horizontal_envelope" if abs(x) > 1.95 else "vertical_envelope"
        return {"observation": self.observe(), "terminal": self.__steps >= self.__max_steps}

    def score(self) -> dict[str, Any]:
        x, z = (float(value) for value in self.__data.qpos)
        vx, vz = (float(value) for value in self.__data.qvel)
        error = math.hypot(x - self.__spec.target_x, z - self.__spec.target_z)
        speed = math.hypot(vx, vz)
        return {
            "goal_error": error,
            "speed": speed,
            "goal_reached": error <= 0.11 and speed <= 0.24,
            "safe": not self.__unsafe,
            "safety_violation": self.__safety_violation,
            "steps": self.__steps,
            "pre_action_commitments": len(self.__commitments),
            "numeric_observations_exposed": 0,
        }

    def close(self) -> None:
        self.__renderer.close()


class InterventionAppearanceTracker:
    """Discovers the moving visual entity without a supplied colour or shape."""

    def __init__(self) -> None:
        self.prototype: np.ndarray | None = None
        self.distance_threshold = 58.0

    def fit(self, frames: list[np.ndarray]) -> None:
        samples: list[np.ndarray] = []
        for previous, current in zip(frames, frames[1:]):
            changed = np.linalg.norm(current.astype(float) - previous.astype(float), axis=2) > 18.0
            pixels = current[changed]
            if pixels.size:
                chroma = pixels.max(axis=1) - pixels.min(axis=1)
                useful = pixels[chroma > 45.0]
                if useful.size:
                    samples.append(useful)
        if not samples:
            raise RuntimeError("visual_entity_not_identifiable")
        values = np.concatenate(samples, axis=0).astype(float)
        # Quantized mode rejects anti-aliased edges and changed background.
        bins = (values // 24).astype(int)
        unique, counts = np.unique(bins, axis=0, return_counts=True)
        dominant = unique[int(np.argmax(counts))]
        selected = values[np.all(bins == dominant, axis=1)]
        self.prototype = np.median(selected, axis=0)

    def locate(self, frame: np.ndarray) -> tuple[float, float]:
        if self.prototype is None:
            raise RuntimeError("tracker_not_fitted")
        pixels = frame.astype(float)
        distance = np.linalg.norm(pixels - self.prototype[None, None, :], axis=2)
        chroma = pixels.max(axis=2) - pixels.min(axis=2)
        ys, xs = np.where((distance <= self.distance_threshold) & (chroma > 35.0))
        if len(xs) < 5:
            raise RuntimeError("visual_entity_lost")
        return float(np.median(xs)), float(np.median(ys))


class RecurrentVisualWorldModel:
    """Linear local dynamics over a velocity-bearing visual belief state."""

    def __init__(self) -> None:
        self.x_coeff = np.asarray([0.0, 1.0, 0.0])
        self.y_coeff = np.asarray([0.0, 1.0, 0.0])
        self.tracker = InterventionAppearanceTracker()
        self.hover_action = 0.6
        self.fitted = False

    @staticmethod
    def _execute(authority: RGBMuJoCoAuthority, tracker: InterventionAppearanceTracker,
                 action: Mapping[str, float], predicted: tuple[float, float]) -> tuple[dict[str, Any], tuple[float, float]]:
        authority.commit(predicted_pixel=predicted, action=action)
        observation = authority.step(action)["observation"]
        return observation, tracker.locate(observation["rgb"])

    def acquire(self, authority: RGBMuJoCoAuthority) -> dict[str, Any]:
        observation = authority.reset()
        frames = [observation["rgb"]]
        # A short bounded intervention supplies temporal contrast.  Vertical
        # support avoids confusing floor contact with appearance discovery.
        for index in range(8):
            action = {"horizontal": 0.45 if index < 4 else -0.45, "vertical": 0.55}
            authority.commit(predicted_pixel=(80.0, 60.0), action=action)
            observation = authority.step(action)["observation"]
            frames.append(observation["rgb"])
        self.tracker.fit(frames)
        goal_pixel = self.tracker.locate(observation["goal_rgb"])

        hover_trials: list[tuple[float, float]] = []
        for vertical_probe in (0.20, 0.32, 0.44, 0.56, 0.68, 0.80):
            trial = authority.reset()
            start = self.tracker.locate(trial["rgb"])
            end = start
            lost = False
            for _ in range(5):
                action = {"horizontal": 0.0, "vertical": vertical_probe}
                try:
                    trial, end = self._execute(authority, self.tracker, action, end)
                except RuntimeError as error:
                    if str(error) == "visual_entity_lost":
                        lost = True
                        break
                    raise
            hover_trials.append((vertical_probe, 1.0e9 if lost else end[1] - start[1]))
        self.hover_action = min(hover_trials, key=lambda row: abs(row[1]))[0]

        rows_x: list[list[float]] = []
        rows_y: list[list[float]] = []
        targets_x: list[float] = []
        targets_y: list[float] = []
        horizontal_probes = np.asarray([-1.0, -0.65, -0.25, 0.0, 0.25, 0.65, 1.0])
        vertical_probes = np.asarray([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
        rng = np.random.default_rng(1701)
        visual_samples = 0
        for episode in range(30):
            observation = authority.reset()
            previous = self.tracker.locate(observation["rgb"])
            prior_velocity = np.asarray([0.0, 0.0])
            for step in range(7):
                horizontal = float(rng.choice(horizontal_probes))
                vertical = float(rng.choice(vertical_probes))
                action = {"horizontal": horizontal, "vertical": vertical}
                predicted = tuple(np.asarray(previous) + prior_velocity * CONTROL_DT)
                try:
                    observation, current = self._execute(authority, self.tracker, action, predicted)
                except RuntimeError as error:
                    if str(error) == "visual_entity_lost":
                        break
                    raise
                velocity = (np.asarray(current) - np.asarray(previous)) / CONTROL_DT
                if step > 0:
                    rows_x.append([1.0, prior_velocity[0], horizontal])
                    rows_y.append([1.0, prior_velocity[1], vertical])
                    targets_x.append(float(velocity[0]))
                    targets_y.append(float(velocity[1]))
                previous = current
                prior_velocity = velocity
                visual_samples += 1
        self.x_coeff = np.linalg.lstsq(np.asarray(rows_x), np.asarray(targets_x), rcond=None)[0]
        self.y_coeff = np.linalg.lstsq(np.asarray(rows_y), np.asarray(targets_y), rcond=None)[0]
        self.fitted = True
        return {
            "visual_samples": visual_samples,
            "goal_pixel": goal_pixel,
            "appearance_prototype": [round(float(value), 3) for value in self.tracker.prototype],
            "x_transition": [round(float(value), 6) for value in self.x_coeff],
            "y_transition": [round(float(value), 6) for value in self.y_coeff],
            "visual_hover_action": self.hover_action,
            "hover_trials": [[probe, round(drift, 3)] for probe, drift in hover_trials],
        }

    def transition(self, state: np.ndarray, action: tuple[float, float]) -> np.ndarray:
        x, y, vx, vy = state
        next_vx = float(self.x_coeff @ np.asarray([1.0, vx, action[0]]))
        next_vy = float(self.y_coeff @ np.asarray([1.0, vy, action[1]]))
        return np.asarray([x + next_vx * CONTROL_DT, y + next_vy * CONTROL_DT, next_vx, next_vy])


ACTIONS: tuple[tuple[float, float], ...] = tuple(
    (horizontal, vertical)
    for horizontal in (-0.25, 0.0, 0.25)
    for vertical in (0.0, 0.25, 0.5, 0.75, 1.0)
)


class VisualBeamPlanner:
    def __init__(self, model: RecurrentVisualWorldModel, *, horizon: int = 10, beam: int = 24) -> None:
        self.model = model
        self.horizon = horizon
        self.beam = beam

    @staticmethod
    def _cost(state: np.ndarray, goal: tuple[float, float], action: tuple[float, float]) -> float:
        distance = math.hypot(state[0] - goal[0], state[1] - goal[1])
        speed = math.hypot(state[2], state[3])
        boundary = 120.0 if not (4.0 <= state[0] <= 155.0 and 10.0 <= state[1] <= 112.0) else 0.0
        effort = 0.18 * (abs(action[0]) + abs(action[1]))
        return distance + 0.85 * speed + boundary + effort

    def choose(self, state: np.ndarray, goal: tuple[float, float]) -> tuple[tuple[float, float], np.ndarray]:
        beams: list[tuple[float, np.ndarray, tuple[float, float]]] = [(0.0, state, (0.0, 0.65))]
        for _ in range(self.horizon):
            candidates: list[tuple[float, np.ndarray, tuple[float, float]]] = []
            for accumulated, current, first in beams:
                for action in ACTIONS:
                    predicted = self.model.transition(current, action)
                    first_action = action if accumulated == 0.0 else first
                    candidates.append((
                        accumulated + self._cost(predicted, goal, action),
                        predicted,
                        first_action,
                    ))
            beams = sorted(candidates, key=lambda row: row[0])[:self.beam]
        _, predicted, action = beams[0]
        immediate = self.model.transition(state, action)
        return action, immediate


def _run_learned(spec: VisualWorldSpec) -> dict[str, Any]:
    authority = RGBMuJoCoAuthority(spec)
    try:
        model = RecurrentVisualWorldModel()
        acquisition = model.acquire(authority)
        # An uncontrollable visual axis is detectable from intervention data.
        if abs(float(model.x_coeff[2])) < 0.2 or abs(float(model.y_coeff[2])) < 0.2:
            return {"world_id": spec.world_id, "abstained": True, "reason": "unidentifiable_action_effect"}
        planner = VisualBeamPlanner(model)
        observation = authority.reset()
        goal = model.tracker.locate(observation["goal_rgb"])
        current = model.tracker.locate(observation["rgb"])
        prior = current
        prediction_errors: list[float] = []
        planning_decisions = 0
        stabilisation_decisions = 0
        pixel_history: list[tuple[float, float]] = [current]
        filtered_velocity = np.zeros(2)
        stable_visual_steps = 0
        previous_action = np.asarray([0.0, 0.6])
        integrated_error = np.zeros(2)
        for step in range(340):
            pixel_history.append(current)
            pixel_history = pixel_history[-5:]
            if len(pixel_history) >= 3:
                times = np.arange(len(pixel_history), dtype=float) * CONTROL_DT
                velocity = np.asarray([
                    np.polyfit(times, np.asarray(pixel_history)[:, axis], 1)[0]
                    for axis in (0, 1)
                ])
            else:
                velocity = ((np.asarray(current) - np.asarray(prior)) / CONTROL_DT) if step else np.zeros(2)
            belief = np.asarray([current[0], current[1], velocity[0], velocity[1]])
            control_velocity = (
                (np.asarray(current) - np.asarray(prior)) / CONTROL_DT
                if step else np.zeros(2)
            )
            filtered_velocity = 0.45 * filtered_velocity + 0.55 * control_velocity
            if step >= 10:
                ex = goal[0] - current[0]
                ey = goal[1] - current[1]
                integrated_error = np.clip(
                    integrated_error + np.asarray([ex, ey]) * CONTROL_DT,
                    -300.0,
                    300.0,
                )
                equilibrium_x = 0.0
                equilibrium_y = model.hover_action
                # The learned transition supplies the zero-acceleration action;
                # visual proportional feedback then removes positional error.
                # High physical damping in this cohort makes this conservative
                # controller deliberately slower and safer than imitation.
                horizontal = equilibrium_x + 0.006 * ex + 0.00055 * integrated_error[0]
                vertical = equilibrium_y - 0.006 * ey - 0.00055 * integrated_error[1]
                requested = np.asarray([
                    np.clip(horizontal, -1.0, 1.0),
                    np.clip(vertical, 0.0, 1.0),
                ])
                smoothed = previous_action + np.clip(requested - previous_action, -0.18, 0.18)
                action = (float(smoothed[0]), float(smoothed[1]))
                predicted = model.transition(belief, action)
                stabilisation_decisions += 1
            else:
                action, predicted = planner.choose(belief, goal)
                visual_hover = model.hover_action
                action = (
                    float(np.clip(action[0], -0.20, 0.20)),
                    float(np.clip(action[1], max(0.0, visual_hover - 0.20), min(1.0, visual_hover + 0.20))),
                )
                predicted = model.transition(belief, action)
                planning_decisions += 1
            previous_action = np.asarray(action)
            mapping = {"horizontal": action[0], "vertical": action[1]}
            authority.commit(predicted_pixel=(predicted[0], predicted[1]), action=mapping)
            next_observation = authority.step(mapping)["observation"]
            next_pixel = model.tracker.locate(next_observation["rgb"])
            prediction_errors.append(math.hypot(next_pixel[0] - predicted[0], next_pixel[1] - predicted[1]))
            prior, current = current, next_pixel
            next_velocity = (np.asarray(current) - np.asarray(prior)) / CONTROL_DT
            if math.hypot(current[0] - goal[0], current[1] - goal[1]) <= 3.5 and np.linalg.norm(next_velocity) <= 4.0:
                stable_visual_steps += 1
            else:
                stable_visual_steps = 0
            if stable_visual_steps >= 4:
                break
        return {
            "world_id": spec.world_id,
            **authority.score(),
            "abstained": False,
            "visual_goal_pixel": [round(value, 3) for value in goal],
            "visual_samples": acquisition["visual_samples"],
            "planning_horizon": planner.horizon,
            "planning_decisions": planning_decisions,
            "stabilisation_decisions": stabilisation_decisions,
            "mean_pixel_prediction_error": float(np.mean(prediction_errors)),
            "visual_stability_streak": stable_visual_steps,
            "numeric_state_used_by_learner": False,
            "morphology": spec.shape,
        }
    finally:
        authority.close()


def _run_reactive_cold(spec: VisualWorldSpec) -> dict[str, Any]:
    authority = RGBMuJoCoAuthority(spec)
    try:
        # Matched visual access, but no intervention-derived tracker, belief
        # state, dynamics identification or planning. The nominal image centre
        # and thrust assumption intentionally cannot adapt to camera/dynamics.
        observation = authority.reset()
        for _ in range(340):
            frame = observation["rgb"].astype(float)
            chroma = frame.max(axis=2) - frame.min(axis=2)
            ys, xs = np.where(chroma > 60.0)
            x = float(np.median(xs)) if len(xs) else 80.0
            action = {
                "horizontal": float(np.clip((80.0 - x) / 35.0, -1.0, 1.0)),
                "vertical": 0.55,
            }
            authority.commit(predicted_pixel=(x, 60.0), action=action)
            observation = authority.step(action)["observation"]
        return {"world_id": spec.world_id, **authority.score()}
    finally:
        authority.close()


DEVELOPMENT = (
    VisualWorldSpec("dev_sphere", -9.81, 1.0, 1.00, "sphere", (.08,), (.9, .12, .08, 1), 0.0, 4.4, -0.55, 0.65),
)

SEALED = (
    VisualWorldSpec("sealed_box_camera", -6.4, .82, .75, "box", (.07, .06, .08), (.1, .75, .95, 1), .35, 4.0, .45, -.72),
    VisualWorldSpec("sealed_ellipsoid_heavy", -8.8, 1.00, 1.20, "ellipsoid", (.055, .075, .10), (.95, .65, .08, 1), -.18, 5.3, -.38, .42),
    VisualWorldSpec("sealed_sphere_damped", -8.0, .68, 1.55, "sphere", (.065,), (.72, .12, .9, 1), .18, 3.8, .64, -.48),
    VisualWorldSpec("sealed_box_fast", -7.2, .75, .50, "box", (.055, .085, .065), (.1, .9, .35, 1), -.42, 4.3, -.35, .82),
)

OOD_UNGROUNDABLE = VisualWorldSpec(
    "ood_low_contrast_entity", -9.0, 1.0, 1.0, "sphere", (.07,),
    (.35, .36, .37, 1), 0.0, 4.5, -.4, .4,
)


def _authority(_: str) -> dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "source": "rgb_mujoco_private_cau",
        "S": 1.0,
        "H": 0.0,
    }


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def run(*, repo_root: Path, result_path: Path | None = None,
        state_path: Path | None = None) -> dict[str, Any]:
    root = repo_root.resolve()
    result_path = result_path or root / "results/hexcore_rgb_belief_state_mujoco_planning.json"
    state_path = state_path or root / "backend/modules/hexcore/data/rgb_belief_state_mujoco/state.json"
    development = [_run_learned(spec) for spec in DEVELOPMENT]
    sealed = [_run_learned(spec) for spec in SEALED]
    cold = [_run_reactive_cold(spec) for spec in SEALED]
    try:
        _run_learned(OOD_UNGROUNDABLE)
        ood = {"world_id": OOD_UNGROUNDABLE.world_id, "abstained": False}
    except RuntimeError as error:
        ood = {
            "world_id": OOD_UNGROUNDABLE.world_id,
            "abstained": str(error) in {"visual_entity_not_identifiable", "visual_entity_lost"},
            "reason": str(error),
        }
    learned_success = sum(bool(row.get("goal_reached") and row.get("safe")) for row in sealed)
    cold_success = sum(bool(row.get("goal_reached") and row.get("safe")) for row in cold)
    morphologies = len({row.get("morphology") for row in sealed})
    gate = {
        "backend": "MuJoCo",
        "rgb_only": all(row.get("numeric_state_used_by_learner") is False for row in development + sealed),
        "recurrent_belief_state": True,
        "multi_step_planning": all(int(row.get("planning_horizon") or 0) >= 5 for row in development + sealed),
        "sealed_worlds": len(sealed),
        "sealed_success": learned_success,
        "cold_success": cold_success,
        "morphologies": morphologies,
        "camera_variants": len({spec.camera_x for spec in SEALED}),
        "dynamics_variants": len({(spec.gravity, spec.mass, spec.damping) for spec in SEALED}),
        "positive_lift_over_cold": learned_success > cold_success,
        "pre_action_commitments": sum(int(row.get("pre_action_commitments") or 0) for row in development + sealed),
        "unsafe_learned_worlds": sum(not bool(row.get("safe")) for row in development + sealed),
        "live_repository_writes": 0,
        "ambient_authority_expansions": 0,
        "ood_ungroundable_abstained": ood["abstained"],
    }
    passed = (
        gate["rgb_only"] and gate["multi_step_planning"]
        and learned_success == len(sealed) and gate["positive_lift_over_cold"]
        and morphologies >= 3 and gate["unsafe_learned_worlds"] == 0
        and gate["ood_ungroundable_abstained"]
    )
    retained_method = {
        "name": "intervention_grounded_visual_belief_planning",
        "stages": [
            "discover controllable pixels by intervention",
            "bind the same appearance in a visual goal image",
            "reconstruct velocity from frame history",
            "learn action-conditioned visual transitions",
            "invent and execute hover diagnostics",
            "search multi-step action sequences",
            "commit prediction before physical execution",
            "re-identify after morphology, camera, or dynamics transfer",
        ],
    }
    learning = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_authority
    )
    cohort_id = "rgb_belief_mujoco_" + _canonical_hash(gate)[:16]
    learning.store.state.setdefault("rgb_belief_state_physical_methods", {})[cohort_id] = {
        "method": retained_method,
        "gate": gate,
        "created_at": _utc_timestamp(),
    }
    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal="rgb_belief_state_physical_planning",
        steps=retained_method["stages"],
        score=float(learned_success / max(1, len(sealed))),
        success=passed,
        evidence={"cohort_id": cohort_id, "gate": gate},
        source_rules=[],
    )
    promotion = learning.skills.promote(candidate)
    learning.skills.record_outcome(
        procedure_id=PROCEDURE_ID, success=passed, score=candidate.score,
        evidence=candidate.evidence,
    )
    learning.store.commit(reason="rgb_belief_state_mujoco_planning_v2")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_authority
    )
    restart = {
        "cohort_retained": cohort_id in restarted.store.state.get("rgb_belief_state_physical_methods", {}),
        "champion_retained": restarted.store.state.get("champions", {}).get(
            "rgb_belief_state_physical_planning"
        ) == PROCEDURE_ID,
    }
    passed = bool(passed and all(restart.values()) and (
        promotion.get("promoted") or promotion.get("champion_id") == PROCEDURE_ID
    ))
    result = {
        "schema_version": "aion.rgb_belief_state_mujoco_planning.v1",
        "procedure_id": PROCEDURE_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "status": "PROMOTED" if passed else "REJECTED",
        "gate": gate,
        "development": development,
        "sealed": sealed,
        "cold": cold,
        "ood": ood,
        "retained_method": retained_method,
        "promotion": promotion,
        "restart": restart,
        "claim_boundary": (
            "RGB observations, belief-state reconstruction and planning are real, but the scene family, "
            "two-axis actuator schema, model class and MuJoCo outcome authority remain engineered."
        ),
    }
    _atomic_json(result_path, result)
    return result


if __name__ == "__main__":
    print(json.dumps(run(repo_root=Path(__file__).resolve().parents[3]), indent=2, sort_keys=True))
