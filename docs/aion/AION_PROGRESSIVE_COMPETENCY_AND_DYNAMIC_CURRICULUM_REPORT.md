# AION Progressive Competency and Dynamic Curriculum

## Purpose

The former Academy reported whether AION passed a committed assessment.  That
was useful evidence, but the terminal display made a single bounded pass look
like a whole-subject qualification.  The progressive competency system replaces
that binary interpretation with separate knowledge and practical development
from Unassessed through Beginner, Intermediate, Advanced and Expert.

Every core subject has a minimum target of **Advanced**.  After the breadth
programme reaches Advanced or a legitimate external-practical boundary, an
Expert-deepening stage becomes eligible.  Catalogue membership, teacher advice,
an Academy receipt and restart persistence cannot independently raise a subject
to Advanced.

## Evidence contract

Advanced requires all of the following:

- at least two verified knowledge encounters for every declared major subskill;
- at least two verified practical encounters for every declared major subskill;
- at least five practical projects, three genuinely unfamiliar;
- at least three diagnosed debugging or recovery cases;
- at least two source-disjoint transfers;
- a delayed closed-book fresh-task retention result;
- at least three independently owned outcomes;
- at least ten repeated trials;
- mean verified score of at least 90 percent; and
- recent scaffolding no greater than 35 percent.

Expert applies materially stronger thresholds: four knowledge and four
practical encounters per subskill, twelve projects, eight unfamiliar projects,
six recovery cases, four transfers, two delayed retention results, eight
independent outcomes, at least twenty-five trials and no more than 15 percent
recent scaffolding.

The overall level is the lower of knowledge and practical competence.  Where
knowledge reaches Advanced but a real physical task is unavailable, the ledger
reports `advanced_theory_practical_blocked`, records the missing authority and
allows other learning to continue.  Missing internal tooling instead reports
`advanced_theory_executor_blocked` and remains the active acquisition target;
it is not treated as an excuse to abandon the subject.

## Anti-inflation corrections

The new ledger makes several strict distinctions:

1. An old Academy `PASS` imports as one evidence event only.
2. Restart persistence is recorded separately and does not count as delayed
   closed-book retention.
3. Repeated execution of one laboratory cannot count as multiple unfamiliar
   projects.
4. Creating a curriculum contract does not change competence.
5. Teacher and neural outputs remain proposals, never assessment authority.
6. An open executor gap becomes visibly blocked and eventually stalled rather
   than being displayed as active learning.

The terminal dashboard therefore relabels the thirteen former module passes as
`EVIDENCE`, explicitly stating that they are not subject levels.

The same ledger exposes a capability query for work allocation. A request such
as “Can you build this in Python?” returns separate knowledge/practical levels,
work readiness, unresolved blockers and the target gap. An unknown domain is
answered with `unknown_subject` and a mission-gap/clarification action rather
than an invented claim of competence.

## Curriculum breadth

The initial progressive catalogue contains 44 subjects. It incorporates the
North-Star registry, the thirteen foundation modules and additional coverage
for:

- cloud, DevOps and site reliability;
- machine learning and AI engineering;
- compilers and programming languages;
- embedded systems and robotics;
- computer graphics and visual computing;
- economics and entrepreneurship;
- product, project and Scrum management;
- research, writing and professional communication; and
- law, policy and applied ethics.

The existing language, mathematics, science, programming, database, security,
business, finance, design, social and creative subjects remain present.  The
catalogue is not terminal: authorized missions may add unfamiliar domains.

For example, a mission requiring a pet-food startup can register a new
`Pet Food Industry` subject with nutrition, regulation, manufacturing and unit
economics subskills. That mission-bound gap becomes the active curriculum; it
must acquire authoritative sources, exercises, practical outcomes, failure
cases, transfer and retention under the same gates.

## First live progressive cycle

Testing and Debugging was selected as the first depth subject. The executor ran
fresh isolated Python processes, executable assertions, counterexample
mutations and security rejection across repeated micro-assessments.

Current live state:

| Measure | Result |
|---|---:|
| Declared subskill knowledge coverage | 100% |
| Declared subskill practical exposure | 100% |
| Verified evidence records | 21 |
| Repeated trials | 61 |
| Knowledge level | **Advanced** |
| Practical level | **Intermediate** |
| Unfamiliar projects | **5** |
| Diagnosed debugging cases | **3** |
| Delayed retention | 0 |
| Display level | **Intermediate overall; retention pending** |

The system correctly refused to count more renamed copies of its micro-lab as
the required unfamiliar projects. It then acquired a diverse portfolio covering
ledger reconciliation, sensor anomalies, transactional inventory,
configuration precedence and dependency scheduling, plus three distinct fault
diagnoses. Its only remaining Advanced gate is an elapsed closed-book fresh task
scheduled for 2026-08-02; the retention task uses a previously unseen cache-
invalidation problem rather than replaying a training solution.

During the first portfolio run, repeated requirements initially produced the
same contract identifier and later artifacts overwrote earlier paths. The
integrity audit detected five hash mismatches, invalidated those evidence rows,
superseded the dependent retention contract and reran every affected project
under generation-specific commitments. Invalidated rows remain in the audit
history and contribute nothing to competency.

## Dynamic mission integration

The canonical cognitive runtime now binds the first unsatisfied capability of
an owner-authorized mission into the progressive ledger. It reuses an existing
subject when a grounded match exists and creates a mission-specific subject when
the domain is genuinely missing. The mission establishes relevance, not
competence; normal evidence gates remain unchanged.

This produces the intended loop:

\[
\text{mission}
\rightarrow
\text{knowledge-gap detection}
\rightarrow
\text{progressive curriculum}
\rightarrow
\text{verified practice}
\rightarrow
\text{independent consequence}
\rightarrow
\text{retention and transfer}
\rightarrow
\text{revised competency level}.
\]

## Current boundary

The competency control plane and first automatic micro-exercise executor are
operational. AION has not yet earned Advanced overall competence in any subject
under these stricter gates. This is expected: the new rules deliberately reject
the earlier one-pass interpretation. Diverse project executors, elapsed
retention and independent real outcomes must now supply the missing evidence.
