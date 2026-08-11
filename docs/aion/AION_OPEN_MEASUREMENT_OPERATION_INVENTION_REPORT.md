# AION Open Measurement-Operation Invention

## Result

AION invented `ORDERED_REPLICATE_CHANGE_DISCRIMINATOR`, a bounded measurement
that distinguishes transient evidence corruption from durable environmental
change using ordered replicas. Existing diagnostic actions could only request
another observation; they could not interpret the temporal evidence pattern.

Promoted private procedure: `procedure_open_measurement_operation_invention_v1`.

Promoted delayed procedure: `procedure_delayed_measurement_operation_runtime_promotion_v1`.

## Rejection-driven design

Three challengers were rejected: latest-snapshot-wins confused transient
corruption with change; unordered replica median erased temporal direction; and
exact equality rejected bounded numerical noise. The retained operation compares
an old observation with two later replicas under bounded relative tolerance.
It reports `TRANSIENT_EVIDENCE_DEFECT`, `DURABLE_ENVIRONMENT_CHANGE`,
`STABLE_REPLICAS`, or `ABSTAIN` for mixed/OOD patterns.

## Results

| Measure | Result |
|---|---:|
| New private measurements | 1 |
| Candidate implementations | 4 |
| Semantic properties | 6/6 |
| Development success | 1/1 |
| Source-disjoint transfers | 3/3 |
| Public authority families | 4 |
| Mixed/OOD abstention | 4/4 |
| Later public confirmations | 4/4 |
| Cold-runtime classifications | 4/4 |
| Hostile measurements rejected | 8/8 |
| Previous diagnostic mean actions | 2.25 |
| New diagnostic mean actions | 1.75 |
| Additional diagnostic reduction | 22.22% |
| Premature installation | 0 |
| Ambient authority added | 0 |
| Unsafe actions/live writes | 0 |

The four authorities were World Bank GDP, FRED GDP, NOAA temperature and U.S.
Treasury exchange rates, spanning 66, 318, 236 and 100 values. Every authority
correctly distinguished transient, durable and stable cases and abstained on a
mixed pattern.

## Delayed promotion

The exact digest
`dd720aaf3b8c0ee0b40fe3e3b32557f5cee6256ecb079cdb12a521a45c4684be`
was precommitted while the measurement runtime registry remained absent. Four
later public re-executions reproduced transient, durable and mixed/OOD
semantics, promoting
`procedure_delayed_measurement_operation_runtime_promotion_v1`. The public
payloads remained stable, establishing delayed retained execution rather than
external change. A fresh runtime verified the digest and reproduced all four
classification modes without private invention state.

## Boundary

The replica interventions, tolerance grammar and public series remain
engineered. This is bounded measurement invention, not unrestricted sensing.
The next boundary is open latent diagnostic ontology invention: AION must
discover new failure-origin concepts when observed signatures cannot be
represented by candidate, evidence, environment or critic categories.
