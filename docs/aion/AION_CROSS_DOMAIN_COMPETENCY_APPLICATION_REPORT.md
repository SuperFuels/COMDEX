# AION Cross-Domain Competency Application

## Research question

Can AION use an evidenced intermediate competency on fresh practical work, and
can it recognize when a second competency is required rather than treating all
work as one undifferentiated programming task?

## Competencies selected

The progressive ledger identified three current intermediate competencies:
Algorithms and Data Structures, Python Core, and Testing and Debugging.  Two
source-disjoint objectives were supplied without capability labels.

For a deterministic dependency-ordering objective, the mission router selected
only Algorithms and Data Structures.  For diagnosis and repair of a dependency
scheduler with counterexample invention, it selected Algorithms and Data
Structures plus Testing and Debugging.  Both routes were authorized only as
bounded execution with strong verification because the competencies are
intermediate rather than advanced.

## Practical outcomes

The single-domain construction passed five of five hidden executable checks,
including deterministic ordering, implicit dependency nodes, empty input and
cycle rejection.

On the mixed-domain task, an algorithm-only repair corrected cycle handling but
missed an implicit dependency case, passing four of five hidden checks.  The
Testing and Debugging competence supplied executable properties for cycles,
implicit nodes, deterministic behavior and input immutability.  The composed
repair then passed four of four invented falsification checks and five of five
separate hidden checks.

Candidate source and invented tests were SHA-256 committed before hidden
execution.  A deliberately unsafe challenger was rejected and no live repository
files were modified by candidate execution.

## Architectural correction

The initial routing attempt revealed excessive domain selection caused by common
word and substring matches.  The mission router was corrected to use bounded
phrase cues, stop-word removal, discriminative token weighting and a strong-match
floor.  Regression tests now require exact separation between the one-domain and
two-domain objectives.

## Claim boundary

This is positive evidence that AION can retrieve and compose two retained
intermediate competencies on fresh bounded executable work.  It is not evidence
of unrestricted software mastery, arbitrary domain composition or advanced
competence.  Broader evidence requires repeated projects with different domain
pairs and independently supplied objectives and hidden outcomes.
