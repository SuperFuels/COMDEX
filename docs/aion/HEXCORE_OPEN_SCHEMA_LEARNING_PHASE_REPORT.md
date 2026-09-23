# HexCore Phase 41 - Open-Schema Learning and Explanatory Graphs

**Date:** 29 July 2026  
**Status:** Passed and promoted  
**Procedure:** `procedure_open_schema_learning_1d0456fd3c9f`

## Executive result

Phase 41 tests whether AION can construct an internal relation schema rather
than receive a fixed ontology from the benchmark. The solver sees unfamiliar
documents, entity names, relation wording and decision contracts. It does not
receive the expected schema, goal operator, missing relation or final answer.

AION now:

1. parses factual propositions from independently cited documents;
2. infers conditional relation structure from new wording;
3. invents stable schema identifiers from operator structure and arity;
4. validates those schemas across unrelated domains;
5. induces all-of, any-of, threshold and ordered goal contracts;
6. recursively chains relations into multi-hop explanatory graphs;
7. distinguishes explicit counter-evidence from absent knowledge;
8. asks for the exact missing relation only when required;
9. resumes inference after a verified clarification;
10. retains the schema library, explanations and champion across restart.

## Experimental separation

Development contains 18 projects from:

- river archive;
- ceramic workshop;
- forest survey.

The sealed cohort contains 48 projects from six different domains:

- orbital greenhouse;
- linguistic conservatory;
- deep sea observatory;
- nomadic energy cooperative;
- heritage seed bank;
- polar communications station.

Every project uses names prefixed with a project-specific namespace.
Consequently, no development entity identity is available in the sealed
cohort. The solver must transfer abstract structure rather than memorize
symbols.

## Structural schema invention

The system does not assign a supplied semantic label such as `enables` or
`requires`. Each parsed conditional rule is represented by an induced
signature:

```text
antecedent_operator
antecedent_arity
consequence_arity
temporal_direction
```

The canonical hash of this representation becomes the invented schema
identifier. Three schemas emerged:

| Schema | Structural interpretation |
|---|---|
| `schema_1c0b8c98a583` | one antecedent, conjunctive implication |
| `schema_83d172a79837` | two antecedents, all required |
| `schema_8cff722cd53b` | two antecedents, either sufficient |

All three appeared in every sealed domain and were validated against successful
outcomes. The persistent library stores both development and sealed usage
counts and the domains in which each schema succeeded.

## Open goal-schema induction

The decision document is independently parsed into one of four structures:

- all requirements must hold;
- any requirement is sufficient;
- at least \(k\) of \(n\) requirements must hold;
- requirements must be established in a declared order.

These structures are not passed to the solver as benchmark labels. They are
induced from the decision prose and evaluated against hidden contracts.

## Multi-hop explanatory reasoning

Facts begin at proof depth zero. A rule may add its consequence only when its
induced antecedent operator is satisfied. Each inferred proposition retains:

- proof depth;
- the exact relation schema used;
- antecedent propositions;
- source document;
- provenance hash;
- the complete supporting proof chain.

The engine iterates until no new proposition can be derived. Ordered goals
also require strictly increasing proof depths, preventing an unordered set of
facts from satisfying a temporal explanation.

## Missing knowledge versus falsity

If a required proposition is absent, HexCore recursively searches for rules
that could produce it. Missing leaves with no producer become explicit
knowledge gaps. A query is generated in the form:

```text
Which verified relation or observation establishes ENTITY::STATE?
```

If the entity has instead been directly observed in a conflicting state, the
system classifies the goal as unsupported rather than unknown. This is the
critical epistemic distinction:

- no evidence path: unknown, ask;
- verified opposing state: unsupported, do not ask merely to obtain a desired
  answer;
- complete supporting path: supported.

## Corrected first cohort

The first compact cohort was rejected. Schema recovery was 100%, but three
negative cases were incorrectly represented by the generator as missing
terminal evidence. The benchmark was corrected by adding explicit opposing
observations to negative projects. No gate was lowered and no solver-visible
answer was added.

## Sealed results

| Measure | Result |
|---|---:|
| Sealed projects | 48 |
| Goal accuracy | **100%** |
| Weakest-domain accuracy | **100%** |
| Schema recovery | **100%** |
| Cross-domain validated schemas | **3/3** |
| Multi-hop explanation rate | **89.58%** |
| Missing-knowledge identification | **100%** |
| Recovery after clarification | **100%** |
| Unnecessary clarification questions | **0** |
| Complete provenance | **100%** |
| Verified project memories committed | **48/48** |
| One-hop control accuracy | **20.83%** |
| Restart relearning | **0** |

The one-hop control uses the same parsed facts and rules but cannot recursively
compose them. Its 20.83% accuracy demonstrates that the result depends on
multi-stage explanation rather than isolated phrase matching.

## Governance and persistence

Promotion required:

- at least 90% mean accuracy;
- at least 85% weakest-domain accuracy;
- at least 90% schema recovery;
- at least two schemas validated across unrelated domains;
- at least 70% multi-hop coverage;
- at least 90% missing-knowledge accuracy;
- at least 90% clarification recovery;
- zero unnecessary questions;
- complete provenance;
- all verified sealed outcomes committed;
- CAU authorization;
- schema, project and champion retention after restart.

All gates passed. The schema library and all 48 sealed project records were
reloaded without relearning.

## Claim boundary

Phase 41 is open-schema learning inside a bounded conditional-logic family. It
does not provide unrestricted ontology invention. The natural-language
grammar, binary proposition form, conditional operator family, goal operators,
documents and executable oracle remain engineered. The system invents
structural signatures, not arbitrary human concepts.

This is not unrestricted scientific discovery, general natural-language
understanding or AGI. The next phase should require schema revision when an
invented abstraction fails, compositional relations with variable arity,
probabilistic and defeasible rules, competing explanatory models, and
selection of new observations that best distinguish those models.

## Reproducibility

- `backend/modules/hexcore/open_schema_learning_benchmark.py`
- `backend/modules/hexcore/persistent_learning.py`
- `backend/tests/test_hexcore_persistent_learning.py`
- `results/hexcore_open_schema_learning.json`

