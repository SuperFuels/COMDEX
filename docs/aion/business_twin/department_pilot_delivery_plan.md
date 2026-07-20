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
- **Phase 5 execution and conversation slices complete:** a queued Finance Boardroom action can now claim and run a permission-checked read-only management analysis, retrieve the exact hash-bound context, store its report under `Finance/Reports`, update Finance Department Intelligence, create an execution receipt and expose a durable handback to the next Boardroom snapshot. The permanent Finance terminal now uses a separate backend-authoritative conversation session, selectively retrieves canonical Finance evidence, labels reliability and sources, and leaves the Financial Model unchanged. Re-running a completed task is idempotent and execution or conversation failures are visible in the Pilot interface. Period comparisons, forecasting, scenarios and reconciliation remain the next Finance capability increments.
- **Verification baseline:** 56 focused contract, persistence, genuine Boardroom producer, routing API, Finance execution/handback, grounded conversation, desktop bridge, Finance/Xero, shared terminal and Products & Services tests pass. JavaScript and Python syntax checks pass; the packaged desktop verification is repeated at each milestone.

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

Remaining Finance capability increments:

- Period and budget comparisons, richer KPI reporting and management-account presentation.
- Cash forecasting and pricing, volume, cost, hiring, stock and downside scenarios.
- Xero-to-spreadsheet reconciliation with visible conflicts and freshness.
- Proposed Finance actions that use the exact-payload approval contracts before any controlled side effect.

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
