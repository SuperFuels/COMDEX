# AION Riemann Programme - Governed Execution Report

**Completed:** 15 August 2026  
**Formal authority:** Lean 4.24.0 kernel with Mathlib v4.32.1  
**Live model:** GPT-4.1, temperature 0  
**Verdict:** mechanism signal observed; precommitted superiority criterion not met; RH remains open

## Executive result

The fresh, source-closed v3 comparison completed with zero infrastructure
failures. Full AION achieved the highest primary score, but passed 3 of 6 tasks
against a precommitted absolute floor of 4. Therefore no AION superiority claim
is supported.

| Arm | Lean-accepted | Model calls | Total tokens |
|---|---:|---:|---:|
| Proposer alone | 0/6 | 12 | 3,043 |
| AION memory + repair | 3/6 | 11 | 8,403 |
| AION without memory | 0/6 | 12 | 6,888 |
| AION without repair | 2/6 | 11 | 6,449 |
| Cold AION, isolated state | 1/6 | 12 | 6,714 |

Full AION exceeded every comparator by at least one task, but the absolute floor
was deliberately conjunctive. The correct interpretation is a promising
operational signal requiring replication, not established superiority.

## What the mechanisms actually contributed

Full AION converted syntax failures into accepted special-value and trivial-zero
proofs and solved the real-axis positivity task on its first attempt. The
no-memory repair arm scored 0/6, while the memory-only/no-repair arm scored 2/6.
The cold isolated-state arm scored 1/6. This pattern suggests that retained
verified method structure contributed materially, while repair added one task
over memory alone in this small packet.

Three failures reveal the next engineering targets:

1. Order-theoretic contradiction diagnostics were classified as unclassified,
   so the strict upper-bound proof was not repaired.
2. The differentiability repair failed to transport the supplied set-membership
   hypothesis into `DifferentiableWithinAt`.
3. Compact-zero repair found relevant library declarations but did not resolve
   the closed-ball type inference required by `isCompact_closedBall`.

These are concrete repair-curriculum targets. They are not new mathematics.

## Protocol integrity and incidents

The first v2 request was rejected with HTTP 401 before model execution because
the process environment contained a stale key. The separately configured
repository credential authenticated successfully. The 401 produced no proof
candidate and no paid comparison.

V2.1 then exposed a protocol defect: a 400-token cap truncated a strict JSON
response during the partial proposer arm. No comparator or AION arm completed,
so no comparative result exists. The incident was frozen, the exposed tasks
were retired, and v3 used fresh tasks, a 1,000-token cap, exception-safe
provider-output scoring, and active-arm checkpoints. No v3 infrastructure
failure occurred.

## Formal mathematics completed

`CriticalStripFoundation.lean` now kernel-checks 17 established zeta facts and
consequences. The most useful new local theorem is:

```lean
theorem zeta_zero_re_lt_one {s : ℂ} (hz : riemannZeta s = 0) : s.re < 1
```

This is a formal reconstruction from Mathlib's closed-half-plane
nonvanishing theorem. It is established mathematics, not a novel RH result.

The critical-strip target is now split cleanly:

- completed: every zeta zero satisfies `Re(s) < 1`;
- precise blocker: prove that every zero with `Re(s) <= 0` belongs to the
  negative-even trivial-zero family;
- consequence once blocked step is reconstructed: every nontrivial zero lies
  in `0 < Re(s) < 1`;
- still open: every nontrivial zero lies on `Re(s) = 1/2`.

## Scale-up completed

The curriculum expanded from six immediate tasks to 36 governed items across
analytic continuation, Dirichlet series, nonvanishing, zero topology,
symmetry, critical-strip reconstruction, and evaluation. Fifteen curriculum
items are kernel-reconstructed, seven are source-closed evaluations, eleven are
queued established reconstructions, and three are frontier statements.

Verified memory contains six active Lean-backed claims, six evidence capsules,
zero contradictions, high-level method patterns, and no retained proof bodies.
Repair now includes deterministic theorem discovery over the pinned local
Mathlib source tree with exact declaration provenance.

## Delayed retention result

The time gate released after 08:00 UTC. All six source-closed tasks and the
pinned environment were locally reverified before a ready copy was sealed.
The paid runner ignored the stale process credential and used the valid
repository credential. Exactly one two-arm comparison was executed.

- AION memory plus repair: **2/6**.
- Isolated cold AION: **3/6**.
- Model calls: **24**; tokens: **15,704** total.
- Infrastructure incidents: **1** incomplete structured provider output. The
  affected task passed on its second attempt, but the incident still counts
  under the precommitted zero-failure rule.

The memory-and-repair arm missed the 4/6 floor, trailed cold AION by one task,
and failed the infrastructure rule. The criterion was not met. This establishes
neither delayed-retention advantage nor AION superiority.

## Evidence

- Completed v3 result SHA-256: `52899a504530456f1c6f90acf28a34edddc54ccbb4ce765d145c2f9166bc951d`
- Sealed v3 packet SHA-256: `1771f8b9977ce0cf1ffac73b1284361e61ae92d4f86672afe97a241a786abb6e`
- Pinned environment SHA-256: `6776200251cfd041ecda62038ae8ff02980bf1066a332289b6c96ca015485591`
- Original immutable v1 result SHA-256: `5795e3faa55cf2a7466a3537ac41005056d44711eaa826c84935af318437b2e6`
- Retention ready packet SHA-256: `2a103a6634f2819e5320f68f4aa20790691d422bbbc26b299082e004b095530a`
- Retention seal SHA-256: `49d8142a93100005fafa01de8bbe2635a9d08be3cf86375c915db19ae8487c57`
- Retention result SHA-256: `875a5248dbc1e4f8d161c71930b78c7bf7839bd94406ff350cd6e47b1f37bcbd`
- Retention one-shot receipt SHA-256: `0d5c959f081bbb74da112dc435abb9809942bc8921940195dad8d9fe7ab19571`

## Truth boundary

This work establishes a reproducible formal laboratory, a clean mechanism
signal, a 17-theorem critical-strip foundation, and a precise next blocker. It
does not establish AION superiority, does not introduce new RH mathematics,
and does not solve the Riemann Hypothesis.
