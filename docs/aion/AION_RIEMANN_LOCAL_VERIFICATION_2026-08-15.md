# AION Riemann Programme — Local Verification Report

**Completed:** 15 August 2026  
**Authority:** Lean 4.24.0 kernel and Mathlib v4.32.1  
**Provider/API calls:** 0  
**Result:** PASS

## Outcome

The local authority path is reconciled and the old paid result remains
immutable. The live source generator now imports the Mathlib `Dirichlet`
module required by `riemannZeta_ne_zero_of_one_lt_re`; this was the concrete
environment mismatch behind the earlier unknown-identifier failures.

The exact established baseline, catalogue, and generated theorem templates
compile. A scoped adapter now uses AION's real
`HexCorePersistentLearningRuntime` knowledge store. Only methods accepted by
Lean with a retained source hash can enter it. Proof bodies are not retained.
The clean store contains six active claims, six verified evidence capsules and
zero contradictions.

Compiler failures are routed through an explicit bounded Lean repair record.
Unknown theorem names, syntax errors, type mismatches and unsolved goals receive
distinct routes. A repair-enabled arm gets the record and diagnostic; a
no-repair arm does not.

## Experiment state

- The original packet truthfully records the completed 14 August paid run.
- The timestamped paid result remains unchanged at SHA-256
  `5795e3faa55cf2a7466a3537ac41005056d44711eaa826c84935af318437b2e6`.
- The live harness refuses to load an API key unless an explicitly selected
  packet has `execution_status: ready`.
- The new v2 packet is deliberately blocked at `local_verification_only`.

## V2 held-out set

Six locally kernel-accepted reformulations are frozen across six families:

1. special-value transfer;
2. trivial-zero specialization;
3. non-vanishing contrapositive;
4. analytic prerequisite;
5. right-half-plane positivity;
6. zero-set topology.

Their statement hashes and the pinned environment hash are recorded in
`research/riemann_lab/live_task_packet_v2.json`. Scoring and the no-tie
superiority rule are precommitted. The packet must remain blocked until an
independent sealing review confirms source closure and delayed-retention timing.

## Claim boundary

This work establishes a trusted local experiment path. It establishes neither
an AION advantage nor new RH-relevant mathematics. It does not solve the
Riemann Hypothesis.
