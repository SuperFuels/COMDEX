# AION Autonomous Mastery Curriculum Supervisor

## Result

Promoted procedure:

`procedure_autonomous_mastery_curriculum_supervisor_v1`

A persistent North-Star-driven curriculum service is now operational. It runs
independently of a manually launched benchmark and repeatedly performs:

```text
reconstruct evidence-backed mastery map
  -> select highest-value unresolved subject
  -> consult cached proposal-only teacher
  -> commit a learning contract
  -> locate independent examiner and executor
  -> execute when grounded, otherwise request executor acquisition
  -> schedule fresh elapsed retention
  -> continue into depth and cross-subject transfer
```

The service is registered with AION Heartbeat and is currently active as
`aion_mastery_curriculum_service.py`.

## Initial autonomous operation

The supervisor imported the existing bounded Python Core certificate and
scheduled a fresh delayed retention assessment with solution replay forbidden.
It then selected the first three unresolved subjects directly from the North
Star priority portfolio:

1. social and commonsense intelligence;
2. biology and medicine; and
3. chemistry and materials.

It consulted the installed `gemma3:1b` teacher for each subject. Teacher prompts
contained no exam answers, and the resulting curricula remain proposals only.

The supervisor did not call these subjects learned. Social intelligence needs
independent multi-rater judgment and legitimate disagreement; biology and
chemistry need official evidence plus independently withheld observations or
safe controlled outcomes. No verified executor currently satisfies these
contracts. The supervisor therefore opened three persistent executor-acquisition
requests instead of generating false certificates.

## Exhaustion behaviour

The programme has no finite-list completion shortcut. Its modes are:

1. **Breadth:** address target-level gaps in the North Star portfolio.
2. **Depth:** revisit every non-mastered subject using new authorities and harder
   unfamiliar work.
3. **Retention:** issue fresh delayed tests whenever certificates become stale.
4. **Cross-subject transfer:** require a method learned in one subject to improve
   learning in another.
5. **Executor acquisition:** invent or acquire the tool and examiner needed when
   a learning contract cannot yet be executed.

Consequently, exhausting the first subject list changes the curriculum mode; it
does not cause the apprentice to stop or declare itself complete. A new subject
or specialisation must still be justified by the constitutional purpose, an
observed capability gap, a recurring failure, a project requirement or a
transfer opportunity. Teacher novelty alone cannot add durable knowledge.

## Initial metrics

| Measure | Result |
|---|---:|
| Autonomous curriculum cycles | 3 |
| Live teacher consultations | 3 |
| Completed bounded certificates imported | 1 |
| Fresh delayed retention tests scheduled | 1 |
| Executor-acquisition requests | 3 |
| Owner-supplied lesson steps | 0 |
| Unsafe actions | 0 |
| Objective mutation | 0 |
| Focused integrated tests | 13/13 |

## Claim boundary

The curriculum supervisor, teacher consultation, contract compilation, delayed
retest scheduling and fail-closed acquisition outbox are operational. Arbitrary
subject executors are not. Python has one bounded executable cycle; the new
social, biology and chemistry curricula are awaiting trustworthy practical
authorities. This promotes continuous curriculum governance, not completion of
those subjects, autonomous general apprenticeship or AGI.

The next decisive engineering task is an Executor Acquisition Worker that
consumes the outbox, finds or constructs safe learning environments, proves
that their tests measure the intended competence, and returns verified executor
contracts to the supervisor. That worker must support partial progression:
knowledge may advance from authoritative documents while practical mastery
remains explicitly unearned.

