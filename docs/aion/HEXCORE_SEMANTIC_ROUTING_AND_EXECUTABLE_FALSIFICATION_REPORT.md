# HexCore Governed Semantic Routing and Executable Falsification

## Outcome

This cycle implemented an outcome-governed semantic-memory router and
model-generated functional and adversarial test programs executed in fresh
repository sandboxes. Neither challenger was promoted. The router reproduced
the retained documentation-memory policy but did not beat it, while executable
test invention demonstrated real falsification signal without reliable
repository-specific execution grounding.

## Governed semantic-memory router

The router compared source/issue-only context, documentation ontology memory,
and expanded source/test/call-site memory. Unsafe or capability-regressing arms
were ineligible; among safe arms, it selected the lowest-cost policy and kept
no-memory fallback available.

| Measure | Result |
|---|---:|
| Outcome rows | 9 |
| Context routes | 3 |
| Repositories | 3 |
| Routed repair success | 100% |
| Weakest-repository success | 100% |
| Routed attempts | 4 |
| Never-memory attempts | 5 |
| Always-documentation attempts | 4 |
| Unsafe acceptances | 0 |

The selected route was documentation memory. It beat never-memory but tied the
always-documentation champion, and repository diversity was below the
predeclared five-repository floor. CAU therefore rejected
`procedure_governed_semantic_memory_router_4e76e58498a8`. Wrapping a fixed
winning policy in routing logic is not counted as learned routing.

## Executable falsification invention

For each accepted documentation-guided repair, the proposal substrate generated
two standalone Python programs without access to the historical human patch or
hidden verifier tests: a functional falsifier required to fail on the original
checkout and pass on the selected repair, and an adversarial program required
to exercise at least two relevant boundary or security properties.

An AST audit prohibited network access, subprocess creation, dynamic execution,
repository writes, permission changes and verification bypass. Programs ran in
separate working trees under process timeouts and resource limits.

| Measure | First pass | One criticism round |
|---|---:|---:|
| Original buggy checkouts rejected | 3/3 | 3/3 |
| Selected repairs accepted | 1/3 | 1/3 |
| Adversarial programs accepted | 1/3 | 1/3 |
| End-to-end repository success | 33.33% | 33.33% |
| Unsafe programs executed | 0 | 0 |
| Timeouts | 0 | 0 |
| Live repository writes | 0 | 0 |

All three generated functional programs rejected the corresponding original
buggy checkout. The missing capability was execution grounding. The pydicom
fixture did not activate the intended lazy-materialisation path; pvlib entered
an unrelated NumPy incompatibility during package import before reaching the
target function. One trace-only criticism round diagnosed both failures
accurately but did not generate valid corrected harnesses.

CAU rejected both
`procedure_executable_falsification_invention_76dbafce2714` and
`procedure_revised_executable_falsification_e4d6d473c3db`. Their programs and
outcome traces remain research memory, not promoted skills.

## Architectural conclusion

Test intent and execution grounding must be separated. AION should invent
properties and counterexamples, while a governed learnable library supplies or
acquires verified environment adapters for package loading, lazy data
construction, compilers, runtimes and test frameworks. Adapter acquisition must
come from public repository evidence and successful execution, never hidden
answers.

The next software gate has four coupled parts:

1. acquire or invent a minimal execution adapter and prove it reaches the target
   symbol without unrelated failure;
2. generate functional and adversarial properties inside that adapter;
3. require original-fail, candidate-pass and malicious-candidate-reject outcomes;
4. evaluate routing and tests over at least five repositories, three languages
   and repeated seeds before independent hidden administration.

## Claim boundary

This cycle establishes safe executable test generation with original-bug
falsification on a three-repository public cohort. It does not establish
reliable self-invented verification, learned semantic routing at scale,
autonomous software engineering or independent hidden certification.
