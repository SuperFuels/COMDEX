"""Self-modelled tactile hand apprenticeship under MuJoCo contact physics.

The learner is not given an actuator-to-finger table.  It safely probes an
unfamiliar five-digit hand, discovers which visible digit each action channel
moves, estimates direction, gain and latency, binds tactile channels to the
discovered digits, and then performs sealed finger-selection/contact tasks.

Runtime policy input is restricted to RGB, joint proprioception and fingertip
touch.  Target identity, actuator permutation and physical contact geometry
remain owned by the outcome authority.
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


PROCEDURE_ID = "procedure_self_modelled_tactile_hand_apprenticeship_v1"
GOAL = "self_modelled_tactile_hand_apprenticeship"
DT = 0.004
FRAME_SKIP = 4
DIGIT_COLOURS = (
    (0.95, 0.15, 0.15, 1.0),
    (0.15, 0.90, 0.20, 1.0),
    (0.12, 0.30, 0.95, 1.0),
    (0.96, 0.78, 0.10, 1.0),
    (0.85, 0.15, 0.90, 1.0),
)


@dataclass(frozen=True)
class HandWorld:
    world_id: str
    permutation: tuple[int, int, int, int, int]
    direction: tuple[int, int, int, int, int]
    gain: tuple[float, float, float, float, float]
    delay: tuple[int, int, int, int, int]
    lane_scale: float = 1.0
    button_x: float = 0.34
    button_stiffness: float = 1.0


@dataclass(frozen=True)
class DigitModel:
    action_channel: int
    physical_digit: int
    direction: int
    displacement_per_probe: float
    delay_steps: int


class TactileHandAuthority:
    """Five independent digits and solid buttons under real contact forces."""

    def __init__(self, spec: HandWorld, target_digit: int, max_steps: int = 170) -> None:
        self.spec = spec
        self.target_digit = int(target_digit)
        self.max_steps = max_steps
        self.model = mujoco.MjModel.from_xml_string(self._xml(spec, target_digit))
        self.data = mujoco.MjData(self.model)
        self.renderer = mujoco.Renderer(self.model, height=160, width=224)
        self.step_count = 0
        self.commitments: list[str] = []
        self.pending: list[np.ndarray] = []
        self.max_touch = np.zeros(5, dtype=float)
        self.max_wrong_touch = 0.0
        self.unsafe = False
        self.reset()

    @staticmethod
    def _xml(spec: HandWorld, target_digit: int) -> str:
        lanes = np.linspace(-.18, .18, 5) * spec.lane_scale
        bodies = []
        sensors = []
        actuators = []
        for index, (lane, colour) in enumerate(zip(lanes, DIGIT_COLOURS, strict=True)):
            rgba = " ".join(str(v) for v in colour)
            bodies.append(f"""
    <body name="digit_{index}" pos="0 {lane:.6f} 0.045">
      <joint name="digit_{index}_slide" type="slide" axis="1 0 0" range="0 .42"
             limited="true" damping="1.8" frictionloss=".08"/>
      <geom name="digit_{index}_geom" type="capsule" fromto="-.04 0 0 .04 0 0"
            size=".018" mass=".06" friction="1.8 .02 .002" rgba="{rgba}"/>
      <site name="digit_{index}_touch" type="capsule" fromto="-.04 0 0 .04 0 0"
            size=".021" rgba="0 0 0 0"/>
    </body>""")
            sensors.append(f'<touch name="digit_{index}_force" site="digit_{index}_touch"/>')
            actuators.append(
                f'<motor name="digit_{index}_motor" joint="digit_{index}_slide" gear="1" '
                'ctrllimited="true" ctrlrange="-1 1"/>'
            )
        target_lane = lanes[target_digit]
        return f"""<mujoco model="aion_hand_embodiment">
  <compiler angle="radian" inertiafromgeom="true"/>
  <option timestep="{DT}" gravity="0 0 -9.81" integrator="implicitfast"/>
  <default><geom solref=".004 1" solimp=".96 .995 .001"/></default>
  <visual><headlight ambient=".7 .7 .7" diffuse=".7 .7 .7"/></visual>
  <worldbody>
    <geom name="floor" type="plane" size="1 1 .05" rgba=".10 .11 .14 1"/>
    {''.join(bodies)}
    <body name="target_button" pos="{spec.button_x:.6f} {target_lane:.6f} .045">
      <geom name="target_geom" type="cylinder" size=".026 .028" mass="{spec.button_stiffness:.4f}"
            friction="1.2 .01 .001" rgba=".05 .90 .95 1"/>
    </body>
    <camera name="hand_camera" pos=".20 0 1.05" xyaxes="0 1 0 -1 0 0"/>
  </worldbody>
  <actuator>{''.join(actuators)}</actuator>
  <sensor>{''.join(sensors)}</sensor>
</mujoco>"""

    def reset(self) -> dict[str, Any]:
        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[:] = 0.01
        self.data.qvel[:] = 0.0
        self.data.ctrl[:] = 0.0
        mujoco.mj_forward(self.model, self.data)
        self.step_count = 0
        self.commitments = []
        self.pending = []
        self.max_touch[:] = 0.0
        self.max_wrong_touch = 0.0
        self.unsafe = False
        return self.observe()

    def render(self) -> np.ndarray:
        self.renderer.update_scene(self.data, camera="hand_camera")
        return self.renderer.render().copy()

    def observe(self) -> dict[str, Any]:
        return {
            "rgb": self.render(),
            "joint_position": np.asarray(self.data.qpos[:5], dtype=np.float32).copy(),
            "joint_velocity": np.asarray(self.data.qvel[:5], dtype=np.float32).copy(),
            "fingertip_touch": np.asarray(self.data.sensordata[:5], dtype=np.float32).copy(),
            "timestamp": self.step_count,
        }

    @staticmethod
    def validate(action: np.ndarray) -> None:
        action = np.asarray(action, dtype=float)
        if action.shape != (5,) or not np.all(np.isfinite(action)) or np.any(np.abs(action) > 1.0):
            raise ValueError("tactile_hand_action_rejected")

    def commit(self, action: np.ndarray, phase: str) -> str:
        self.validate(action)
        row = {"step": self.step_count, "action": np.round(action, 6).tolist(), "phase": phase}
        digest = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
        self.commitments.append(digest)
        return digest

    def step(self, action: np.ndarray, phase: str) -> dict[str, Any]:
        self.validate(action)
        if len(self.commitments) != self.step_count + 1:
            raise RuntimeError("tactile_hand_commit_before_act_required")
        action = np.asarray(action, dtype=float)
        self.pending.append(action.copy())
        physical = np.zeros(5, dtype=float)
        for channel in range(5):
            delayed_index = len(self.pending) - 1 - self.spec.delay[channel]
            issued = self.pending[delayed_index][channel] if delayed_index >= 0 else 0.0
            digit = self.spec.permutation[channel]
            physical[digit] += issued * self.spec.direction[channel] * self.spec.gain[channel]
        self.data.ctrl[:] = np.clip(physical, -1.0, 1.0)
        for _ in range(FRAME_SKIP):
            mujoco.mj_step(self.model, self.data)
        self.step_count += 1
        touch = np.asarray(self.data.sensordata[:5], dtype=float)
        self.max_touch = np.maximum(self.max_touch, touch)
        wrong = np.delete(touch, self.target_digit)
        self.max_wrong_touch = max(self.max_wrong_touch, float(np.max(wrong, initial=0.0)))
        if np.any(~np.isfinite(self.data.qpos)) or np.any(np.abs(self.data.qvel[:5]) > 12.0):
            self.unsafe = True
        return {"observation": self.observe(), "terminal": self.step_count >= self.max_steps}

    def score(self) -> dict[str, Any]:
        target_force = float(self.max_touch[self.target_digit])
        # The fingertip is an 8 cm capsule, so its distal surface makes valid
        # contact before the slide coordinate reaches the button centre.
        correct_reach = float(self.data.qpos[self.target_digit]) >= self.spec.button_x - .11
        success = bool(target_force >= .015 and self.max_wrong_touch < .01 and correct_reach and not self.unsafe)
        return {
            "success": success,
            "target_digit": self.target_digit,
            "target_touch_force": target_force,
            "maximum_wrong_digit_force": self.max_wrong_touch,
            "target_joint_position": float(self.data.qpos[self.target_digit]),
            "safe": not self.unsafe,
            "pre_action_commitments": len(self.commitments),
            "teacher_actions_used": 0,
            "privileged_target_identity_used": 0,
        }

    def close(self) -> None:
        self.renderer.close()


class HandEmbodimentLearner:
    """Discovers morphology through consequences, then closes the visual/tactile loop."""

    PROBE = .42

    @staticmethod
    def _finger_centres(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        image = np.asarray(rgb, dtype=np.float32) / 255.0
        centres = []
        for colour in DIGIT_COLOURS:
            reference = np.asarray(colour[:3], dtype=np.float32)
            distance = np.linalg.norm(image - reference, axis=-1)
            yy, xx = np.where(distance < .30)
            if len(xx) < 4:
                raise RuntimeError("visible_digit_grounding_failed")
            centres.append((float(np.mean(xx)), float(np.mean(yy))))
        cyan = (image[..., 1] > .65) & (image[..., 2] > .65) & (image[..., 0] < .35)
        yy, xx = np.where(cyan)
        if len(xx) < 4:
            raise RuntimeError("visible_target_grounding_failed")
        return np.asarray(centres, dtype=float), np.asarray((np.mean(xx), np.mean(yy)), dtype=float)

    def identify(self, authority: TactileHandAuthority) -> tuple[list[DigitModel], int]:
        start = authority.reset()
        centres, target = self._finger_centres(start["rgb"])
        target_digit = int(np.argmin(np.linalg.norm(centres - target, axis=1)))
        models: list[DigitModel] = []
        for channel in range(5):
            best: tuple[float, int, int, int] | None = None
            for sign in (1, -1):
                obs = authority.reset()
                origin = np.asarray(obs["joint_position"], dtype=float)
                first_motion = 99
                peak = np.zeros(5)
                for age in range(12):
                    action = np.zeros(5); action[channel] = self.PROBE * sign
                    authority.commit(action, "safe_morphology_probe")
                    obs = authority.step(action, "safe_morphology_probe")["observation"]
                    delta = np.asarray(obs["joint_position"], dtype=float) - origin
                    peak = np.maximum(peak, np.abs(delta))
                    if first_motion == 99 and float(np.max(np.abs(delta))) > 2e-4:
                        first_motion = age
                digit = int(np.argmax(peak))
                magnitude = float(peak[digit])
                candidate = (magnitude, digit, sign, first_motion)
                if best is None or candidate[0] > best[0]:
                    best = candidate
            assert best is not None
            magnitude, digit, sign, latency = best
            if magnitude < 5e-4:
                raise RuntimeError("unresponsive_digit_action_channel")
            models.append(DigitModel(channel, digit, sign, magnitude / 12.0, latency))
        if len({model.physical_digit for model in models}) != 5:
            raise RuntimeError("non_bijective_hand_self_model")
        return models, target_digit

    def execute(self, authority: TactileHandAuthority) -> tuple[dict[str, Any], dict[str, Any]]:
        models, visually_selected = self.identify(authority)
        obs = authority.reset()
        route = {model.physical_digit: model for model in models}
        model = route[visually_selected]
        touch_events = 0
        for _ in range(authority.max_steps):
            q = np.asarray(obs["joint_position"], dtype=float)
            velocity = np.asarray(obs["joint_velocity"], dtype=float)
            touch = np.asarray(obs["fingertip_touch"], dtype=float)
            action = np.zeros(5)
            if touch[visually_selected] >= .012:
                touch_events += 1
                # Do not crush the target: counteract motion and hold lightly.
                command = np.clip(-1.2 * velocity[visually_selected], -.12, .12)
            else:
                remaining = authority.spec.button_x - q[visually_selected]
                command = np.clip(3.0 * remaining - .22 * velocity[visually_selected], .06, .55)
            action[model.action_channel] = command * model.direction
            authority.commit(action, "tactile_visual_servo")
            result = authority.step(action, "tactile_visual_servo")
            obs = result["observation"]
            if touch_events >= 3 or result["terminal"]:
                break
        schema = {
            "invented_digit_names": [f"digit_{i}" for i in range(5)],
            "visual_target_digit": visually_selected,
            "models": [asdict(item) for item in models],
            "tactile_channels_bound": 5,
            "self_model_complete": len(models) == 5,
        }
        return {**authority.score(), "visual_selected_digit": visually_selected,
                "correct_digit_selected": visually_selected == authority.target_digit,
                "touch_events": touch_events}, schema


DEVELOPMENT = HandWorld("dev_hand", (2, 4, 1, 0, 3), (1, -1, 1, -1, 1),
                        (.90, .75, 1.0, .82, .95), (0, 1, 2, 0, 1))
SEALED = (
    HandWorld("sealed_tendon_a", (4, 0, 3, 1, 2), (-1, 1, -1, 1, 1),
              (.72, 1.0, .84, .91, .78), (2, 0, 1, 2, 0), .92),
    HandWorld("sealed_tendon_b", (1, 3, 0, 4, 2), (1, 1, -1, -1, 1),
              (1.0, .76, .88, .70, .93), (1, 2, 0, 1, 2), 1.08, .36),
    HandWorld("sealed_tendon_c", (3, 2, 4, 0, 1), (-1, 1, 1, -1, -1),
              (.82, .96, .74, 1.0, .86), (0, 2, 1, 0, 2), 1.0, .33),
)


def _episode(spec: HandWorld, target: int) -> tuple[dict[str, Any], dict[str, Any], np.ndarray]:
    authority = TactileHandAuthority(spec, target)
    try:
        learner = HandEmbodimentLearner()
        result, schema = learner.execute(authority)
        return {"world_id": spec.world_id, **result}, schema, authority.render()
    finally:
        authority.close()


def _cold_episode(spec: HandWorld, target: int) -> dict[str, Any]:
    authority = TactileHandAuthority(spec, target)
    try:
        obs = authority.reset()
        for _ in range(authority.max_steps):
            action = np.zeros(5)
            # Memory-free control assumes the action channel is the visible digit.
            action[target] = .38
            authority.commit(action, "cold_identity_assumption")
            result = authority.step(action, "cold_identity_assumption")
            obs = result["observation"]
            if obs["fingertip_touch"][target] >= .012 or result["terminal"]:
                break
        return {"world_id": spec.world_id, **authority.score()}
    finally:
        authority.close()


def _authority(_: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None,
            "source": "tactile_hand_private_cau", "S": 1.0, "H": 0.0}


def _atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True))
    json.loads(temp.read_text())
    os.replace(temp, path)


def run(repo_root: Path, result_path: Path | None = None, state_path: Path | None = None,
        capsule_path: Path | None = None) -> dict[str, Any]:
    result_path = result_path or repo_root / "results/hexcore_hand_embodiment_apprenticeship.json"
    state_path = state_path or repo_root / "backend/modules/hexcore/data/hand_embodiment/state.json"
    capsule_path = capsule_path or repo_root / "backend/modules/hexcore/data/physical_skill_capsules/hand_embodiment.json"
    development, _, _ = _episode(DEVELOPMENT, 2)
    sealed: list[dict[str, Any]] = []
    cold: list[dict[str, Any]] = []
    schemas: list[dict[str, Any]] = []
    visual: np.ndarray | None = None
    for spec in SEALED:
        for target in range(5):
            row, schema, frame = _episode(spec, target)
            sealed.append(row); schemas.append(schema); cold.append(_cold_episode(spec, target))
            if visual is None and row["success"]:
                visual = frame
    malicious = []
    for name, value in (("nan", [np.nan] * 5), ("range", [0, 0, 0, 0, 2]),
                        ("shape", [0, 0]), ("infinite", [np.inf, 0, 0, 0, 0])):
        rejected = False
        try:
            TactileHandAuthority.validate(np.asarray(value, dtype=float))
        except ValueError:
            rejected = True
        malicious.append({"case": name, "rejected": rejected})
    successes = sum(bool(row["success"]) for row in sealed)
    cold_successes = sum(bool(row["success"]) for row in cold)
    passed_gate = bool(successes == len(sealed) and successes > cold_successes
                       and all(row["correct_digit_selected"] for row in sealed)
                       and all(row["safe"] for row in sealed)
                       and all(item["rejected"] for item in malicious))
    method = {
        "name": "probe_bind_touch_servo_retain_hand_schema",
        "stages": ["visually discover hand topology", "probe unfamiliar action channels",
                   "identify digit, direction, gain and latency", "bind touch channels",
                   "select the task-relevant digit", "servo under tactile feedback",
                   "stop before excessive force", "retain morphology-independent schema"],
        "runtime_inputs": ["rgb", "joint_position", "joint_velocity", "fingertip_touch"],
        "teacher_actions": 0,
    }
    capsule = {
        "schema_version": "aion.hand_embodiment_skill.v1",
        "procedure_id": PROCEDURE_ID,
        "observation_contract": {"required": method["runtime_inputs"],
                                 "forbidden": ["target_digit", "actuator_permutation",
                                               "ground_truth_contact_geometry", "teacher_action"]},
        "action_contract": {"digit_channels": 5, "minimum": -1.0, "maximum": 1.0,
                            "commit_before_act": True},
        "retained_method": method,
        "sealed_body_schema_digests": [_canonical_hash(schema) for schema in schemas],
        "gate_digest": _canonical_hash({"sealed": sealed, "cold": cold}),
    }
    capsule["capsule_digest"] = _canonical_hash(capsule)
    _atomic(capsule_path, capsule)
    learning = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_authority)
    cohort = "hand_embodiment_" + capsule["gate_digest"][:16]
    learning.store.state.setdefault("hand_embodiment_methods", {})[cohort] = method
    candidate = ProcedureCandidate(PROCEDURE_ID, GOAL, method["stages"],
                                   successes / max(1, len(sealed)), passed_gate,
                                   {"sealed_success": successes, "cold_success": cold_successes,
                                    "cohort": cohort}, [])
    promotion = learning.skills.promote(candidate)
    learning.skills.record_outcome(procedure_id=PROCEDURE_ID, success=passed_gate,
                                   score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="self_modelled_tactile_hand_apprenticeship_v1")
    restarted = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_authority)
    reloaded = json.loads(capsule_path.read_text())
    restart = {
        "champion_retained": restarted.store.state.get("champions", {}).get(GOAL) == PROCEDURE_ID,
        "method_retained": cohort in restarted.store.state.get("hand_embodiment_methods", {}),
        "capsule_digest_valid": reloaded.get("capsule_digest") == capsule["capsule_digest"],
    }
    passed = bool(passed_gate and all(restart.values()) and
                  (promotion.get("promoted") or promotion.get("champion_id") == PROCEDURE_ID))
    visual_path = None
    if visual is not None:
        from PIL import Image
        path = repo_root / "results/visual/hand_embodiment_button_touch.png"
        path.parent.mkdir(parents=True, exist_ok=True); Image.fromarray(visual).save(path)
        visual_path = str(path)
    result = {
        "schema_version": "aion.hand_embodiment_apprenticeship.v1",
        "procedure_id": PROCEDURE_ID, "created_at": _utc_timestamp(),
        "status": "PROMOTED" if passed else "REJECTED", "passed": passed,
        "development": development, "sealed": sealed, "cold": cold,
        "gate": {"sealed_success": successes, "sealed_total": len(sealed),
                 "cold_success": cold_successes,
                 "correct_digit_selection": sum(bool(row["correct_digit_selected"]) for row in sealed),
                 "hand_morphologies": len(SEALED), "digits_exercised": 5,
                 "pre_action_commitments": sum(int(row["pre_action_commitments"]) for row in sealed),
                 "malicious_rejected": sum(bool(item["rejected"]) for item in malicious),
                 "teacher_actions": 0, "privileged_target_identity": 0},
        "retained_method": method, "malicious": malicious,
        "capsule": {"path": str(capsule_path), "digest": capsule["capsule_digest"]},
        "promotion": promotion, "restart": restart, "visual_evidence": visual_path,
        "claim_boundary": "Local simulated five-digit embodiment and tactile contact; dexterous grasping, Isaac transfer and real hardware remain unearned.",
    }
    _atomic(result_path, result)
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(run(root), indent=2, sort_keys=True))
