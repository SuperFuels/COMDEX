# AION HexCore Phases 46–48: Mathematical Operators, Tool Invention and Persistent Projects

**Date:** 30 July 2026

**Status:** Phases 46, 47 and 48 passed their declared sealed gates.

**Authority:** All retained procedures were promoted through HexCore's governed skill path.

## Executive result

This cycle extended AION in three connected directions:

1. It inferred algebraic properties of previously invented predicates and learned compact continuous symbolic operators from observations.
2. It synthesized reusable executable numeric tools in a restricted Photon subset, rejected unsafe candidates and retained only independently verified tools.
3. It executed multi-stage projects across interruption and rule change while preserving unresolved questions, provenance, checkpoints and plan revisions.

These are bounded, inspectable capabilities. They are not unrestricted mathematical discovery, autonomous software engineering, arbitrary real-world project execution or AGI.

## Phase 46 — Algebraic and continuous operator learning

### Architecture

The Phase 46 learner has two paths.

The discrete algebraic path exhaustively evaluates each Phase 45 binary predicate over 27 three-valued assignments. It records symmetry, reflexivity, irreflexivity, transitivity, monotonicity, equivalence status and recursive path soundness.

The continuous path searches a fixed symbolic feature grammar:

- sum;
- product;
- absolute distance;
- squared sum;
- sum of cubes;
- squared distance.

For each world it fits all one- and two-feature supports by least squares and selects a compact explanation with an MDL/BIC-style complexity penalty. Learned operators are tested on 110 unseen continuous points and under recursive composition. External test worlds use a separately coded reference implementation.

### Sealed outcome

| Measure | Result |
|---|---:|
| Phase 45 primitives profiled | 4 |
| Exhaustive law checks complete | 100% |
| Exact support recovery | 92.31% |
| External exact support recovery | 100% |
| Mean validation RMSE | 0.000463 |
| Worst validation RMSE | 0.001228 |
| Mean recursive RMSE | 0.001881 |
| Provenance completeness | 100% |

Promoted procedure:

`procedure_algebraic_continuous_4a0872dae723`

### Important negative result

The experimental model-disagreement policy did **not** reduce observations. Mean active observations were 10.5769, compared with 10.5577 for the random control. The active policy was therefore explicitly rejected:

`REJECTED_NO_EFFICIENCY_GAIN`

Only the algebraic-law and continuous symbolic-model capability was promoted. This separation prevents a successful modelling result from concealing a failed experiment-selection result.

## Phase 47 — Governed Photon tool invention

### Architecture

The tool inventor receives demonstrations of a missing composite operation and searches a bounded candidate library. Candidate programs are represented as `aion.photon.numeric_tool.v1` capsules.

Execution is restricted by two independent controls:

1. `SandboxKernelGuard` rejects known privileged or unsafe patterns.
2. An AST allowlist accepts only numeric constants, declared inputs, bounded arithmetic operators and `abs`, `min` and `max`.

No candidate can import modules, access files, call unrestricted Python, use dynamic evaluation, access a network or promote itself.

The accepted path is:

```text
missing operation
  -> candidate Photon capsules
  -> static safety checks
  -> restricted sandbox execution
  -> development verification
  -> source-disjoint sealed verification
  -> independent external implementation
  -> CAU-governed retention
```

### Invented tools

| Tool | Verified expression |
|---|---|
| Squared separation | `(x - y) ** 2` |
| Coupled flux | `x * y + abs(x - y)` |
| Threshold margin | `max(0.0, x + y - t)` |
| Bounded balance | `min(t, abs(x - y) + x * y)` |

### Sealed outcome

| Measure | Result |
|---|---:|
| Tool families invented | 4 |
| Sealed exact accuracy | 100% |
| External exact accuracy | 100% |
| Weakest-family accuracy | 100% |
| Repeated execution-cost reduction | 71.43% |
| Unsafe probes rejected | 5/5 |
| Provenance completeness | 100% |
| Symbolic fallback accuracy | 100% |
| Restart retention | 100% |

Promoted procedure:

`procedure_governed_tool_invention_852fbd569125`

The 71.43% figure compares a verified one-call retained tool against repeatedly composing its underlying primitive operations. It is not a hardware speed benchmark.

## Phase 48 — Persistent long-horizon project intelligence

### Architecture

Each project is represented as a durable state machine with:

- a decomposed milestone plan;
- completed milestones;
- unresolved questions;
- artifacts and execution receipts;
- active rule provenance;
- plan revisions;
- a chronological trace;
- final verification status.

The sealed projects use six stages:

1. ingest the project brief;
2. establish the governing rule and provenance;
3. invent a reusable decision tool;
4. monitor for an external rule revision;
5. execute the project cases;
6. verify and close.

The runtime is forcibly reconstructed after three milestone boundaries. When the governing rule changes, AION supersedes the old rule, records why the plan changed and revises only the affected future milestones.

### Sealed outcome

| Measure | Result |
|---|---:|
| New sealed projects | 48 |
| Project accuracy | 100% |
| Weakest-domain accuracy | 100% |
| Stateless-control accuracy | 12.5% |
| Accuracy gain | +87.5 points |
| Projects surviving all three restarts | 100% |
| Rule-change revision accuracy | 100% |
| Open questions resolved | 100% |
| Provenance completeness | 100% |
| Restart retention | 100% |

Promoted procedure:

`procedure_long_horizon_project_466318894969`

The low stateless-control score is expected because the control retains the obsolete initial rule. It establishes the value of persistent revision in this benchmark; it is not a comparison with a frontier agent.

## Persistent schema additions

The HexCore persistent store now includes:

- `algebraic_law_models`;
- `continuous_operator_models`;
- `invented_photon_tools`;
- `tool_invention_sessions`;
- `long_horizon_projects`;
- `project_revision_events`.

Every promoted artifact is restart-persistent. Neural or generative providers remain proposal sources only; truth acceptance, execution verification and promotion authority remain outside them.

## Claim boundary

The cycle establishes bounded progress in mathematical abstraction, executable invention and persistent project control. All three environments still supply engineered grammars, interfaces and verification oracles. The next leap must test these mechanisms against natural documents, unfamiliar schemas, richer tools, longer projects, multimodal evidence and independent external tasks.
