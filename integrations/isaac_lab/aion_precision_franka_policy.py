"""Portable teacher-removed Franka precision program with v13 fallback."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import sys
from typing import Any, Mapping

import numpy as np
import torch

_ROOT = Path(os.environ.get("AION_ISAAC_POLICY_ROOT", "/workspace/aion"))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.modules.hexcore.episodic_embodied_skill_memory import load_runtime
from integrations.isaac_lab.active_tactile_franka_adapter import ActiveTactileFrankaOption
from integrations.isaac_lab.learn_physx_attachment_signature import AttachmentSignature

_RUNTIME = None


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     default=str).encode()).hexdigest()


def polynomial(xy: np.ndarray) -> np.ndarray:
    xy = np.asarray(xy, np.float32).reshape(-1, 2)
    x, y = xy[:, 0], xy[:, 1]
    return np.column_stack((np.ones(len(x)), x, y, x*x, x*y, y*y)).astype(np.float32)


def linear(features: np.ndarray, coef: np.ndarray, intercept: np.ndarray) -> np.ndarray:
    return np.asarray(features) @ np.asarray(coef).T + np.asarray(intercept)


def _transform(xyz=(0.0, 0.0, 0.0), rpy=(0.0, 0.0, 0.0)) -> np.ndarray:
    r, p, y = rpy
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    value = np.eye(4, dtype=np.float64)
    value[:3, :3] = ((cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr),
                     (sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr),
                     (-sp, cp * sr, cp * cr))
    value[:3, 3] = xyz
    return value


_FRANKA_FIXED = (
    _transform((0, 0, .333)),
    _transform(rpy=(-math.pi / 2, 0, 0)),
    _transform((0, -.316, 0), (math.pi / 2, 0, 0)),
    _transform((.0825, 0, 0), (math.pi / 2, 0, 0)),
    _transform((-.0825, .384, 0), (-math.pi / 2, 0, 0)),
    _transform(rpy=(math.pi / 2, 0, 0)),
    _transform((.088, 0, 0), (math.pi / 2, 0, 0)),
)
_FRANKA_HAND = _transform((0, 0, .107), (0, 0, -math.pi / 4))
# Isaac-Lift-Cube-Franka-v0 uses JointPositionActionCfg(scale=0.5,
# use_default_offset=True).  These are the official FRANKA_PANDA_CFG defaults,
# frozen here so the policy emits the task's actual absolute joint-position
# command instead of passing final approach through a learned one-step model.
_FRANKA_DEFAULT = np.asarray((0.0, -.569, 0.0, -2.810, 0.0, 3.037, .741), np.float32)
_FRANKA_LOWER = np.asarray((-2.8973, -1.7628, -2.8973, -3.0718, -2.8973, -.0175, -2.8973), np.float32)
_FRANKA_UPPER = np.asarray((2.8973, 1.7628, 2.8973, -.0698, 2.8973, 3.7525, 2.8973), np.float32)
_FRANKA_ACTION_SCALE = .5


def franka_hand_pose(q: np.ndarray) -> np.ndarray:
    pose = np.eye(4, dtype=np.float64)
    for fixed, angle in zip(_FRANKA_FIXED, np.asarray(q, np.float64)):
        pose = pose @ fixed @ _transform(rpy=(0, 0, float(angle)))
    return (pose @ _FRANKA_HAND).astype(np.float32)


def franka_hand_position(q: np.ndarray) -> np.ndarray:
    return franka_hand_pose(q)[:3, 3]


def rotation_vector(rotation: np.ndarray) -> np.ndarray:
    rotation = np.asarray(rotation, np.float64)
    cosine = float(np.clip((np.trace(rotation) - 1.0) * .5, -1.0, 1.0))
    angle = math.acos(cosine)
    skew = np.asarray((rotation[2, 1] - rotation[1, 2],
                       rotation[0, 2] - rotation[2, 0],
                       rotation[1, 0] - rotation[0, 1]), np.float64)
    if angle < 1e-6:
        return (.5 * skew).astype(np.float32)
    if math.pi - angle < 1e-4:
        diagonal = np.maximum((np.diag(rotation) + 1.0) * .5, 0.0)
        axis = np.sqrt(diagonal)
        axis *= np.sign(np.asarray((skew[0], skew[1], skew[2])) + 1e-9)
        axis /= max(float(np.linalg.norm(axis)), 1e-9)
        return (axis * angle).astype(np.float32)
    return (skew * (angle / (2.0 * math.sin(angle)))).astype(np.float32)


def franka_position_jacobian(q: np.ndarray, epsilon: float = 1e-4) -> np.ndarray:
    q = np.asarray(q, np.float64)
    base = franka_hand_position(q)
    columns = []
    for index in range(7):
        shifted = q.copy()
        shifted[index] += epsilon
        columns.append((franka_hand_position(shifted) - base) / epsilon)
    return np.column_stack(columns).astype(np.float32)


def franka_pose_jacobian(q: np.ndarray, epsilon: float = 1e-4) -> np.ndarray:
    q = np.asarray(q, np.float64)
    base = franka_hand_pose(q)
    columns = []
    for index in range(7):
        shifted = q.copy()
        shifted[index] += epsilon
        moved = franka_hand_pose(shifted)
        translation = (moved[:3, 3] - base[:3, 3]) / epsilon
        angular = rotation_vector(moved[:3, :3] @ base[:3, :3].T) / epsilon
        columns.append(np.concatenate((translation, angular)))
    return np.column_stack(columns).astype(np.float32)


class PrecisionFrankaRuntime:
    def __init__(self, tactile_direction: float = 0.0, attachment_search: bool = False,
                 search_radius: float = .015, search_strategy: str = "single_scale",
                 precision_contact: bool = False,
                 direct_joint_servo: bool = False,
                 exploratory_width_margin: float = 0.0) -> None:
        root = _ROOT
        manifest_path = root / "results/immutable/isaac_precision_franka/contact_ready_franka_v4.json"
        archive_path = root / "results/immutable/isaac_precision_franka/contact_ready_franka_v4.npz"
        manifest = json.loads(manifest_path.read_text())
        unsigned = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
        if manifest.get("manifest_sha256") != digest(unsigned):
            raise RuntimeError("precision_franka_manifest_integrity_failure")
        if manifest.get("archive_sha256") != hashlib.sha256(archive_path.read_bytes()).hexdigest():
            raise RuntimeError("precision_franka_archive_integrity_failure")
        with np.load(archive_path, allow_pickle=False) as raw:
            self.c = {key: np.asarray(raw[key]) for key in raw.files}
        self.nominal = load_runtime(
            root / "results/immutable/isaac_lab/aion_episodic_capsule_v13_phase.json",
            root / "results/immutable/isaac_lab/aion_episodic_memory_v13_phase.npz",
            device="cuda" if torch.cuda.is_available() else "cpu",
        )
        self.tactile_direction = float(tactile_direction)
        self.tactile = (ActiveTactileFrankaOption.load(
            root / "results/immutable/isaac_precision_franka/active_tactile_franka_adapter_v1.json"
        ) if self.tactile_direction else None)
        self.attachment_search = bool(attachment_search)
        self.search_radius = float(search_radius)
        if not 0 < self.search_radius <= .035:
            raise ValueError("attachment_search_radius_rejected")
        self.search_strategy = str(search_strategy)
        if self.search_strategy not in {"single_scale", "coarse_to_fine"}:
            raise ValueError("attachment_search_strategy_rejected")
        self.precision_contact = bool(precision_contact)
        self.direct_joint_servo = bool(direct_joint_servo)
        self.exploratory_width_margin = float(exploratory_width_margin)
        if not 0.0 <= self.exploratory_width_margin <= .003:
            raise ValueError("exploratory_width_margin_rejected")
        self.attachment_signature = (AttachmentSignature.load(
            root / "results/immutable/isaac_precision_franka/physx_attachment_signature_v1.json"
        ) if self.attachment_search else None)
        if self.attachment_search and self.tactile is not None:
            # PhysX contacts are impulsive (typically 1--3 frames), unlike the
            # smooth local proxy. This is a runtime binding, not a mutation of
            # the promoted local capsule.
            self.tactile.capsule["persistent_one_sided_steps"] = 2
        self.episode = None
        self.phase = self.phase_age = 0
        self.close_age = 0
        self.finger_close_latched = False
        self.xy_history: list[np.ndarray] = []
        self.frozen_xy: np.ndarray | None = None
        self.grasp_attempt = 0
        self.replans = 0
        self.occlusion_age = 0
        self.contact_correction_xy = np.zeros(2, dtype=np.float32)
        self.contact_correction_cooldown = 0
        self.tactile_centering_applied = False
        self.tactile_centering_count = 0
        self.precision_handoff_q: np.ndarray | None = None
        self.precision_recovery_q: np.ndarray | None = None
        self.visual_warmup_q: np.ndarray | None = None
        self.precision_goal_q: np.ndarray | None = None
        self.precision_setpoint_q: np.ndarray | None = None
        self.precision_goal_phase: int | None = None
        self.precision_contact_hold_xyz: np.ndarray | None = None
        self.precision_contact_balance_xy = np.zeros(2, dtype=np.float32)
        self.attachment_latched = False
        self.exploratory_attachment_latched = False
        self.attachment_loss_age = 0

    def reset(self, episode: int) -> None:
        self.episode, self.phase, self.phase_age = episode, 0, 0
        self.close_age = 0
        self.finger_close_latched = False
        self.xy_history, self.frozen_xy = [], None
        self.grasp_attempt = 0
        self.replans = 0
        self.occlusion_age = 0
        self.contact_correction_xy = np.zeros(2, dtype=np.float32)
        self.contact_correction_cooldown = 0
        self.tactile_centering_applied = False
        self.tactile_centering_count = 0
        self.precision_handoff_q = None
        self.precision_recovery_q = None
        self.visual_warmup_q = None
        self.precision_goal_q = None
        self.precision_setpoint_q = None
        self.precision_goal_phase = None
        self.precision_contact_hold_xyz = None
        self.precision_contact_balance_xy = np.zeros(2, dtype=np.float32)
        if self.tactile is not None:
            self.tactile.reset()
        self.attachment_latched = False
        self.exploratory_attachment_latched = False
        self.attachment_loss_age = 0
        if self.attachment_signature is not None:
            self.attachment_signature.reset()

    def fallback(self, rgb: np.ndarray, pro: np.ndarray, episode: int, step: int, reason: str):
        proposal = self.nominal.propose(rgb, pro, episode_id=episode, step=step)
        values = np.zeros(8, np.float32) if proposal.get("abstain") else np.asarray(proposal["values"], np.float32)
        return values, f"protected_v13_fallback:{reason}"

    def detect_xy(self, rgb: np.ndarray) -> np.ndarray:
        x0, y0, x1, y1 = self.c["detector_roi"].astype(int)
        crop = np.asarray(rgb, np.float32)[y0:y1, x0:x1, :3] + 1.0
        unit = crop / np.linalg.norm(crop, axis=-1, keepdims=True).clip(1e-6)
        distance = np.square(unit.reshape(-1, 3) - self.c["detector_prototype"]).sum(-1)
        count = min(int(self.c["detector_top_pixels"][0]), len(distance))
        chosen = np.argpartition(distance, count - 1)[:count]
        yy, xx = np.mgrid[y0:y1, x0:x1]
        points = np.column_stack((xx.ravel(), yy.ravel())).astype(np.float32)
        raw = np.average(points[chosen], axis=0, weights=np.exp(-distance[chosen] * 40.0))
        uv = self.c["detector_affine"] @ np.asarray([raw[0], raw[1], 1.0], np.float32)
        return linear(polynomial(uv), self.c["camera_coef"], self.c["camera_intercept"])[0]

    def retry_offsets(self) -> np.ndarray:
        """Return a frozen, bounded spatial curriculum for failed grasps."""
        radius = self.search_radius
        local = ((0, 0), (0, radius), (0, -radius), (radius, 0), (-radius, 0))
        if self.search_strategy == "coarse_to_fine":
            outer = min(radius * 2.0, .035)
            # Preserve the entire successful local cross before increasing
            # displacement. Diagonals come last because they spend both axes.
            points = local + (
                (0, outer), (0, -outer), (outer, 0), (-outer, 0),
                (radius, radius), (-radius, radius),
                (radius, -radius), (-radius, -radius),
            )
        else:
            points = local + (
                (radius, radius), (-radius, radius),
                (radius, -radius), (-radius, -radius),
            )
        return np.asarray(points, np.float32)

    def phase_position_tolerances(self) -> tuple[float, ...]:
        if self.precision_contact:
            # Do not close while merely in the vicinity.  The previous 32--35
            # mm thresholds were larger than the cube's grasp tolerance.
            # Enter the contact phase once the hand is within 12 mm, but keep
            # the fingers open until the final 5 mm alignment is complete.
            # The earlier 8 mm phase gate starved contact acquisition, while
            # the former 32--35 mm gate permitted visibly premature closes.
            return (.045, .012, .005, .020, .040)
        readiness = self.c["contact_readiness_tolerances"]
        return (.045, float(readiness[0]), .035, .045, .055)

    def phase_cartesian_step_limit(self) -> float:
        if not self.precision_contact:
            return .025
        return (.025, .008, .003, .006, .015)[self.phase]

    def gripper_should_close(self, task_distance: float) -> bool:
        if self.phase > 2:
            return True
        if self.phase < 2:
            return False
        # Once a well-aligned close begins, keep closing for the bounded grasp
        # attempt. Reopening on the next frame's small visual/pose fluctuation
        # produced one-frame close pulses and made attachment impossible.
        # The independent PhysX probe bottomed out at 5.6 mm, so a 5.0 mm
        # trigger never closed at all. Eight millimetres remains far inside
        # the rejected 32--35 mm regime, while the 3 mm controller continues
        # aligning during the now-latched close.
        close_trigger = (
            .012 if self.precision_contact and getattr(self, "tactile_centering_count", 0) > 0
            else .008 if self.precision_contact
            else self.phase_position_tolerances()[2]
        )
        if not self.precision_contact or task_distance <= close_trigger:
            self.finger_close_latched = True
        return self.finger_close_latched

    @staticmethod
    def direct_joint_position_action(q: np.ndarray, joint_delta: np.ndarray) -> np.ndarray:
        """Map a bounded IK correction to Isaac Lab's absolute action surface."""
        q = np.asarray(q, np.float32)
        joint_delta = np.asarray(joint_delta, np.float32)
        if q.shape != (7,) or joint_delta.shape != (7,) or not (
            np.all(np.isfinite(q)) and np.all(np.isfinite(joint_delta))
        ):
            raise ValueError("direct_joint_servo_input_rejected")
        # One frame can request at most 35 mrad per joint.  The absolute target
        # is clipped to the Franka limits and then mapped through Isaac Lab's
        # scale/default offset.  JointPositionAction is not a normalized
        # [-1, 1] surface: clipping here stranded the arm at default +/- 0.5 rad
        # and caused the repeatable retreat seen in the first fresh-world run.
        bounded_delta = np.clip(joint_delta, -.035, .035)
        q_target = np.clip(q + bounded_delta, _FRANKA_LOWER, _FRANKA_UPPER)
        return ((q_target - _FRANKA_DEFAULT) / _FRANKA_ACTION_SCALE).astype(np.float32)

    def reopen_action(self, q: np.ndarray) -> np.ndarray:
        """Open the fingers without moving a direct-position-controlled arm."""
        # JointPositionAction uses a default-pose offset.  Seven zero action
        # values therefore mean "return to the Franka default", not "hold the
        # current pose".  Contact retries previously used zero and yanked the
        # hand away from the cube after every useful tactile observation.
        arm = (self.direct_joint_position_action(q, np.zeros(7, np.float32))
               if self.direct_joint_servo else np.zeros(7, np.float32))
        return np.concatenate((arm, [4.0])).astype(np.float32)

    @staticmethod
    def absolute_joint_position_action(q_target: np.ndarray) -> np.ndarray:
        """Map one safe absolute Franka pose to Isaac Lab's action surface."""
        q_target = np.asarray(q_target, np.float32)
        if q_target.shape != (7,) or not np.all(np.isfinite(q_target)):
            raise ValueError("absolute_joint_position_target_rejected")
        bounded = np.clip(q_target, _FRANKA_LOWER, _FRANKA_UPPER)
        return ((bounded - _FRANKA_DEFAULT) / _FRANKA_ACTION_SCALE).astype(np.float32)

    @classmethod
    def tracking_compensated_position_action(
        cls, q_desired: np.ndarray, q_measured: np.ndarray,
        q_velocity: np.ndarray
    ) -> np.ndarray:
        """Add bounded load compensation to Isaac's compliant position servo."""
        q_desired = np.asarray(q_desired, np.float32)
        q_measured = np.asarray(q_measured, np.float32)
        q_velocity = np.asarray(q_velocity, np.float32)
        if (q_desired.shape != (7,) or q_measured.shape != (7,)
                or q_velocity.shape != (7,)) or not (
            np.all(np.isfinite(q_desired)) and np.all(np.isfinite(q_measured))
            and np.all(np.isfinite(q_velocity))
        ):
            raise ValueError("tracking_compensation_input_rejected")
        # The pinned Franka uses 80 Nm/rad stiffness without gravity
        # feed-forward. A 60 mrad target lead supplies only 4.8 Nm, and the
        # reset arm sagged 18 cm while receiving the correct position target.
        # Amplify measured tracking error through the same bounded position
        # surface; the 350 mrad cap limits added target authority per joint.
        # Isaac's own joint damping remains authoritative. An earlier target-
        # velocity term created a discrete-time sign flip and raised measured
        # speed from 2.8 to 5.7 rad/s. Position-lag compensation alone reduced
        # gravity sag and is allowed to settle before any phase transition.
        compensation = np.clip(4.0 * (q_desired - q_measured), -.350, .350)
        return cls.absolute_joint_position_action(q_desired + compensation)

    @classmethod
    def damped_joint_position_action(
        cls, q: np.ndarray, joint_delta: np.ndarray, velocity: np.ndarray
    ) -> np.ndarray:
        """Command a bounded IK increment while cancelling measured momentum."""
        q = np.asarray(q, np.float32)
        joint_delta = np.asarray(joint_delta, np.float32)
        velocity = np.asarray(velocity, np.float32)
        if q.shape != (7,) or joint_delta.shape != (7,) or velocity.shape != (7,) or not (
            np.all(np.isfinite(q)) and np.all(np.isfinite(joint_delta))
            and np.all(np.isfinite(velocity))
        ):
            raise ValueError("damped_joint_position_input_rejected")
        # Direct position increments accumulated 2.5 rad/s and rotated the
        # gripper onto its side.  A short measured-velocity lookback converts
        # the target into a critically damped receding command.  Both the
        # intended movement and braking term remain inside the same 35 mrad
        # per-joint authority as the original precision controller.
        damped_delta = np.clip(joint_delta - .025 * velocity, -.035, .035)
        return cls.direct_joint_position_action(q, damped_delta)

    @staticmethod
    def solve_fixed_position_goal(
        q_seed: np.ndarray, task_target: np.ndarray, *, tolerance: float = 5e-4
    ) -> np.ndarray:
        """Solve one bounded, posture-preserving Cartesian goal before acting."""
        q_goal = np.asarray(q_seed, np.float32).copy()
        task_target = np.asarray(task_target, np.float32)
        if q_goal.shape != (7,) or task_target.shape != (3,) or not (
            np.all(np.isfinite(q_goal)) and np.all(np.isfinite(task_target))
        ):
            raise ValueError("fixed_position_goal_input_rejected")
        for _ in range(40):
            error = task_target - franka_hand_position(q_goal)
            if float(np.linalg.norm(error)) <= tolerance:
                break
            delta = np.linalg.pinv(
                franka_position_jacobian(q_goal), rcond=.04
            ) @ error
            q_goal = np.clip(
                q_goal + np.clip(delta, -.035, .035),
                _FRANKA_LOWER,
                _FRANKA_UPPER,
            )
        if float(np.linalg.norm(task_target - franka_hand_position(q_goal))) > .003:
            raise RuntimeError("fixed_position_goal_unreachable")
        return q_goal.astype(np.float32)

    def fixed_goal_trajectory_action(
        self, q: np.ndarray, velocity: np.ndarray,
        task_target: np.ndarray, posture_seed: np.ndarray
    ) -> np.ndarray:
        """Track a pre-solved goal with a smooth setpoint, not velocity ratchets."""
        if self.precision_goal_q is None or self.precision_goal_phase != self.phase:
            self.precision_goal_q = self.solve_fixed_position_goal(
                posture_seed, task_target
            )
            self.precision_setpoint_q = np.asarray(q, np.float32).copy()
            self.precision_goal_phase = self.phase
        assert self.precision_setpoint_q is not None
        # Advance the commanded trajectory independently of measured velocity.
        # Keep it at most 60 mrad ahead of the physical joints, then converge
        # to one fixed goal so the position servo can settle without drift.
        progress = np.clip(
            self.precision_goal_q - self.precision_setpoint_q, -.012, .012
        )
        proposed = self.precision_setpoint_q + progress
        self.precision_setpoint_q = np.clip(proposed, q - .060, q + .060)
        return self.tracking_compensated_position_action(
            self.precision_setpoint_q, q, velocity
        )

    def safe_approach_waypoint_action(
        self, q: np.ndarray, velocity: np.ndarray, task_target: np.ndarray
    ) -> np.ndarray:
        """Follow a settle-gated Cartesian path above the table."""
        if (self.precision_setpoint_q is None
                or self.precision_goal_phase != self.phase):
            self.precision_setpoint_q = np.asarray(q, np.float32).copy()
            self.precision_goal_phase = self.phase
        setpoint_pose = franka_hand_pose(self.precision_setpoint_q)
        measured_pose = franka_hand_pose(q)
        setpoint_xyz = setpoint_pose[:3, 3]
        measured_xyz = measured_pose[:3, 3]
        # A compliant gravity-loaded arm has persistent joint target error even
        # after its Cartesian pose is stable. Gate waypoint progress on the
        # measured hand consequence and low speed, not unreachable zero joint
        # error. The damping-20 trace settled at 0.095 rad/s while retaining a
        # safe 6.7 cm vertical load offset.
        settled = bool(
            np.linalg.norm(measured_xyz[:2] - setpoint_xyz[:2]) <= .045
            and abs(float(measured_xyz[2] - setpoint_xyz[2])) <= .085
            and np.linalg.norm(velocity) <= .20
        )
        if settled:
            next_xyz = setpoint_xyz.copy()
            clearance = max(float(task_target[2]) + .10, .36)
            xy_error = task_target[:2] - setpoint_xyz[:2]
            xy_distance = float(np.linalg.norm(xy_error))
            measured_task_error = task_target - measured_xyz
            # If load pulled the measured hand into the table corridor, recover
            # vertically before allowing any further lateral command.
            if (self.phase in (1, 2, 3, 4)
                    and np.linalg.norm(measured_task_error) > .006):
                # Cancel configuration-dependent compliance from measured
                # consequences. The first safe phase-1 trace stopped 22 mm
                # from target despite a settled unloaded setpoint. Integrate
                # at most 10 mm per axis; no object pose or reward enters.
                next_xyz += np.clip(measured_task_error, -.010, .010)
            elif xy_distance > .012 and measured_xyz[2] < .30:
                next_xyz = measured_xyz + np.asarray((0.0, 0.0, .020), np.float32)
            elif xy_distance > .012:
                # Preserve the current high approach plane while translating;
                # joint interpolation between distant endpoints previously
                # dipped 25 cm below both endpoints and hit the table.
                next_xyz[:2] += xy_error * min(1.0, .020 / max(xy_distance, 1e-6))
                next_xyz[2] = max(float(setpoint_xyz[2]), clearance)
            else:
                # Command the measured compliant-load offset so the physical
                # hand, rather than its unloaded target, reaches contact height.
                loaded_target_z = float(task_target[2]) + .067
                z_error = loaded_target_z - float(setpoint_xyz[2])
                next_xyz[2] += float(np.clip(z_error, -.015, .015))
                next_xyz[:2] = task_target[:2]
            self.precision_setpoint_q = self.solve_fixed_position_goal(
                self.precision_setpoint_q, next_xyz
            )
        return self.tracking_compensated_position_action(
            self.precision_setpoint_q, q, velocity
        )

    def propose(self, rgb: np.ndarray, pro: np.ndarray, episode: int, step: int,
                fingertip_touch: np.ndarray | None = None):
        if self.episode != episode or step == 0:
            self.reset(episode)
        if pro.shape != (18,) or not np.all(np.isfinite(pro)):
            return self.fallback(rgb, pro, episode, step, "proprioception_ood")
        detected_xy = self.detect_xy(rgb).astype(np.float32)
        lower, upper = self.c["cube_xy_bounds"]
        nearest = float(np.linalg.norm(self.c["training_cube_xy"] - detected_xy, axis=1).min())
        # Reset positions occupy only a narrow part of the table.  Contact can
        # legitimately displace the cube beyond that envelope; treating such a
        # displacement as OOD made recovery impossible.  The enlarged bounds
        # remain inside the physical table and never add a privileged input.
        table_lower = np.minimum(lower - .14, np.asarray((.22, -.38), np.float32))
        table_upper = np.maximum(upper + .14, np.asarray((.72, .38), np.float32))
        visual_valid = bool(
            np.all(detected_xy >= table_lower)
            and np.all(detected_xy <= table_upper)
            and nearest <= .24
        )
        visual_occluded = False
        if visual_valid:
            xy = detected_xy
            self.occlusion_age = 0
        elif self.frozen_xy is not None and self.phase >= 1 and self.occlusion_age < 48:
            # The hand commonly occludes the cube exactly while the fingers
            # close.  Preserve the last grounded object belief for a bounded
            # horizon so contact evidence can arrive; never extrapolate it
            # indefinitely or use it before an initial visual grounding.
            xy = self.frozen_xy.copy()
            self.occlusion_age += 1
            visual_occluded = True
        else:
            return self.fallback(rgb, pro, episode, step, "visual_geometry_ood")
        if (self.phase == 0
                and (not self.direct_joint_servo or self.precision_goal_phase is None)):
            # Learn the object location while the hand is safely above it, then
            # commit. Close-range frames are dominated by the white robot and
            # task markers; continuing to rewrite the target in phase 1 moved
            # the measured cube belief by 17 cm and turned grasping into a
            # table push. Tactile evidence owns the final approach instead.
            self.xy_history = (self.xy_history + [xy])[-7:]
            self.frozen_xy = np.median(np.stack(self.xy_history), axis=0)
        robust_xy = self.frozen_xy
        waypoints = linear(polynomial(robust_xy), self.c["waypoint_coef"],
                           self.c["waypoint_intercept"])[0].reshape(5, 7)
        q, velocity = pro[:7], pro[9:16]
        if self.direct_joint_servo and self.phase == 0 and step < 16:
            # The reset render is not a stable object observation: on the
            # matched trace frame zero was displaced by 20 cm, while frames
            # 10--16 converged. Remain physically still, collect the rolling
            # visual median, and only then solve the fixed motion goal.
            if self.visual_warmup_q is None:
                self.visual_warmup_q = q.copy()
            arm = self.tracking_compensated_position_action(
                self.visual_warmup_q, q, velocity
            )
            return np.concatenate((arm, [4.0])).astype(np.float32), \
                f"visual_belief_warmup:{step + 1}/16"
        hand_pose = franka_hand_pose(q)
        hand = hand_pose[:3, 3]
        contact_offset = linear(
            polynomial(robust_xy), self.c["contact_offset_coef"], self.c["contact_offset_intercept"]
        )[0]
        retry_offsets = (self.retry_offsets() if self.attachment_search else np.asarray((
            (0, 0), (.010, 0), (-.010, 0), (0, .010), (0, -.010),
        ), np.float32))
        corrected_xy = (robust_xy + retry_offsets[min(self.grasp_attempt, len(retry_offsets) - 1)]
                        + self.contact_correction_xy)
        contact_target = np.asarray((corrected_xy[0], corrected_xy[1], .055), np.float32) + contact_offset
        task_targets = np.stack((
            contact_target + (0, 0, .12), contact_target, contact_target,
            # Verify attachment with a small lift before commanding a large
            # displacement.  The earlier 25 cm first lift converted marginal
            # grasps into immediate slips.
            contact_target + (0, 0, .04 if self.attachment_search else .08),
            contact_target + (0, 0, .25),
        )).astype(np.float32)
        task_target = task_targets[self.phase]
        task_error = task_target - hand
        task_distance = float(np.linalg.norm(task_error))
        desired_pose = franka_hand_pose(waypoints[self.phase])
        orientation_error = rotation_vector(desired_pose[:3, :3] @ hand_pose[:3, :3].T)
        orientation_distance = float(np.linalg.norm(orientation_error))
        readiness = self.c["contact_readiness_tolerances"]
        position_tolerances = self.phase_position_tolerances()
        orientation_tolerances = (0.40, float(readiness[1]), float(readiness[1]), 0.35, 0.45)
        if self.attachment_search:
            # Posture is continuously regulated in the positional null space.
            # It is not an independent authority for contact; the learned
            # physical attachment signature owns that transition.
            orientation_tolerances = (math.pi, math.pi, math.pi, math.pi, math.pi)
        phase_tolerance = position_tolerances[self.phase]
        orientation_tolerance = orientation_tolerances[self.phase]
        minimum_age = (3, 3, 12, 3, 3)[self.phase]
        finger_width = float(np.mean(pro[7:9]))
        tactile = np.asarray(fingertip_touch if fingertip_touch is not None else [], np.float32)
        tactile_available = tactile.shape == (2,) and bool(np.all(np.isfinite(tactile)))
        tactile_dual = bool(tactile_available and np.min(tactile) >= .35)
        tactile_one_sided = bool(tactile_available and np.max(tactile) >= .35 and np.min(tactile) < .18)
        tactile_decision = (self.tactile.update(tactile, hand_pose[:3, :3], self.phase)
                            if tactile_available and self.tactile is not None else None)
        self.contact_correction_cooldown = max(0, self.contact_correction_cooldown - 1)
        signature_now = (self.attachment_signature.update(tactile, finger_width)
                         if tactile_available and self.attachment_signature is not None else False)
        exploratory_signature_now = False
        if (
            self.exploratory_width_margin > 0.0
            and self.attachment_signature is not None
            and len(self.attachment_signature.history)
                == int(self.attachment_signature.c["history_steps"])
        ):
            # Probe-only information action. Keep every sealed force and
            # balance requirement; admit only a measured sub-millimetre width
            # margin. Post-action object height, not this branch, owns success.
            median_touch = np.median(
                np.stack(self.attachment_signature.history), axis=0
            )
            force_ratio = float(
                median_touch.min() / max(float(median_touch.max()), 1e-6)
            )
            capsule = self.attachment_signature.c
            exploratory_signature_now = bool(
                median_touch.min() >= capsule["force_minimum"]
                and median_touch.max() <= capsule["force_maximum"]
                and force_ratio >= capsule["minimum_force_balance_ratio"]
                and capsule["finger_width_minimum"] <= finger_width
                <= capsule["finger_width_maximum"] + self.exploratory_width_margin
            )
        if signature_now:
            self.attachment_latched = True
            self.attachment_loss_age = 0
        if exploratory_signature_now:
            self.exploratory_attachment_latched = True
            self.attachment_loss_age = 0
        elif ((self.attachment_latched or self.exploratory_attachment_latched)
              and self.phase >= 3 and not tactile_dual):
            self.attachment_loss_age += 1
        elif self.phase >= 3 and tactile_dual:
            # The recognition signature owns the transition into lift, not a
            # permanent force/width invariant. Keep an earned latch while both
            # fingers remain in physical contact; force balance naturally
            # changes as the cube accelerates upward.
            self.attachment_loss_age = 0
        contact_confirmed = (
            (self.attachment_latched or self.exploratory_attachment_latched)
            if self.attachment_search
            else tactile_dual if tactile_available else (.012 <= finger_width <= .032)
        )
        # Real opposed fingertip contact outranks a visual/FK target that may
        # still carry frame-calibration error.  v4 first produced dual contact
        # during the final approach, but the old state machine kept chasing
        # its nominal target and moved away before closing. Capture that
        # physically grounded pose, close in place, and still require the
        # later-consequence attachment signature before any lift transition.
        if self.phase == 1 and tactile_dual:
            self.phase = 2
            self.phase_age = 0
            self.close_age = 0
            self.finger_close_latched = True
            # The physically contacted pose outranks the nominal geometric
            # pose during closure. Freeze it rather than resolving a new goal.
            self.precision_goal_q = q.copy()
            if self.precision_setpoint_q is None:
                self.precision_setpoint_q = q.copy()
            self.precision_goal_phase = 2
            self.precision_contact_hold_xyz = hand.copy()
            self.precision_contact_balance_xy[:] = 0.0
        # Do not close directly from one-sided contact. That shortcut fired one
        # frame after requesting the tactile centering move, before the arm had
        # physically executed it. Phase 1 now remains open until the corrected
        # task-space target passes the ordinary measured settle gate.
        if (self.phase == 1 and tactile_decision
                and tactile_decision.get("orientation_unsafe")):
            # One-sided object contact with a near-vertical closing axis is
            # real evidence that the approach posture has collapsed. Reopen
            # and return to the safe above-object option; never crash the run
            # or keep pushing the object sideways.
            self.phase, self.phase_age = 0, 0
            self.close_age = 0
            self.finger_close_latched = False
            self.precision_handoff_q = None
            self.precision_recovery_q = None
            self.precision_goal_q = None
            self.precision_setpoint_q = None
            self.precision_goal_phase = None
            self.grasp_attempt = min(self.grasp_attempt + 1, len(retry_offsets) - 1)
            self.replans += 1
            if self.tactile is not None:
                self.tactile.reset()
            return self.reopen_action(q), "unsafe_wrist_reacquire_reopen"
        if self.phase == 2 and self.gripper_should_close(task_distance):
            self.close_age += 1
        elif self.phase == 2:
            self.close_age = 0
        # One-sided contact is already directional evidence during the final
        # open-finger approach. Waiting for phase 2 made the correction
        # unreachable: phase 2 itself requires opposed contact. Re-open and
        # shift laterally as soon as persistent one-sided contact is observed
        # in either approach/contact phase.
        if (self.phase in (1, 2) and tactile_decision
                and tactile_decision["reopen_and_correct"]
                and self.tactile_centering_count < 2
                and (self.tactile_centering_count == 0
                     or (self.phase_age >= 12
                         and float(np.linalg.norm(velocity)) <= .25))
                and self.contact_correction_cooldown == 0):
            tactile_step = tactile_decision["correction_xy"] * self.tactile_direction
            proposed = (
                self.contact_correction_xy + tactile_step
                if self.tactile_centering_count == 0
                else self.contact_correction_xy - 2.0 * tactile_step
            )
            norm = float(np.linalg.norm(proposed))
            maximum = float(self.tactile.capsule["maximum_accumulated_correction_metres"])
            self.contact_correction_xy = (
                proposed * min(1.0, maximum / max(norm, 1e-9))
            ).astype(np.float32)
            self.phase, self.phase_age = 1, 0
            self.close_age = 0
            self.finger_close_latched = False
            self.precision_goal_q = None
            self.precision_setpoint_q = None
            self.precision_goal_phase = None
            # Do not stack 10 mm corrections faster than the arm can execute
            # the first information action.
            self.contact_correction_cooldown = 8
            # One opposed 10 mm move matches the measured 7.4 mm centre error
            # with margin. Repeated corrections previously accumulated to
            # 40--70 mm and swept completely across the cube.
            self.tactile_centering_applied = True
            self.tactile_centering_count += 1
            self.replans += 1
            direction = "declared" if self.tactile_direction > 0 else "opposed"
            return self.reopen_action(q), f"causal_tactile_probe_{direction}_reopen"
        # A failed close is evidence, not permission to lift. Re-open and try a
        # small object-relative offset before escalating to protected v13.
        # Finger closure itself consumes roughly nine frames. Allow four
        # additional frames for the sealed attachment signature plus margin;
        # ten frames could reopen immediately after first meaningful contact.
        # The measured direct-servo close needs about 15 frames merely to move
        # from 39 mm to the proven 23--25 mm grasp band. Preserve another
        # bounded window for force balancing before declaring the grasp lost.
        close_limit = 24 if self.attachment_search else (12 if tactile_one_sided else 24)
        if self.phase == 2 and self.close_age >= close_limit and not contact_confirmed:
            if self.grasp_attempt < len(retry_offsets) - 1:
                self.grasp_attempt += 1
                self.phase, self.phase_age = 1, 0
                self.close_age = 0
                self.finger_close_latched = False
                self.precision_goal_q = None
                self.precision_setpoint_q = None
                self.precision_goal_phase = None
                self.precision_contact_hold_xyz = None
                self.precision_contact_balance_xy[:] = 0.0
                # A close that retained only one object contact is fresh
                # directional evidence. Re-arm one bounded tactile centering
                # action for the next open-finger attempt rather than timing
                # out while repeating the same geometry.
                self.tactile_centering_applied = self.tactile_centering_count > 0
                # Re-observe after a failed close.  The cube may have moved;
                # retaining the pre-contact coordinate would repeat the miss.
                self.xy_history = [xy]
                self.frozen_xy = xy.copy()
                self.replans += 1
                if self.attachment_signature is not None:
                    self.attachment_signature.reset()
                self.exploratory_attachment_latched = False
                return self.reopen_action(q), "contact_retry_reopen"
            return self.fallback(rgb, pro, episode, step, "contact_not_confirmed")
        tactile_slip = bool(tactile_decision and tactile_decision["slip"])
        learned_slip = bool(self.attachment_search
                            and (self.attachment_latched or self.exploratory_attachment_latched)
                            and self.attachment_loss_age >= 4)
        if self.phase >= 3 and (finger_width < .010 or tactile_slip or learned_slip):
            if self.grasp_attempt < len(retry_offsets) - 1:
                self.grasp_attempt += 1
                self.phase, self.phase_age = 0, 0
                self.close_age = 0
                self.finger_close_latched = False
                self.precision_goal_q = None
                self.precision_setpoint_q = None
                self.precision_goal_phase = None
                self.xy_history = [xy]
                self.frozen_xy = xy.copy()
                self.replans += 1
                self.attachment_latched = False
                self.exploratory_attachment_latched = False
                self.attachment_loss_age = 0
                if self.attachment_signature is not None:
                    self.attachment_signature.reset()
                return self.reopen_action(q), "slip_recovery_reopen"
            return self.fallback(rgb, pro, episode, step, "grasp_lost_before_lift")
        phase_ready = (
            (task_distance <= phase_tolerance
             or (self.phase == 2 and contact_confirmed))
            and orientation_distance <= orientation_tolerance
            and self.phase_age >= minimum_age
            and float(np.linalg.norm(velocity)) <= .35
            and (self.phase != 2 or contact_confirmed)
        )
        # Time alone is not evidence of alignment.  The old controller crossed
        # phase boundaries on a timeout and could therefore close beside the
        # cube.  Approach phases advance only on measured pose convergence.
        relaxed_progress = (
            self.phase == 0
            and self.phase_age >= 40
            and task_distance <= .080
            and orientation_distance <= .55
            and float(np.linalg.norm(velocity)) <= .35
        )
        if phase_ready or relaxed_progress:
            self.phase = min(4, self.phase + 1)
            if self.phase == 1:
                # The coarse learned controller can arrive with >2 rad/s of
                # residual joint motion. Freeze the exact safe handoff pose so
                # stiffness and damping remove momentum before precision IK;
                # a moving current-q hold simply follows the overshoot.
                self.precision_handoff_q = q.copy()
                self.precision_recovery_q = None
            self.precision_goal_q = None
            self.precision_setpoint_q = None
            self.precision_goal_phase = None
            self.phase_age = 0
            self.close_age = 0
            if self.phase == 2:
                self.precision_contact_hold_xyz = hand.copy()
                self.precision_contact_balance_xy[:] = 0.0
            if self.phase != 2:
                self.finger_close_latched = False
            task_target = task_targets[self.phase]
            task_error = task_target - hand
            task_distance = float(np.linalg.norm(task_error))
            desired_pose = franka_hand_pose(waypoints[self.phase])
            orientation_error = rotation_vector(desired_pose[:3, :3] @ hand_pose[:3, :3].T)
            orientation_distance = float(np.linalg.norm(orientation_error))
        # Receding six-dimensional task-space step. Position and wrist
        # orientation must both converge before the fingers close.
        norm = float(np.linalg.norm(task_error))
        step_limit = self.phase_cartesian_step_limit()
        cartesian_step = task_error * min(1.0, step_limit / max(norm, 1e-6))
        angular_step = orientation_error * min(1.0, .12 / max(orientation_distance, 1e-6))
        closing_hold = bool(self.phase == 2 and self.finger_close_latched)
        balanced_contact_xy = np.zeros(2, dtype=np.float32)
        if closing_hold:
            # Preserve the earned contact pose while the fingers close. The
            # previous controller chased a noisy visual target. The measured
            # close now permits only the sealed 2.5 mm tactile balance servo:
            # no object pose or reward enters this correction.
            if tactile_dual and self.tactile is not None:
                # A force-balancing direction is only identifiable after both
                # fingers touch the object.  Applying it to one-sided contact
                # accumulated 2.5 mm every frame, translated the hand roughly
                # 7 cm, and swept the cube out of the closing fingers.  Freeze
                # the earned single-contact pose until opposed evidence exists.
                balanced_contact_xy = self.tactile.balanced_servo(
                    tactile, hand_pose[:3, :3]
                )
                assert self.precision_contact_hold_xyz is not None
                proposed_balance = (
                    self.precision_contact_balance_xy + balanced_contact_xy
                )
                balance_norm = float(np.linalg.norm(proposed_balance))
                proposed_balance *= min(1.0, .003 / max(balance_norm, 1e-9))
                applied_balance = proposed_balance - self.precision_contact_balance_xy
                self.precision_contact_hold_xyz[:2] += applied_balance
                self.precision_contact_balance_xy = proposed_balance.astype(np.float32)
            cartesian_step = np.asarray(
                (balanced_contact_xy[0], balanced_contact_xy[1], 0.0), np.float32
            )
            angular_step = np.zeros(3, dtype=np.float32)
        jacobian = franka_pose_jacobian(q)
        # Strict hierarchy: translation consumes authority first; orientation
        # may use only the positional null space and therefore cannot trade a
        # closer grasp for a prettier wrist pose.
        position_inverse = np.linalg.pinv(jacobian[:3], rcond=.05)
        position_delta = position_inverse @ cartesian_step
        null_position = np.eye(7, dtype=np.float32) - position_inverse @ jacobian[:3]
        if closing_hold:
            orientation_delta = np.zeros(7, dtype=np.float32)
        elif self.attachment_search:
            # The earlier rotation-vector solver found the cube but produced
            # large wrist flips. Preserve translation authority and converge
            # toward the demonstrated joint posture only in its null space.
            posture_error = (waypoints[self.phase] - q + np.pi) % (2 * np.pi) - np.pi
            orientation_delta = null_position @ np.clip(posture_error, -.10, .10)
        else:
            orientation_map = jacobian[3:] @ null_position
            orientation_residual = angular_step - jacobian[3:] @ position_delta
            orientation_delta = null_position @ np.linalg.pinv(orientation_map, rcond=.08) @ orientation_residual
        features = np.concatenate((velocity, np.zeros(7), np.sin(q), np.cos(q)))[None]
        if self.direct_joint_servo:
            # Directly command the bounded IK target on Isaac Lab's documented
            # joint-position surface from the initial safe pose onward. The
            # learned coarse option reached phase 1 at 5.9 rad/s and became
            # collision-pinned before any recovery could act; there is no
            # longer a high-speed controller handoff in this probe.
            velocity_norm = float(np.linalg.norm(velocity))
            handoff_error = (
                float(np.linalg.norm(q - self.precision_handoff_q))
                if self.precision_handoff_q is not None else 0.0
            )
            if (self.phase == 1 and self.precision_handoff_q is not None
                    and hand[2] < .220 and self.precision_recovery_q is None):
                # Once overshoot enters the table corridor, retracing the old
                # joint path can remain collision-pinned. Arm a measured
                # vertical Cartesian escape before any lateral grasp motion.
                self.precision_recovery_q = q.copy()
            if self.phase == 1 and self.precision_recovery_q is not None:
                if hand[2] < .270 or velocity_norm > .35:
                    if velocity_norm > .35:
                        # First dissipate the coarse motion at the measured
                        # pose. Once slow, climb in tiny world-Z increments;
                        # a single distant joint goal can demand motion through
                        # the table and remain torque-pinned indefinitely.
                        arm = self.absolute_joint_position_action(q)
                        vertical_step = 0.0
                    else:
                        delta = np.linalg.pinv(
                            franka_position_jacobian(q), rcond=.04
                        ) @ np.asarray((0.0, 0.0, .006), np.float32)
                        arm = self.direct_joint_position_action(q, delta)
                        vertical_step = .006
                    self.phase_age += 1
                    return np.concatenate((arm, [4.0])).astype(np.float32), \
                        (f"precision_vertical_recovery:height={hand[2]:.3f}:"
                         f"velocity={velocity_norm:.3f}:step={vertical_step:.3f}")
                self.precision_recovery_q = None
                self.precision_handoff_q = None
            if (self.phase == 1 and self.precision_handoff_q is not None
                    and (velocity_norm > .75 or handoff_error > .025)):
                arm = self.tracking_compensated_position_action(
                    self.precision_handoff_q, q, velocity
                )
                self.phase_age += 1
                return np.concatenate((arm, [4.0])).astype(np.float32), \
                    (f"precision_handoff_brake:velocity={velocity_norm:.3f}:"
                     f"pose_error={handoff_error:.3f}")
            self.precision_handoff_q = None
            joint_delta = position_delta + orientation_delta * .10
            if closing_hold and float(np.linalg.norm(balanced_contact_xy)) < 1e-7:
                joint_delta = np.zeros(7, dtype=np.float32)
            if closing_hold:
                # Retain the *loaded task-space* contact pose. Replacing the
                # existing compensated setpoint with measured q made the
                # compliant arm sag roughly 5 cm during closure, even with a
                # zero Cartesian delta. The safe tracker preserves the earned
                # world pose and its bounded gravity-load lead.
                assert self.precision_contact_hold_xyz is not None
                arm = self.safe_approach_waypoint_action(
                    q, velocity, self.precision_contact_hold_xyz
                )
            elif self.phase in (0, 1, 2, 3, 4):
                arm = self.safe_approach_waypoint_action(
                    q, velocity, task_target
                )
            else:
                arm = self.fixed_goal_trajectory_action(
                    q, velocity, task_target, waypoints[self.phase]
                )
            self.phase_age += 1
            mode = (f"fixed_goal_joint_trajectory_phase_{self.phase}:distance={task_distance:.4f}:"
                    f"angle={orientation_distance:.3f}:replans={self.replans}:"
                    f"dual={int(tactile_dual)}:signature={int(signature_now)}:"
                    f"exploratory_signature={int(exploratory_signature_now)}:"
                    f"closing_hold={int(closing_hold)}:"
                    f"balance_step={float(np.linalg.norm(balanced_contact_xy)):.4f}")
            close = self.gripper_should_close(task_distance)
            return np.concatenate((arm, [-4.0 if close else 4.0])).astype(np.float32), mode
        passive = linear(features, self.c["dynamics_coef"], self.c["dynamics_intercept"])[0]
        candidates = []
        ranked = []
        # Backtrack both the wrist contribution and the complete motion.  A
        # failed full step is therefore converted into a smaller information-
        # preserving correction instead of an irreversible fallback.
        for motion_scale in (1.0, .50, .25, .10):
            for scale in (0.0, .10, .25, .50, 1.0):
                desired_delta = np.clip(
                    (position_delta + orientation_delta * scale) * motion_scale, -.045, .045
                )
                candidate = np.clip(
                    self.c["action_matrix_inverse"] @ (desired_delta - passive), -4.5, 4.5
                )
                prediction_features = features.copy()
                prediction_features[0, 7:14] = candidate
                predicted_q = q + linear(
                    prediction_features, self.c["dynamics_coef"], self.c["dynamics_intercept"]
                )[0]
                predicted_pose = franka_hand_pose(predicted_q)
                predicted_distance = float(np.linalg.norm(task_target - predicted_pose[:3, 3]))
                predicted_angle = float(np.linalg.norm(rotation_vector(
                    desired_pose[:3, :3] @ predicted_pose[:3, :3].T)))
                row = (
                    predicted_distance + .08 * predicted_angle,
                    scale,
                    motion_scale,
                    candidate,
                )
                ranked.append(row)
                if predicted_distance <= task_distance + .002:
                    candidates.append(row)
        if not candidates:
            # When every full candidate is pessimistic, execute only the best
            # 10%-scale correction.  This converts uncertainty into a bounded
            # information action instead of permanent inaction.
            exploratory = [row for row in ranked if row[2] == .10]
            _, selected_scale, selected_motion_scale, arm = min(
                exploratory or ranked, key=lambda row: row[0]
            )
            self.phase_age += 1
            mode = (f"predictive_micro_explore_phase_{self.phase}:distance={task_distance:.4f}:"
                    f"angle={orientation_distance:.3f}:orientation_scale={selected_scale:.2f}")
            close = self.gripper_should_close(task_distance)
            return np.concatenate((arm, [-4.0 if close else 4.0])).astype(np.float32), mode
        _, selected_scale, selected_motion_scale, arm = min(candidates, key=lambda row: row[0])
        self.phase_age += 1
        mode = (f"predictive_pose_phase_{self.phase}:distance={task_distance:.4f}:"
                f"angle={orientation_distance:.3f}:orientation_scale={selected_scale:.2f}:"
                f"motion_scale={selected_motion_scale:.2f}:replans={self.replans}:"
                f"occluded={int(visual_occluded)}:occlusion_age={self.occlusion_age}:"
                f"tactile={int(tactile_available)}:dual={int(tactile_dual)}:"
                f"signature={int(signature_now)}:latched={int(self.attachment_latched)}:"
                f"search_radius={self.search_radius:.3f}:search_strategy={self.search_strategy}:"
                f"precision_contact={int(self.precision_contact)}:close_age={self.close_age}:"
                f"closing_hold={int(closing_hold)}")
        close = self.gripper_should_close(task_distance)
        return np.concatenate((arm, [-4.0 if close else 4.0])).astype(np.float32), mode


def runtime() -> PrecisionFrankaRuntime:
    global _RUNTIME
    if _RUNTIME is None:
        _RUNTIME = PrecisionFrankaRuntime()
    return _RUNTIME


def propose(*, permitted: Mapping[str, Any], action_space: Any, arm_id: str, **_: Any):
    rgb = np.asarray(permitted["rgb"], np.uint8)
    pro = np.asarray(permitted["proprioception_bounded"], np.float32)
    episode, step = int(permitted["episode_id"]), int(permitted["timestamp"])
    if arm_id == "aion_retained":
        values, mode = runtime().propose(
            rgb, pro, episode, step,
            np.asarray(permitted.get("fingertip_touch", []), np.float32),
        )
    elif arm_id == "aion_distilled":
        values, mode = runtime().fallback(rgb, pro, episode, step, "protected_comparison")
    elif arm_id == "aion_cold":
        values, mode = np.zeros(action_space.shape, np.float32), "matched_memory_free_cold"
    else:
        raise RuntimeError("precision_franka_arm_mismatch")
    values = np.clip(values, np.asarray(action_space.low), np.asarray(action_space.high)).astype(np.float32)
    if values.shape != tuple(action_space.shape) or not np.all(np.isfinite(values)):
        raise RuntimeError("precision_franka_action_contract_failure")
    return {"values": values,
            "prediction": {"kind": mode, "policy_mode": mode, "teacher_used": False,
                           "runtime_privileged_inputs": [], "abstained": False},
            "action_space_digest": digest({"shape": list(action_space.shape),
                                            "low": np.asarray(action_space.low).tolist(),
                                            "high": np.asarray(action_space.high).tolist(),
                                            "dtype": str(action_space.dtype)})}
