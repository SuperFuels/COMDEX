# AION Business Twin and Department Pilot Delivery Plan

## Outcome

Deliver a reusable, approval-gated Department Pilot system that turns canonical business evidence into Boardroom decisions, routes approved actions to specialist department agents, records their work and evidence, and returns verified results to the next Boardroom meeting.

The target operating loop is:

`Function discovery -> Canonical function model -> Boardroom context -> Approved Boardroom package -> Department Pilot task queue -> Pilot work and user conversation -> Artifacts and evidence -> Business Container writeback -> Boardroom handback`

## Implementation status — 20 July 2026

- **Phase 0 complete:** the founder approved the redesigned light Products & Services workspace in the packaged desktop application. The design remains modular in `aion_operating_model_workspace.js`; `app.js` was not expanded.
- **Phase 1 complete:** commit `ec55457a` is on `origin/main` and tagged `aion-business-twin-finance-foundation-2026-07-16`.
- **Phase 2 complete:** the versioned `aion.department_pilot.*.v1` contract family now covers an approved Boardroom package, specialist task, progress events, conversation, context references, proposed tools, exact-payload approvals, artifacts, receipts, Department Intelligence patches and Boardroom handback. Existing mission queue and capability receipts are adapted into this family rather than replaced by a parallel queue.
- **Phase 3 read-only foundation complete:** the durable runtime now provides atomic backend persistence, task queues by workspace and department, guarded lifecycle transitions, conversation persistence, append-only audit records, restart recovery, stale-writer protection, canonical context retrieval, backend capability enforcement, Finance report storage, File Cabinet registration, applied Department Intelligence updates, Boardroom handback projection and user-visible completed/failed task states. Exact-payload approval adapters for future external side effects remain later controlled-execution work.
- **Phase 4 complete:** the founder's existing `Delegate to Agents` decision after a live, non-simulated Boardroom task build now creates the canonical Finance assignment package. The backend hash-binds the current Business Container context at approval, routes Finance idempotently to the Finance Pilot queue and exposes the same task in the Central Pilot monitor. Finance is the only enabled specialist. Every other function remains blocked by an explicit design gate.
- **Phase 5 execution, conversation, management-reporting, scenario and reconciliation slices complete:** a queued Finance Boardroom action can now claim and run a permission-checked read-only management analysis, retrieve the exact hash-bound context, store its report under `Finance/Reports`, update Finance Department Intelligence, create an execution receipt and expose a durable handback to the next Boardroom snapshot. The permanent Finance terminal uses a separate backend-authoritative conversation session, selectively retrieves canonical Finance evidence, labels reliability and sources, and leaves the Financial Model unchanged. Management reports now produce period-aware profit-and-loss, cash and working-capital KPIs; calculate supported margins and cost relationships; compare actuals with canonical budgets and previous periods; expose evidence freshness, verification and missing comparisons; and consume accepted artifact facts without exposing raw external payloads. Conflicting accepted facts are visibly withheld rather than silently selected. Finance scenarios create expected, upside and downside monthly projections for revenue, price, volume, costs, hiring, stock purchases and protected cash reserves. Scenario inputs and outputs are hash-bound, stored separately under `Finance/Scenarios`, summarised into Finance Intelligence and projected to the Boardroom without mutating historical evidence. Reconciliation now compares accepted spreadsheet facts with the latest read-only Xero report values only when their reporting periods match, surfaces matches, conflicts, missing values and period problems, and records a founder review decision without silently replacing canonical truth. An incomplete evidence baseline is rejected rather than invented. Re-running a completed task remains idempotent. Exact-payload proposed Finance actions are the next Finance capability increment.
- **Verification baseline:** the focused current-architecture contract, persistence, genuine Boardroom producer, routing API, Finance execution/handback, grounded conversation, management reporting, scenario, desktop bridge, Finance/Xero, shared terminal and Products & Services suites pass. JavaScript and Python syntax checks pass; packaged desktop verification is repeated at each milestone. An obsolete legacy O14A1 incoming-package-panel lock is outside this baseline because that preview panel is no longer installed and must not be restored into the canonical runtime.

## Delivery principles

1. The local COMDEX repository is the source of truth.
2. New function work remains modular and must not materially expand `desktop/mac/src/app.js`.
3. The Central Pilot coordinates, routes and monitors work. It does not replace specialist Department Pilots.
4. All Department Pilots use one shared runtime configured by department role, context, permissions, tools and specialist capabilities.
5. The Business Container, Business Map, Department Intelligence and canonical domain models are the durable memory. External AI providers are not treated as durable memory.
6. Read-only analysis is enabled before any external write capability.
7. Consequential actions remain approval-gated and produce immutable receipts.
8. Source evidence, extracted facts, accepted facts, assumptions and generated conclusions remain distinguishable.
9. Large catalogues are summarized for Boardroom use and retrieved selectively rather than copied wholesale into prompts.
10. Each phase must be tested through the packaged desktop application as well as by automated tests.
11. Sales, Marketing, Support, HR and Operations remain unconfigured until their purpose, workflows, capabilities, interface and permissions have been discussed with the founder.

## Phase 0 — Products and Services design completion

This phase is first in the delivery order. Its detailed visual changes will be finalised after the current Products & Services screen is reviewed with the founder.

Required design pass:

- Review the complete Products & Services workspace in its current packaged-app state.
- Simplify its information hierarchy and remove duplicated or development-oriented presentation.
- Preserve the clean terminal visual language used by Finance while making structured tables easy for a non-technical business owner.
- Make the simple case fast: a sole trader must be able to add one service and one hourly/day rate without completing an enterprise form.
- Keep the advanced case available: products, services, variants, bundles, production lines, labour, materials, capacity, inventory and procurement.
- Separate setup/editing views from day-to-day Pilot conversation and operational monitoring.
- Establish clear empty, incomplete, imported, verified and attention-required states.
- Ensure every material figure shows its source and verification status where relevant.
- Confirm responsive layout, keyboard operation, readable contrast and consistent active/disabled button styling.
- Re-test persistence, imports, Boardroom projection and file-cabinet access after the design changes.

Exit gate: the founder approves the Products & Services information architecture and visual direction, and existing operating-model tests continue to pass.

## Phase 1 — Source checkpoint and baseline verification

- Commit the completed Business Foundation, Finance, Xero, evidence, operating-model, inventory, procurement, navigation, HR and shared-runtime work.
- Exclude packaged applications, virtual environments, voice-model staging and recovery backups from Git.
- Record the automated-test baseline.
- Package and smoke-test Tessaris from the committed source.
- Tag the checkpoint so it can be restored independently of later Department Pilot work.

Exit gate: a reproducible source checkpoint exists on `origin/main`, with no required application source left untracked.

## Phase 2 — Canonical Department Pilot contracts

Create versioned shared contracts for:

- Boardroom assignment packages.
- Department tasks and subtasks.
- Task state and progress events.
- Conversation turns.
- Context references and retrieved evidence.
- Proposed tool calls.
- Approval requests and decisions.
- Generated reports and artifacts.
- Execution and completion receipts.
- Department Intelligence patches.
- Boardroom handback summaries.

Reuse the existing mission, department queue, approval and safe-step contracts where compatible. Remove or adapt preview-only duplication rather than creating a parallel queue system.

Exit gate: one schema family represents an approved Boardroom action from creation through completion and handback.

## Phase 3 — Durable Department Pilot runtime

Extend the current department role/context shell into a backend-authoritative runtime with:

- Persistent department task queues.
- Task claiming, status, retry, cancellation and resume.
- Department-specific system prompts and capability profiles.
- Canonical context assembly and selective evidence retrieval.
- Persistent conversation history linked to tasks and the business identity.
- Permission enforcement and approval gates.
- Tool and connector adapters.
- Artifact storage and file-cabinet registration.
- Evidence and completion receipts.
- Department Intelligence writeback.
- Boardroom handback.
- Audit and failure telemetry suitable for user-visible diagnostics.

Exit gate: a synthetic department task can survive an application restart and complete with a stored receipt without relying on browser local storage as its authority.

## Phase 4 — Central Pilot routing and monitoring

Connect the existing Central Pilot and Boardroom package flow to the shared runtime:

- Convert approved Boardroom actions into canonical department tasks.
- Route each action to the correct specialist Pilot.
- Monitor cross-department dependencies and blocked work.
- Surface approval requests without bypassing department permissions.
- Escalate conflicts, missing evidence and failed work to the user or Boardroom.
- Keep the Central Pilot as coordinator; specialist reasoning remains department-scoped.

Exit gate: an approved Finance action appears automatically in the Finance Pilot queue and is visible from the Central Pilot monitor.

Implementation boundary:

- `finance_pilot` is enabled.
- `sales_pilot`, `marketing_pilot`, `support_pilot`, `hr_pilot` and `operations_pilot` return `design_required` and cannot receive canonical work.
- Legacy preview packages and local-browser demo queues cannot be promoted into the canonical runtime.
- Boardroom approval and queue delivery use one backend transaction, avoiding an approved-but-not-routed intermediate state.
- Only `aion.department_task_build.live.v1` records produced through live provider fanout can be promoted by the Boardroom producer. Simulated, legacy and preview-panel records are rejected.
- The founder's `Delegate to Agents` action is the approval boundary. Current Finance actions are converted into one canonical, hash-bound package; non-Finance actions remain design-gated and are reported rather than silently routed.
- When explicit context references are not supplied, the backend binds the current business identity, Business Map, Department Intelligence, financial model and operating model that exist at the moment of Finance approval.

## Phase 5 — Finance as the first complete vertical implementation

Implement Finance on the shared runtime before building more function onboarding.

Initial read-only capabilities:

- Explain the canonical financial model and its evidence.
- Produce management summaries and Boardroom-ready Finance reports.
- Calculate revenue, direct costs, gross margin, overheads, operating profit and cash measures.
- Compare actuals, budgets and previous periods.
- Create cash-flow forecasts.
- Run pricing, volume, cost, hiring, stock and cash scenarios.
- Reconcile accepted spreadsheet facts with Xero and visibly report conflicts.
- Identify missing, stale, assumed and unverified values.
- Answer arbitrary Finance questions using retrieved business context.

Implemented first slice:

- Run an approved `finance.boardroom_analysis`, management-report or other explicitly permitted read-only Finance capability from the Finance Pilot queue.
- Retrieve and verify the Business Container records hash-bound when the founder approved the Boardroom package.
- Produce a deterministic management report covering available revenue, gross profit, operating profit and cash figures.
- Store the report in the Finance Business Container and register an index pointer under `Finance/Reports` in the File Cabinet.
- Record the report artifact, completion receipt, Finance Intelligence result and Boardroom handback in the canonical work envelope.
- Project the latest handback into the durable Boardroom snapshot when that container exists.
- Show completed handbacks and failed analyses in the Finance and Central Pilot queues.
- Refuse unapproved capabilities before the task is claimed; no Xero or other external writes are permitted.
- Answer free-form Finance questions through the permanent Finance terminal using selectively retrieved Business Financial Model, Operating Model and Finance Intelligence context.
- Persist the hash-linked Finance conversation under the Department Pilot runtime instead of storing chat inside the Financial Model or incrementing its revision.
- Expose answer reliability, canonical source labels, revisions and content hashes while retaining a deterministic evidence-grounded fallback when no model provider is available.
- Bound large offering and unit-economics collections before prompt construction, and omit operating or Boardroom context when the question does not require it.

Implemented controlled-action slice:

- Finance may stage only explicitly permitted draft actions using the shared proposed-tool-call contract.
- The complete payload is canonicalised and hash-bound before it is shown for approval.
- A positive decision is rejected unless the founder supplies the exact proposal payload hash.
- Approval cannot be reused for an altered payload, a different tool call, task, department or business.
- Approved proposals remain non-executable while the corresponding live connector permission is disabled.
- The Finance and Central Pilot queues show the exact JSON payload, hash and decision state.
- No external financial write is enabled by this slice.

Implemented forecasting and scenario slice:

- Derive a monthly planning baseline only from supported canonical management-account values.
- Run expected, upside and downside variants across a one-to-36-month horizon.
- Model revenue growth, price, volume, direct-cost and overhead changes, monthly hiring cost, one-off stock purchases and a protected cash reserve.
- Show monthly revenue, gross profit, operating profit, cash movement and closing cash plus reserve breaches.
- Store every scenario as a separate hash-bound planning record under `Finance/Scenarios` and index it in the File Cabinet.
- Summarise the latest scenario in Finance Department Intelligence and the durable Boardroom snapshot.
- Keep scenario assumptions explicitly labelled `modelled_not_actual`; never update accepted accounting facts or the historical Financial Model.
- Refuse to run when revenue, direct costs, overheads or opening cash are missing from the evidence baseline.

Implemented reconciliation slice:

- Read the latest Xero report evidence from the existing read-only sync; no Xero write scope is added.
- Compare accepted spreadsheet facts only when their reporting period matches the Xero period.
- Classify each comparable metric as matching, conflicting, missing in the spreadsheet, missing in Xero, missing a period or using a different period.
- Store a hash-bound reconciliation artifact under `Finance/Reconciliations` and project its compact summary into Finance Intelligence and the Boardroom.
- Allow the founder to record `keep_spreadsheet`, `prefer_xero`, `needs_investigation` or `no_change` as a review decision.
- Keep review separate from canonical replacement: even `prefer_xero` records intent but cannot silently edit accepted historical values.

Controlled outputs:

- Reports and analysis artifacts stored in the Finance file cabinet.
- Proposed actions staged for approval.
- No Xero writes in the initial implementation.
- Completion receipts and Finance Intelligence updates returned to the Boardroom.

Exit gate: a real approved Boardroom Finance package completes end to end and its verified result is available to a subsequent Boardroom meeting.

## Phase 6 — Recurring Finance work

- Add scheduled Finance tasks and recurring reporting.
- Support period-close checks, weekly cash updates, monthly management reporting and exception alerts.
- Persist schedules and last/next-run state in the backend.
- Require explicit approval before enabling any schedule that could cause an external side effect.

Exit gate: a recurring read-only Finance task runs, stores its report and updates Finance Intelligence without manual re-entry.

Implemented recurring-work and recovery slice:

- Durable weekly cash updates, monthly management reports, monthly period-close checks and daily cash-buffer/exception alerts.
- Hash-bound schedule records with enabled state, cadence, next/last run, run count, failure count and latest error.
- Hash-bound run artifacts stored below the Finance Business Container and indexed under `Finance/Recurring` in the File Cabinet.
- Compact latest-run projections into Finance Department Intelligence and the Boardroom snapshot.
- Read-only execution with `external_action_performed: false` on every recurring result.
- Backend-authoritative pause, resume, manual run and due-run operations.
- User-visible task diagnostics plus controlled retry, recovery and cancellation without replaying an external action.

Completed Finance finalisation, security and installed-application validation:

- The Finance review screen now builds the model through a canonical backend finalisation transaction. Large workbook analysis is no longer copied into browser storage before the transition, preventing storage-quota failures that previously made **Build Financial Model** appear unresponsive.
- The interface exposes progress and a recoverable error when canonical persistence fails; Finance is marked complete only after the Business Container returns a receipt.
- A backend-authoritative Finance security policy now classifies financial summaries, transaction detail, counterparty personal data, credentials and tokens, and payroll or tax-sensitive data.
- External financial writes remain denied by default. Credentials remain in macOS Keychain and are never stored in the Business Container, Pilot conversation or Boardroom context.
- Exact-payload approval remains mandatory for any staged action. Payments, transfers, tax filing, journal posting and accounting reconciliation posting remain prohibited.
- Xero connector success, retry and failure attempts now create durable, secret-free receipts under `Finance/Connector Receipts`, with provider status, retryability, error classification, request hash and an explicit `external_write_performed: false` marker.
- Installed-app testing has proved that approved Finance work, exact-payload decisions, recurring schedules, last-run/failure state and File Cabinet evidence survive a complete application restart.
- Route-shadow regressions affecting recurring work, scenarios and reconciliations were removed and covered by backend tests.
- The installed executable passed when launched directly. Normal macOS `open`/Finder launch did not remain alive reliably in the test environment, so application launch ownership remains a packaging exit-gate item rather than being misreported as complete.

Current Finance capability boundary:

- Finance can read canonical financial evidence and the existing read-only Xero reporting connection.
- Finance can produce management reports, KPIs, cash views, deterministic forecasts and scenarios.
- Finance can compare accepted spreadsheet summaries with Xero report summaries for aligned periods.
- Finance can hold grounded conversations, identify evidence gaps, schedule recurring read-only work and stage controlled proposals.
- Finance cannot yet match individual bank transactions to invoices or bills, post reconciliations, create journals, edit Xero, send debt-collection messages, issue invoices, make payments or file taxes.

The next Finance milestone is the Finance Director transaction and decision vertical:

1. Build a canonical ledger and transaction layer for accounts, bank transactions, invoices, bills, payments, journals, projects and tracking categories.
2. Add transaction-level matching, confidence scoring, duplicate and missing-record detection, exceptions and founder/accountant review.
3. Add an inspectable reconciliation workspace. Suggested matches begin as drafts; any accounting-platform write requires an individually enabled connector permission and exact-payload approval.
4. Extend the living Business Financial Model across profit and loss, balance sheet, cash flow, receivables, payables, working capital, budgets, jobs/projects, work in progress, pipeline and Products & Services unit economics.
5. Add proactive Finance Director signals for runway, protected cash reserve, margin erosion, overdue debtors, quote leakage, WIP, capacity and pipeline risk.
6. Convert recommendations into canonical Boardroom proposals and cross-department requests. Finance may propose invoice chasing, quote follow-up, pricing changes or demand-generation work, but Sales, Marketing and Operations retain their own execution permissions.
7. Add narrowly scoped connector adapters only after the review and receipt path is proven. Generic Finance write access must never be granted.

Exit gate: Finance can explain the current position, forecast the consequences of a decision, identify the transactions or operational drivers behind a risk, prepare a fully inspectable response, obtain the precise required approval, and return verified evidence to the Business Container and Boardroom.

Completed Finance Director transaction and decision vertical:

- The latest read-only Xero snapshot is normalised into a canonical, hash-verified transaction ledger covering accounts, sales invoices, supplier bills, bank transactions, payments, manual journals, tracking categories and projects.
- Large ledger collections are persisted as bounded JSONL records below `Finance/Ledgers`; compact counts, receivables, payables and overdue totals are projected into the living Financial Model, Finance Intelligence and File Cabinet.
- Transaction reconciliation proposes payment-to-invoice and bank-entry-to-invoice matches with confidence scores and reasons. It identifies duplicate records, unmatched entries and overdue receivables/payables in an exception queue.
- A founder or authorised accountant may accept a suggested match as a draft intent, reject it or mark it for investigation. Review does not post a reconciliation, journal or other change to Xero.
- The Finance Director operating view combines the canonical ledger, accepted Financial Model and Products & Services operating model into an evidence-labelled operating P&L, partial balance sheet, cash-flow proxy, working-capital view, projects, budgets, WIP, pipeline and unit economics.
- Net cash burn, rather than total expenses, drives the runway calculation. Signals cover protected-reserve breaches, runway, low margin, operating losses, overdue invoices, quote leakage, weak pipeline, WIP cash, missing unit economics and unverified evidence.
- Signals produce inspectable Boardroom-review proposals for invoice chasing, quote follow-up, pricing scenarios, controllable-cost review, Sales pipeline work, Marketing demand-generation options and Operations WIP completion. No proposal is routed, sent or executed merely because it was generated.
- The permanent Finance terminal now contains the Finance Director workspace, ledger controls, working-capital totals, warnings, proposals, suggested matches, review controls and open exceptions.
- New Xero collections remain read-only. Existing Xero connections may require reauthorisation for the added manual-journal and project scopes.
- Backend policy explicitly permits ledger construction, transaction matching and reviewed draft intent while continuing to prohibit reconciliation posting, journal posting, payments, transfers and tax filing.

Completed reconciliation intelligence and Xero handoff boundary:

- Known counterparties reuse only mappings previously confirmed by an authorised reviewer. Provider account codes already present on a Xero transaction remain visible as provider evidence.
- An unknown counterparty may be sent to the configured LLM with a minimised transaction description and the bounded, existing chart of accounts. The model may suggest only an existing account code; invented codes are discarded. Malformed confidence is treated as zero confidence.
- LLM classification is capped per run. Every new mapping requires human confirmation before it becomes reusable canonical memory. Low-confidence and unsupported classifications become clarification requests rather than bookkeeping entries.
- Xero's Accounting API does not expose bank-statement-line reconciliation. AION therefore never reports a bank entry as reconciled through the API. It creates an exact, inspectable manual handoff for an accepted draft match, binds approval to the payload hash and stores an immutable provider-limitation receipt in `Finance/Xero Reconciliation Handoffs`.
- Repeated receipt creation is idempotent, business-container isolation is enforced and the receipt records zero provider reconciliations and `external_write_performed=false`.
- Existing Xero connections now report missing scopes. When manual-journal or project read access is absent, Finance displays **Reauthorise Xero** before the next sync.

The remaining Finance production boundary is live-data validation of this hybrid review path and, where Xero genuinely exposes a supported write operation, a separately scoped provider adapter. Payment creation, journals, transfers and other mutations must never be conflated with bank-statement reconciliation and remain disabled until separately designed and approved.

## Phase 7 — Sales design and implementation

- Agree the Sales operating model before defining its Pilot capabilities or interface.
- Build Sales discovery, pipeline, customer, pricing and payment-term models.
- Add CRM, ecommerce and sales-source mappings, starting with imports and then selected connectors.
- Decide the role of inbound and outbound phone agents for qualification, calling and human handoff.
- Design email sales, follow-up and funnel workflows, including consent and approval boundaries.
- Configure the agreed `sales_pilot` capabilities for pipeline analysis, forecasting, follow-up preparation and revenue reporting.
- Send recognised revenue and customer-payment implications to Finance through canonical references.

Exit gate: Sales operates on the shared runtime and its results are reconciled with Finance and Products & Services.

## Phase 8 — Marketing design and implementation

- Agree the Marketing workspace, channels, attribution model, operating rhythm and automation boundaries before activation.
- Consolidate existing Marketing Pilot work into the shared runtime.
- Build canonical audience, offer, channel, campaign, budget, lead and attribution context.
- Link campaigns to Sales outcomes and Finance-approved budgets.
- Keep publishing and advertising spend approval-gated.

Exit gate: Marketing can receive an approved Boardroom campaign package, prepare work, record results and return evidence.

## Phase 9 — Support design and implementation

- Agree whether phone and messaging support are native capabilities or selected communication plugins.
- Build Support discovery and canonical customer-service context.
- Model channels, issue categories, service levels, policies, knowledge and escalation rules.
- Configure read-only analysis and drafted responses before enabling any outbound communication.
- Link product issues to Products & Services, retention signals to Sales, and cost implications to Finance.

Exit gate: Support completes the standard Department Pilot loop with controlled communication permissions.

## Phase 10 — HR and People design and implementation

- Design the visible organisation chart and accountability canvas before settling the HR workspace.
- Build the canonical people, role, responsibility and accountability model.
- Capture employees, contractors, founders, reporting lines, skills, capacity and employment cost.
- Define application roles and data/action permissions separately from job titles.
- Configure `hr_pilot` for workforce analysis, role clarity, capacity and policy support.
- Protect sensitive people data with stricter retrieval and visibility rules.

Exit gate: HR provides reliable people/capacity context to Operations and Finance while enforcing role-based access.

## Phase 11 — Operations design and implementation

Operations is deliberately last because it is the broadest function and depends on the canonical models established by the other departments.

- Agree the full operating-system scope before defining its Pilot interface or capabilities.
- Build the Operations discovery schema and canonical Operations model.
- Reuse Products & Services, labour, production, stock, procurement and capacity domains.
- Configure `operations_pilot` prompts, permissions, calculations and tools only after the design is approved.
- Support delivery planning, capacity, bottlenecks, work queues, supplier lead times and operational performance.
- Prove cross-functional dependencies through shared canonical references.

Exit gate: Operations completes the same discovery-to-Boardroom-to-execution-to-handback loop and coordinates agreed dependencies without becoming a second Central Pilot.

## Phase 12 — Connector expansion and catalogue scale

Prioritise connectors based on real user demand:

- QuickBooks and Sage for Finance.
- Shopify, WooCommerce, Magento and Square for catalogue, order and stock data.
- CRM and payment-source connectors for Sales and Finance.
- Supplier, purchasing and inventory sources for Operations and Procurement.

Move large catalogues and high-volume transactions from monolithic JSON documents to a canonical database/index with summary projection and selective retrieval.

Exit gate: high-volume data can be queried without placing entire catalogues or transaction histories into an AI prompt.

## Definition of production completion

The architecture is production-complete when:

- Every material value has provenance and verification state.
- Department tasks and conversations survive restart and sign-in.
- Approved Boardroom packages route reliably to specialist Pilots.
- Permissions are enforced in the backend, not only the interface.
- External side effects require exact, inspectable approval.
- Every execution produces a result or failure receipt.
- Artifacts are accessible from the correct Business Container file-cabinet location.
- Department Intelligence and Boardroom context update without duplicating raw evidence.
- Cross-department references remain consistent.
- Automated tests and packaged-app end-to-end tests cover the complete loop.
