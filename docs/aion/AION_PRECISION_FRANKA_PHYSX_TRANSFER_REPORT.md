# AION Precision Franka Transfer and PhysX Tournament

## Executive result

The local articulated precision result authorized one frozen transfer attempt
to NVIDIA Isaac/PhysX. The attempt was executed honestly and rejected. The new
Franka precision challenger achieved **0/12** strict lifts, while the protected
v13 policy achieved **2/12** on the same fresh seeds and action budget. No new
procedure was promoted and `procedure_rgb_phase_bound_episodic_memory_v13`
remains the protected PhysX champion.

This is a useful negative result. It disproves the hypothesis that accurate RGB
cube geometry, accurate joint-waypoint reconstruction and accurate one-step
joint dynamics are sufficient to produce reset-disjoint contact manipulation.

## Transfer architecture

The adapter was built from previously retained, successful Isaac teacher
trajectories. Forty successful programs were used for private construction,
eight for development criticism and five sealed programs for offline scoring.
At runtime the challenger received only RGB observations and the same 18-value
bounded joint/gripper proprioception available to the protected policy.

The private capsule contained:

1. a digest-checked RGB cube detector and camera projection;
2. five cube-conditioned Franka joint waypoints;
3. an identified seven-joint action-to-motion model;
4. one-step inverse-dynamics micro-corrections with re-observation after every
   action; and
5. a protected-v13 fallback for geometry or uncertainty outside the capsule's
   admitted region.

The deployed runtime was converted to a portable NumPy capsule. It required no
`joblib` or `scikit-learn` installation in the Isaac container, expanded no
network or filesystem authority, and verified the capsule digest before use.

## Offline authorization gates

| Gate | Sealed result | Decision |
|---|---:|---|
| RGB cube world-position mean error | 0.000630 m | pass |
| RGB cube world-position p90 error | 0.000907 m | pass |
| Joint-waypoint mean error | 0.050689 rad | pass |
| Joint-waypoint p90 error | 0.108063 rad | pass |
| Next-motion mean error | 0.007623 rad | pass |
| Next-motion p90 error | 0.020122 rad | pass |
| Action-matrix condition number | 31.19 | pass |
| Malicious contracts rejected | 6/6 | pass |
| Unsafe actions | 0 | pass |

These gates authorized a tournament; they did not authorize promotion.

## Frozen NVIDIA PhysX tournament

The exam used `Isaac-Lift-Cube-Franka-v0`, twelve fresh seeds
(`99107--99118`), 250 actions per episode, teacher actions disabled and zero
privileged runtime geometry or contact fields.

| Arm | Strict lifts | Mean maximum cube height | Mean return | Unsafe |
|---|---:|---:|---:|---:|
| Routed precision challenger | 0/12 | 0.055000 m | 0.6580 | 0 |
| Protected v13 | 2/12 | 0.132124 m | 15.7639 | 0 |

The challenger advanced through all five nominal phases, but the cube height
never moved above its initial 0.055 m in any episode. Once it had already lost
to the protected champion, the paid cold arm was omitted: a cold result could
not make the challenger satisfy the mandatory `challenger > v13` rule.

## Failure attribution

The failure is **task-space contact grounding**, not cube visibility. Joint
space is redundant: several plausible seven-joint configurations can have low
imitation error while placing or orienting the gripper incorrectly relative to
the cube. The offline targets rewarded resemblance to teacher joint states but
did not prove that successive actions reduced end-effector-to-object error,
straddled the cube with both fingers, created contact, or retained the object
during lift.

The correct learned lesson is:

\[
\text{low joint imitation error}
\not\Rightarrow
\text{correct object-relative end-effector geometry}
\not\Rightarrow
\text{contact or lift}.
\]

## Revised pre-paid gates

Another paid PhysX run is blocked until a new controller passes all of the
following on fresh held-out resets:

1. reconstruct gripper/end-effector pose from RGB and bounded joints;
2. demonstrate monotonic reduction of object-relative task-space error during
   approach;
3. verify a two-finger straddle/contact predicate rather than a time-based
   phase transition;
4. use short, interruptible task-space corrections followed by re-observation;
5. prove recovery after an induced miss or slip; and
6. retain v13 fallback authority when the relational state is uncertain.

The preferred design is a geometric task-space servo plus a learned bounded
residual, using public Franka kinematics or a source-attested URDF and RGB cube
geometry. Isaac remains the exam, not the practice environment.

### Temporal belief-state requirement

The next controller must also exploit simulation's frame-by-frame asymmetry.
It may deliberate between physics steps, but it may not treat a predicted
future as observed truth. A rolling strip of recent RGB, joint and committed
action observations will reconstruct relative motion and uncertainty. For each
small intervention it must predict whether gripper-to-cube distance, alignment
or contact confidence should improve, commit the action, allow PhysX to advance
one step and compare the prediction with the next frame. Divergence triggers
braking, re-observation or replanning rather than continuation along a stored
joint timeline.

Thus the intended loop is:

\[
\text{temporal belief state}
\rightarrow \text{short-horizon task-space prediction}
\rightarrow \text{one bounded action}
\rightarrow \text{independent physics}
\rightarrow \text{prediction error}
\rightarrow \text{micro-correction}.
\]

This uses additional thinking time between simulator frames without claiming
access to hidden state, future outcomes or a rewritable timeline.

## Claim boundary

The result establishes a fail-closed Franka adapter, portable capsule, clean
teacher-removed PhysX comparison and a falsified representation hypothesis. It
does **not** establish improvement over v13, general manipulation, robotics
mastery, Cosmos mastery, AGA or AGI. No procedure was promoted.

## Rapid task-space learning cycle

A subsequent rapid cycle used the rejected tournament as developmental
evidence rather than repeating the same controller. Public Franka kinematics
showed that the first live task-space servo reached the cube but disturbed it
with the wrong wrist orientation. That controller improved mean return from
0.6580 to 0.9067 but still scored 0/12 lifts. A frame strip confirmed the arm
approached and then pushed the cube before lifting empty.

Two full-pose solvers were rejected offline because their orientation
corrections sacrificed positional convergence. The accepted private challenger
then used budgeted deliberation between frames: it generated five orientation
strengths, predicted each candidate through the identified actuator model,
rejected candidates expected to increase hand--cube distance, and committed
only the best remaining action. On five sealed programs this raised positive
distance improvement to 92%, positive combined-pose improvement to 100%, and
reduced predicted relational error by 5.48% per step.

On a new precommitted PhysX cohort (`99207--99218`), predictive pose control
produced its first strict live lift: 1/12, with a 0.5142 m maximum cube height
in episode five. Protected v13 scored 0/12 on that cohort. The challenger won
the matched comparison but failed the absolute requirement of more than 2/12,
so it was rejected and v13 remains the champion. This is a real lineage advance
from never touching the cube to one complete teacher-removed lift, not yet a
reliable manipulation breakthrough.

## Contact relation and recovery lineage

The next cycle separated contact acquisition from gross reaching. The v2
adapter learned a tool--object contact relation from successful teacher
episodes rather than aiming the hand at the cube centre. On sealed successful
programs its mean three-dimensional contact-relation error was 0.01697 m
(0.02955 m at p90). RGB geometry, waypoint, identified-dynamics and contact
gates all passed before cloud execution.

On fresh seeds `99307--99318`, v2 achieved 1/12 strict lifts; protected v13
also achieved 1/12. Mean returns were 7.8467 and 8.4652 respectively, with
zero unsafe actions. The challenger therefore failed both the absolute
greater-than-2/12 gate and the comparative gate. Analysis of the immutable
trace showed that 56.37% of its proposals had reverted to v13. Of those
fallbacks, 1,171 followed visual-envelope rejection after contact moved the
cube and 520 followed a pessimistic one-step prediction. Ordinary object
displacement was being misclassified as a terminal distribution shift.

The v3 challenger enlarged only the bounded physical table envelope, re-read
cube position after a failed close, tried object-relative contact offsets,
backtracked candidate step sizes and removed timeout-only phase transitions.
Fallback use fell to 6.6%, demonstrating that the diagnosed failure was real.
It nevertheless overcorrected: 877 actions held position for re-observation,
1,372 remained in phase zero, and the controller achieved 0/12 strict lifts on
seeds `99407--99418` versus 1/12 for protected v13. It was rejected. One
unsealed execution produced no durable artifact because a container-relative
output path disappeared at teardown; it was discarded and never entered the
result ledger. The identical frozen cohort was repeated with an absolute
mounted path to obtain the cited immutable receipt.

The frozen v4 proposal composes the useful parts of both failures:

1. phase transitions require measured convergence, with one explicitly
   bounded progress relaxation for coarse approach;
2. if all full corrections are pessimistic, the controller executes the best
   ten-percent-scale information action rather than holding indefinitely;
3. attachment is tested with an 8 cm lift before a larger 25 cm lift; and
4. detected slip causes reopen, re-observation and private re-planning rather
   than immediate delegation to the old policy.

The v4 policy digest is
`738e2d02a91e57a054f08e3c4e1015ec75307968efd747ce7fc4546ed1f3994d`.
Its required prospective cohort is `99507--99518`. It has no PhysX credit: the
Brev account rejected instance start for insufficient credit. Promotion
remains impossible until a complete immutable receipt establishes more than
2/12 lifts, superiority to protected v13 and a matched cold control, with zero
unsafe actions.

## Artifacts

- Offline adapter result: `results/hexcore_precision_franka_adapter.json`
- PhysX CAU result: `results/hexcore_precision_franka_physx_tournament.json`
- Immutable PhysX receipt:
  `results/immutable/isaac_precision_franka/precision_franka_physx_receipt.json`
- Portable capsule:
  `results/immutable/isaac_precision_franka/precision_franka_v1.npz`
- Visual evidence: `results/visual/precision_franka_physx_sequence.png`
- Position-servo evidence: `results/visual/task_space_franka_physx_sequence.png`
- Predictive-pose evidence: `results/visual/predictive_pose_franka_physx_sequence.png`
- Contact-relation evidence: `results/visual/contact_consistent_franka_physx_sequence.png`
- Re-plan/backtracking evidence: `results/visual/replan_backtracking_franka_physx_sequence.png`
- Contact-recovery lineage result: `results/hexcore_contact_recovery_franka_lineage.json`
- Adapter builder: `integrations/isaac_lab/build_precision_franka_adapter.py`
- Runtime policy: `integrations/isaac_lab/aion_precision_franka_policy.py`
- CAU evaluator: `integrations/isaac_lab/evaluate_precision_franka_tournament.py`
