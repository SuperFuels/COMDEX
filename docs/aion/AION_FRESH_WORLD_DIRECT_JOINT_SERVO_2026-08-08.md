# AION fresh-world direct-joint servo result — 2026-08-08

## Outcome

The cube was not lifted in this bounded cycle. The corrected controller did,
however, convert an approach-only failure into repeatable opposed fingertip
contact under an independent PhysX world.

| Probe | Fresh worlds | Lifts | Opposed-contact frames | Unsafe outcomes |
|---|---:|---:|---:|---:|
| v1, falsely normalized joint target | 2 | 0 | 0 | 0 |
| v2, corrected Isaac Lab joint target | 1 | 0 | 75 | 0 |

The v2 episode return rose from 0.826 on the same v1 seed to 1.902. Object
height stayed at 0.055 m, so no lift claim is permitted.

## Fault found and corrected

`JointPositionActionCfg(scale=0.5, use_default_offset=True)` scales and offsets
the action; it does not define a normalized `[-1, 1]` command surface. The
first direct servo incorrectly clipped its output to that interval. This
trapped the robot within default pose plus or minus 0.5 rad and made it retreat
after approaching the cube.

The correction preserves the 35 mrad per-frame IK limit and Franka joint
limits, then maps the absolute target through the task scale/default offset
without the false normalization clamp. All 26 focused local contract, safety,
cost, and fresh-world tests pass.

## Remaining blocker

The corrected episode accumulated 75 opposed-contact frames across bounded
close attempts, but the sealed attachment signature never fired. Therefore the
controller correctly refused to enter the lift phase. The next probe must
capture fingertip-force and finger-width histories during those contact frames
and determine which sealed signature condition is mismatched: minimum force,
force balance, four-frame persistence, or the 20–26 mm finger-width band.

No controller is promoted from this result. Both NVIDIA workspaces were stopped
after evidence retrieval.

## Tactile fail-fast iteration

Three instrumented single-world probes then isolated the remaining contact
fault without using object pose, reward, teacher action, or contact geometry:

- Baseline: 116 frames of force on one finger, peaking at 169.8 N, with zero
  force on the opposite finger.
- Opposed correction: rejected after 35 bounded re-centering attempts continued
  to hit the same finger.
- Declared Panda digit direction: produced 88 opposed-contact frames, reached
  both fingers (250 N and 147.7 N maxima), and entered the close phase for 92
  frames with no unsafe outcome.

The declared-direction controller did not lift because its 16-frame close
window often ended before force could remain balanced for the sealed four-frame
attachment signature. Some attempts reached the proven 24--25 mm per-finger
width band, but the forces alternated between fingers. The next offline build
therefore preserves the declared re-centering direction, extends the bounded
close window to 24 frames, and enables the already sealed 2.5 mm tactile
force-balance servo during closing. Thirty-one focused tests pass. This build
has not yet been promoted or evaluated on the GPU.

## Retry authority and first physical micro-lift

Later trajectory capture invalidated one assumption in the preceding tactile
comparison: retry branches returned seven zero arm actions. On this task zero
means the Franka default pose, not the current pose. The resulting whole-arm
motion confounded the apparent tactile direction. All reopen/retry branches now
emit an absolute current-joint hold, and a regression test protects that action
surface.

With that confounder removed, the measured direction is opposite the local-left
axis for declared-left contact. An eight-frame cooldown also prevents 10 mm
tactile information actions from stacking faster than the arm can execute
them. Reopens fell from 31 to 12, and the controller reached 23 consecutive
two-finger closing frames.

That episode produced the first measured physical cube rise in this direct
servo series: post-action height increased from 0.0210 m to 0.0289 m while the
fingers held median forces of roughly 67 N and 79 N. This is a 7.9 mm
micro-lift, not a successful task lift. The independent success threshold is
still object height greater than 0.10 m.

The secure-grasp recognizer missed the strongest window by 0.26 mm of finger
width (28.26 mm versus the probe's then 28.00 mm maximum) despite a 0.857 force
balance ratio. The probe-only width margin is now 3 mm. An earned grasp latch
is also retained while both tactile sensors remain in contact; the recognition
signature owns entry into lift but is no longer incorrectly treated as a
permanent force invariant during acceleration. The default/promoted controller
retains the strict sealed threshold.

A fresh repeat did not reacquire contact and therefore could not validate the
continuation change. No greater-than-10 cm lift is claimed. Thirty-three
focused tests pass, both NVIDIA workspaces are stopped, and no controller is
promoted from these results.
