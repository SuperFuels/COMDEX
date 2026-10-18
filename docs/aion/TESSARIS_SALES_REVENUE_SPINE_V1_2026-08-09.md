# Tessaris Sales Revenue Spine v1

**Date:** 9 August 2026  
**Status:** Operational internal vertical slice; external communications and telephony remain closed.

## Purpose

The Sales Revenue Spine is the canonical provider-neutral commercial ledger between Marketing, Sales conversations, appointments, Operations, Finance and the Boardroom. HubSpot, calendars, email, SMS and telephone platforms are adapters around this ledger rather than alternative sources of authority.

## Implemented capability

- Canonical company, contact and opportunity records.
- Deterministic contact deduplication by normalised email or telephone number.
- Deterministic company deduplication by normalised company name.
- Source-event idempotency using provider/source references.
- Marketing attribution capture for campaign, channel, content and UTM fields.
- Explicit contact-permission and outbound-campaign consent evidence.
- Governed pipeline stages and an allowed-transition graph.
- Evidence-based qualification with required fields, missing evidence, risk flags and a bounded score.
- Human handoff with named owner, reason and urgency.
- Appointment preparation with exact payload hash; no calendar write or notification.
- Provider-neutral conversation sessions for app voice, telephone, email, SMS, web chat and manual notes.
- Mandatory AI identity disclosure for voice and telephone sessions.
- Structured conversation outcome, disposition, summary, next action and human-takeover evidence.
- Hash-bound records, workspace isolation and append-only activity audit.
- Sales summary and latest-opportunity projections into Department Intelligence and the Boardroom.
- A light Sales workspace with Today queue, pipeline, qualification, handoff, appointment and conversation controls.
- Sales Agent Studio v1 containing qualification questions, guardrails and eleven required safety scenarios.

## Authority

Sales uses the organisation authority model. New application roles are available for Sales Manager and Sales Representative. Existing owners retain access through `department.manage_all`; this preserves existing businesses without silently rewriting their saved HR authority record.

The Sales Pilot profile is enabled with safe internal capabilities. External provider writes remain absent from the approved-live permission list.

## Canonical storage

Records are stored beneath:

```text
.runtime/AION_BUSINESS/business_containers/<workspace>/sales/revenue_spine/
  companies/
  contacts/
  opportunities/
  playbooks/
  audit.jsonl
```

Each mutable record carries a canonical hash that is independently verified on read. Cross-workspace reads and unexpected record mutation fail closed.

## HTTP surface

```text
GET  /api/aion/sales/{workspace}
POST /api/aion/sales/{workspace}/enquiries
POST /api/aion/sales/{workspace}/opportunities/{id}/qualification
POST /api/aion/sales/{workspace}/opportunities/{id}/appointments/prepare
POST /api/aion/sales/{workspace}/opportunities/{id}/handoff
POST /api/aion/sales/{workspace}/opportunities/{id}/stage
POST /api/aion/sales/{workspace}/opportunities/{id}/sessions
POST /api/aion/sales/{workspace}/opportunities/{id}/sessions/{session}/complete
```

The API is mounted in both the historical COMDEX backend and the lean Tessaris desktop backend.

## Safety boundaries

The current version does not:

- Initiate an external telephone call.
- Send email or SMS.
- Write a contact or deal to HubSpot.
- Create an external calendar event.
- Notify a customer about an appointment.
- Record a call without explicit recording-consent evidence.
- Reject a customer solely because of a qualification score.
- Deploy the Sales Agent playbook before its safety simulations pass.

## Marketing boundary corrected

The historical Website Enquiries Feed contained a demonstration fallback row. That row is not treated as real evidence and is not imported into Sales. Once genuine Sales opportunities exist, their canonical records become the feed projection. A secured public form/webhook intake and a governed Gmail-to-Sales transformer remain separate production tasks.

## Remaining work

1. Connect genuine Marketing forms, Gmail intake and campaign events to the enquiry endpoint with authentication, rate limiting and abuse controls.
2. Build the executable eleven-scenario simulator, QA evaluator, playbook version promotion and rollback.
3. Add live conversation streaming, transcription, uncertainty indicators, supervisor takeover and warm transfer.
4. Implement a managed production telephony adapter, initially Retell or Twilio, behind the provider-neutral session contract.
5. Connect calendar availability, exact booking approval, reminders, rescheduling and no-show recovery.
6. Add controlled email/SMS drafts and approvals.
7. Add HubSpot import, export, webhooks and conflict resolution while keeping Tessaris canonical.
8. Complete quote, won/lost, Finance customer/invoice and Operations delivery handoffs.
9. Feed actual revenue, margin, cancellation and complaint outcomes back to Marketing and the Boardroom.
10. Validate the complete flow on one genuine warm lead before enabling outbound campaign calling.

## Verification

Focused tests cover deduplication, company identity, authority, qualification, pipeline transitions, appointment boundaries, voice disclosure, structured outcomes, workspace isolation, tamper detection, API behaviour and visible interface contracts. The Tessaris desktop application was rebuilt and the live Home Fixed Sales endpoint was verified healthy.
