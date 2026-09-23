# AION Progressive Executor Registry and Stall Recovery

## Problem

The progressive competency service could select an unsupported active subject,
then execute an unrelated supported contract.  This hid the missing capability,
allowed repeated no-progress cycles and made the dashboard's executor state
ambiguous.  Historical one-pass Academy receipts were also not equivalent to a
progressive executor capable of satisfying knowledge, practice, project,
debugging, transfer and retention requirements.

## Runtime correction

A persistent executor capability registry now separates subject selection,
historical evidence and currently verified execution authority.  For every
active contract the runtime now performs exactly one of three actions:

1. execute the matching verified progressive adapter;
2. record a resumable executor-acquisition gap and park that subject; or
3. wait for an elapsed retention authority.

It never substitutes another subject's executor.  Missing adapters are grouped
by required authority, persisted across restart and automatically resolved when
a matching verified adapter becomes available.  The competency ledger now runs
before execution and again after progress or parking, allowing the curriculum to
close, resume or rotate within one service wake rather than stalling for hours.

## Software Engineering adapter

Software Engineering is now the fifth verified progressive adapter.  Its
knowledge and exercise stages execute a twelve-part engineering suite covering
requirements, architecture, implementation, observability, debugging,
modularity, maintenance, review, delivery, version control, testing and team
practice.  Deliberately incorrect variants must fail, and six unsafe execution
classes must be rejected.  Project, debugging, transfer and retention stages use
fresh unfamiliar subprocess portfolios rather than repeating the concept suite.

## Dashboard and operational truth

The dashboard reports verified executor coverage separately from subject
competency.  It currently distinguishes five available adapters from thirty-nine
catalogue coverage gaps, and displays active acquisition contracts when they are
encountered.  Arena cycle display is capped at the required gate and reports
later cycles as additional observations rather than malformed `13/12` progress.

## Verification and live outcome

The focused canonical-runtime, curriculum, registry and dashboard stack passes
31/31 tests.  A negative test proves that an unsupported active subject cannot
borrow the Advanced Python executor.  After the live curriculum service was
restarted, Software Engineering advanced through successive requirements with no
manual intervention; the progressive evidence ledger increased beyond its prior
134-record stall and continued generating the next requirement automatically.

## Claim boundary

This removes the systemic silent-stall and executor-substitution failure.  It
does not claim that all forty-four subjects already possess deep executors or
that one executable lesson establishes competence.  Thirty-nine catalogue
adapters still require acquisition or invention.  The registry makes that work
explicit, resumable and non-blocking while the five verified lanes continue to
advance under the full progressive evidence gates.
