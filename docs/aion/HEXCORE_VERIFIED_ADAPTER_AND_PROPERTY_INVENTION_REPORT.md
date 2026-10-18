# HexCore Verified Adapter Acquisition and Property Invention

## Outcome

The separation of execution grounding from falsification intent removed the
previous one-of-three executable-verification ceiling on the existing public
repository cohort.

Two governed procedures were promoted:

- `procedure_verified_execution_adapter_acquisition_4b5bdc4a2a7e`
- `procedure_adapter_grounded_property_invention_60fe24a6e28a`

## Verified execution-adapter acquisition

For each repository, AION received only the public issue, original target file
and public in-tree test excerpts. It generated a minimal program that bound
`AION_TARGET` to the genuine target module, class or callable. An independent
suffix recovered the target object's source path and required an exact match to
the declared repository file. A fabricated success marker or substitute symbol
therefore could not pass.

Marshmallow and pydicom were acquired on the first attempt. Pvlib initially
entered unrelated package initialization and then used an invalid `__file__`
assumption. From those two execution traces it learned a minimal isolated loader
for `pvlib.tools` and `pvlib.iam`. The original acquisition session therefore
used five attempts and two revisions. A deterministic verification replay then
confirmed all three retained adapters in three attempts.

| Measure | Result |
|---|---:|
| Repositories | 3 |
| Verified adapters | 3/3 |
| Weakest-repository success | 100% |
| Source-path attestation | 100% |
| Initial acquisition attempts | 5 |
| Trace-driven revisions | 2 |
| Unsafe programs executed | 0 |
| Timeouts | 0 |
| Live writes | 0 |
| Restart retention | 100% |

## Adapter-grounded property invention

Once target reachability was independently established, AION generated
functional and adversarial properties inside the verified adapters. Presentation
wrappers were normalized and all discovered `test_*` or `property_*` functions
were executed automatically; neither operation changed assertion semantics.

The complete causal gate was:

1. the generated functional program must fail on the original checkout;
2. the same program must pass on the selected repaired checkout;
3. the generated adversarial program must pass the repaired checkout;
4. both programs and the selected patch must pass static security audits;
5. no hidden verifier test or historical human patch may enter generation.

| Measure | Result |
|---|---:|
| End-to-end repository success | 3/3 (100%) |
| Weakest-repository success | 100% |
| Original buggy checkouts rejected | 3/3 |
| Repaired checkouts accepted | 3/3 |
| Adversarial suites accepted | 3/3 |
| Property attempts | 6 |
| Unsafe programs executed | 0 |
| Timeouts | 0 |
| Live writes | 0 |
| Restart relearning | 0 |

Outcome criticism made substantive corrections rather than weakening the gate:

- Marshmallow removed an over-specific nested-container shape assumption while
  retaining binding, round-trip, isolation and explicit-format invariants.
- Pydicom learned to construct a raw invalid `IS` element that materializes
  during `to_json_dict`, thereby making the original failure observable while
  verifying selective omission, non-mutation and determinism.
- Pvlib used the isolated adapter and removed a contradictory test that had
  asserted the original buggy behavior; the retained properties require finite
  zero output beyond grazing incidence, reference-value preservation,
  boundedness, NaN propagation and index stability.

## What changed architecturally

The operational chain is now:

```text
public issue + source + in-tree tests
  -> private execution-adapter proposal
  -> exact source-path attestation
  -> property and counterexample proposal
  -> static safety audit
  -> original-fail / candidate-pass execution
  -> adversarial candidate execution
  -> CAU promotion or rejection
  -> restart-persistent adapter and property memory
```

This establishes that environment contact and behavioral criticism can be
learned and recomposed as separate governed skills. It is a stronger result
than generating plausible test descriptions or executing tests inside a
development-authored harness.

## Remaining scale gate

The result remains bounded to three public Python repositories and selected
development repairs. The next strong claim still requires:

- at least five unrelated repositories and three programming languages;
- repeated-seed stability;
- explicit malicious-candidate rejection, not only adversarial boundary tests;
- conditional semantic routing that beats both always-memory and never-memory;
- independently administered hidden failures, tests and matched controls.

No result here constitutes general autonomous software engineering or AGI.
