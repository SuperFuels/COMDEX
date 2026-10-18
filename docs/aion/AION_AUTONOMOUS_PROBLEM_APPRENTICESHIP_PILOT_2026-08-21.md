# AION Autonomous Problem-Apprenticeship Pilot

**Date:** 21 August 2026  
**Status:** PASS  
**Scope:** Deterministic, local, bounded micro-domain pilot

## Purpose

This pilot tests one complete learning loop rather than another isolated AION
subsystem. AION is given a problem requiring an unfamiliar operating rule. It
must identify the missing capability, select a narrowly relevant curriculum,
learn through practice and repair, close the teaching source, pass a different
hidden exam, return to solve the original problem, and reuse the capability
after a process restart.

The chosen micro-domain is the fictional Kestrel-7 drone reserve-energy
standard. Using a fictional standard makes the cold control meaningful: the
answer cannot be recovered from general background knowledge.

## Precommitted flow

1. Present the original Kestrel-7 delivery-safety problem.
2. Diagnose the smallest missing subject from four candidate subject families.
3. Select a local tutor packet without revealing the original answer or hidden
   exam.
4. Attempt two practice cases with an intentionally incomplete first method.
5. Use independently scored failures to repair the method.
6. Persist only a compact functional procedure capsule, not the source prose or
   practice answers.
7. Close the source and take a source-disjoint hidden exam.
8. Solve the original mission without reopening the source.
9. Restart the process and solve a further novel transfer case with zero
   relearning actions.
10. Compare against cold, no-memory, and no-repair controls.

## Result

The pilot passed every gate.

- AION selected `drone_energy_reserve_planning` with a diagnostic score of 8;
  all three irrelevant subjects scored 0.
- It rejected the unnecessarily broad curriculum “learn everything about
  drones” and requested the minimum mission-relevant capability.
- The incomplete first method failed both practice cases.
- The repair correctly added payload energy and the fractional-reserve branch.
- Both practice cases then passed.
- The teaching source was closed before evaluation.
- The different hidden case passed with no source access and zero relearning.
- The original mission was then solved with no source access and zero
  relearning.
- A new transfer case passed after a process restart, again with zero
  relearning.
- Cold, no-memory, and no-repair controls all failed.
- A deliberately corrupted learning capsule was rejected rather than used.
- Network calls: 0. Paid API calls: 0. Unsafe actions: 0.

The retained method calculated the hidden case as approximately
\(239.55\,\mathrm{Wh}\) consumed, \(60.45\,\mathrm{Wh}\) remaining, and a
required reserve of \(75\,\mathrm{Wh}\), correctly classifying the mission as
unsafe. It calculated the original case as \(255\,\mathrm{Wh}\) consumed,
\(245\,\mathrm{Wh}\) remaining, and a \(100\,\mathrm{Wh}\) reserve, correctly
classifying it as safe.

## What this establishes

The test establishes that the current backend can execute the intended
control-plane sequence:

\[
\text{problem}
\rightarrow \text{capability diagnosis}
\rightarrow \text{targeted curriculum}
\rightarrow \text{practice and repair}
\rightarrow \text{source closure}
\rightarrow \text{hidden transfer exam}
\rightarrow \text{original solution}
\rightarrow \text{retained reuse}.
\]

It also shows that memory and repair are causally necessary within this pilot,
because their matched controls fail.

## Claim boundary

This is not evidence that AION can yet research and learn an arbitrary real
subject by itself. The subject catalogue, tutor packets, mission generator and
independent verifier are engineered. The pilot validates orchestration,
evidence separation, repair, persistence and fail-closed behaviour. It does not
establish unrestricted web research, complete-subject learning, general
intelligence, or permanent mastery of every future problem in a domain.

## Scale-up gate

The next version should preserve this exact evidence architecture while
removing one engineered support at a time:

1. Use two genuinely different subjects rather than one fictional rule set.
2. Require AION to choose and cite externally supplied source documents from a
   larger distractor library.
3. Use separately authored hidden exams and independent evaluators.
4. Re-examine after 1, 7 and 30 days with source access disabled.
5. Add matched full-AION, no-memory, no-repair and cold cohorts.
6. Only after that succeeds, permit bounded live research for a subject not
   represented in the internal catalogue.

## Artifacts

- Implementation: `backend/modules/hexcore/autonomous_problem_apprenticeship_pilot.py`
- Tests: `backend/tests/test_autonomous_problem_apprenticeship_pilot.py`
- Persistent capsule: `backend/modules/hexcore/data/autonomous_problem_apprenticeship_pilot/state.json`
- Machine-readable result: `results/aion_autonomous_problem_apprenticeship_pilot_2026-08-21.json`
