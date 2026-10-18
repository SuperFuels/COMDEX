# AION object-filtered general grasp control leap — 2026-08-08

## Verdict

No new verified cube lift was earned in this cycle. The historical retained
controller still has two genuine PhysX lifts in twelve trials, but the new
controller has not yet reproduced one. No result is promoted or sealed.

The cycle did remove four major sources of false learning and wasted GPU spend:

1. Close-range visual occlusion can no longer rewrite the object target.
2. Fingertip evidence is filtered to the active object; table and self-contact
   no longer count as grasp evidence.
3. Unsafe wrist orientation causes a controlled reopen/reacquire, not a crashed
   episode.
4. The unstable learned coarse inverse-dynamics controller has been removed
   from the direct-servo probe. A smooth, pre-solved joint trajectory now owns
   motion from the initial safe pose onward.

## What the matched trials proved

- `object_filtered_handoff_brake_20260808_v1`: stopped on a recoverable wrist
  orientation check after genuine one-sided object contact. This led to the
  safe reacquisition path.
- `object_filtered_damped_servo_20260808_v1`: completed safely, but accumulated
  Cartesian drift and made no object-only fingertip contact.
- `object_filtered_fixed_goal_20260808_v1`: kept the wrist upright and reduced
  late motion, but inherited the coarse controller's table-collision state.
- `object_filtered_recovered_fixed_goal_20260808_v1`: correctly refused to
  proceed because pose recovery never completed.
- `object_filtered_early_fixed_goal_20260808_v1`: earlier takeover improved the
  final hand height from roughly 11.2 cm to 15.4 cm, but inherited velocity was
  still too high.
- `object_filtered_vertical_recovery_20260808_v1`: a distant recovery target
  remained torque-pinned.
- `object_filtered_incremental_escape_20260808_v1`: issued 46 small upward
  commands after settling, but the collision-pinned robot did not follow them.
  This proved that recovery after the unsafe coarse descent is the wrong place
  to solve the problem.

Every trial used post-action object height above 0.10 m as the lift authority.
Every outcome was safe; none lifted.

## Final architecture prepared offline

The precision controller now:

- grounds the object in RGB while safely above it and commits that belief;
- solves a bounded Cartesian grasp target to a fixed Franka joint goal;
- advances a smooth joint-position setpoint by at most 12 mrad per frame;
- preserves a horizontal gripper closing axis;
- requires object-filtered opposed fingertip contact;
- closes at the measured contact pose;
- requires the learned attachment signature before entering lift;
- uses post-action object height, never reward or object pose, for success.

This control decomposition is object-generic: the contact filter binds to the
environment's active object prim rather than a cube-specific collision path.
General competence still requires a later curriculum over size, shape, mass,
friction, pose and occlusion; the current evidence supports only the cube task.

## Verification

Forty-one focused offline tests pass. Both NVIDIA workspaces are stopped.
Estimated GPU spend for this fail-fast cycle is approximately $1.20–$1.50,
subject to Brev billing granularity.

## Next decisive test

Run exactly one fresh-world episode with the final all-direct controller. It
must show this sequence before any wider search is authorized:

1. smooth phase-0 convergence with no coarse controller modes;
2. hand remains above the table corridor;
3. fixed-goal phase-1 convergence;
4. object-only one- or two-finger contact;
5. attachment-qualified close and post-action lift.

If phase 0 remains safe but misses laterally, tune only the bounded object-
relative contact offset. If phase 0 again descends unsafely, audit the local
Franka kinematic frame against Isaac's measured end-effector frame before any
additional GPU search.
