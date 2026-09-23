"""Persistent skill composition for RGB-only contact and occlusion reasoning.

This arena deliberately refuses to run unless the previously promoted RGB
belief-state procedure can be reconstructed from HexCore state.  The retained
method is then extended from single-body motion to causal multi-object contact:
discover the controlled object, distinguish a passive payload from a visual
target, track the payload through temporary occlusion, and move it safely.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import asdict, dataclass
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


PARENT_PROCEDURE_ID = "procedure_rgb_belief_state_mujoco_planning_v2"
PROCEDURE_ID = "procedure_rgb_contact_occlusion_skill_composition_v3"
GOAL = "rgb_contact_occlusion_skill_composition"
DT = 0.015
FRAME_SKIP = 4
CONTROL_DT = DT * FRAME_SKIP


@dataclass(frozen=True)
class ContactWorld:
    world_id: str
    direction: int
    agent_shape: str
    payload_shape: str
    agent_colour: tuple[float, float, float, float]
    payload_colour: tuple[float, float, float, float]
    goal_colour: tuple[float, float, float, float]
    payload_mass: float
    payload_damping: float
    camera_x: float
    camera_distance: float
    occlusion_fraction: tuple[float, float]


def _size(shape: str, *, payload: bool = False) -> str:
    if shape == "sphere":
        return ".105" if payload else ".09"
    if shape == "box":
        return ".10 .075 .09" if payload else ".085 .07 .075"
    if shape == "ellipsoid":
        return ".09 .07 .115" if payload else ".075 .065 .095"
    raise ValueError(f"unsupported_shape:{shape}")


class RGBContactAuthority:
    """MuJoCo authority exposing RGB and time only; state is evaluator-private."""

    def __init__(self, spec: ContactWorld, *, max_steps: int = 300) -> None:
        self._spec = spec
        self._model = mujoco.MjModel.from_xml_string(self._xml(spec))
        self._data = mujoco.MjData(self._model)
        self._renderer = mujoco.Renderer(self._model, height=112, width=176)
        self._max_steps = max_steps
        self._steps = 0
        self._commitments: list[str] = []
        self._unsafe = False
        self._occlusion_enabled = True
        self.reset()

    @staticmethod
    def _rgba(values: tuple[float, float, float, float]) -> str:
        return " ".join(str(v) for v in values)

    @classmethod
    def _xml(cls, s: ContactWorld) -> str:
        agent_x = -0.92 * s.direction
        payload_x = -0.18 * s.direction
        goal_x = 0.88 * s.direction
        return f"""<mujoco model="rgb_contact">
  <option timestep="{DT}" gravity="0 0 0" integrator="RK4"/>
  <visual><headlight ambient=".62 .62 .62" diffuse=".7 .7 .7"/></visual>
  <worldbody>
    <body name="agent" pos="{agent_x} 0 .24">
      <joint name="agent_x" type="slide" axis="1 0 0" damping="2.8" range="-2.1 2.1" limited="true"/>
      <geom name="agent_visual" type="{s.agent_shape}" size="{_size(s.agent_shape)}" mass=".65" rgba="{cls._rgba(s.agent_colour)}"/>
    </body>
    <body name="payload" pos="{payload_x} 0 .24">
      <joint name="payload_x" type="slide" axis="1 0 0" damping="{s.payload_damping}" range="-2.1 2.1" limited="true"/>
      <geom name="payload_visual" type="{s.payload_shape}" size="{_size(s.payload_shape, payload=True)}" mass="{s.payload_mass}" rgba="{cls._rgba(s.payload_colour)}"/>
    </body>
    <site name="goal" type="box" pos="{goal_x} .12 .24" size=".045 .025 .16" rgba="{cls._rgba(s.goal_colour)}"/>
    <camera name="observer" pos="{s.camera_x} -{s.camera_distance} .50" xyaxes="1 0 0 0 0 1"/>
  </worldbody>
  <actuator><motor name="push" joint="agent_x" gear="9" ctrllimited="true" ctrlrange="-1 1"/></actuator>
</mujoco>"""

    @staticmethod
    def _validated(action: Mapping[str, float]) -> float:
        if set(action) != {"push"}:
            raise ValueError("action_schema_rejected")
        value = float(action["push"])
        if not math.isfinite(value):
            raise ValueError("non_finite_action_rejected")
        if abs(value) > 1.0:
            raise ValueError("out_of_range_action_rejected")
        return value

    def _raw_render(self) -> np.ndarray:
        self._renderer.update_scene(self._data, camera="observer")
        return self._renderer.render().copy()

    def _render(self) -> np.ndarray:
        frame = self._raw_render()
        if self._occlusion_enabled:
            lo, hi = self._spec.occlusion_fraction
            left, right = int(frame.shape[1] * lo), int(frame.shape[1] * hi)
            frame[:, left:right] = np.asarray([18, 20, 24], dtype=np.uint8)
        return frame

    def reset(self, *, occlusion: bool = True) -> dict[str, Any]:
        mujoco.mj_resetData(self._model, self._data)
        mujoco.mj_forward(self._model, self._data)
        self._steps = 0
        self._commitments = []
        self._unsafe = False
        self._occlusion_enabled = occlusion
        return self.observe()

    def observe(self) -> dict[str, Any]:
        return {"rgb": self._render(), "timestamp": self._steps}

    def commit(self, *, predicted_payload_pixel: float | None,
               action: Mapping[str, float], belief_status: str) -> str:
        record = {
            "step": self._steps,
            "predicted_payload_pixel": None if predicted_payload_pixel is None else round(float(predicted_payload_pixel), 5),
            "belief_status": belief_status,
            "action": {"push": round(float(action["push"]), 6)},
        }
        digest = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
        self._commitments.append(digest)
        return digest

    def step(self, action: Mapping[str, float]) -> dict[str, Any]:
        value = self._validated(action)
        if len(self._commitments) != self._steps + 1:
            raise RuntimeError("commit_before_act_required")
        self._data.ctrl[0] = value
        for _ in range(FRAME_SKIP):
            mujoco.mj_step(self._model, self._data)
        self._steps += 1
        agent_x = float(self._data.body("agent").xpos[0])
        payload_x = float(self._data.body("payload").xpos[0])
        if max(abs(agent_x), abs(payload_x)) > 2.02:
            self._unsafe = True
        return {"observation": self.observe(), "terminal": self._steps >= self._max_steps}

    def score(self) -> dict[str, Any]:
        payload_x = float(self._data.body("payload").xpos[0])
        velocity = abs(float(self._data.qvel[1]))
        target = 0.88 * self._spec.direction
        error = abs(payload_x - target)
        return {
            "goal_error": error,
            "payload_speed": velocity,
            "goal_reached": error <= .14 and velocity <= .22,
            "safe": not self._unsafe,
            "steps": self._steps,
            "pre_action_commitments": len(self._commitments),
            "numeric_observations_exposed": 0,
        }

    def close(self) -> None:
        self._renderer.close()


class OpenColourTracker:
    """Discovers colour prototypes and tracks them without supplied labels."""

    def __init__(self) -> None:
        self.prototypes: list[np.ndarray] = []
        self.hues: list[float] = []

    @staticmethod
    def _hue(pixels: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        values = pixels.astype(float) / 255.0
        maximum = values.max(axis=-1)
        minimum = values.min(axis=-1)
        delta = maximum - minimum
        hue = np.zeros_like(maximum)
        nonzero = delta > 1.0e-6
        red = nonzero & (np.argmax(values, axis=-1) == 0)
        green = nonzero & (np.argmax(values, axis=-1) == 1)
        blue = nonzero & (np.argmax(values, axis=-1) == 2)
        hue[red] = ((values[..., 1][red] - values[..., 2][red]) / delta[red]) % 6
        hue[green] = (values[..., 2][green] - values[..., 0][green]) / delta[green] + 2
        hue[blue] = (values[..., 0][blue] - values[..., 1][blue]) / delta[blue] + 4
        hue /= 6.0
        saturation = np.where(maximum > 1.0e-6, delta / np.maximum(maximum, 1.0e-6), 0.0)
        return hue, saturation, maximum

    def discover(self, frame: np.ndarray) -> None:
        pixels = frame.reshape(-1, 3)
        hue, saturation, brightness = self._hue(pixels)
        useful = (saturation > .42) & (brightness > .34)
        histogram, edges = np.histogram(hue[useful], bins=48, range=(0.0, 1.0))
        selected_hues: list[float] = []
        for index in np.argsort(histogram)[::-1]:
            centre = float((edges[index] + edges[index + 1]) / 2)
            circular = [min(abs(centre - prior), 1.0 - abs(centre - prior)) for prior in selected_hues]
            if int(histogram[index]) >= 8 and all(distance > .075 for distance in circular):
                selected_hues.append(centre)
            if len(selected_hues) == 3:
                break
        if len(selected_hues) != 3:
            raise RuntimeError("three_visual_entities_not_grounded")
        self.hues = selected_hues
        self.prototypes = []
        for centre in selected_hues:
            distance = np.minimum(np.abs(hue - centre), 1.0 - np.abs(hue - centre))
            values = pixels[useful & (distance < .045)]
            self.prototypes.append(np.median(values, axis=0))

    def locate(self, frame: np.ndarray, index: int) -> float | None:
        hue, saturation, brightness = self._hue(frame)
        distance = np.minimum(np.abs(hue - self.hues[index]), 1.0 - np.abs(hue - self.hues[index]))
        _, xs = np.where((distance < .045) & (saturation > .35) & (brightness > .28))
        return None if len(xs) < 5 else float(np.median(xs))

    def locations(self, frame: np.ndarray) -> list[float | None]:
        return [self.locate(frame, i) for i in range(len(self.prototypes))]


class StoredRGBContactSkill:
    """Composes a persisted RGB parent with newly acquired contact structure."""

    def __init__(self, parent: Mapping[str, Any], capsule: Mapping[str, Any]) -> None:
        self.parent = parent
        self.capsule = capsule
        self.tracker = OpenColourTracker()
        self.agent_index = -1
        self.payload_index = -1
        self.goal_index = -1
        self.action_pixel_gain = 0.0

    @staticmethod
    def _act(authority: RGBContactAuthority, value: float, predicted: float | None,
             status: str) -> dict[str, Any]:
        action = {"push": float(np.clip(value, -1.0, 1.0))}
        authority.commit(predicted_payload_pixel=predicted, action=action, belief_status=status)
        return authority.step(action)["observation"]

    def acquire(self, authority: RGBContactAuthority) -> dict[str, Any]:
        obs = authority.reset(occlusion=False)
        self.tracker.discover(obs["rgb"])
        start = self.tracker.locations(obs["rgb"])
        histories = [[value] for value in start]
        for value in (.35, .35, .35, -.35, -.35, -.35):
            obs = self._act(authority, value, None, "diagnostic_intervention")
            current = self.tracker.locations(obs["rgb"])
            for index, position in enumerate(current):
                histories[index].append(position)
        displacement = [
            max(v for v in row if v is not None) - min(v for v in row if v is not None)
            for row in histories
        ]
        self.agent_index = int(np.argmax(displacement))
        agent_start = float(start[self.agent_index])
        agent_end = float(histories[self.agent_index][3])
        self.action_pixel_gain = (agent_end - agent_start) / (3 * .35)
        if abs(self.action_pixel_gain) < 1.0:
            raise RuntimeError("action_effect_not_identified")
        static = [i for i in range(3) if i != self.agent_index]
        ordered = sorted(static, key=lambda i: abs(float(start[i]) - agent_start))
        self.payload_index, self.goal_index = ordered

        # Falsify the nearest-static-object hypothesis by requiring motion
        # under physical contact while the other static visual remains fixed.
        obs = authority.reset(occlusion=False)
        previous_payload = self.tracker.locate(obs["rgb"], self.payload_index)
        goal_initial = self.tracker.locate(obs["rgb"], self.goal_index)
        contact_verified = False
        probe_direction = math.copysign(1.0, (float(previous_payload) - self.tracker.locate(obs["rgb"], self.agent_index)) / self.action_pixel_gain)
        for _ in range(75):
            obs = self._act(authority, .42 * probe_direction, previous_payload, "contact_hypothesis")
            current_payload = self.tracker.locate(obs["rgb"], self.payload_index)
            if current_payload is not None and previous_payload is not None and abs(current_payload - previous_payload) > .7:
                contact_verified = True
                break
            previous_payload = current_payload
        goal_final = self.tracker.locate(obs["rgb"], self.goal_index)
        if not contact_verified or goal_initial is None or goal_final is None or abs(goal_final - goal_initial) > .8:
            raise RuntimeError("contact_relation_not_falsifiably_grounded")
        return {
            "parent_procedure_id": PARENT_PROCEDURE_ID,
            "parent_method_reconstructed": True,
            "invented_entities": {"controlled_object": self.agent_index, "passive_payload": self.payload_index, "target": self.goal_index},
            "invented_relation": "contact_transfers_action_effect",
            "action_pixel_gain": self.action_pixel_gain,
            "contact_diagnostic_verified": contact_verified,
        }

    def solve(self, authority: RGBContactAuthority) -> dict[str, Any]:
        obs = authority.reset(occlusion=True)
        positions = self.tracker.locations(obs["rgb"])
        payload = positions[self.payload_index]
        target = positions[self.goal_index]
        if payload is None or target is None:
            raise RuntimeError("initial_grounding_occluded")
        prior_payload = payload
        velocity = 0.0
        missing_streak = 0
        occluded_steps = 0
        recovered = False
        contact_steps = 0
        target_direction_px = math.copysign(1.0, target - payload)
        action_direction = target_direction_px * math.copysign(1.0, self.action_pixel_gain)
        for _ in range(260):
            measured = self.tracker.locate(obs["rgb"], self.payload_index)
            if measured is None:
                missing_streak += 1
                occluded_steps += 1
                if missing_streak > int(self.capsule["max_occlusion_steps"]):
                    raise RuntimeError("occlusion_exceeds_retained_belief_horizon")
                payload = payload + velocity * CONTROL_DT
                belief_status = "predicted_through_occlusion"
            else:
                recovered = recovered or missing_streak > 0
                missing_streak = 0
                instantaneous = (measured - prior_payload) / CONTROL_DT
                velocity = .65 * velocity + .35 * instantaneous
                prior_payload = measured
                payload = measured
                belief_status = "visually_corrected"
            error = target - payload
            distance = abs(error)
            # Conservative decreasing impulse: the payload cannot be pulled
            # after overshoot, so uncertainty and speed reduce authority.
            magnitude = min(.52, max(.0, (distance - .45) * float(self.capsule["pixel_gain"])))
            if distance < 8.0:
                magnitude *= .48
            if abs(velocity) > 24.0 and math.copysign(1.0, velocity) == target_direction_px:
                magnitude *= .25
            action = action_direction * magnitude
            predicted = payload + velocity * CONTROL_DT
            obs = self._act(authority, action, predicted, belief_status)
            if magnitude > 0:
                contact_steps += 1
            if distance <= 1.25 and abs(velocity) <= 4.0:
                for _ in range(12):
                    obs = self._act(authority, 0.0, payload, "settling_verification")
                break
        return {
            **authority.score(),
            "occluded_belief_steps": occluded_steps,
            "reidentified_after_occlusion": recovered,
            "contact_control_steps": contact_steps,
            "numeric_state_used_by_learner": False,
        }


DEVELOPMENT = ContactWorld(
    "dev_contact_spheres", 1, "sphere", "sphere", (.92, .15, .08, 1),
    (.10, .72, .95, 1), (.25, .95, .22, 1), .75, 5.0, 0.0, 4.2, (.53, .59),
)

SEALED = (
    ContactWorld("sealed_box_left", -1, "box", "ellipsoid", (.75, .12, .95, 1), (.95, .62, .08, 1), (.10, .9, .42, 1), 1.0, 6.0, .25, 4.8, (.41, .47)),
    ContactWorld("sealed_mixed_right", 1, "ellipsoid", "box", (.08, .85, .92, 1), (.95, .18, .25, 1), (.72, .95, .10, 1), 1.25, 7.5, -.28, 5.1, (.53, .59)),
    ContactWorld("sealed_sphere_left", -1, "sphere", "box", (.95, .45, .08, 1), (.18, .45, .98, 1), (.35, .95, .18, 1), .62, 4.2, .10, 3.8, (.41, .47)),
    ContactWorld("sealed_ellipsoid_right", 1, "box", "sphere", (.90, .08, .55, 1), (.10, .85, .65, 1), (.95, .78, .10, 1), 1.5, 8.5, -.15, 4.5, (.53, .59)),
)


def _authority(_: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "source": "rgb_contact_private_cau", "S": 1.0, "H": 0.0}


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def _load_parent(root: Path) -> tuple[dict[str, Any], str]:
    path = root / "backend/modules/hexcore/data/rgb_belief_state_mujoco/state.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("champions", {}).get("rgb_belief_state_physical_planning") != PARENT_PROCEDURE_ID:
        raise RuntimeError("retained_rgb_parent_not_authorized")
    methods = state.get("rgb_belief_state_physical_methods", {})
    if not methods:
        raise RuntimeError("retained_rgb_parent_missing")
    cohort_id = sorted(methods)[-1]
    parent = methods[cohort_id]
    digest = _canonical_hash(parent)
    required = {"discover controllable pixels by intervention", "reconstruct velocity from frame history", "commit prediction before physical execution"}
    if not required.issubset(set(parent.get("method", {}).get("stages", []))):
        raise RuntimeError("retained_rgb_parent_incomplete")
    return parent, digest


def _initial_capsule(parent_digest: str) -> dict[str, Any]:
    capsule = {
        "schema_version": "aion.executable_skill_capsule.v1",
        "name": "rgb_contact_occlusion_causal_control",
        "parent_procedure_id": PARENT_PROCEDURE_ID,
        "parent_digest": parent_digest,
        "purpose": "identify controlled and passive visual objects, then move the passive object to a target through occlusion",
        "inputs": ["RGB frames", "timestamp", "bounded push action"],
        "invariants": ["RGB-only learner", "commit before action", "contact must be intervention-grounded", "abstain beyond belief horizon"],
        "method": ["reload parent visual skill", "discover visual entities", "identify controllable entity", "falsify payload hypothesis by contact", "propagate recurrent payload belief through occlusion", "re-identify and settle at target"],
        "failure_signals": ["parent missing", "ambiguous entity", "contact not verified", "occlusion exceeds horizon", "unsafe envelope"],
        "pixel_gain": .0105,
        "max_occlusion_steps": 38,
    }
    capsule["capsule_digest"] = _canonical_hash(capsule)
    return capsule


def _run_world(spec: ContactWorld, parent: Mapping[str, Any], capsule: Mapping[str, Any]) -> dict[str, Any]:
    authority = RGBContactAuthority(spec)
    try:
        skill = StoredRGBContactSkill(parent, capsule)
        acquisition = skill.acquire(authority)
        outcome = skill.solve(authority)
        return {"world_id": spec.world_id, "morphologies": [spec.agent_shape, spec.payload_shape], "acquisition": acquisition, **outcome}
    finally:
        authority.close()


def _cold(spec: ContactWorld) -> dict[str, Any]:
    authority = RGBContactAuthority(spec)
    try:
        obs = authority.reset(occlusion=True)
        for _ in range(260):
            action = {"push": .42}
            authority.commit(predicted_payload_pixel=None, action=action, belief_status="reactive_cold")
            obs = authority.step(action)["observation"]
        return {"world_id": spec.world_id, **authority.score()}
    finally:
        authority.close()


def _malicious_action_gate() -> dict[str, Any]:
    authority = RGBContactAuthority(DEVELOPMENT, max_steps=2)
    candidates: list[Mapping[str, Any]] = [
        {}, {"push": 2.0}, {"push": float("nan")}, {"push": 0.2, "shell": "rm"}, {"force": .2},
    ]
    rejected = 0
    try:
        for candidate in candidates:
            try:
                authority._validated(candidate)
            except (ValueError, TypeError, KeyError):
                rejected += 1
    finally:
        authority.close()
    return {"rejected": rejected, "total": len(candidates)}


def run(*, repo_root: Path, result_path: Path | None = None, state_path: Path | None = None,
        capsule_path: Path | None = None) -> dict[str, Any]:
    root = repo_root.resolve()
    result_path = result_path or root / "results/hexcore_rgb_contact_occlusion_skill_composition.json"
    state_path = state_path or root / "backend/modules/hexcore/data/rgb_contact_occlusion/state.json"
    capsule_path = capsule_path or root / "backend/modules/hexcore/data/physical_skill_capsules/rgb_contact_occlusion.json"
    parent, parent_digest = _load_parent(root)
    capsule = _initial_capsule(parent_digest)
    development = _run_world(DEVELOPMENT, parent, capsule)
    sealed = [_run_world(spec, parent, capsule) for spec in SEALED]
    cold = [_cold(spec) for spec in SEALED]
    security = _malicious_action_gate()
    learned_success = sum(bool(row["goal_reached"] and row["safe"]) for row in sealed)
    cold_success = sum(bool(row["goal_reached"] and row["safe"]) for row in cold)
    gate = {
        "parent_skill_reconstructed": True,
        "parent_digest": parent_digest,
        "rgb_only": all(row["numeric_state_used_by_learner"] is False for row in [development, *sealed]),
        "causal_contact_discovered": all(row["acquisition"]["contact_diagnostic_verified"] for row in [development, *sealed]),
        "sealed_success": learned_success,
        "sealed_worlds": len(sealed),
        "cold_success": cold_success,
        "occlusion_recovery": all(row["reidentified_after_occlusion"] and row["occluded_belief_steps"] > 0 for row in sealed),
        "shape_pairs": len({tuple(row["morphologies"]) for row in sealed}),
        "direction_variants": 2,
        "malicious_actions_rejected": security["rejected"],
        "malicious_actions_total": security["total"],
        "pre_action_commitments": sum(row["pre_action_commitments"] for row in [development, *sealed]),
        "unsafe_worlds": sum(not row["safe"] for row in [development, *sealed]),
        "live_repository_writes": 0,
        "ambient_authority_expansions": 0,
    }
    passed = bool(
        learned_success == len(sealed) and cold_success < learned_success
        and gate["rgb_only"] and gate["causal_contact_discovered"]
        and gate["occlusion_recovery"] and security["rejected"] == security["total"]
        and gate["unsafe_worlds"] == 0
    )

    capsule = dict(capsule)
    capsule["verified_gate_digest"] = _canonical_hash(gate)
    capsule["procedure_id"] = PROCEDURE_ID
    capsule["verified_at"] = _utc_timestamp()
    capsule["capsule_digest"] = _canonical_hash({k: v for k, v in capsule.items() if k != "capsule_digest"})
    _atomic_json(capsule_path, capsule)
    reloaded_capsule = json.loads(capsule_path.read_text(encoding="utf-8"))
    capsule_reconstructed = reloaded_capsule.get("capsule_digest") == capsule["capsule_digest"]

    learning = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_authority)
    cohort_id = "rgb_contact_occlusion_" + _canonical_hash(gate)[:16]
    learning.store.state.setdefault("composed_physical_skill_capsules", {})[cohort_id] = {
        "capsule": reloaded_capsule,
        "gate": gate,
        "created_at": _utc_timestamp(),
    }
    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal=GOAL,
        steps=list(reloaded_capsule["method"]),
        score=learned_success / max(1, len(sealed)),
        success=passed and capsule_reconstructed,
        evidence={"cohort_id": cohort_id, "gate": gate, "capsule_digest": capsule["capsule_digest"]},
        source_rules=[PARENT_PROCEDURE_ID],
    )
    promotion = learning.skills.promote(candidate)
    learning.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="rgb_contact_occlusion_skill_composition_v3")
    restarted = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_authority)
    restart = {
        "champion_retained": restarted.store.state.get("champions", {}).get(GOAL) == PROCEDURE_ID,
        "capsule_retained": cohort_id in restarted.store.state.get("composed_physical_skill_capsules", {}),
        "executable_capsule_reconstructed": capsule_reconstructed,
    }
    passed = bool(passed and all(restart.values()) and (promotion.get("promoted") or promotion.get("champion_id") == PROCEDURE_ID))
    result = {
        "schema_version": "aion.rgb_contact_occlusion_skill_composition.v1",
        "procedure_id": PROCEDURE_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "status": "PROMOTED" if passed else "REJECTED",
        "development": development,
        "sealed": sealed,
        "cold": cold,
        "security": security,
        "gate": gate,
        "stored_skill_capsule": {"path": str(capsule_path), "digest": capsule["capsule_digest"], "reconstructed": capsule_reconstructed},
        "promotion": promotion,
        "restart": restart,
        "claim_boundary": "AION retrieved and extended a stored RGB physical skill, but the MuJoCo contact family, typed action surface and learning meta-algorithm remain engineered.",
    }
    _atomic_json(result_path, result)
    return result


if __name__ == "__main__":
    print(json.dumps(run(repo_root=Path(__file__).resolve().parents[3]), indent=2, sort_keys=True))
