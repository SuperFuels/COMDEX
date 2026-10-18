# HexCore Arena v8: Closed-Loop Physical Intelligence

## Outcome

Arena v8 is internally promoted as
`procedure_closed_loop_physical_intelligence_v8_b603d84be41a`.

AION now closes the loop from rendered perception to intervention and delayed
consequence.  A separately implemented authority owns hidden actuation gain,
drag, delay, regime changes and target dynamics.  AION receives only rendered
pixels, a noisy velocity channel and bounded actions.

## Learning and action cycle

1. Recover object position from pixels without a coordinate label.
2. Maintain competing gain/drag/delay models.
3. Choose diagnostic pulses by expected model disagreement.
4. Hash-commit the next-state prediction before executing the action.
5. Update model probability from the independently returned state.
6. Plan a short action sequence against the selected dynamics model.
7. Detect persistent residual surprise and revise the dynamics model.
8. Abstain if repeated action cannot control an out-of-family system.

The transfer prior was not encoded.  It was induced from outcomes in 32
development worlds, with Dirichlet smoothing retaining non-zero probability for
every candidate.  The sealed learner and cold control then received the same 24
new worlds, tools, actions, targets and stopping rule; only accumulated outcome
experience differed.

## Governed correction history

The first implementation reached every target but failed the learning gates:
zero intervention reduction, zero changed-world revision and no OOD abstention.
It was rejected.  A hand-authored prior briefly demonstrated the desired
mechanism but was replaced before final acceptance.  The final procedure learns
its prior solely from source-disjoint development outcomes and stops when the
operationally relevant gain/delay family is resolved, without pretending that
weakly identifiable drag is known exactly.

## Sealed results

| Measure | Result |
|---|---:|
| Development worlds used to induce prior | 32 |
| Sealed worlds | 24 |
| Dynamics families | 3 |
| Goal success | 100% |
| Weakest-family success | 100% |
| Cold-control goal success | 100% |
| Mean diagnostic probes | 3.625 |
| Cold-control probes | 6.625 |
| Probe reduction | 45.28% |
| Hidden actuator changes | 4 |
| Changed-world revision | 75% |
| Prediction-before-action commitments | 273 |
| Out-of-family abstention | Passed |
| Unsafe physical actions | 0 |
| Restart relearning | 0 |

## Interpretation

This is the first AION arena in which learned experience measurably changes
physical investigation and action through a complete pixel-to-outcome loop.
The cold learner ultimately controls the same systems, but requires almost twice
as many diagnostic interventions.  The improvement is therefore efficiency of
learning rather than an easier success criterion.

## Claim boundary

The authority is independently separated in software but remains
development-authored.  The systems are bounded one-dimensional dynamics with a
finite action set and candidate family.  This does not establish robotics,
unrestricted embodiment, real-world safety, independent physical certification
or AGI.  A historical claim requires the same result on evaluator-owned devices
or simulators whose dynamics, tasks and outcomes were unavailable during
development.

