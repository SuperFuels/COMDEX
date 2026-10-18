# AION trusted Riemann laboratory

This is an isolated, minimal laboratory for testing whether AION can acquire,
repair and retain formally verified mathematics relevant to the Riemann
Hypothesis (RH).

## What counts

- A Lean file accepted by the pinned Lean kernel and Mathlib dependency.
- A source-closed reconstruction whose inputs and proof hashes are recorded.
- A failed proof repaired into a kernel-accepted proof, with the failed and
  repaired candidates retained in the evidence record.

## What does not count

- Numerical agreement, plots or floating-point zero searches as proof.
- A model's confidence or prose explanation.
- Project-declared axioms, placeholders or admitted proof obligations.
- Reproduction of an established theorem as new progress on RH.
- Any self-awarded success without Lean's return code and evidence hashes.

Mathlib and Lean are the declared trusted base. The local policy prohibits the
laboratory from adding new axioms or incomplete proof placeholders.

## Trusted smoke test

The baseline reproduces three established facts: zeta at zero, the trivial
zeros, and non-vanishing in the half-plane with real part greater than one.
The local harness then feeds four arms fixed proof strings on the same statement:

1. proposer alone;
2. AION with verified memory and repair;
3. AION without memory;
4. AION without repair.

This is deliberately only a plumbing test. It proves that Lean rejects an
invalid candidate, accepts a valid candidate and that the evidence record is
fail-closed. Because the candidates are fixed fixtures, it does **not** measure
AION, proposer quality, memory advantage, repair advantage or retention.

## Sealed live examination

`live_task_packet.json` defines the matched experiment. One paid run completed
on 14 August 2026 and its immutable result is referenced in the packet. That
run exercised a live proposer and Lean gate, but its memory and repair labels
were prompt-level approximations rather than genuine AION mechanisms. It does
not establish an AION advantage. A new sealed experiment must not run until
real AION verified-memory retrieval and governed repair are connected.

The local v2 packet contains six compiler-verified reformulations across six
task families. It is marked `ready` only after the governed local verification and machine seal; the live
harness refuses to load an API key unless an explicitly selected packet is
marked `ready`. The v2 packet was machine-sealed under the user's explicit
authorization; no independent external review is claimed.

FLINT/Arb numerical certification is intentionally deferred from this minimal
phase. It belongs in a separate certified-zero laboratory and must never be
presented as a proof of RH.

## Run

From the COMDEX repository:

```text
.venv/bin/python scripts/aion_riemann_lab.py
.venv/bin/python scripts/aion_riemann_local_verify.py
```

The result is written below `results/riemann_lab/`.
