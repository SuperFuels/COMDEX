# Tessaris Finance Inbox: Receipt and Invoice Intake

**Implemented:** 9 August 2026  
**Status:** Operational local v1  
**Purpose:** Move daily transaction evidence from a photo or file into a governed, person-scoped accounting draft without prematurely writing to an accounting provider.

## Product boundary

The Finance Inbox is separate from the existing Finance artifact uploader. Annual accounts, spreadsheets and bank reports remain financial-model evidence. A receipt, supplier invoice, sales invoice, credit note or expense claim is a daily transaction document with a submitter, responsible card, allocation, review and approval lifecycle.

The current release accepts desktop file uploads, including phone images transferred to the Mac. It deliberately uses a channel-neutral intake contract so later mobile capture, phone share, forwarded email, an Agent mailbox, scanners and accounting connectors do not create parallel document ledgers.

## Operational workflow

1. Upload an image, PDF, CSV or XML document.
2. Hash and preserve the original bytes.
3. Deduplicate repeated uploads by content hash.
4. Link the document to the person, department, company card, project and cost centre.
5. Check that the person may submit expenses and owns the selected card.
6. Review the supplier/customer, date, net, tax, total, reference and description.
7. Allocate an account, tax code and provider-neutral accounting destination.
8. Calculate an approval route from reporting lines, Finance roles, Owner roles, department scope and amount limits.
9. Require an authorised approval decision.
10. Create a hash-bound `aion.finance.accounting_instruction.v1` draft.
11. Keep both `external_write_permitted` and `external_write_performed` false.

## Canonical container

`finance_inbox.json` stores:

- documents and their state histories;
- configured and planned intake channels;
- accounting destinations;
- future reviewer-confirmed mappings;
- governance settings;
- a compact operational summary; and
- an optimistic revision number.

The original document bytes live beneath the business container at:

```text
business_containers/{workspace_id}/finance/inbox/documents/{document_id}/original.{extension}
```

The canonical document identifier is derived from the SHA-256 content hash. Reuploading identical bytes returns the existing document rather than producing a duplicate expense.

## State model

```text
received
  -> needs_submitter | needs_review
  -> needs_information | awaiting_approval
  -> rejected | approved_for_accounting
```

An approved item is still only a provider-neutral accounting draft. It is not evidence that Xero, QuickBooks, Sage or another platform was changed.

## HR authority integration

The Inbox consumes `organization_authority.v1` for:

- active person validation;
- expense submission capability;
- department scope;
- assigned company-card ownership;
- reporting manager;
- Finance Controller and Owner/Director fallbacks;
- approval capability; and
- transaction approval limits.

A card assigned to another person is rejected. Approval fails closed when the decision maker lacks `expenses.approve`, is outside the department scope or is below the required amount limit. A route that can only self-approve is exposed rather than hidden.

## Supported accounting destinations

- Business expense / spend-money draft
- Supplier bill / accounts-payable draft
- Sales invoice / accounts-receivable draft
- Credit note / credit-adjustment draft

Provider adapters must translate the approved canonical instruction into the exact target-provider schema. No generic Finance write permission is introduced.

## Intake channels

| Channel | Current state | Adapter contract |
|---|---|---|
| Desktop upload | Enabled | Multipart upload |
| Phone photo / mobile app | Planned | Same canonical inbox contract |
| Phone share sheet | Planned | Authenticated upload link |
| Finance Agent mailbox | Planned | Email adapter |
| Forwarded email | Planned | Email adapter |
| Scanner / watched folder | Planned | File adapter |
| Accounting provider | Planned | Provider adapter |
| External API | Planned | Signed API |

Every adapter must preserve the original bytes, content hash, received time, source channel and source reference. It must also establish or request a submitter identity. Email address alone may be used as a matching hint but not as sufficient authority for consequential actions.

## API surface

```text
GET  /api/aion/business/finance-inbox/channels
GET  /api/aion/business/finance-inbox/{workspace_id}
POST /api/aion/business/finance-inbox/{workspace_id}/documents
GET  /api/aion/business/finance-inbox/{workspace_id}/documents/{document_id}/file
PUT  /api/aion/business/finance-inbox/{workspace_id}/documents/{document_id}/review
POST /api/aion/business/finance-inbox/{workspace_id}/documents/{document_id}/decision
```

## User interface

The Finance Pilot now displays a light Finance Inbox above the existing Finance operating view. It includes:

- needs-review, awaiting-approval, approved-draft and external-write counters;
- an upload form with mobile camera capture semantics;
- person, department, card and project selection;
- original-image preview or original-document link;
- structured accounting review;
- explainable approval routing;
- approve, reject and request-information decisions; and
- a channel roadmap showing how phone and mailbox delivery converge on the same inbox.

## Audit and projection

Receipt, review and decision events are appended to the `finance_inbox` audit stream. The Finance Department Intelligence and Boardroom runtime projections receive only operational counts and status, not the original image or sensitive transaction detail.

## Verification

- Python compilation passed.
- JavaScript syntax validation passed.
- Nine focused service and API tests passed after adding a production-relative-path regression.
- Eighty-four combined Finance, HR authority and operating-model tests passed before final live verification.
- Packaged desktop health returned `status=ok`.
- Live browser testing completed upload, review, HR-routed approval and exact-draft preparation.
- The live approval evidence showed `external_write_permitted=false`, `external_write_performed=false` and zero external writes.
- The packaged application settled to negligible CPU use after startup.

## Honest remaining work

### Automated extraction

Image and PDF extraction is not yet enabled in this release. The reviewer currently enters or confirms the accounting fields from the protected original. The next extraction adapter should produce field-level suggestions and confidence, never accepted facts. Low-confidence fields, tax inconsistencies and totals that do not balance must remain visible for review.

### Authenticated mobile capture

A mobile app or mobile web capture page must bind the session to a person and workspace. It should support direct camera capture, gallery selection, upload retry and offline queueing. Authentication is required before the channel can safely infer the submitter.

### Finance Agent mailbox

The mailbox adapter must:

1. receive emails and attachments through a provider webhook or bounded poller;
2. verify provider signatures where available;
3. preserve message and attachment identifiers;
4. hash and deduplicate each attachment;
5. match a verified sender to an organisation person where possible;
6. quarantine unmatched or suspicious senders;
7. ignore executable and unsupported attachments; and
8. submit accepted attachments through the same canonical intake service.

### Provider posting

Approved drafts still require provider-specific adapters, exact-payload approval, idempotency keys, restricted OAuth scopes, retry classification and immutable outcome receipts. Supplier bills, expenses, sales invoices and credit notes must be implemented as separately authorised capabilities. Payments, transfers, journals and tax filing remain outside this authority.

### Production security

True multi-user deployment still requires authenticated person binding, backend viewer enforcement, malware scanning, encryption/key management, data retention controls and stronger step-up authentication for sensitive financial actions.

## Key implementation files

- `backend/modules/aion_business/contracts/business_containers.py`
- `backend/modules/aion_business/runtime/business_container_repository.py`
- `backend/modules/aion_business/runtime/finance_inbox_service.py`
- `backend/modules/aion_business/api/finance_inbox_api.py`
- `backend/desktop_app.py`
- `backend/main.py`
- `desktop/mac/src/aion_finance_inbox_workspace.js`
- `desktop/mac/src/index.html`
- `backend/tests/test_finance_inbox_service.py`
- `backend/tests/test_finance_inbox_api.py`
- `backend/tests/workflow_capsules/test_aion_finance_inbox_ui_lock.py`

## Recovery

The pre-Finance-Inbox application is retained at:

```text
/Applications/Tessaris.app.backup-20260809-before-finance-inbox
```

The current operational application is installed at:

```text
/Applications/Tessaris.app
```
