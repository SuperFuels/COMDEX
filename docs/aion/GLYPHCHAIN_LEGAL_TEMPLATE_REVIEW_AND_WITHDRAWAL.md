# Legal Template Review and Withdrawal Process

Status date: 26 September 2026

## Boundary

Tessaris stores and enforces review metadata; it does not certify a reviewer's
qualification, select the applicable jurisdiction or provide legal advice. A
template becomes usable only after the business records that a named suitably
qualified reviewer approved the exact content hash for the stated jurisdiction,
scope and intended use.

## Initial approval

The reviewer record binds:

- the immutable template and family/version identifiers;
- exact SHA-256 content digest;
- reviewer name and stated qualification/regulator;
- review scope and approved jurisdiction;
- approval actor and UTC time;
- review interval and next mandatory review time.

The allowed interval is 1--1,825 days and defaults to 365 days. This default is
an operational reminder, not a statement that annual review is adequate for
every document or jurisdiction. The qualified reviewer/business must select an
appropriate interval.

## Scheduled enforcement

Template listing, opening and instantiation enforce the schedule. A periodic
caller may also invoke the workspace-scoped review-schedule route. When the due
time is reached, the exact version changes from
`APPROVED_FOR_CONTROLLED_USE` to
`REVIEW_OVERDUE_REQUIRES_QUALIFIED_REVIEW` before a new document can be
created. The transition is hash-chained into the encrypted audit history.

There is no grace period or silent fallback. Existing documents and historical
approval evidence are not deleted or relabelled.

## Legal-change withdrawal

An authorized workspace user may immediately withdraw an approved version when
a law, regulator notice, court decision, policy decision or professional review
indicates that it should no longer be used. Withdrawal requires:

- a recorded reason;
- the source/notice/review reference;
- explicit withdrawal acknowledgement;
- actor, UTC time and exact content digest.

The status becomes `WITHDRAWN_FOR_LEGAL_CHANGE`. New instantiation is blocked,
but the encrypted version, prior approvals, documents already created and audit
history remain intact. A replacement is created as a new immutable family
version and separately reviewed.

## Renewal

An overdue or withdrawn exact version can return to controlled use only through
a new qualified-review record bound to the unchanged digest. Renewal appends to
the approval history, sets a new review deadline and clears the active
withdrawal marker; it never overwrites prior review or withdrawal evidence.

If wording changes, renewal is inappropriate: create and approve a new version.
Approval of that successor marks the former version superseded while preserving
both versions.

## Operational monitoring

The Legal workspace shows status, active reviewer and review due date. Operators
should run the review-schedule check daily and route approaching deadlines or
legal-change notices to the Legal product owner and qualified reviewer. The
production schedule mechanism must authenticate as the intended workspace and
must not scan or alter another workspace.

No exact template may be marketed as approved until qualified review has
actually been recorded. The remaining checklist therefore continues to require
appointment of reviewers and approval/population of each supported template
family; this process only supplies the controlled lifecycle around that work.
