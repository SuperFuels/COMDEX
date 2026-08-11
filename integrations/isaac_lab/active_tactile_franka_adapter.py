"""Fail-closed adapter from the local tactile skill to Franka task space."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

import numpy as np


SCHEMA = "aion.active_tactile_franka_adapter.v1"


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


class ActiveTactileFrankaOption:
    """Translate fingertip history into bounded task-space information actions."""

    def __init__(self, capsule: Mapping[str, Any]) -> None:
        unsigned = {key: value for key, value in capsule.items() if key != "capsule_digest"}
        if capsule.get("capsule_digest") != digest(unsigned):
            raise RuntimeError("active_tactile_franka_capsule_integrity_failure")
        if capsule.get("schema_version") != SCHEMA or not capsule.get("gate", {}).get("passed"):
            raise RuntimeError("active_tactile_franka_capsule_gate_failure")
        self.capsule = dict(capsule)
        self.reset()

    @classmethod
    def load(cls, path: Path) -> "ActiveTactileFrankaOption":
        return cls(json.loads(path.read_text()))

    def reset(self) -> None:
        self.one_sided_age = 0
        self.stable_dual = 0
        self.lost_age = 0
        self.attachment_latched = False
        self.corrections = 0

    def update(self, touch: np.ndarray, hand_rotation: np.ndarray, phase: int) -> dict[str, Any]:
        touch = np.asarray(touch, dtype=float)
        rotation = np.asarray(hand_rotation, dtype=float)
        if touch.shape != (2,) or rotation.shape != (3, 3) or not np.all(np.isfinite(touch)) \
                or not np.all(np.isfinite(rotation)) or np.any(touch < 0) or np.any(touch > 250):
            raise ValueError("active_tactile_franka_observation_rejected")
        threshold = float(self.capsule["contact_threshold"])
        left, right = touch >= threshold
        dual = bool(left and right)
        one_sided = bool(left ^ right)
        self.stable_dual = self.stable_dual + 1 if dual else 0
        self.one_sided_age = self.one_sided_age + 1 if one_sided else 0
        if self.stable_dual >= int(self.capsule["stable_dual_steps"]):
            self.attachment_latched = True
        if phase >= 3 and self.attachment_latched and not dual:
            self.lost_age += 1
        else:
            self.lost_age = 0
        slip = self.lost_age >= int(self.capsule["lost_contact_steps"])
        if slip:
            self.attachment_latched = False
        correction = np.zeros(2, dtype=np.float32)
        correct = self.one_sided_age >= int(self.capsule["persistent_one_sided_steps"])
        orientation_unsafe = False
        if correct:
            # Panda's declared order is left then right.  The local-y hand axis
            # is transformed into world XY; no object pose crosses the policy
            # boundary.  Opposite contacts must yield opposite corrections.
            sign = 1.0 if left else -1.0
            axis = rotation[:2, 1]
            norm = float(np.linalg.norm(axis))
            if norm < .25:
                # A nearly vertical closing axis cannot support a meaningful
                # planar left/right correction.  This is a recoverable grasp
                # state, not a process failure: expose it to the controller so
                # it can reopen, retreat and reacquire a safe wrist posture.
                orientation_unsafe = True
                correct = False
            else:
                correction = (axis / norm * sign * float(self.capsule["correction_metres"])).astype(np.float32)
            self.one_sided_age = 0
            if correct:
                self.corrections += 1
        state = ("slipping" if slip else "attached" if self.attachment_latched and dual
                 else "dual_unstable" if dual else "left_only" if left
                 else "right_only" if right else "no_contact")
        return {"state": state, "dual": dual, "stable_dual": self.stable_dual,
                "attachment_latched": self.attachment_latched, "slip": slip,
                "reopen_and_correct": correct, "correction_xy": correction,
                "orientation_unsafe": orientation_unsafe,
                "corrections": self.corrections}

    def balanced_servo(self, touch: np.ndarray, hand_rotation: np.ndarray,
                       *, step_metres: float = .0025) -> np.ndarray:
        """Return a bounded contact-preserving correction from force imbalance."""
        touch = np.asarray(touch, dtype=float)
        rotation = np.asarray(hand_rotation, dtype=float)
        if touch.shape != (2,) or rotation.shape != (3, 3) or not np.all(np.isfinite(touch)) \
                or not np.all(np.isfinite(rotation)) or np.any(touch < 0) or np.any(touch > 250):
            raise ValueError("active_tactile_franka_observation_rejected")
        total = float(touch.sum())
        if total < 5.0:
            return np.zeros(2, dtype=np.float32)
        axis = rotation[:2, 1]
        norm = float(np.linalg.norm(axis))
        if norm < .25:
            raise RuntimeError("franka_closing_axis_projection_ood")
        imbalance = float(np.clip((touch[0] - touch[1]) / max(total, 1e-6), -1.0, 1.0))
        # Move toward the weaker digit. A stronger declared-left contact
        # therefore requires motion opposite the local-left axis. This sign
        # was measured after retry actions were fixed to hold all arm joints;
        # older traces were confounded by a return-to-default command.
        return (-axis / norm * imbalance * min(float(step_metres), .0025)).astype(np.float32)


def build(root: Path, output: Path | None = None) -> dict[str, Any]:
    output = output or root / "results/immutable/isaac_precision_franka/active_tactile_franka_adapter_v1.json"
    parent_path = root / "backend/modules/hexcore/data/physical_skill_capsules/active_tactile_grasp.json"
    parent = json.loads(parent_path.read_text())
    parent_unsigned = {key: value for key, value in parent.items() if key != "capsule_digest"}
    if parent.get("capsule_digest") != digest(parent_unsigned):
        raise RuntimeError("active_tactile_parent_integrity_failure")
    if parent.get("procedure_id") != "procedure_active_tactile_grasp_apprenticeship_v2":
        raise RuntimeError("active_tactile_parent_not_promoted_v2")
    capsule = {
        "schema_version": SCHEMA,
        "parent_procedure": parent["procedure_id"],
        "parent_capsule_digest": parent["capsule_digest"],
        "digit_order": ["panda_leftfinger", "panda_rightfinger"],
        "contact_threshold": .35,
        "persistent_one_sided_steps": 6,
        "stable_dual_steps": 2,
        "lost_contact_steps": 2,
        "correction_metres": .010,
        "maximum_accumulated_correction_metres": .040,
        "authority": {"runtime_inputs": ["rgb", "bounded_proprioception", "fingertip_touch"],
                      "forbidden": ["object_pose", "contact_geometry", "reward", "teacher_action"],
                      "symmetric_gripper": True, "commit_before_act": True},
    }
    # Source-disjoint kinematic poses exercise different hand-axis projections.
    rotations = []
    from integrations.isaac_lab.aion_precision_franka_policy import franka_hand_pose
    qs = (
        np.asarray([0, -.55, 0, -2.1, 0, 1.55, .75]),
        np.asarray([.35, -.80, .22, -1.8, -.15, 1.20, .35]),
        np.asarray([-.40, -.35, -.30, -2.3, .25, 1.80, 1.05]),
    )
    for q in qs:
        rotations.append(franka_hand_pose(q)[:3, :3])
    capsule["gate"] = {"passed": True, "pose_count": len(rotations),
                       "opposite_direction_checks": 0, "bounded_checks": 0,
                       "semantic_checks": 0, "malicious_rejected": 0}
    capsule["capsule_digest"] = digest(capsule)
    option = ActiveTactileFrankaOption(capsule)
    for rotation in rotations:
        option.reset()
        left = right = None
        for _ in range(6):
            left = option.update(np.asarray([1.0, 0.0]), rotation, 2)
        option.reset()
        for _ in range(6):
            right = option.update(np.asarray([0.0, 1.0]), rotation, 2)
        assert left is not None and right is not None
        if not np.allclose(left["correction_xy"], -right["correction_xy"], atol=1e-7):
            raise RuntimeError("franka_tactile_correction_not_opposed")
        if max(np.linalg.norm(left["correction_xy"]), np.linalg.norm(right["correction_xy"])) > .01001:
            raise RuntimeError("franka_tactile_correction_unbounded")
        capsule["gate"]["opposite_direction_checks"] += 1
        capsule["gate"]["bounded_checks"] += 2
        option.reset()
        option.update(np.asarray([1.0, 1.0]), rotation, 2)
        attached = option.update(np.asarray([1.0, 1.0]), rotation, 3)
        option.update(np.asarray([0.0, 0.0]), rotation, 3)
        slipping = option.update(np.asarray([0.0, 0.0]), rotation, 3)
        if not attached["attachment_latched"] or not slipping["slip"]:
            raise RuntimeError("franka_tactile_semantics_failed")
        capsule["gate"]["semantic_checks"] += 1
    for value in (np.asarray([np.nan, 0]), np.asarray([300.0, 0]), np.asarray([0.0]),
                  np.asarray([-1.0, 0])):
        try:
            option.update(value, np.eye(3), 2)
        except ValueError:
            capsule["gate"]["malicious_rejected"] += 1
    capsule["gate"]["passed"] = bool(
        capsule["gate"]["opposite_direction_checks"] == 3
        and capsule["gate"]["bounded_checks"] == 6
        and capsule["gate"]["semantic_checks"] == 3
        and capsule["gate"]["malicious_rejected"] == 4
    )
    capsule["capsule_digest"] = digest({key: value for key, value in capsule.items()
                                         if key != "capsule_digest"})
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(capsule, indent=2, sort_keys=True))
    json.loads(temporary.read_text())
    os.replace(temporary, output)
    return capsule


if __name__ == "__main__":
    print(json.dumps(build(Path(__file__).resolve().parents[2]), indent=2))
