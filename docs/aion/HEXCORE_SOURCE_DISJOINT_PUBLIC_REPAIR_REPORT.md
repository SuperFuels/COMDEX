# HexCore Source-Disjoint Public Repository Repair

**Date:** 31 July 2026  
**Status:** Bounded public-benchmark pilot passed and retained

## Objective

The preceding natural-repair work used authentic COMDEX Git history. This
successor tested whether the same governed chain could operate at original
base revisions from repositories that did not participate in AION
development.

The pilot used three public tasks from the SWE-bench Lite development split:

1. Marshmallow: nested `DateTime` fields lost the root schema format;
2. pydicom: invalid raw data escaped the requested suppression boundary;
3. pvlib: a refractive-index singularity produced invalid values and lost
   container-type guarantees.

The task issue and base revision were available during search. The official
repair patch and test metadata were not opened until one candidate had passed
AION's constructed behavioral checks.

No target file was supplied to the localization path. AION ranked Python files
from traceback filenames, module/function references, class--method pairs and
source-symbol matches. The correct repair file ranked first in all three
repositories; the known target paths were used only for scoring afterward.

A fourth held-out issue then tested experience transfer. The narrow
exception-boundary principle learned from pydicom was applied to a different
Marshmallow failure. The same successful repair required three attempts under
cold ordering and one under the retained outcome prior.

## Architecture

```text
public issue + authentic base revision
→ source/contract localization
→ generic repair-operator instantiation
→ self-constructed behavioral checks
→ fresh private sandbox per candidate
→ reject counterexamples
→ select one repair or abstain
→ reveal official patch/test metadata
→ verify affected path and official behavior
→ HexCore/CAU retention
```

Every candidate ran in a temporary copy without `.git` history. The three
read-only base worktrees were hashed before and after the experiment.

## Results

| Measure | Result |
|---|---:|
| Source-disjoint repositories | 3 |
| Authentic public issue revisions | 3 |
| Base-commit integrity | 100% |
| Fault-localization top-1 accuracy | 100% |
| Repair success | 100% |
| Weakest-repository success | 100% |
| Hidden behavioral verification | 100% |
| Incorrect candidates rejected | 6 |
| Held-out operator transfer | Passed |
| Transfer attempts, cold | 3 |
| Transfer attempts, retained prior | 1 |
| Transfer attempt reduction | 66.67% |
| Live repository writes | 0 |
| Unsafe acceptances | 0 |
| Restart relearning | 0 |

Selected repair abstractions:

- bind a nested field to its root schema contract;
- expand suppression to cover lazy value materialization;
- guard a numerical singularity while preserving array and Series behavior.

The retained champion is:

```text
procedure_source_disjoint_swebench_repair_2f2e871e3879
```

The failed first run is intentionally retained in the outcome ledger. It
exposed an evaluation-environment error: converting all warnings to exceptions
changed the behavior of two old repository revisions. The corrected evaluator
isolated numerical-warning checks to the pvlib property that required them.
This is evaluator criticism, not a hidden relaxation of the repair gates.

All three primary families required three cold attempts. The outcome-led
curriculum therefore retained all three as tied weaknesses and selected one
shared next objective: replace the task-family candidate menus with open patch
generation. Future source-disjoint hidden tasks—not this learner—remain the
evaluation authority.

## Persistence

HexCore retained:

- the public task and base-revision provenance;
- all rejected repair attempts and their failed checks;
- the selected repair abstraction and source hash;
- the official patch and test-patch commitments;
- the held-out transfer outcome and attempt accounting;
- the outcome-selected open-generation curriculum;
- the promoted procedure and complete outcome sessions.

The champion, all three patch abstractions and the successful session survived
runtime reconstruction with zero relearning.

## Claim boundary

This is a stronger development result than the earlier single-repository
history because the repositories and issue structures are source-disjoint.
However:

- SWE-bench Lite is public and may be present in model training data;
- only three primary and one held-out development task were selected;
- the file ranker, repair-operator families and behavioral-check generators
  remain bounded;
- the full containerized SWE-bench harness was not run;
- no independent organization administered the tasks.

Therefore this result establishes bounded source-disjoint repair transfer. It
does not establish contamination-proof external performance, unrestricted
software engineering or AGI.

## Next gate

The next repair evaluation must be independently authored or held out:

1. at least ten failures across five unrelated repositories;
2. at least three implementation languages;
3. no task-family-specific repair menu;
4. evaluator-controlled hidden tests and human repairs;
5. matched budgets against a frontier coding agent and the same language
   substrate without HexCore memory;
6. explicit abstention, cost, weakest-family and unsafe-side-effect reporting.
