# AION HexCore Phase 43 - Compositional Theory Program Induction

**Status:** Promoted  
**Promoted procedure:** `procedure_compositional_theory_program_67d49719b0b9`  
**Parent:** `procedure_adaptive_schema_revision_d5ea7bf85c36`

## Research Question

Can AION decide whether predictive failure requires a parameter change, a contextual exception, a hidden intermediate concept, or a different operator—and then identify the exact executable theory through active experiments?

Phase 43 replaces Phase 42's binary, single-rule setting with ternary variables and four bounded executable program families:

1. **Parameter revision:** change a sum threshold.
2. **Contextual exception:** preserve the threshold but add a variable-specific veto.
3. **Latent predicate invention:** derive an unnamed conjunction from two variables and compose it with a second threshold clause.
4. **Operator invention:** use a range-sensitive aggregation rule rather than the inherited sum-only rule.

The truth program, required revision class, and out-of-grammar status are hidden from the solver.

## Dual-Level Inference

For every arity \(n\in\{3,4,5\}\), HexCore constructs all programs allowed by the bounded grammar and removes predictively equivalent duplicates. It assigns a complexity-sensitive prior, maintains a Bayesian posterior over the remaining programs, and chooses interventions by expected information gain per unit cost:

\[
x^\star=\arg\max_x
\frac{H[P(h)]-\mathbb{E}_{y\mid x}H[P(h\mid x,y)]}{c(x)}.
\]

The learner must collect at least 12 discovery observations and reach 98.5% posterior confidence. The selected program is then tested on 16 unseen interventions. Acceptance requires at least 87.5% verification agreement. Failure produces `NO_ADEQUATE_THEORY`, not a forced explanation.

This yields two linked decisions:

- **Model-class diagnosis:** parameter, exception, latent predicate, or new operator.
- **Program identification:** the exact variables and parameters inside that class.

## Out-of-Grammar Criticism

Twelve additional sealed worlds use a parity interaction deliberately absent from the candidate language. They test whether AION can recognise an architectural boundary rather than choose the least-bad available theory.

All 12 were rejected as `NO_ADEQUATE_THEORY`. There were zero unsafe forced theories.

## Sealed Contract

The evaluation contained:

- 48 source-disjoint sealed worlds;
- 16 independently named external-domain worlds;
- 12 out-of-grammar parity worlds;
- equal representation of the four in-grammar program families;
- arities of three, four, and five;
- ternary intervention values;
- a deterministic 2% observation-noise process;
- a matched random-experiment control using the same grammar, prior, likelihood, stopping rule, verification rule, and budget.

Degenerate truth programs with near-constant outputs were excluded before sealing because they do not meaningfully test compositional invention.

## Results

| Measure | Result |
|---|---:|
| Exact executable-program recovery | **100.00%** |
| Revision-class diagnosis | **100.00%** |
| Weakest program family | **100.00%** |
| Full-state predictive accuracy | **100.00%** |
| External-domain exact recovery | **100.00%** |
| Out-of-grammar safe abstention | **100.00%** |
| Unsafe forced theories | **0** |
| Mean active environmental observations | **28.094** |
| Mean random-control observations | **48.594** |
| Environmental observation reduction | **42.19%** |
| Unjustified complexity violations | **0** |
| Provenance completeness | **100.00%** |
| Restart relearning | **0 worlds** |

Every pre-declared gate passed. CAU promoted the challenger, and the program library, session records, and champion survived restart.

## Interpretation

In plain English, AION can now distinguish:

> "The overall rule is right but its threshold is wrong."

from:

> "The rule usually works, except in this context."

from:

> "Two observed variables jointly create a hidden condition that matters."

from:

> "A sum is the wrong kind of relationship; the spread of the values matters."

It then chooses experiments that discriminate those explanations, verifies the selected executable program on observations not used for discovery, and abstains when none of its available conceptual tools explain the world.

This is a meaningful expansion from schema revision to bounded program induction. It is not unrestricted operator invention because the four program families remain engineered.

## Recommended Phase 44

Phase 44 should introduce a small typed domain-specific language whose primitive operators can themselves be composed and mutated. AION should construct previously unseen expression trees, introduce reusable latent subprograms, compare minimum-description-length and predictive evidence, and test them through active interventions.

The decisive external test should use separately implemented simulators with continuous or mixed-valued state, delayed effects, and programs not emitted by the training generator. Promotion should require positive transfer of invented primitives, safe timeout and abstention, reduced real interventions, and unchanged provenance, restart, weakest-family, and CAU protections.

