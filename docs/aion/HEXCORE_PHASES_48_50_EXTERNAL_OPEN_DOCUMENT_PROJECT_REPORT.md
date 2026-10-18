# AION HexCore Phases 48–50 — External Evaluation, Open Documents, and Autonomous Knowledge Projects

**Date:** 30 July 2026
**Status:** Bounded V1 implementations completed and promoted.

## Purpose

These phases test whether the Phase 47 dual-process architecture survives
outside its internally authored procedure-paraphrase benchmark and can be
connected to persistent document knowledge and autonomous project execution.

The invariant authority path remains:

```text
public or open document
  -> frozen Gemma proposal
  -> HexCore compatibility / evidence gate
  -> independent evaluation or executable authority
  -> verified knowledge
  -> persistent project graph
  -> CAU promotion
```

Gemma remains frozen, local, replaceable and proposal-only.

## Phase 48 — Public external-source evaluation

### Evaluation contract

The interfaces and model were frozen before evaluation. The cohort contained
120 examples selected deterministically from held-out validation splits:

- 40 naturally occurring BoolQ yes/no reading questions;
- 40 human-authored AI2 ARC science questions;
- 40 SQuAD 2.0 answerability decisions.

Gold labels were excluded from prompts. The exact source files, revisions and
SHA-256 checksums were recorded. No evaluation example was used for AION
adapter training or prompt demonstrations.

The source licences recorded by their dataset cards are CC BY-SA 3.0 for
BoolQ and CC BY-SA 4.0 for AI2 ARC. SQuAD 2.0 is retained under its existing
project dataset manifest.

### Results

| Measure | Result |
|---|---:|
| Public human-authored cases | 120 |
| Mean frozen-substrate accuracy | **72.50%** |
| Weakest-family accuracy | **62.50%** |
| Chance reference | 41.67% |
| Gain over chance | **+30.83 points** |
| Valid constrained proposals | 100% |
| ARC science accuracy | 82.50% |
| BoolQ accuracy | 62.50% |
| SQuAD answerability accuracy | 72.50% |
| Prompt label leakage | 0 |
| Restart retention | 100% |

Promoted procedure:

`procedure_external_evaluation_8e4881f75523`

### Contamination boundary

This is an external-source, source-split-isolated evaluation, but it is not a
proof of pretrained-model decontamination. The public benchmark items may have
been present in Gemma's unknown pretraining mixture. The result is therefore
useful transfer evidence, not a claim of independently administered or
contamination-proof frontier evaluation.

## Phase 49 — Open-document intelligence V1

### Architecture

Phase 49 reads natural SQuAD 2.0 passages as immutable documents. Each record
stores:

- dataset, revision and validation split;
- title and exact document SHA-256;
- question and presence decision;
- proposed answer or abstention;
- whether the proposed span occurs in the source;
- independent evaluation-authority result;
- accepted answer or rejected/abstained status;
- observation time.

The first single-pass reader was rejected. Although it recovered supported
answers, it abstained correctly on only 5.56% of unanswerable passages and
generated 19 plausible but unsupported spans.

The accepted architecture separates:

1. evidence-presence classification;
2. exact-span proposal, executed only when presence is predicted;
3. independent verification before knowledge commitment;
4. synthesis using verified records only.

### Results

| Measure | Result |
|---|---:|
| Natural documents | 60 |
| Evidence-presence accuracy | **81.67%** |
| Raw exact-answer-or-abstain accuracy | 48.33% |
| Verified answer coverage | **45.24%** |
| Accepted-answer precision | **100%** |
| Unanswerable abstention | **55.56%** |
| Plausible unsupported spans caught before commitment | 19 |
| Unsafe answers committed | **0** |
| Provenance completeness | **100%** |
| Verified two-document syntheses | 9 |
| Restart retention | 100% |

Promoted procedure:

`procedure_open_document_v2_723cbb2ca787`

The low coverage and modest unanswerable abstention are material limitations.
The promotion establishes a conservative verified-knowledge path, not reliable
general reading comprehension.

## Phase 50 — Autonomous knowledge projects V1

### Architecture

Phase 50 consumes only Phase 49 records with independently verified answers.
For each unfamiliar portfolio, AION receives one broad objective:

> Produce an evidence-backed briefing that resolves every supported question,
> discloses missing knowledge, and preserves exact sources.

The runtime then constructs:

- explicit success criteria;
- retrieval-and-verification subgoals;
- a dependency graph terminating in synthesis;
- immutable source citations;
- an evidence-backed final artifact;
- an execution trace and persistent project state.

The process is forcibly restarted after planning and after execution. No live
external side effect is authorized.

### Results

| Measure | Result |
|---|---:|
| Verified knowledge projects | 5 |
| Dynamically constructed subgoal graphs | 100% |
| Project completion | 100% |
| Artifact verification | 100% |
| Citation completeness | 100% |
| Forced restarts | 10 |
| Restart recovery | 100% |
| Unsafe external actions | 0 |

Promoted procedure:

`procedure_autonomous_project_v2_8b874b0cc948`

## Persistent HexCore extensions

The persistent state schema now includes:

- `external_benchmark_evaluations`;
- `open_document_knowledge`;
- `autonomous_knowledge_projects`.

All promoted evaluations, accepted knowledge records, project graphs,
artifacts and champion identifiers survive process reconstruction without
relearning.

## Combined interpretation

The three phases establish a bounded but coherent chain:

```text
public human-authored task
  -> measurable frozen-model transfer
  -> conservative document knowledge acceptance
  -> provenance-bearing multi-document synthesis
  -> autonomous dependency-graph construction
  -> restart-persistent verified project artifact
```

This is a stronger result than another internal simulator because the language
and labels originate in public human-authored datasets. It remains far below
AGI: the external evaluation is small and public, Phase 49 uses an evaluation
oracle to decide which proposals may become benchmark knowledge, and Phase 50
executes short briefing projects over already verified records.

## Next requirements

The next programme should:

1. commission private, independently administered task sets created after the
   model and interface freeze;
2. add natural PDFs, websites, tables and contradictory time-versioned sources;
3. replace benchmark-label verification with evidence entailment, execution,
   proof or qualified human review as appropriate;
4. expand Phase 50 to dozens or hundreds of subgoals, real elapsed time,
   changing local applications and explicit human approval gates;
5. compare the full AION assembly with Gemma-only, frontier-model and agent
   baselines under matched tools, budgets and source access.
