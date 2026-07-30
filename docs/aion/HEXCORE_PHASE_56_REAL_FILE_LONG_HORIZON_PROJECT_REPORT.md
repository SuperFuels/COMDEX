# AION HexCore Phase 56 — Real-File Long-Horizon Project Intelligence

**Date:** 30 July 2026

## Purpose

Phase 56 tests whether AION can carry a project across multiple persistent
milestones while its real source files change. It strengthens the earlier
Phase 48 numeric project simulator by operating on actual repository result
files and technical reports.

The capability contract requires AION to:

1. bind a project goal to checksum-addressed real files;
2. construct and persist an explicit task dependency graph;
3. preserve source evidence and reported-versus-verified status;
4. checkpoint and recover after interruption at every milestone;
5. notice a source revision after a draft has already been produced;
6. invalidate only the work that depends on the changed source;
7. reconcile the revision or abstain when it remains contradictory; and
8. pass an independent verifier that rereads the current files from disk.

## Evaluation design

### Development projects

The development cohort used the real outputs and reports from Phases 48–52:

- external evaluation;
- open-document intelligence;
- autonomous project decomposition;
- general tool invention; and
- continual multi-track self-improvement.

### Sealed projects

The unchanged evaluation path was then run on the source-disjoint Phase 53–55
families:

- blind external evaluation;
- open-world ingestion; and
- recursive Photon synthesis.

Each project used two real source files: the authoritative JSON result and the
associated Markdown technical report. The original repository files were
read-only. All controlled revision tests were performed on isolated copies.

### Revision and negative control

After AION created and persisted its draft status manifest, the sealed file
controller amended the copied result file. The amendment was not present when
the draft was produced. AION had to discover the new checksum, supersede the
stale draft and rebuild the dependent status record.

The Phase 55 project was an explicit unresolved-conflict control. Correct
behaviour was abstention, not forced completion.

### Independent verification

The final verifier does not trust AION's stored manifest. It independently
rereads both current files and checks:

- phase identity;
- current projected status;
- current result and report hashes;
- exact recovery of cited report evidence;
- recorded source-revision detection; and
- absence of unresolved questions.

This verifier remains internally implemented. It is stronger than self-review,
but it is not a substitute for the externally administered Phase 62 protocol.

## Persistent architecture

Each `real_file_projects` session contains:

- project goal and family;
- milestone plan;
- explicit dependency graph;
- current source snapshots;
- exact evidence positions;
- unresolved questions;
- invalidated and rerun tasks;
- draft and final manifests;
- restart count;
- independent verification record; and
- an append-only trace of revision and closure decisions.

Every milestone is committed through the HexCore persistent store and CAU
authority boundary. The benchmark reconstructs the runtime after every
milestone, producing six forced restart recoveries per sealed project.

Source changes are also written to the persistent `project_revision_events`
ledger. The promoted procedure depends explicitly on the Phase 54 ingestion
champion and the frozen Phase 53 evaluation contract.

## Selective invalidation

The project graph contains seven logical tasks. When the authoritative result
changes, AION preserves independent registration and report-ingestion work,
then invalidates:

1. result-status extraction;
2. report-evidence binding;
3. manifest synthesis;
4. independent verification; and
5. project closure.

This produces five targeted reruns rather than seven stateless full-replay
tasks:

```text
re-execution reduction = 1 - (5 / 7) = 28.57%
```

The purpose is not the size of this bounded saving. It establishes that AION
can reason over a persistent dependency graph and revise only the consequences
of changed knowledge.

## Sealed results

| Measure | Result |
|---|---:|
| Sealed projects | 3 |
| Real sealed source files | 6 |
| Project outcome accuracy | 100% |
| Weakest-family accuracy | 100% |
| Accepted-manifest accuracy | 100% |
| Source-change detection | 100% |
| Restart recovery | 100% |
| Provenance completeness | 100% |
| Conflict-control safe abstention | Passed |
| Mean dependency-aware reruns | 5.0 |
| Stateless full-replay tasks | 7.0 |
| Re-execution reduction | 28.57% |
| Original repository files modified | 0 |

## Promotion

CAU promoted:

`procedure_real_file_projects_3aff718b5c0d`

The procedure performs:

```text
checksum-bound source ingestion
  -> persistent dependency graph
  -> checkpointed draft
  -> external revision detection
  -> selective invalidation
  -> reconciliation or abstention
  -> independent disk reread
  -> CAU-governed retention
```

Restart verification confirmed:

- every development and sealed project was retained;
- every revision event was retained;
- the promoted champion was retained; and
- zero projects required relearning.

## Interpretation

This is the first HexCore phase to combine real-file ingestion, persistent
project execution, interruption recovery, source-change monitoring,
dependency-aware revision, conflict abstention and independent final
verification in one governed loop.

In plain English, AION can now begin a file-backed project, remember exactly
where it reached, wake up after interruption, notice that its evidence has
changed, identify which conclusions became stale, redo only the affected work,
and refuse to finish when the new evidence cannot be reconciled.

## Claim boundary

Phase 56 remains bounded:

- the broad project objective and task schema were engineered;
- the file-revision controller was implemented by the benchmark;
- the files were local repository artifacts, not arbitrary applications or
  changing web sources;
- project horizons were seven milestones rather than days or months;
- correctness was machine-checkable; and
- the independent verifier was internally implemented.

It does not demonstrate unrestricted autonomous project management, reliable
understanding of arbitrary files, real organizational authority, or
externally certified general intelligence.

## Next development

Phase 57 should use this persistent project substrate to learn richer world
models from event streams attached to real files. The next learner should:

- infer typed entities, events and state transitions from heterogeneous
  records;
- distinguish observation, action, consequence and background condition;
- construct competing relational/dynamic models rather than use a supplied
  transition schema;
- predict withheld future events;
- identify when no current model explains a revision;
- preserve uncertainty and provenance; and
- expose its predictions to the same independent and CAU-governed checks.

Phase 58 can then connect those learned dynamics to natural multimodal
evidence rather than synthetic modality contracts.
