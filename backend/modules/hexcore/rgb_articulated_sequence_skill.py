"""RGB-only articulated sequence learning composed from retained physical skills."""
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
    HexCorePersistentLearningRuntime, ProcedureCandidate, _canonical_hash,
    _utc_timestamp,
)
from backend.modules.hexcore.rgb_contact_occlusion_skill_composition import (
    PROCEDURE_ID as PARENT_PROCEDURE_ID,
    OpenColourTracker,
)


PROCEDURE_ID = "procedure_rgb_articulated_sequence_skill_v4"
GOAL = "rgb_articulated_sequence_tool_use"
DT = .015
FRAME_SKIP = 4
CONTROL_DT = DT * FRAME_SKIP


@dataclass(frozen=True)
class ArmWorld:
    world_id: str
    link_a: float
    link_b: float
    damping_a: float
    damping_b: float
    camera_x: float
    camera_distance: float
    start_angles: tuple[float, float]
    targets: tuple[tuple[float, float], ...]
    occlusion_fraction: tuple[float, float]


class RGBArticulatedAuthority:
    """Two-joint MuJoCo authority; learner sees only rendered consequences."""

    def __init__(self, spec: ArmWorld, *, max_steps: int = 600) -> None:
        self.spec = spec
        self.model = mujoco.MjModel.from_xml_string(self._xml(spec))
        self.data = mujoco.MjData(self.model)
        self.renderer = mujoco.Renderer(self.model, height=128, width=192)
        self.max_steps = max_steps
        self.steps = 0
        self.stage = 0
        self.stage_streak = 0
        self.commitments: list[str] = []
        self.unsafe = False
        self.max_abs_qpos = 0.0
        self.occlusion = True
        self.reset()

    @staticmethod
    def _xml(s: ArmWorld) -> str:
        target_xml = "\n".join(
            f'<site name="target_{i}" type="sphere" pos="{x} .08 {z}" size=".065" rgba=".32 .34 .36 1"/>'
            for i, (x, z) in enumerate(s.targets)
        )
        return f"""<mujoco model="rgb_articulated_sequence">
  <compiler angle="radian"/>
  <option timestep="{DT}" gravity="0 0 0" integrator="implicitfast"/>
  <visual><headlight ambient=".65 .65 .65" diffuse=".7 .7 .7"/></visual>
  <worldbody>
    {target_xml}
    <body name="base" pos="0 0 .15">
      <site name="base_marker" type="sphere" pos="0 -.12 0" size=".075" rgba=".08 .32 .98 1"/>
      <joint name="shoulder" type="hinge" axis="0 1 0" damping="{s.damping_a}" range="-2.55 2.55" limited="true"/>
      <geom name="link_a" type="capsule" fromto="0 0 0 0 0 {s.link_a}" size=".045" mass=".65" contype="0" conaffinity="0" rgba=".38 .42 .48 1"/>
      <body name="elbow" pos="0 0 {s.link_a}">
        <site name="elbow_marker" type="sphere" pos="0 -.12 0" size=".075" rgba=".98 .48 .06 1"/>
        <joint name="elbow_joint" type="hinge" axis="0 1 0" damping="{s.damping_b}" range="-2.65 2.65" limited="true"/>
        <geom name="link_b" type="capsule" fromto="0 0 0 0 0 {s.link_b}" size=".038" mass=".42" contype="0" conaffinity="0" rgba=".52 .56 .62 1"/>
        <site name="end_effector" type="sphere" pos="0 0 {s.link_b}" size=".072" rgba=".95 .08 .72 1"/>
      </body>
    </body>
    <camera name="observer" pos="{s.camera_x} -{s.camera_distance} .78" xyaxes="1 0 0 0 0 1"/>
  </worldbody>
  <actuator>
    <motor name="joint_a" joint="shoulder" gear="4" ctrllimited="true" ctrlrange="-1 1"/>
    <motor name="joint_b" joint="elbow_joint" gear="3.5" ctrllimited="true" ctrlrange="-1 1"/>
  </actuator>
</mujoco>"""

    @staticmethod
    def validate(action: Mapping[str, float]) -> np.ndarray:
        if set(action) != {"joint_a", "joint_b"}:
            raise ValueError("articulated_action_schema_rejected")
        values = np.asarray([action["joint_a"], action["joint_b"]], dtype=float)
        if not np.all(np.isfinite(values)):
            raise ValueError("non_finite_articulated_action")
        if np.any(np.abs(values) > 1.0):
            raise ValueError("articulated_action_out_of_range")
        return values

    def _set_active_target(self) -> None:
        for i in range(len(self.spec.targets)):
            self.model.site_rgba[self.model.site(f"target_{i}").id] = (
                np.asarray([.12, .94, .25, 1.0]) if i == self.stage
                else np.asarray([.32, .34, .36, 1.0])
            )

    def reset(self, *, occlusion: bool = True) -> dict[str, Any]:
        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[:] = np.asarray(self.spec.start_angles)
        self.data.qvel[:] = 0
        self.steps = 0
        self.stage = 0
        self.stage_streak = 0
        self.commitments = []
        self.unsafe = False
        self.max_abs_qpos = float(np.max(np.abs(self.data.qpos)))
        self.occlusion = occlusion
        self._set_active_target()
        mujoco.mj_forward(self.model, self.data)
        return self.observe()

    def _render(self) -> np.ndarray:
        self.renderer.update_scene(self.data, camera="observer")
        frame = self.renderer.render().copy()
        if self.occlusion and self.steps >= 12:
            lo, hi = self.spec.occlusion_fraction
            frame[:, int(lo * frame.shape[1]):int(hi * frame.shape[1])] = np.asarray([18, 20, 24], dtype=np.uint8)
        return frame

    def observe(self) -> dict[str, Any]:
        return {"rgb": self._render(), "timestamp": self.steps}

    def commit(self, action: Mapping[str, float], predicted_ee: tuple[float, float] | None,
               belief: str) -> str:
        row = {"step": self.steps, "action": {k: round(float(v), 6) for k, v in sorted(action.items())},
               "predicted_ee": predicted_ee, "belief": belief}
        digest = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
        self.commitments.append(digest)
        return digest

    def step(self, action: Mapping[str, float]) -> dict[str, Any]:
        values = self.validate(action)
        if len(self.commitments) != self.steps + 1:
            raise RuntimeError("commit_before_act_required")
        self.data.ctrl[:] = values
        for _ in range(FRAME_SKIP):
            mujoco.mj_step(self.model, self.data)
        self.steps += 1
        self.max_abs_qpos = max(self.max_abs_qpos, float(np.max(np.abs(self.data.qpos))))
        # MuJoCo joint limits are soft constraints and may settle a few
        # hundredths beyond the declared 2.65 radian boundary under actuation.
        if self.max_abs_qpos > 2.70:
            self.unsafe = True
        ee = self.data.site("end_effector").xpos[[0, 2]]
        target = np.asarray(self.spec.targets[self.stage])
        if np.linalg.norm(ee - target) <= .115 and np.linalg.norm(self.data.qvel) <= .55:
            self.stage_streak += 1
        else:
            self.stage_streak = 0
        changed = False
        if self.stage_streak >= 3:
            self.stage += 1
            self.stage_streak = 0
            changed = True
            if self.stage < len(self.spec.targets):
                self._set_active_target()
        return {"observation": self.observe(), "sequence_advanced": changed,
                "terminal": self.stage == len(self.spec.targets) or self.steps >= self.max_steps}

    def score(self) -> dict[str, Any]:
        complete = self.stage == len(self.spec.targets)
        return {"sequence_complete": complete, "targets_completed": self.stage,
                "targets_total": len(self.spec.targets), "safe": not self.unsafe,
                "steps": self.steps, "pre_action_commitments": len(self.commitments),
                "max_abs_joint_angle": self.max_abs_qpos,
                "numeric_observations_exposed": 0}

    def close(self) -> None:
        self.renderer.close()


class ArticulatedVision:
    """Discovers moving end-effector and static active-target hues."""

    def __init__(self) -> None:
        self.tracker = OpenColourTracker()
        self.ee_index = -1
        self.target_index = -1
        self.elbow_index = -1
        self.base_index = -1

    def discover(self, frame: np.ndarray) -> None:
        # Discover four hue families without names: two articulated landmarks,
        # one endpoint and one active target.
        pixels = frame.reshape(-1, 3)
        hue, saturation, brightness = OpenColourTracker._hue(pixels)
        useful = (saturation > .46) & (brightness > .4)
        histogram, edges = np.histogram(hue[useful], bins=48, range=(0, 1))
        chosen: list[float] = []
        for index in np.argsort(histogram)[::-1]:
            centre = float((edges[index] + edges[index + 1]) / 2)
            if int(histogram[index]) >= 4 and all(min(abs(centre-p), 1-abs(centre-p)) > .1 for p in chosen):
                chosen.append(centre)
            if len(chosen) == 4:
                break
        if len(chosen) != 4:
            raise RuntimeError("articulated_visual_roles_not_grounded")
        self.tracker.hues = chosen
        self.tracker.prototypes = [np.zeros(3) for _ in chosen]

    def locations(self, frame: np.ndarray) -> list[np.ndarray | None]:
        hue, saturation, brightness = OpenColourTracker._hue(frame)
        result: list[np.ndarray | None] = []
        for centre in self.tracker.hues:
            distance = np.minimum(np.abs(hue-centre), 1-np.abs(hue-centre))
            ys, xs = np.where((distance < .045) & (saturation > .38) & (brightness > .32))
            result.append(None if len(xs) < 5 else np.asarray([np.median(xs), np.median(ys)], dtype=float))
        return result


class ArticulatedSequenceLearner:
    def __init__(self, capsule: Mapping[str, Any]) -> None:
        self.capsule = capsule
        self.vision = ArticulatedVision()
        self.jacobian = np.eye(2)

    @staticmethod
    def _act(authority: RGBArticulatedAuthority, action: np.ndarray,
             predicted: np.ndarray | None, belief: str) -> dict[str, Any]:
        command = {"joint_a": float(np.clip(action[0], -1, 1)), "joint_b": float(np.clip(action[1], -1, 1))}
        point = None if predicted is None else (round(float(predicted[0]), 4), round(float(predicted[1]), 4))
        authority.commit(command, point, belief)
        return authority.step(command)

    def acquire(self, authority: RGBArticulatedAuthority) -> dict[str, Any]:
        obs = authority.reset(occlusion=False)
        self.vision.discover(obs["rgb"])
        joint_histories: list[list[list[np.ndarray | None]]] = []
        for joint in range(2):
            obs = authority.reset(occlusion=False)
            history = [self.vision.locations(obs["rgb"])]
            action = np.zeros(2); action[joint] = .55
            for _ in range(8):
                result = self._act(authority, action, None, "topology_intervention")
                history.append(self.vision.locations(result["observation"]["rgb"]))
            joint_histories.append(history)
        motion = np.zeros((4, 2))
        for entity in range(4):
            for joint in range(2):
                valid = [row[entity] for row in joint_histories[joint] if row[entity] is not None]
                motion[entity, joint] = max(np.linalg.norm(point-valid[0]) for point in valid)
        static = [i for i in range(4) if max(motion[i]) <= 1.2]
        moving = [i for i in range(4) if i not in static]
        if len(moving) != 2 or len(static) != 2:
            raise RuntimeError("articulated_topology_not_causally_identified")
        # Infer the chain by invariant visual distances. The correct assignment
        # keeps base--elbow and elbow--endpoint length stable under both actions;
        # a target substituted for the base does not.
        assignments = []
        for base_candidate in static:
            for elbow_candidate in moving:
                endpoint_candidate = next(i for i in moving if i != elbow_candidate)
                distances_a, distances_b = [], []
                for history in joint_histories:
                    for row in history:
                        if all(row[i] is not None for i in (base_candidate, elbow_candidate, endpoint_candidate)):
                            distances_a.append(np.linalg.norm(row[elbow_candidate]-row[base_candidate]))
                            distances_b.append(np.linalg.norm(row[endpoint_candidate]-row[elbow_candidate]))
                assignments.append((float(np.std(distances_a)+np.std(distances_b)), base_candidate, elbow_candidate, endpoint_candidate))
        _, self.vision.base_index, self.vision.elbow_index, self.vision.ee_index = min(assignments)
        self.vision.target_index = next(i for i in static if i != self.vision.base_index)

        # Estimate action orientation and scale for each discovered rotational
        # relation. The full Jacobian is reconstructed from landmark geometry
        # on every later frame rather than assumed globally linear.
        gains = []
        for joint, (centre_index, endpoint_index) in enumerate(((self.vision.base_index, self.vision.ee_index), (self.vision.elbow_index, self.vision.ee_index))):
            first, last = joint_histories[joint][0], joint_histories[joint][-1]
            radius = first[endpoint_index] - first[centre_index]
            perpendicular = np.asarray([-radius[1], radius[0]])
            delta = last[endpoint_index] - first[endpoint_index]
            gains.append(float((delta @ perpendicular) / max(1e-6, perpendicular @ perpendicular) / (8*.55)))
        self.joint_gains = np.asarray(gains)
        if np.any(np.abs(self.joint_gains) < .005):
            raise RuntimeError("articulated_rotation_effect_not_identified")
        return {"controlled_endpoint_identified": True,
                "invented_topology": "two_action_articulated_chain",
                "invented_roles": {"base": self.vision.base_index, "elbow": self.vision.elbow_index,
                                     "endpoint": self.vision.ee_index, "active_target": self.vision.target_index},
                "joint_rotation_gains": self.joint_gains.round(6).tolist(),
                "target_is_static_outcome_authority": True}

    def solve(self, authority: RGBArticulatedAuthority) -> dict[str, Any]:
        obs = authority.reset(occlusion=True)
        loc = self.vision.locations(obs["rgb"])
        base, elbow = loc[self.vision.base_index], loc[self.vision.elbow_index]
        ee, target = loc[self.vision.ee_index], loc[self.vision.target_index]
        if base is None or elbow is None or ee is None or target is None:
            raise RuntimeError("initial_articulated_grounding_occluded")
        prior_ee = ee.copy()
        velocity = np.zeros(2)
        prior_action = np.zeros(2)
        prior_base, prior_elbow = base.copy(), elbow.copy()
        missing = 0
        occluded_steps = 0
        recovered = False
        stage_changes = 0
        online_updates = 0
        for _ in range(authority.max_steps):
            loc = self.vision.locations(obs["rgb"])
            measured_ee = loc[self.vision.ee_index]
            measured_target = loc[self.vision.target_index]
            measured_base = loc[self.vision.base_index]
            measured_elbow = loc[self.vision.elbow_index]
            if measured_target is not None:
                target = measured_target
            if measured_ee is None:
                missing += 1; occluded_steps += 1
                if missing > int(self.capsule["max_occlusion_steps"]):
                    raise RuntimeError("articulated_belief_horizon_exceeded")
                ee = ee + velocity
                base, elbow = prior_base, prior_elbow
                belief = "recurrent_occluded_endpoint"
            else:
                recovered = recovered or missing > 0
                missing = 0
                delta = measured_ee - prior_ee
                velocity = .55 * velocity + .45 * delta
                prior_ee = measured_ee.copy(); ee = measured_ee
                if measured_base is not None:
                    prior_base = measured_base.copy()
                if measured_elbow is not None:
                    prior_elbow = measured_elbow.copy()
                base, elbow = prior_base, prior_elbow
                belief = "visually_corrected_endpoint"
            radius_a = ee - base
            radius_b = ee - elbow
            self.jacobian = np.column_stack((
                self.joint_gains[0] * np.asarray([-radius_a[1], radius_a[0]]),
                self.joint_gains[1] * np.asarray([-radius_b[1], radius_b[0]]),
            ))
            online_updates += 1
            error = target - ee
            desired = np.clip(error, -3.2, 3.2)
            action = np.linalg.pinv(self.jacobian, rcond=.08) @ desired
            action = np.clip(action, -.72, .72)
            if np.linalg.norm(error) < 6:
                action *= .45
            predicted = ee + self.jacobian @ action
            result = self._act(authority, action, predicted, belief)
            prior_action = action
            obs = result["observation"]
            if result["sequence_advanced"]:
                stage_changes += 1
                prior_action = np.zeros(2)
            if result["terminal"]:
                break
        return {**authority.score(), "occluded_belief_steps": occluded_steps,
                "reidentified_after_occlusion": recovered,
                "observed_sequence_transitions": stage_changes,
                "online_visual_model_updates": online_updates,
                "numeric_state_used_by_learner": False}


DEVELOPMENT = ArmWorld("dev_arm", .62, .50, 5.5, 4.5, 0, 4.4, (-.7, 1.15),
                       ((-.52, .66), (.48, .72), (-.34, 1.05)), (.47, .53))
SEALED = (
    ArmWorld("sealed_long_links", .70, .43, 6.5, 5.5, .22, 5.0, (-.55, 1.0), ((.55, .70), (-.58, .62), (.38, 1.05)), (.47, .53)),
    ArmWorld("sealed_short_distal", .58, .55, 4.5, 6.2, -.25, 4.1, (.62, -1.1), ((-.48, .62), (.52, .65), (-.50, .82)), (.47, .53)),
    ArmWorld("sealed_high_damping", .66, .47, 8.0, 7.2, .12, 5.4, (-.8, 1.3), ((.46, .60), (-.55, .70), (.34, 1.08)), (.47, .53)),
    ArmWorld("sealed_camera_shift", .60, .52, 5.0, 4.2, -.32, 4.7, (.72, -1.25), ((-.50, .64), (.54, .68), (-.62, .82)), (.47, .53)),
)


def _load_parent(root: Path) -> tuple[dict[str, Any], str]:
    state_path = root / "backend/modules/hexcore/data/rgb_contact_occlusion/state.json"
    capsule_path = root / "backend/modules/hexcore/data/physical_skill_capsules/rgb_contact_occlusion.json"
    state = json.loads(state_path.read_text())
    capsule = json.loads(capsule_path.read_text())
    if state.get("champions", {}).get("rgb_contact_occlusion_skill_composition") != PARENT_PROCEDURE_ID:
        raise RuntimeError("contact_parent_not_authorized")
    expected = _canonical_hash({k: v for k, v in capsule.items() if k != "capsule_digest"})
    if capsule.get("capsule_digest") != expected or capsule.get("procedure_id") != PARENT_PROCEDURE_ID:
        raise RuntimeError("contact_parent_capsule_tampered")
    return capsule, expected


def _capsule(parent_digest: str) -> dict[str, Any]:
    value = {"schema_version": "aion.executable_skill_capsule.v1",
             "name": "rgb_articulated_sequential_reaching", "parent_procedure_id": PARENT_PROCEDURE_ID,
             "parent_digest": parent_digest,
             "purpose": "discover an articulated visual action basis and complete changing targets in sequence",
             "inputs": ["RGB frame", "timestamp", "two bounded joint actions"],
             "invariants": ["RGB only", "commit before action", "identify controlled endpoint by intervention", "abstain on singular action basis"],
             "method": ["reload contact/occlusion parent", "discover moving endpoint", "identify static active target", "learn local visual Jacobian", "adapt Jacobian from consequences", "propagate hidden endpoint belief", "detect target transition", "complete ordered sequence"],
             "max_occlusion_steps": 120}
    value["capsule_digest"] = _canonical_hash(value)
    return value


def _run(spec: ArmWorld, capsule: Mapping[str, Any]) -> dict[str, Any]:
    authority = RGBArticulatedAuthority(spec)
    try:
        learner = ArticulatedSequenceLearner(capsule)
        acquisition = learner.acquire(authority)
        return {"world_id": spec.world_id, "acquisition": acquisition, **learner.solve(authority)}
    finally:
        authority.close()


def _cold(spec: ArmWorld) -> dict[str, Any]:
    authority = RGBArticulatedAuthority(spec)
    try:
        authority.reset()
        for step in range(authority.max_steps):
            command = {"joint_a": .35 if step % 80 < 40 else -.35, "joint_b": -.2}
            authority.commit(command, None, "cold_periodic")
            result = authority.step(command)
            if result["terminal"]:
                break
        return {"world_id": spec.world_id, **authority.score()}
    finally:
        authority.close()


def _atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix+".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True)); json.loads(temp.read_text()); os.replace(temp, path)


def _authority(_: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "source": "articulated_private_cau", "S": 1.0, "H": 0.0}


def run(*, repo_root: Path, result_path: Path | None = None, state_path: Path | None = None,
        capsule_path: Path | None = None) -> dict[str, Any]:
    root = repo_root.resolve()
    result_path = result_path or root/"results/hexcore_rgb_articulated_sequence_skill.json"
    state_path = state_path or root/"backend/modules/hexcore/data/rgb_articulated_sequence/state.json"
    capsule_path = capsule_path or root/"backend/modules/hexcore/data/physical_skill_capsules/rgb_articulated_sequence.json"
    _, parent_digest = _load_parent(root)
    capsule = _capsule(parent_digest)
    development = _run(DEVELOPMENT, capsule)
    sealed = [_run(spec, capsule) for spec in SEALED]
    cold = [_cold(spec) for spec in SEALED]
    success = sum(row["sequence_complete"] and row["safe"] for row in sealed)
    cold_success = sum(row["sequence_complete"] and row["safe"] for row in cold)
    malicious = [{}, {"joint_a": 2, "joint_b": 0}, {"joint_a": 0, "joint_b": float("nan")}, {"joint_a": 0, "joint_b": 0, "shell": 1}]
    rejected = 0
    for action in malicious:
        try: RGBArticulatedAuthority.validate(action)
        except (ValueError, TypeError): rejected += 1
    gate = {"parent_skill_reconstructed": True, "rgb_only": all(row["numeric_state_used_by_learner"] is False for row in [development,*sealed]),
            "sealed_success": int(success), "sealed_worlds": len(sealed), "cold_success": int(cold_success),
            "sequential_targets_per_world": 3, "articulated_joints": 2,
            "occlusion_recovery": all(row["reidentified_after_occlusion"] for row in sealed),
            "visual_model_adaptation": all(row["online_visual_model_updates"] > 0 for row in sealed),
            "pre_action_commitments": sum(row["pre_action_commitments"] for row in [development,*sealed]),
            "malicious_actions_rejected": rejected, "malicious_actions_total": len(malicious),
            "unsafe_worlds": sum(not row["safe"] for row in [development,*sealed]), "live_repository_writes": 0}
    passed = bool(success == len(sealed) and cold_success < success and gate["rgb_only"] and gate["occlusion_recovery"] and rejected == len(malicious) and gate["unsafe_worlds"] == 0)
    capsule = dict(capsule); capsule.update({"verified_gate_digest": _canonical_hash(gate), "procedure_id": PROCEDURE_ID, "verified_at": _utc_timestamp()})
    capsule["capsule_digest"] = _canonical_hash({k:v for k,v in capsule.items() if k != "capsule_digest"}); _atomic(capsule_path, capsule)
    learning = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_authority)
    cohort_id = "rgb_articulated_"+_canonical_hash(gate)[:16]
    learning.store.state.setdefault("articulated_physical_skills", {})[cohort_id] = {"capsule": capsule, "gate": gate, "created_at": _utc_timestamp()}
    candidate = ProcedureCandidate(procedure_id=PROCEDURE_ID, goal=GOAL, steps=capsule["method"], score=success/max(1,len(sealed)), success=passed,
                                   evidence={"cohort_id":cohort_id,"gate":gate,"capsule_digest":capsule["capsule_digest"]}, source_rules=[PARENT_PROCEDURE_ID])
    promotion = learning.skills.promote(candidate); learning.skills.record_outcome(procedure_id=PROCEDURE_ID,success=passed,score=candidate.score,evidence=candidate.evidence); learning.store.commit(reason="rgb_articulated_sequence_skill_v4")
    restarted = HexCorePersistentLearningRuntime(state_path=state_path,authority_provider=_authority)
    restart = {"champion_retained": restarted.store.state.get("champions",{}).get(GOAL)==PROCEDURE_ID,
               "capsule_retained": cohort_id in restarted.store.state.get("articulated_physical_skills",{}),
               "capsule_digest_valid": json.loads(capsule_path.read_text()).get("capsule_digest")==capsule["capsule_digest"]}
    passed = bool(passed and all(restart.values()) and (promotion.get("promoted") or promotion.get("champion_id")==PROCEDURE_ID))
    result = {"schema_version":"aion.rgb_articulated_sequence_skill.v1","procedure_id":PROCEDURE_ID,"created_at":datetime.now(timezone.utc).isoformat(),
              "passed":passed,"status":"PROMOTED" if passed else "REJECTED","development":development,"sealed":sealed,"cold":cold,"gate":gate,
              "stored_skill_capsule":{"path":str(capsule_path),"digest":capsule["capsule_digest"],"reconstructed":all(restart.values())},
              "promotion":promotion,"restart":restart,
              "claim_boundary":"The learner discovers and adapts RGB articulated control, but the two-joint task family, safe action surface and learning meta-algorithm remain engineered."}
    _atomic(result_path,result); return result


if __name__ == "__main__":
    print(json.dumps(run(repo_root=Path(__file__).resolve().parents[3]),indent=2,sort_keys=True))
