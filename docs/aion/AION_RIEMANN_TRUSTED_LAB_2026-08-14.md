# AION Riemann Trusted Laboratory

**Date:** 14 August 2026  
**Status:** trusted laboratory smoke test implemented; sealed live AION examination prepared but not yet executed

## Purpose

This laboratory gives AION a strict environment for working on established mathematics surrounding the Riemann zeta function. Its purpose is not to invite an unconstrained language model to announce a proof of the Riemann Hypothesis. Every accepted mathematical result must pass an independent Lean 4 and Mathlib kernel check.

The governing loop is:

conjecture or reconstruction -> Lean verification -> diagnosis of failure -> bounded repair -> verified memory -> later source-closed retention test.

## Trusted boundary

The formal authority is Lean 4 with Mathlib. A result is accepted only when the generated theorem compiles in the isolated project without `sorry`, `admit`, project-added axioms, or numerical approximation presented as proof.

The existing factorisation work, visual zeta experiments, heuristic searches, and future FLINT/Arb computations are separate evidence classes. Certified numerical computation may verify bounded regions or support conjecture formation, but it cannot prove the full Riemann Hypothesis.

## Established-mathematics baseline

The smoke test currently verifies three known facts:

1. the value of the Riemann zeta function at zero;
2. the family of trivial zeros at negative even integers;
3. the absence of zeta zeros in the half-plane with real part greater than one.

These are deliberately established results. They verify that the Lean project, imports, theorem statements, candidate files, rejection path, repair path, and evidence recording work correctly.

## Important evidence correction

The original harness supplied fixed proof fixtures to each arm. That is useful for testing infrastructure, but it cannot establish that AION generated a proof, that memory helped, that repair added value, or that knowledge was retained.

The result is therefore classified as a **trusted formal laboratory smoke test**, not an AION intelligence result. Its output explicitly records that neither a live AION executor nor a live proposer was invoked.

## Sealed live examination

The first genuine matched examination is defined in `research/riemann_lab/live_task_packet.json`. It contains four arms:

- proposer alone;
- AION with verified memory and repair;
- AION without memory;
- AION without repair.

All arms must use the same proposer, tools, prompt-visible task statement, token budget, time budget, and maximum of two attempts. The packet publishes theorem statements but contains no proof bodies. Lean is the only pass authority.

The acquisition phase is source-open so AION can reproduce and verify the established material. Sources are then closed before the matched examination. A later delayed examination is required to measure retention independently.

## Claims that are prohibited

Passing the laboratory smoke test or live reconstruction exam does not establish:

- a proof of the Riemann Hypothesis;
- new mathematics;
- consciousness or self-awareness;
- general mathematical superiority;
- memory advantage, unless the matched arms demonstrate it;
- retention, until the delayed source-closed test passes.

## Next execution step

The next implementation must connect a real candidate generator and the governed AION executor to the sealed packet. It must then:

1. run the source-open acquisition phase and store only Lean-verified methods;
2. close the sources and freeze all examination inputs;
3. execute the four matched arms with identical budgets;
4. score exact Lean outcomes, attempts, time, and repair traces;
5. reject any theorem containing forbidden placeholders or new axioms;
6. repeat the protected task after the retention boundary;
7. promote a method only if the evidence shows a genuine advantage over the controls.

Only after AION reliably reconstructs established mathematics under these controls should the programme select a genuine bottleneck lemma from a dependency graph of known RH formulations. Any subsequent claim remains limited to the exact theorem Lean verifies.

## Meaningful success criteria

The first meaningful result would be full AION passing source-closed formal tasks that the same proposer-alone and cold/no-memory controls fail, followed by successful delayed reconstruction without reopening the sources. A stronger result would be a new useful lemma, independently reviewed and Lean-verified, that reduces a recognised dependency in analytic number theory. Neither result has yet been achieved.

