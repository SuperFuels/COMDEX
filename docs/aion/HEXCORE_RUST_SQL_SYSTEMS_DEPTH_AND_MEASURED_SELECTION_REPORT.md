# HexCore Rust/SQL Systems Depth and Measured Technology Selection

## Outcome

AION progressed from one-file Rust and initial SQL construction into a deeper,
governed systems contract. CAU promoted:

`procedure_rust_sql_systems_depth_and_measured_selection_97a48e241cb7`

The retained system passed independent multi-file Rust tests, reversible SQL
migration tests, a matched Rust/Python workload, measurement-grounded technology
selection, malicious-variant rejection and full restart reconstruction.

## Multi-file Rust systems construction

The proposal substrate produced a dependency-free Rust 2021 crate containing a
library and binary. The retained library exposed:

- a public account-store trait;
- a concrete in-memory implementation;
- a structured error enum implementing `Display` and `Error`;
- `Result`-based APIs and optional map lookup;
- shared state using `Arc` and synchronized interior mutability; and
- a cloneable ledger supporting account creation, balance lookup and transfer.

The authority injected its own integration test after construction. The test
required rejection of missing accounts, self-transfers, non-positive values,
insufficient funds and signed overflow. It also ran eight threads performing
4,000 total transfers and required exact conservation of value. Failed
transfers had to preserve both source and destination balances.

The complete crate compiled and tested offline with all warnings treated as
errors. Unsafe Rust, subprocess, filesystem, network, environment-variable and
external-crate variants were rejected before execution.

## SQL lifecycle depth

AION produced three SQLite migrations:

1. V1 created versioning, account and transfer relations, foreign keys, balance
   and owner constraints, positive-transfer and self-transfer rules, and two
   ordered lookup indexes.
2. V2 added a non-null transfer status, an audit relation, a status index and a
   version transition.
3. V2-down removed only V2 artifacts, restored version 1 and preserved V1 data.

The independent evaluator discovered relationship and primary-key columns from
SQLite metadata. It did not require hidden field names or a hidden identifier
type. This mattered because AION independently chose an integer auto-increment
transfer identifier.

The retained migrations passed all fourteen lifecycle checks:

- valid V1 transaction;
- foreign-key, self-transfer and non-positive rejection;
- V2 status, audit and version transition;
- transaction rollback;
- concurrent-writer exclusion and recovery after rollback;
- indexed source/time query plan;
- status removal on downgrade;
- V1 data preservation; and
- version-1 restoration.

Destructive unrelated table removal, foreign-key disabling and extension
loading remained prohibited.

## Measured two-stack bake-off

Rust and Python implementations executed the same checked ledger workload over
20,000 transfer pairs. Both produced the exact expected final state.

| Stack | Build time | Median execution | Source size | Correct |
|---|---:|---:|---:|---:|
| Rust | 0.3009 s | 0.00510 s | 5,254 bytes | Yes |
| Python | 0 s | 0.03062 s | 3,385 bytes | Yes |

AION then received only these measurements. It selected:

- **Rust** for sustained repeated execution because its measured median runtime
  was lower; and
- **Python** for one-shot edit/run iteration because Rust's measured build plus
  run cost exceeded Python's direct execution cost.

Both choices matched the independent consequence rule. Each cited measurements,
provided a rationale and rejected the alternative. This is stronger evidence
than the previous profile-table selection because the choice followed real
artifacts and observed costs.

## Governance and persistence

| Measure | Result |
|---|---:|
| Multi-file Rust depth | Passed |
| SQL migration depth | Passed |
| Matched-stack correctness | Passed |
| Measurement-based choice accuracy | 100% |
| Unsafe Rust variants rejected | 3/3 |
| Unsafe SQL variants rejected | 3/3 |
| Unsafe programs executed | 0 |
| Live repository writes | 0 |
| Restart retention | 100% |
| Focused regression tests | 7/7 |

The generated sources, migration history, measurements, decision policy,
promotion evidence and champion identity survived full runtime reconstruction
without relearning.

## Claim boundary

This is a material depth increase, not complete Rust, SQL or architecture
mastery. The test remains a bounded ledger system with one concurrency model,
one relational engine and two deployment profiles. It does not establish broad
async Rust, lifetimes across unfamiliar libraries, distributed databases,
production operations, general multi-stack architecture or independent hidden
certification.

The next mastery programme should expand by difficulty and transfer, not by
adding languages superficially: unfamiliar multi-module systems, independently
authored requirements, dependency upgrades, performance/security regressions,
delayed maintenance outcomes and hidden repositories. The fifth independent
repository, genuinely conditional semantic-memory router and independent
evaluation gates remain open.
