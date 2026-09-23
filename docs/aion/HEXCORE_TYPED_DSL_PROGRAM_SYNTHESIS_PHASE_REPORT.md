# AION HexCore Phase 44 - Typed DSL Program Synthesis

**Status:** Promoted  
**Procedure:** `procedure_typed_dsl_synthesis_0a203e5df940`  
**Parent:** `procedure_compositional_theory_program_67d49719b0b9`

## Breakthrough Objective

Phase 43 selected executable programs from four engineered theory families. Phase 44 removes those named families from the learner-facing interface and introduces a typed domain-specific language (DSL). AION must compose executable expression trees from lower-level primitives, identify useful subprograms in verified experience, reuse those abstractions in unfamiliar domains, and refuse worlds that the DSL cannot represent.

## Typed Language

Numeric expressions are constructed from:

- typed variables;
- pairwise addition;
- absolute difference;
- pairwise maximum.

Boolean expressions are constructed from:

- numeric threshold comparison;
- conjunction;
- guarded conditional branches.

Programs therefore range from a single comparison to multi-clause and conditional trees. Candidates are executed over the complete finite state space and predictively equivalent trees are collapsed to a minimum-complexity representative.

## Verified Subprogram Learning

AION first solved 18 development worlds without a learned library. Only exact, independently verified programs contributed a motif. Variable identities were replaced with abstract roles, allowing a motif learned over one set of symbols to be instantiated over different variables in another domain.

The resulting library contained **17 verified motifs**. These motifs changed only the reversible search prior; they did not bypass execution, verification, abstention, or CAU.

The sealed comparison used the identical synthesizer twice:

- **Transfer learner:** verified motif library enabled.
- **Cold learner:** uniform experience history, with the same DSL, likelihood, active selection, stopping rule, confirmation block, audit, and budget.

## Active Synthesis and Audit

The learner maintains a posterior over semantically distinct trees and selects interventions by expected information gain. If the finite state space is exhausted under noise, an eight-intervention information-directed confirmation block targets the remaining disagreements. A separate eight-intervention audit is not allowed to select the program.

Acceptance requires 99% posterior confidence and at least 87.5% untouched-audit agreement. Failure returns `DSL_INADEQUATE`.

## External and Out-of-Language Evaluation

Twelve external worlds were executed through an independently implemented interpreter, rather than the learner's normal evaluator. Eight additional parity worlds were deliberately impossible to express using the DSL.

The parity worlds produced 100% safe abstention and zero forced programs.

## Sealed Results

| Measure | Result |
|---|---:|
| Development exact synthesis | **100.00%** |
| Sealed exact synthesis | **97.92%** |
| Weakest tree family | **93.75%** |
| Full-state predictive accuracy | **100.00%** |
| Independent external interpreter | **91.67%** |
| Safe out-of-language abstention | **100.00%** |
| Unsafe forced programs | **0** |
| Verified transferable motifs | **17** |
| Mean transfer observations | **27.146** |
| Mean cold observations | **31.646** |
| Environmental observation reduction | **14.22%** |
| Provenance completeness | **100.00%** |
| Restart relearning | **0 worlds** |

All pre-declared gates passed. The two non-exact external/sealed cases remain recorded rather than being removed. CAU authorised promotion, and the synthesized programs, motif library, session evidence, and champion survived restart.

## Meaning

In plain English, AION can now build small executable explanations rather than choose from a list of complete explanations. It can discover that a useful reasoning fragment learned in one world has the same abstract role in another world, use that experience to ask fewer real questions, and still reject worlds that its current language cannot express.

This is a bounded form of program synthesis and abstraction learning. The primitive set, maximum tree depth, ternary values, simulator, and audit oracle remain engineered.

## Phase 45 Recommendation

The next step should allow **primitive invention and library compression**. When no composition of existing primitives fits, AION should propose a new typed operator from an execution trace, test whether it compresses several previously unrelated programs, and promote it only if it improves prediction and search on source-disjoint external simulators.

Phase 45 should also introduce mixed continuous/discrete state, delayed effects, recursive multi-step programs, execution timeouts, and minimum-description-length penalties. This would test whether AION can expand the language in which it thinks rather than only synthesize inside a language supplied by engineers.

