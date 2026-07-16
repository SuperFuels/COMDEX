# AION Business Twin and Department Pilot Delivery Plan

## Outcome

Deliver a reusable, approval-gated Department Pilot system that turns canonical business evidence into Boardroom decisions, routes approved actions to specialist department agents, records their work and evidence, and returns verified results to the next Boardroom meeting.

The target operating loop is:

`Function discovery -> Canonical function model -> Boardroom context -> Approved Boardroom package -> Department Pilot task queue -> Pilot work and user conversation -> Artifacts and evidence -> Business Container writeback -> Boardroom handback`

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

## Phase 7 — Operations implementation

- Build the Operations discovery schema and canonical Operations model.
- Reuse Products & Services, labour, production, stock, procurement and capacity domains.
- Configure `operations_pilot` prompts, permissions, calculations and tools.
- Support delivery planning, capacity, bottlenecks, work queues, supplier lead times and operational performance.
- Prove Finance-to-Operations dependencies through shared canonical references.

Exit gate: Operations completes the same discovery-to-Boardroom-to-execution-to-handback loop.

## Phase 8 — Sales implementation

- Build Sales discovery, pipeline, customer, pricing and payment-term models.
- Add CRM, ecommerce and sales-source mappings, starting with imports and then selected connectors.
- Configure `sales_pilot` capabilities for pipeline analysis, forecasting, follow-up preparation and revenue reporting.
- Send recognised revenue and customer-payment implications to Finance through canonical references.

Exit gate: Sales operates on the shared runtime and its results are reconciled with Finance and Products & Services.

## Phase 9 — Marketing implementation

- Consolidate existing Marketing Pilot work into the shared runtime.
- Build canonical audience, offer, channel, campaign, budget, lead and attribution context.
- Link campaigns to Sales outcomes and Finance-approved budgets.
- Keep publishing and advertising spend approval-gated.

Exit gate: Marketing can receive an approved Boardroom campaign package, prepare work, record results and return evidence.

## Phase 10 — Support implementation

- Build Support discovery and canonical customer-service context.
- Model channels, issue categories, service levels, policies, knowledge and escalation rules.
- Configure read-only analysis and drafted responses before enabling any outbound communication.
- Link product issues to Products & Services, retention signals to Sales, and cost implications to Finance.

Exit gate: Support completes the standard Department Pilot loop with controlled communication permissions.

## Phase 11 — HR and People implementation

- Build the canonical people, role, responsibility and accountability model.
- Capture employees, contractors, founders, reporting lines, skills, capacity and employment cost.
- Define application roles and data/action permissions separately from job titles.
- Configure `hr_pilot` for workforce analysis, role clarity, capacity and policy support.
- Protect sensitive people data with stricter retrieval and visibility rules.

Exit gate: HR provides reliable people/capacity context to Operations and Finance while enforcing role-based access.

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
