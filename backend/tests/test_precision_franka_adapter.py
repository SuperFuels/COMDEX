from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np

from integrations.isaac_lab.aion_precision_franka_policy import PrecisionFrankaRuntime


ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "results/hexcore_precision_franka_adapter.json"
CAPSULE = ROOT / "results/immutable/isaac_precision_franka/precision_franka_v1.joblib"
RUNTIME = ROOT / "results/immutable/isaac_precision_franka/precision_franka_v1.npz"
TASK_SPACE_RESULT = ROOT / "results/hexcore_task_space_franka_gate.json"


def test_precision_franka_offline_authority() -> None:
    result = json.loads(RESULT.read_text())
    assert result["offline_gates_passed"]
    assert result["physx_tournament_authorized"]
    assert result["geometry_gate"]["passed"]
    assert result["waypoint_gate"]["passed"]
    assert result["identified_dynamics_gate"]["passed"]
    assert result["runtime_contract"]["privileged_runtime_inputs"] == 0
    assert result["runtime_contract"]["teacher_present"] is False


def test_precision_franka_capsule_is_bounded() -> None:
    capsule = joblib.load(CAPSULE)
    assert capsule["runtime_inputs"] == ["rgb", "bounded_joint_position_velocity", "episode_step"]
    assert capsule["privileged_runtime_inputs"] == []
    assert np.asarray(capsule["action_matrix_inverse"]).shape == (7, 7)
    assert np.asarray(capsule["training_cube_xy"]).shape[1] == 2
    with np.load(RUNTIME, allow_pickle=False) as runtime:
        assert runtime["action_matrix_inverse"].shape == (7, 7)
        assert runtime["waypoint_coef"].shape == (35, 6)


def test_task_space_gate_earns_one_physx_comparison_only() -> None:
    result = json.loads(TASK_SPACE_RESULT.read_text())
    assert result["passed"]
    assert result["physx_tournament_authorized"]
    assert result["analytic_contact_geometry"]["mean_xy_error_m"] <= 0.025
    assert result["analytic_contact_geometry"]["vertical_offset_std_m"] <= 0.01
    assert result["one_step_relational_control"]["positive_improvement_fraction"] >= 0.80
    assert result["one_step_relational_control"]["mean_after_before_ratio"] < 0.98
    assert result["privileged_runtime_inputs"] == 0
    assert result["teacher_present_at_runtime"] is False
    assert "authorize one PhysX comparison only" in result["claim_boundary"]


def test_coarse_to_fine_search_preserves_local_cross_before_expansion() -> None:
    runtime = PrecisionFrankaRuntime.__new__(PrecisionFrankaRuntime)
    runtime.search_radius = .015
    runtime.search_strategy = "coarse_to_fine"
    offsets = runtime.retry_offsets()
    assert offsets.shape == (13, 2)
    assert np.allclose(offsets[:5], np.asarray((
        (0, 0), (0, .015), (0, -.015), (.015, 0), (-.015, 0),
    )))
    assert np.max(np.linalg.norm(offsets, axis=1)) <= .03501


def test_precision_contact_requires_millimetre_alignment_and_small_steps() -> None:
    runtime = PrecisionFrankaRuntime.__new__(PrecisionFrankaRuntime)
    runtime.precision_contact = True
    assert runtime.phase_position_tolerances()[1:3] == (.012, .005)
    runtime.phase = 1
    assert runtime.phase_cartesian_step_limit() == .008
    runtime.phase = 2
    assert runtime.phase_cartesian_step_limit() == .003


def test_precision_contact_close_timer_is_independent_of_alignment_age() -> None:
    runtime = PrecisionFrankaRuntime.__new__(PrecisionFrankaRuntime)
    runtime.precision_contact = True
    runtime.phase = 2
    runtime.phase_age = 19
    runtime.close_age = 0
    runtime.finger_close_latched = False
    assert runtime.phase_position_tolerances()[2] == .005
    assert not runtime.gripper_should_close(.0081)
    assert runtime.gripper_should_close(.0080)
    assert runtime.gripper_should_close(.0200)
    assert runtime.close_age == 0


def test_direct_joint_servo_matches_isaac_absolute_position_action_mapping() -> None:
    default = np.asarray((0.0, -.569, 0.0, -2.810, 0.0, 3.037, .741), np.float32)
    assert np.allclose(
        PrecisionFrankaRuntime.direct_joint_position_action(default, np.zeros(7)),
        np.zeros(7),
    )
    action = PrecisionFrankaRuntime.direct_joint_position_action(
        default, np.asarray((.025, -.025, .1, 0, 0, 0, 0), np.float32)
    )
    assert np.allclose(action[:3], (.05, -.05, .07), atol=1e-6)
    # Isaac Lab scales and offsets joint-position actions but does not
    # normalize them to [-1, 1].  A reachable pose outside default +/- 0.5 rad
    # must therefore remain commandable.
    displaced = default.copy()
    displaced[0] = .8
    mapped = PrecisionFrankaRuntime.direct_joint_position_action(
        displaced, np.zeros(7, np.float32)
    )
    assert np.isclose(mapped[0], 1.6)


def test_direct_joint_retry_opens_gripper_while_holding_current_arm_pose() -> None:
    runtime = PrecisionFrankaRuntime.__new__(PrecisionFrankaRuntime)
    runtime.direct_joint_servo = True
    q = np.asarray((.8, -.4, .2, -2.2, .1, 2.4, -.3), np.float32)
    action = runtime.reopen_action(q)
    expected = PrecisionFrankaRuntime.direct_joint_position_action(
        q, np.zeros(7, np.float32)
    )
    assert np.allclose(action[:7], expected)
    assert action[-1] == 4.0
    # This is deliberately not seven zeroes: zero would command the Franka
    # default pose on Isaac Lab's offset action surface.
    assert not np.allclose(action[:7], 0.0)


def test_precision_handoff_uses_fixed_absolute_pose_until_velocity_settles() -> None:
    default = np.asarray((0.0, -.569, 0.0, -2.810, 0.0, 3.037, .741), np.float32)
    target = default + np.asarray((.2, .1, -.1, .15, 0, -.2, .1), np.float32)
    action = PrecisionFrankaRuntime.absolute_joint_position_action(target)
    assert np.allclose(default + .5 * action, target, atol=1e-6)
    source = (ROOT / "integrations/isaac_lab/aion_precision_franka_policy.py").read_text()
    assert "precision_handoff_brake:velocity=" in source
    assert "velocity_norm > .75" in source
    assert "handoff_error > .025" in source
    assert "pose_error={handoff_error:.3f}" in source
    assert "self.precision_handoff_q = q.copy()" in source
    assert "if self.direct_joint_servo:" in source
    assert "there is no\n            # longer a high-speed controller handoff" in source
    assert "precision_vertical_recovery:height=" in source
    assert "@ np.asarray((0.0, 0.0, .006)" in source
    assert "vertical_step = .006" in source


def test_direct_joint_servo_cancels_momentum_within_original_authority() -> None:
    default = np.asarray((0.0, -.569, 0.0, -2.810, 0.0, 3.037, .741), np.float32)
    delta = np.full(7, .02, np.float32)
    velocity = np.full(7, 2.0, np.float32)
    action = PrecisionFrankaRuntime.damped_joint_position_action(
        default, delta, velocity
    )
    target = default + .5 * action
    commanded_delta = target - default
    assert np.all(commanded_delta < 0.0)
    assert np.max(np.abs(commanded_delta)) <= .03501


def test_fixed_goal_solver_reaches_cartesian_target_and_preserves_safe_wrist() -> None:
    seed = np.asarray((-.65, .60, .27, -2.15, -.05, 2.95, .37), np.float32)
    target = np.asarray((.541, -.214, .148), np.float32)
    goal = PrecisionFrankaRuntime.solve_fixed_position_goal(seed, target)
    from integrations.isaac_lab.aion_precision_franka_policy import franka_hand_pose
    pose = franka_hand_pose(goal)
    assert np.linalg.norm(pose[:3, 3] - target) <= .0005
    assert np.linalg.norm(pose[:2, 1]) >= .90


def test_fixed_goal_trajectory_advances_smooth_setpoint_not_measured_velocity() -> None:
    runtime = PrecisionFrankaRuntime.__new__(PrecisionFrankaRuntime)
    runtime.phase = 1
    runtime.precision_goal_q = None
    runtime.precision_setpoint_q = None
    runtime.precision_goal_phase = None
    q = np.asarray((-.5, .5, .2, -2.2, 0., 2.8, .4), np.float32)
    target = np.asarray((.54, -.21, .15), np.float32)
    velocity = np.zeros(7, np.float32)
    action = runtime.fixed_goal_trajectory_action(q, velocity, target, q)
    setpoint = np.asarray(runtime.precision_setpoint_q)
    assert np.max(np.abs(setpoint - q)) <= .01201
    assert np.allclose(
        action, PrecisionFrankaRuntime.tracking_compensated_position_action(
            setpoint, q, velocity
        )
    )


def test_unsafe_wrist_contact_is_reacquired_without_process_failure() -> None:
    source = (ROOT / "integrations/isaac_lab/aion_precision_franka_policy.py").read_text()
    assert 'tactile_decision.get("orientation_unsafe")' in source
    assert '"unsafe_wrist_reacquire_reopen"' in source


def test_dual_approach_contact_is_captured_without_authorizing_lift() -> None:
    source = (ROOT / "integrations/isaac_lab/aion_precision_franka_policy.py").read_text()
    assert "if self.phase == 1 and tactile_dual:" in source
    assert "self.finger_close_latched = True" in source
    assert "close_limit = 24 if self.attachment_search" in source
    # Physical approach contact starts a close, but the independently learned
    # later-consequence signature remains the sole lift transition authority.
    assert "exploratory_width_margin: float = 0.0" in source
    assert "(self.attachment_latched or self.exploratory_attachment_latched)" in source


def test_one_sided_approach_contact_can_reopen_and_correct() -> None:
    source = (ROOT / "integrations/isaac_lab/aion_precision_franka_policy.py").read_text()
    assert 'and tactile_decision["reopen_and_correct"]' in source
    assert "and self.contact_correction_cooldown == 0" in source
    probe = (ROOT / "integrations/isaac_lab/physx_direct_joint_ik_contact_probe.py").read_text()
    assert "tactile_direction=-1.0" in probe
    assert "self.contact_correction_cooldown = 8" in source


def test_object_belief_is_committed_before_close_range_occlusion() -> None:
    source = (ROOT / "integrations/isaac_lab/aion_precision_franka_policy.py").read_text()
    assert "if (self.phase == 0" in source
    assert "Tactile evidence owns the final approach instead" in source
    assert "if self.phase < 2:\n            self.xy_history" not in source
    assert "visual_belief_warmup:{step + 1}/16" in source
    assert "self.direct_joint_servo and self.phase == 0 and step < 16" in source
    assert "self.visual_warmup_q = q.copy()" in source
    assert "self.tracking_compensated_position_action(" in source


def test_tracking_compensation_adds_bounded_authority_against_load() -> None:
    default = np.asarray((0.0, -.569, 0.0, -2.810, 0.0, 3.037, .741), np.float32)
    measured = default.copy()
    measured[3] -= .20
    action = PrecisionFrankaRuntime.tracking_compensated_position_action(
        default, measured, np.zeros(7, np.float32)
    )
    target = default + .5 * action
    assert np.isclose(target[3], default[3] + .35, atol=1e-6)
    assert np.allclose(target[[0, 1, 2, 4, 5, 6]], default[[0, 1, 2, 4, 5, 6]])


def test_approach_uses_settle_gated_cartesian_safe_waypoints() -> None:
    source = (ROOT / "integrations/isaac_lab/aion_precision_franka_policy.py").read_text()
    assert "def safe_approach_waypoint_action(" in source
    assert "xy_distance > .012 and measured_xyz[2] < .30" in source
    assert "np.linalg.norm(velocity) <= .20" in source
    assert "loaded_target_z = float(task_target[2]) + .067" in source
    assert "measured_task_error = task_target - measured_xyz" in source
    assert "np.clip(measured_task_error, -.010, .010)" in source
    assert "self.phase in (1, 2, 3, 4)" in source
    assert "elif self.phase in (0, 1, 2, 3, 4):" in source
    assert "self.safe_approach_waypoint_action(" in source


def test_close_window_allows_tactile_force_balancing() -> None:
    source = (ROOT / "integrations/isaac_lab/aion_precision_franka_policy.py").read_text()
    assert "close_limit = 24 if self.attachment_search" in source
    assert "balanced_contact_xy = self.tactile.balanced_servo(" in source
    assert "if tactile_dual and self.tactile is not None:" in source
    assert "self.precision_contact_hold_xyz = hand.copy()" in source
    assert "if self.phase == 2:" in source
    assert "q, velocity, self.precision_contact_hold_xyz" in source
    assert "self.precision_contact_hold_xyz[:2] += applied_balance" in source
    assert ".003 / max(balance_norm" in source
    assert "or (self.phase == 2 and contact_confirmed)" in source
    assert "balance_step=" in source
    assert "self.tactile_centering_count < 2" in source
    assert "else self.contact_correction_xy - 2.0 * tactile_step" in source
    assert "self.phase_age >= 12" in source
    assert "self.phase in (1, 2) and tactile_decision" in source
    assert "Do not close directly from one-sided contact" in source
    assert '.012 if self.precision_contact and getattr(self, "tactile_centering_count", 0) > 0' in source
    assert "A close that retained only one object contact" in source


def test_probe_only_width_margin_is_bounded_and_explicit() -> None:
    source = (ROOT / "integrations/isaac_lab/aion_precision_franka_policy.py").read_text()
    probe = (ROOT / "integrations/isaac_lab/physx_direct_joint_ik_contact_probe.py").read_text()
    assert 'raise ValueError("exploratory_width_margin_rejected")' in source
    assert "exploratory_signature=" in source
    assert "exploratory_width_margin=.003" in probe
    assert "and self.phase >= 3 and not tactile_dual" in source
