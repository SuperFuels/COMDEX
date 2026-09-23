# AION HexCore Phase 58 — Open Multimodal Project Intelligence

**Date:** 30 July 2026

## Purpose

Phase 58 removes several pieces of task scaffolding from AION's real-file
project intelligence. AION receives only a broad natural-language objective
and an unfamiliar folder of files. It is not supplied with a workflow, entity
list, dependency graph, transition grammar or expected answer structure.

The system must:

1. discover the available evidence;
2. infer what each source can contribute;
3. invent a bounded evidence schema;
4. construct its own information and verification plan;
5. reconcile evidence expressed in different modalities;
6. detect changed evidence and revise downstream conclusions;
7. abstain when the modalities remain inconsistent; and
8. retain the learned schema, project state and promoted procedure across
   restart.

Phase 58 builds directly on Phase 56 persistent real-file projects and Phase
57 relational world modelling.

## Natural evidence substrate

The development and sealed portfolios used copies of real repository files.
No original source was modified.

The modalities included:

- paginated PDF documents and their rendered page layouts;
- natural PNG charts;
- numerical CSV tables;
- Markdown technical reports;
- YAML governance configuration; and
- executable Python source.

PDF pages were rendered with Poppler and visually inspected during
implementation. This confirmed that the extracted evidence corresponded to
the visible page content rather than only to an assumed text stream.

### Development portfolios

The schema learner observed three disjoint development portfolios:

- a temporal-decay CSV and chart;
- a Page-curve CSV and chart; and
- a governed-software report, configuration and implementation portfolio.

These examples established reusable relation types such as:

```text
numeric table <-> natural chart
document <-> structured configuration
document <-> executable code
structured configuration <-> executable code
```

### Sealed portfolios

Three previously unopened portfolio families were then evaluated:

1. **Financial document:** a 25-page half-year results PDF.
2. **Scientific chart:** a Fourier-spectrum table and natural chart, followed
   by a checksum-visible table revision.
3. **Software architecture:** a GlyphOS architecture PDF, current governance
   configuration and executable HexCore memory implementation.

## Open-goal contract

Each portfolio exposed only:

- a broad objective;
- a folder containing the available files; and
- the fixed information and action budget.

The expected family, answer and correctness rule remained verifier-side.
AION's generated schema explicitly records:

```text
supplied_workflow           = false
supplied_entity_list        = false
supplied_dependency_graph   = false
supplied_transition_grammar = false
```

## Schema and plan invention

Source discovery produces checksum-grounded evidence capsules. Depending on
the observed portfolio, AION invents fields including:

- reported claims and exact page locations;
- numerical series and visual series;
- document revisions;
- configured authority;
- executable controls; and
- implemented symbols.

It then proposes relations between compatible evidence types and constructs a
goal graph containing:

```text
discover sources
  -> identify relevant evidence fields
  -> compare mutually informative modalities
  -> detect contradictions or revisions
  -> preserve exact evidence
  -> independently recompute the conclusion
  -> accept, revise or abstain
```

The schema and plan are persisted before execution. A forced runtime
reconstruction occurs at that checkpoint, after which the project resumes
without regenerating either structure.

## Cross-modal reasoning outcomes

### Financial PDF

AION recovered exact, location-bound evidence:

| Measure | Current period | Prior period | Reported change |
|---|---:|---:|---:|
| Revenue | £798.4m | £898.0m | -11.1% |
| Operating profit | £2.1m | £28.4m | -92.5% |

It independently compared the current and prior figures and concluded that
both declined. The figures remain marked as reported source values; the
comparison is the independently verified conclusion.

### Fourier table and chart

The copied CSV was changed after the draft checkpoint. AION detected the new
SHA-256 value, reopened the affected evidence relation and found that the
table did not provide enough compatible series to support the three plotted
visual traces.

It recorded:

```text
insufficient_cross_modal_series
numeric_visual_rank_mismatch
```

and abstained instead of forcing consistency.

### GlyphOS architecture

AION separated claims describing present architecture from future
aspirations. Present memory-related claims were accepted only where the
current implementation corroborated the relevant term. Claims about future
quantum-symbolic reasoning, integrated vault encryption and bidirectional
scroll-to-glyph learning remained unverified.

This prevented an architectural aspiration from being silently converted
into present knowledge.

## Independent verification and cold control

The evaluation path recomputed the expected result directly from the sealed
files. It did not accept the project system's own confidence as proof.

The matched cold control received the same files and tools but no learned
cross-modal relation model. It used exhaustive comparisons and could not
safely resolve two of the three unfamiliar portfolios.

## Sealed results

| Measure | Result |
|---|---:|
| Development portfolios | 3 |
| Sealed portfolios | 3 |
| Natural evidence kinds | 5 |
| Project completion | 100% |
| Weakest-family accuracy | 100% |
| Accuracy gain over cold control | +66.67 points |
| Schema invention | 100% |
| Goal-graph construction | 100% |
| Provenance completeness | 100% |
| Changed-evidence detection | 100% |
| Contradiction handling | 100% |
| Unsafe knowledge commitments | 0 |
| Restart recovery | 100% |
| Learned information actions | 8 |
| Cold information actions | 10 |
| Information-action reduction | 20.00% |
| Original repository files modified | 0 |

## Persistent architecture

HexCore now persists:

- `open_multimodal_projects`;
- `multimodal_schema_models`;
- `multimodal_project_outcomes`;
- source hashes and exact evidence locations;
- invented fields and relations;
- generated project plans;
- pre- and post-revision schemas;
- contradiction and abstention records;
- independent-verification outcomes; and
- the promoted procedure lineage.

Restart validation found:

| Persistence check | Result |
|---|---:|
| Learned schema retained | Passed |
| All sealed projects retained | Passed |
| Champion retained | Passed |
| Projects relearned after restart | 0 |

## Promotion

CAU promoted:

`procedure_open_multimodal_projects_3cbe82ceb6c9`

The operational chain is:

```text
broad goal + unfamiliar natural files
  -> modality discovery
  -> schema invention
  -> goal and verification graph
  -> cross-modal evidence binding
  -> change and contradiction detection
  -> independent recomputation
  -> accept, revise or abstain
  -> CAU-governed persistence
```

The complete HexCore history passes **63/63** regression tests.

## Interpretation

Phase 58 is a meaningful integration result. AION no longer requires a
predeclared workflow for these portfolios. It can discover a mixture of
natural and structured evidence, decide which relationships must be checked,
construct a verification plan, revise that plan after a source changes and
avoid accepting a plausible but unsupported cross-modal conclusion.

The result connects open-goal project execution, multimodal grounding,
provenance, contradiction handling, world-model revision and restart
persistence in one governed path.

## Claim boundary

The result remains bounded and should not be described as unrestricted
multimodal intelligence:

- the file parsers and low-level visual feature extractors were engineered;
- the candidate semantic features were bounded;
- portfolio selection and the mid-project revision controller were internal;
- the independent correctness oracle was implemented by the development
  team;
- natural photographs, audio and video were not evaluated;
- the sealed set contains only three portfolios;
- software corroboration currently uses conservative term-level grounding,
  not complete semantic proof of an implementation; and
- this is not external certification or AGI.

The important advance is removal of workflow and schema scaffolding while
preserving verification and authority boundaries.

## Next development

The next high-value stage should connect these open multimodal projects to
real outcome learning. AION should:

- construct projects from larger, source-disjoint portfolios;
- observe delayed real or independently executed outcomes;
- distinguish perception, interpretation, planning and execution failures;
- revise its invented schemas and tools from those failures;
- test learned revisions on unrelated portfolios;
- retain only improvements that survive weakest-family, forgetting,
  provenance and CAU gates; and
- submit the integrated system to the frozen blind external-evaluation
  protocol.

That would test whether multimodal project experience produces transferable
improvement rather than only successful completion of three engineered
portfolios.
