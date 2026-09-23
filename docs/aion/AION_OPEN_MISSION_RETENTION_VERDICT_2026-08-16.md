# AION Open-Mission Learning — Retention Verdict and Executor Repair

**Recorded:** 16 August 2026

**Campaign:** `aion_seven_day_open_mission_moonshot_202608`

**Scope:** frozen seven-day matched campaign and its source-closed retention follow-up

## Outcome

The retention executor defect has been repaired without changing any frozen
mission, answer, source-closure time, due time, evaluator authority, action
budget, eligibility rule, or success threshold.

Four mature source-closed retention examinations are now recorded and verified:

| Mission | Evaluation | Source replay | Relearning actions | Result |
|---|---|---:|---:|---:|
| Polyglot transaction recovery | fresh hidden integration tests | no | 0 | pass |
| API pagination | fresh source-disjoint renamed variant | no | 0 | pass |
| Repository repair | fresh disposable repository variant | no | 0 | pass |
| Schema migration | fresh source-disjoint renamed variant | no | 0 | pass |

The fixed runner now evaluates every supported mature diagnostic mission exactly
once. A mature failure remains a visible failure and is not silently retried.
Public-world forecast-calibration missions are excluded from retention claims;
they remain calibration evidence rather than protected competence exams.

## Defect and correction

The former `run_due_retention` implementation was hard-coded to score only the
polyglot mission identifier. Other mature diagnostic missions remained due but
were silently ignored. The dashboard consequently mixed those ignored missions
with forecast-calibration records and could show an apparently stalled queue.

The repair adds:

1. family-specific retention evaluators for the structured repair missions;
2. a fresh disposable-repository evaluator for repository repair;
3. renamed, source-disjoint variants derived from frozen mission hashes;
4. fail-closed handling for unsupported families;
5. single-shot mature receipts for both passes and failures;
6. exclusion of public forecast calibration from retention claims; and
7. explicit attempted, passed, failed, outstanding, and next-due dashboard fields.

The executor and compounding services were restarted under the existing AION
heartbeat supervisor so that the live dashboard uses the corrected code.

## Frozen matched-campaign evidence

- Diagnostic cohorts: **34**.
- Full AION: **34/34**, 101 investigation actions.
- AION without memory: **34/34**, 169 investigation actions.
- AION without repair: **1/34**, 68 investigation actions.
- Proposer only: **0/34**, 68 investigation actions.
- Cold AION: **0/34**, 68 investigation actions.
- Confirmed repair receipts: **33**.
- False or unsafe promotions: **0**.
- Mature retention: **4 attempted, 4 verified, 0 failed**.
- `10x` gate: **false**; a zero-success control does not justify a finite
  multiplicative claim.

On this bounded suite, memory reduced investigation actions from 169 to 101 at
equal verified success, a reduction of approximately **40.2%**. The evidence
supports a claim of governed operational method retention on these four
source-closed exams. It does not establish general intelligence, universal
transfer, or a tenfold improvement.

## Receipt identifiers

- Polyglot: `c8cd4a0ef54a172cd7b986f313b08c16c8181c06051ed5efb6c98230d7739768`
- API pagination: `d8ce00710b330d16a3862c68059b80826309bc6e544928807afd070be96992c8`
- Repository repair: `5235d3d8fce65e75d8e5b53d3aa76fa8a80e4c699127b55e54019e75c0215130`
- Schema migration: `ec3290d766ec984628bc5ad32455b5e496932ba50c24f5e4a351c071b217ab98`

## Evidence hashes at verdict capture

- Immutable machine-readable verdict:
  `39312f20439f891da736491fa32265a0b4b6e8693b0292a4329ffaaa3b3f025a`
- Frozen contract:
  `dddddbea7ac14ce13f288629d31050e6103e82a373053c17755f42ba0c789cd4`
- Campaign state:
  `11d36d6658c1defd8076c977ccd52461f61a2d26a2a21ae5f28b116cff84f369`

The live dashboard and executor status contain refresh timestamps and therefore
remain intentionally mutable. The verdict JSON freezes their material fields.

## Remaining retention programme

The campaign is correctly shown as `retention_followup`, not as a perpetually
active seven-day run. Thirty source-closed transfer, reduced-scaffolding, and
cross-context exams remain scheduled. The next due time is
`2026-08-18T00:31:33.069604+00:00`. They must run only when mature and must retain
the same no-replay, independent-authority, single-shot rules.

The seven-day baseline should now remain frozen. The next capability study
should use genuinely held-out mission families and a stronger matched proposer
that sometimes succeeds, so future comparisons can estimate finite reliability
and efficiency effects rather than relying on a zero-success control.

## Verification

- Open-mission governor/executor tests: **21 passed**.
- Dashboard, heartbeat, and portfolio-induction tests: **13 passed**.
- Python compilation checks: **passed**.
- Total targeted regression checks: **34 passed**.

No result in this verdict was self-graded or retrospectively authorised.
