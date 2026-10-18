# HexCore Open Patch Generation — Strict Audit Report

## Outcome

The open patch generator is implemented and operational, but it is **not
promoted** under the strengthened behavioural contract.

Unlike the earlier bounded repair pilot, the generator receives no
task-specific patch menu. A replaceable language model proposes one or more
arbitrary source replacements from the natural issue, localized source and
deepest traceback site. HexCore applies each proposal only in a fresh sandbox,
runs executable behavioural and regression checks, returns verified criticism,
and either selects the repair or abstains. The historical human patch remains
hidden until after selection.

## Architecture

The proposal interface supports a general multi-edit replacement program:

```text
issue + source + deepest traceback site
    -> private model proposal
    -> unique exact/whitespace-tolerant application
    -> fresh sandbox
    -> behavioural + regression verification
    -> verified criticism
    -> bounded revision or abstention
```

Whitespace-tolerant application is fail-closed: it is permitted only when the
model's reflowed token sequence matches exactly one source region. The neural
provider cannot write live files, accept its own patch, open the historical
human patch, or promote itself.

## Strict-audit results

| Measure | Result |
|---|---:|
| Source-disjoint repositories | 3 |
| Task-specific repair menus | 0 |
| Latest-cohort verified repairs | 2 / 3 |
| Latest-cohort success | 66.67% |
| Safe abstentions | 1 |
| Unsafe acceptances | 0 |
| Unsafe live writes | 0 |
| Human patch blind during generation | 100% |
| Live source integrity | 100% |

Marshmallow and pydicom passed on the first proposal. The pvlib numerical
repair had succeeded in earlier audited attempts, but did not reproduce in the
latest complete cohort. The strengthened verifier also exposed two apparently
successful but regressive designs: changing container-parent semantics in
Marshmallow and replacing standard pvlib numerical behaviour. Those candidates
were rejected.

## Interpretation

This is meaningful progress over finite repair menus: AION can generate
coherent, multi-location source changes, use executable criticism and safely
abstain. It is not yet a stable general repair capability. A single successful
run is not sufficient; the weakest repository remains the veto.

The next gate should require:

1. at least ten hidden failures across at least five unrelated repositories;
2. at least three programming languages;
3. repeatability across independent proposal seeds/providers;
4. self-invented falsification tests that reject wrong patches;
5. source-disjoint held-out transfer;
6. zero live writes and zero unsafe acceptance;
7. explicit retirement of any champion validated only under an older verifier.

## Claim boundary

Localization and behavioural verifier families remain engineered. The cohort
contains only three public SWE-bench Lite development issues, and pretraining
contamination cannot be excluded. This does not demonstrate unrestricted
software engineering, independent external evaluation or AGI.
