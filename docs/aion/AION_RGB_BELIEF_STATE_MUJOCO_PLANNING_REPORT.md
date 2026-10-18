# AION RGB Belief-State Physical Planning

## Breakthrough

AION has moved beyond numeric-state MuJoCo control. The promoted procedure
`procedure_rgb_belief_state_mujoco_planning_v2` receives only rendered RGB
frames, a visual goal frame and a timestamp. Hidden position, velocity, mass,
gravity and damping remain inside the evaluator.

The learned chain is:

```text
RGB observations
-> discover controllable pixels through intervention
-> bind the same entity in a visual goal image
-> reconstruct velocity from frame history
-> learn action-conditioned visual transitions
-> invent a hover-identification experiment
-> search ten-step action sequences
-> execute with commit-before-action predictions
-> stabilise and stop from visual evidence
-> retain the method across restart
```

## Why the diagnostic step matters

An early challenger reached target regions but retained excessive momentum.
Another trusted a biased regression intercept and crossed the vertical safety
envelope under low gravity. Both were rejected.

The successful method constructed a new diagnostic experiment: it applied six
short vertical probes in fresh episodes and selected the force producing the
smallest visual drift. This identified the hover action without reading gravity
or mass. The result was then used as the equilibrium point for conservative
visual feedback and accumulated-error correction.

## Transfer cohort

The sealed cohort changed body morphology, colour, camera position and distance,
mass, gravity, damping, starting position and visual target. It contained boxes,
an ellipsoid and a sphere across four disjoint physical configurations.

| Measure | Result |
|---|---:|
| Numeric simulator observations used | 0 |
| Sealed RGB-only success | 4/4 |
| Matched reactive cold control | 0/4 |
| Distinct morphologies | 3 |
| Camera configurations | 4 |
| Dynamics configurations | 4 |
| Pre-action commitments | 709 |
| Unsafe learned worlds | 0 |
| Ungroundable low-contrast OOD world | Abstained |
| Live repository writes | 0 |
| Ambient authority expansions | 0 |
| Restart retention | Passed |

The cold control received the same rendered observations but had no
intervention-derived tracker, belief state, dynamics model or planner. It failed
all four worlds.

## Governance

The first retention attempt was denied because the new module used an invalid
CAU authorization field. The physical result was not promoted through that
path. After correcting the integration to the established `allow_learn`
contract, the complete frozen cohort was rerun. Only then was the method
promoted and reconstructed after restart.

## Boundary and next step

This is genuine RGB-only belief-state reconstruction, diagnostic experiment
invention and multi-step control under MuJoCo-owned physics. The two-axis action
schema, scene family, local transition model and success authority remain
engineered. It is not unrestricted vision, robotics or general physical
intelligence.

The next major physical boundary is topology and contact: multiple independently
moving objects, occlusion, collision, articulated bodies and tasks requiring
the learner to invent which object relationships matter. The practical 70%
lane remains active in parallel.
