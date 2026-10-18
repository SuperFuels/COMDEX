# AION Articulated Precision Cube-Lifting Transfer

## Result

AION has transferred its retained visual, contact and precision-control methods
into a genuine local articulated manipulation task. The MuJoCo authority owns
a two-link arm, opposing fingertip actuators, a free cube, gravity, contact,
friction and hidden action delay. Runtime cognition receives RGB, joint
position, joint velocity and time. Cube pose, contact flags, teacher actions
and evaluator state remain hidden.

HexCore promoted:

`procedure_articulated_precision_cube_lifting_v1`

## Composed intelligence

The procedure reconstructs three previously promoted parents:

- `procedure_cross_body_precision_control_apprenticeship_v1`;
- `procedure_rgb_articulated_sequence_skill_v4`; and
- `procedure_rgb_contact_occlusion_skill_composition_v3`.

The resulting loop is:

\[
\text{RGB landmarks}
\rightarrow
\text{articulated topology}
\rightarrow
\text{pixel-space inverse kinematics}
\rightarrow
\text{motor identification and relevance routing}
\rightarrow
\text{approach}
\rightarrow
\text{opposing-finger contact}
\rightarrow
\text{lift}
\rightarrow
\text{physical outcome}.
\]

The learner infers link geometry from visual landmarks and bounded
proprioception. It evaluates both inverse-kinematic branches, selects the safe
branch closest to its current state, identifies hidden motor delay and
actuation response, predicts delayed consequences, and commits every action
before MuJoCo executes it.

## Failure-driven model extension

The original calibration-lane forward model failed on the articulated arm
because gravity and joint coupling appeared as unexplained acceleration. A
private successor extended the model with learned constant and position-based
acceleration terms. This improved diagnosis, but some nonlinear fits remained
too noisy to deserve action authority.

A governed router was therefore added:

\[
\text{credible identified model}
\Rightarrow
\text{use it},
\qquad
\text{high residual}
\Rightarrow
\text{retain discovered delay but use robust fallback dynamics}.
\]

The unrestricted identified challenger scored only 3/4 and lost to the strong
fixed-model ablation at 4/4. It was rejected. The selective router then matched
the strong ablation without inheriting the bad model. This is evidence for
model relevance and safe fallback, not a claimed success improvement over the
strong ablation.

## Sealed tournament

The untouched cohort varied arm lengths, motor gains, damping, action delay,
camera position, cube size, mass and friction.

| Measure | Routed AION | Strong fixed-model ablation | Cold arm |
|---|---:|---:|---:|
| Successful lifts | 4/4 | 4/4 | 0/4 |
| Mean lift height | 0.08182 m | 0.08178 m | 0.00243 m |
| Privileged runtime geometry | 0 | 0 | 0 |
| Teacher actions | 0 | 0 | 0 |

Additional gates:

| Measure | Result |
|---|---:|
| Weakest-world lift success | 100% |
| Safe worlds | 4/4 |
| Pre-action commitments | 570 |
| Malicious actions rejected | 4/4 |
| Restart retention | passed |
| Simulator-neutral capsule integrity | passed |

The malicious cohort covered non-finite joint commands, out-of-range commands,
wrong-dimensional actions and invalid gripper authority.

## Representative physical sequence

The retained evidence strip contains the start, visual alignment, physical
grasp and successful lift from the first sealed delayed arm. The cube is a free
MuJoCo body: success is awarded only when its maximum physical height rises at
least 0.075 metres above its initial height.

## Isaac handoff

The procedure emits a digest-bound simulator-neutral capsule defining:

- RGB plus bounded joint proprioception inputs;
- two bounded joint actions and one bounded gripper action;
- commit-before-act requirements;
- forbidden privileged runtime channels; and
- the evaluator-owned physical lift property.

This local result authorizes construction of one Isaac adapter and one frozen
PhysX tournament. It does not itself establish Isaac or real-robot competence.
The protected PhysX v13 champion remains unchanged until NVIDIA-owned outcomes
show a strict improvement.

## Claim boundary

This is a bounded but genuine articulated contact-manipulation result under
local MuJoCo physics. The two-link morphology, colored visual landmarks,
inverse-kinematics meta-method, safe action surface and evaluation cohort remain
engineered. It is not unrestricted robotic manipulation, world-model mastery,
real-robot transfer or AGI.
