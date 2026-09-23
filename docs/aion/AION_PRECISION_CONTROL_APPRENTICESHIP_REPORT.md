# AION Precision-Control Apprenticeship

## Result

The precision-control apprenticeship is internally promoted as
`procedure_cross_body_precision_control_apprenticeship_v1`. It addresses the
motor-calibration bottleneck exposed by the Isaac cube-lifting programme: how
to estimate how far and how quickly an unfamiliar actuator will move, when its
command will take effect, when to brake, and how to make small corrective
movements after a disturbance.

This stage is deliberately evaluated locally under MuJoCo before another paid
PhysX run. It is a transferable calibration skill, not another memorized cube
trajectory.

## Architecture

The existing consciousness `PredictionEngine` remains the executive forecast
layer. It predicts feasibility, risk and likely mission outcomes. Precision
control adds a separate numerical forward model because millisecond motor
consequences require measured dynamics rather than semantic prediction.

For an unfamiliar control body, AION now performs:

1. bounded commit-before-act interventions;
2. action-delay identification over delays zero through three;
3. multivariate identification of actuator effectiveness and damping;
4. forward prediction through the identified delay window;
5. uncertainty-scaled control authority;
6. predictive braking before overshoot;
7. closed-loop micro-correction after every observation; and
8. abstention when the identified body is ill-conditioned or effectively
   uncontrollable.

The learned model is

\[
\dot{v}_{t} = A u_{t-d} - Dv_t,
\qquad
q_{t+1} = q_t + v_t\Delta t + \tfrac{1}{2}\dot{v}_t\Delta t^2,
\]

where the delay \(d\), actuation matrix \(A\), and damping matrix \(D\) are
inferred from consequences. Control is recomputed after every observation; no
long open-loop trajectory is executed.

## Sealed evaluation

Six source-disjoint worlds varied dimensionality, action delay, actuator
strength, damping, target location and post-action disturbance. The sealed
cohort ranged from one control dimension to five. A matched cold controller
received the same observation and action budgets but used one fixed motor
assumption and performed no identification.

| Measure | Result |
|---|---:|
| Sealed learned success | 6/6 |
| Matched cold success | 0/6 |
| Weakest-family success | 100% |
| Hidden-delay identification | 100% |
| Mean learned final error | 0.000029995 |
| Mean cold final error | 0.048603 |
| Final-error improvement | 1,620.37x |
| Disturbances recovered | 6/6 |
| Pre-action commitments | 1,560 |
| Malicious actions rejected | 3/3 |
| Near-uncontrollable body | abstained |
| Memorized trajectories | 0 |
| Body-specific parameters retained | 0 |
| Restart retention | passed |

The malicious cohort covered non-finite actions, out-of-range actions and
wrong-dimensional actions. All were rejected before execution. A separate
near-zero-authority actuator was identified as unreliable and caused an
explicit abstention rather than an unsafe or fabricated attempt.

## Retained intelligence

HexCore retains the method
`identify_predict_brake_micro_correct`, including the procedure structure and
its evidence receipt. It does not retain the sealed trajectories or the
individual body parameters. After restart, the procedure and cohort remain
available, so a new body is calibrated from fresh interventions using the same
learned method.

## Claim boundary and next transfer

This is cross-dimensional stop-at-target precision in independent MuJoCo
calibration lanes. It is not yet proof of precise articulated-arm contact,
cube lifting, locomotion or Isaac transfer. The important advance is that the
missing calibration machinery now exists and has a strong causal control.

The next transfer is staged rather than assumed:

\[
\text{calibration lanes}
\rightarrow
\text{articulated joint targets}
\rightarrow
\text{end-effector servo}
\rightarrow
\text{contact/gripper micro-correction}
\rightarrow
\text{one frozen PhysX tournament}.
\]

PhysX remains the independent simulator authority for promotion over the
protected v13 cube-lifting champion.

## Articulated transfer update

The next transfer has now been executed. The lane model was extended with
gravity- and position-dependent acceleration terms, then composed with retained
RGB articulated topology and contact/occlusion skills. An unrestricted
identified controller scored 3/4 and was rejected because a strong fixed-model
ablation scored 4/4. A relevance-routed successor matched the strong ablation
at 4/4 while a genuinely cold arm scored 0/4. The promoted child is documented
in `AION_ARTICULATED_PRECISION_CUBE_LIFTING_REPORT.md`.
