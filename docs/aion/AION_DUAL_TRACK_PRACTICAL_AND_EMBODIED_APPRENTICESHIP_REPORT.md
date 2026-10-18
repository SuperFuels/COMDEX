# AION Dual-Track Practical and Embodied Apprenticeship

## Outcome

AION now has an executable resource policy rather than a narrative priority:
seven of every ten portfolio contracts are reserved for useful intellectual or
practical apprenticeship and three are reserved for embodied physical
learning. The control plane was promoted as
`procedure_dual_track_practical_embodied_portfolio_v1`.

The first physical authority is local MuJoCo 3.11.0 on Apple Silicon. AION is
not credited merely for installing or calling the simulator. It must infer
hidden dynamics by intervention, commit a prediction before each step, control
the body, transfer to sealed worlds and beat a matched no-learning controller.

## Control-plane design

Each ten-contract generation contains:

- seven practical missions spanning software, changing public data,
  machine-checkable reasoning, evidence synthesis, product/business work,
  security and integrated cross-domain construction;
- three physical missions covering system identification, closed-loop control
  and transfer/OOD abstention;
- a declared independent outcome authority and success contract;
- a SHA-256 precommitment before execution;
- a live competency query through the existing Mission Capability Action
  Harness; and
- either governed execution or an explicit learn-before-execute decision.

The scheduler itself cannot award competency. Practical or physical learning
enters the competency ledger only after the corresponding independent outcome
contract closes.

The first live generation found one mission ready for strongly verified
execution and nine that require learning first. It selected the secure-service
mission and placed `product_project_management`, its weakest required retained
capability, into the progressive learning priority queue. This is visible on
the development dashboard and prevents the portfolio from becoming a passive
list of ambitions.

## Simulator-neutral physical contract

The implementation separates the learner from an `EmbodiedAuthority`
interface. MuJoCo owns gravity, mass, damping, integration and contact. The
learner receives only bounded position/velocity observations, targets and two
normalized action channels. It receives no hidden-parameter accessor.

The learned method is:

1. observe passive motion under a committed zero-input probe;
2. estimate gravitational acceleration from consequences;
3. apply a bounded diagnostic force and estimate effective actuation gain;
4. precommit a next-state prediction;
5. use identified dynamics inside bounded feedback control; and
6. re-identify after transfer rather than assuming nominal physics.

## Results

| Measure | Result |
|---|---:|
| Portfolio allocation | 7 practical / 3 embodied |
| Persistent mission precommitments | 10/10 |
| MuJoCo development worlds | 2/2 |
| Sealed source-disjoint worlds | 6/6 |
| Matched cold-controller worlds | 0/6 |
| Pre-action physical commitments | 2,880 |
| Malformed/malicious actions rejected | 5/5 |
| Impossible-actuator OOD abstention | Passed |
| Unsafe learned worlds | 0 |
| Ambient authority expansion | 0 |
| Live repository writes | 0 |

The first challenger was rejected at 5/6 because one evaluation world required
more upward force than its actuator could physically produce. The cohort was
corrected to separate controllable transfer from an explicitly impossible OOD
world. AION then passed all six controllable worlds and abstained on the
impossible world.

## Claim boundary and next stages

This demonstrates simulator-neutral, state-observation physical system
identification and control under real MuJoCo dynamics. It is not pixel-only
embodied learning, robotics, Isaac Lab scale or general physical mastery.

The next physical sequence is RGB belief-state learning, unfamiliar morphology
and multi-step planning locally; then the same authority interface can target
cloud Isaac Lab. Cosmos can later serve as a governed proposal/world-model
substrate, but generated imagery cannot replace consequences from a physics
authority. The practical lane continues to convert capability gaps into useful
projects and later independently checked outcomes.
