# AION Customer Work Lifecycle

**Date:** 25 August 2026  
**Status:** implemented service spine and Sales workspace  
**Claim boundary:** local lifecycle records and safe drafts are operational. External calendar writes, messages, supplier orders, payments and accounting entries are only complete when a connected provider returns an execution receipt.

## Purpose

Tessaris must not split a service customer's history between an inbox, a Sales lead, a diary entry, a quote, a job and an invoice. Each genuine enquiry therefore owns one append-only customer work feed. Communications, Sales, Pilot, Operations and Finance can contribute to the same record under their permissions.

This is intentionally business-neutral. Roofing is a useful example, but the lifecycle is configurable for trades, professional services, field service, maintenance, installation, consulting and other appointment/quotation businesses.

## Canonical lifecycle

The version-one lifecycle is:

```text
enquiry -> qualification -> appointment -> survey -> quote -> negotiation
        -> won -> scheduled -> procurement -> in_progress -> completed
        -> invoiced -> paid -> review_requested -> closed
```

`lost` is a terminal alternative. A record cannot move backwards. Corrections are new events rather than destructive edits to history.

## Event contract

Every event records:

- event type, title and human-readable summary;
- lifecycle stage;
- structured details such as scope, material cost, labour, VAT, terms and dates;
- originating surface and provider;
- optional source reference and file attachments;
- responsible person and timestamp;
- action status: `recorded`, `draft`, `approval_required`, `approved`, `executed` or `failed`;
- an integrity hash;
- an execution receipt whenever an external action is claimed.

Supported events cover enquiries, inbound and outbound communications, calls, booking preparation and confirmation, notes, photographs, documents, voice instructions, quotation preparation/approval/send, customer replies, supplier requests, material quotes, scheduling, work start/completion, invoicing, payment, reconciliation and review requests.

## Governance rule

The system distinguishes four facts that must never be conflated:

1. A person or agent recorded information.
2. AION prepared a draft.
3. A human or policy approved an action.
4. A connected tool actually performed the action.

An event cannot use `executed` unless it includes a receipt reference. Consequently, a prepared appointment is not represented as a calendar booking; a quotation draft is not represented as sent; an invoice is not represented as paid; and a proposed Xero entry is not represented as reconciled.

## Current automatic connections

- A website, email, call or manually entered enquiry creates the customer work feed.
- Sales qualification writes a qualification event.
- A prepared appointment writes an approval-required booking event.
- Logged calls and messages write communication events.
- Sales pipeline changes write lifecycle status events.
- The Sales workspace displays the complete feed and permits authorised people to add photos/file references, voice instructions, scope, costs, terms and other updates.
- The same feed is available through provider-neutral read/write API routes for Pilot and future adapters.

## Target conversational workflow

For a field-service business, the intended interaction is:

1. An enquiry arrives through any connected channel and becomes a customer opportunity.
2. AION checks permitted availability and prepares or executes a site-visit booking according to the owner's authority policy.
3. The worker attaches photographs and dictates scope, materials, labour and quotation instructions to Pilot.
4. AION produces the company's standard VAT-inclusive quotation with approved terms and payment schedule.
5. The quotation is reviewed when required, sent through the chosen provider, and recorded with its provider receipt.
6. AION monitors replies and follows up according to the approved cadence.
7. A won quote becomes scheduled work. Supplier and subcontractor communications are prepared or executed under their separate permissions.
8. Work-start and completion evidence is added to the same feed.
9. AION prepares or sends the invoice, monitors settlement, records payment evidence, and proposes or performs accounting reconciliation through the connected accounting adapter.
10. The customer receives an approved review request, and the job closes with a complete evidence trail.

## Remaining live adapters

The shared lifecycle removes the data-model obstruction, but it does not simulate provider capabilities. The following adapters must individually satisfy the Tessaris tool-manifest and release-gate standard:

- calendar availability and booking;
- Gmail/Outlook read, draft and send;
- SMS, WhatsApp and calling;
- supplier email/order requests;
- quotation and document composition;
- Xero/Sage/QuickBooks invoicing and reconciliation;
- payment-status evidence;
- Google/Checkatrade or equivalent review requests.

Each adapter must declare readable data, permitted draft actions, approval policy, executable actions, idempotency key, receipt format and revocation behaviour.

## Principal implementation

- `backend/modules/aion_business/runtime/sales_revenue_service.py`
- `backend/modules/aion_business/api/sales_revenue_api.py`
- `desktop/mac/src/aion_sales_revenue_workspace.js`
- `backend/tests/test_sales_revenue_service.py`
- `backend/tests/test_sales_revenue_api.py`

