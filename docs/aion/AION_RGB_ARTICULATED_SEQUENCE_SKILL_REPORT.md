# AION RGB Articulated Sequence Skill

## Promotion

`procedure_rgb_articulated_sequence_skill_v4` is promoted. It composes the
retained RGB contact/occlusion procedure into a qualitatively different task:
controlling a two-joint articulated chain to reach three changing targets in
the correct observed sequence.

The learner receives only RGB frames and timestamps. MuJoCo joint position,
velocity, target index, link lengths, damping and camera parameters remain
hidden inside the authority.

## Learned visual topology

Four coloured landmarks are present but no semantic roles are supplied. AION
intervenes independently on both action channels and invents a topology from
motion and invariant-distance evidence:

```text
static pivot -> moving elbow -> moving endpoint
                         + independent active target
```

The base--elbow and elbow--endpoint distances remain stable across
interventions. That invariant distinguishes the physical chain from the static
target even when actuator coupling makes both moving landmarks respond to both
actions. AION then estimates signed rotational action effects and reconstructs
a configuration-dependent visual Jacobian from the current landmark geometry.

The controller updates this model on every visible consequence. When an opaque
region removes the endpoint, it propagates a recurrent belief and then
re-identifies the endpoint when visual evidence returns. Completion of one
target changes which site is visually active; no stage number is exposed.

## Failure-driven construction

Three invalid or inadequate challengers were rejected:

1. Endpoint-only identification produced nearly collinear action effects and
   unreliable control. Multi-landmark topology was introduced.
2. MuJoCo interpreted joint ranges as degrees, forcing the initial arm toward
   zero. The entire run was invalidated and the authority was corrected to
   explicit radians.
3. Two third-stage targets were hidden by the occluder itself. They were moved
   outside the mask so visual instructions remain observable while the moving
   endpoint still experiences occlusion.

The final safety record retains maximum joint excursion. MuJoCo joint limits
are compliant, so the declared safety envelope is 2.70 radians around a 2.65
radian nominal limit.

## Results

| Measure | Result |
|---|---:|
| Sealed articulated worlds | 4 |
| Learned sequence success | 4/4 |
| Cold periodic controller | 0/4 |
| Targets per world | 3 |
| Controlled joints | 2 |
| RGB-only observation | 100% |
| Visual topology discovery | Passed |
| Online visual-model adaptation | 4/4 |
| Occlusion recovery | 4/4 |
| Pre-action commitments | 1,082 |
| Malformed actions rejected | 4/4 |
| Unsafe worlds | 0 |
| Parent skill reconstruction | Passed |
| Skill-capsule reconstruction | Passed |
| Champion retained after restart | Passed |

The sealed cohort changed link lengths, damping, camera position and distance,
initial joint configuration and ordered target geometry.

## Persistent skill composition

The promoted capsule records its parent procedure and digest, visual action
contract, invariants, topology-discovery method, occlusion horizon, failure
signals and verification digest. If the contact/occlusion parent is absent or
altered, the articulated learner fails closed rather than silently relearning
or bypassing ancestry.

This is therefore evidence of accumulating procedural machinery:

```text
single-body RGB control
-> contact and passive-object causality
-> occlusion-aware belief
-> articulated topology
-> changing sequential objectives
```

## Boundary and cloud escalation

This is bounded articulated visual learning, not general robotics. The
two-joint family, safe actuator surface, landmark rendering and learning
meta-algorithm remain engineered. It nevertheless closes the intended local
articulated gate.

The programme can now begin a controlled cloud escalation: package the
simulator-neutral contract for Isaac Lab while retaining MuJoCo as the local
regression authority. The next capability test should add object manipulation
or household navigation in an independently implemented simulator, rather than
another variation of the same reaching world.
