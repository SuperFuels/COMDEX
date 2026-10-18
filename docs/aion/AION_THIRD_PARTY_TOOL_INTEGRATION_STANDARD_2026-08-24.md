# AION Third-Party Tool Integration Standard

**Date:** 24 August 2026  
**Status:** Version 1 implemented and test-enforced  
**Purpose:** Define one repeatable method for adding Gmail, Outlook, Xero, Sage, HubSpot, Salesforce, telephony, messaging, payments, web browsing, computer control and future tools to AION.

## 1. Core rule

Connecting a provider does not grant AION every power offered by that provider. Each useful operation is registered separately and must answer six questions:

1. What business outcome does this operation support?
2. What skill and verified business knowledge must AION use?
3. What exact external operation can the adapter perform?
4. What owner authority is required for this operation and payload?
5. What evidence proves success or failure?
6. How can the operation be stopped, revoked or reconciled?

AION therefore treats a tool as a collection of narrow powers, not as a single all-powerful connection.

## 2. The four-layer model

### 2.1 Intelligence and skill

This layer decides what should be done and why. It retrieves approved company knowledge, relevant experience, policies and constraints. It produces a structured intent such as `gmail.send_email`, `xero.create_invoice` or `hubspot.update_deal`; it never receives or handles provider credentials.

### 2.2 Connector and adapter

This layer translates a validated AION action into the provider's API, MCP server, webhook, local service, browser session or desktop-control operation. The adapter exposes named methods, input and output contracts, dry-run support, timeouts and idempotency behaviour. Arbitrary provider API calls remain blocked unless deliberately registered.

### 2.3 Authority and policy

Authority belongs to the workspace owner and is evaluated per action. Read access does not imply write access. Creating a draft does not imply sending it. Creating an invoice does not imply issuing it or making a payment.

Supported policy modes are:

- `ask_each_time`: show the exact payload and require approval;
- `auto_within_limits`: execute only inside explicit limits and allowlists;
- `full_access`: standing authority for that named action, still subject to adapter, safety and receipt gates;
- `blocked`: do not perform the action and optionally do not ask again.

Financial actions always require an amount, currency and owner-defined limit. High-risk actions cannot default to full access.

### 2.4 Receipt and evidence

Every external write must produce a durable local receipt. A receipt records the provider request identifier, action, workspace, payload hash, policy decision, timestamps, result identifiers and reconciliation status. If success cannot be verified, AION reports the action as unverified or failed; it must not invent completion.

## 3. Standard implementation sequence

Every provider must follow this order.

### Step 1 — Define the business scope

List the jobs the provider can perform for the business. Split them into atomic actions. Examples:

- Gmail: search, read, draft, send, reply, label and archive;
- CRM: read contact, create lead, update stage, add note and assign owner;
- Accounting: read balance, draft invoice, issue invoice, reconcile transaction and prepare payment;
- Voice: prepare call, place call, record consent, capture transcript and log outcome.

Do not register a universal “do anything” action.

### Step 2 — Define the connection

Choose OAuth 2, API key, webhook, MCP, local service, browser session or desktop control. Store credentials only in the local Vault. Declare the least-privilege scopes, a health check and a revocation method. Raw secrets must never appear in manifests, prompts, model context, logs or receipts.

### Step 3 — Define AION's required skill

State what AION must understand before using each action. For example, sending a sales email may require approved product facts, brand voice, contact identity, consent rules and the sales policy. The cognitive control plane retrieves these inputs before planning the action.

### Step 4 — Define each action contract

For each action define:

- stable provider-prefixed action ID;
- plain-English purpose;
- required skill IDs;
- validated inputs and outputs;
- risk tier, write status, reversibility and data classes;
- authority policy key and allowed modes;
- adapter method, timeout, dry-run and idempotency rules;
- receipt fields and read-after-write reconciliation;
- fail-closed behaviour and safe user message.

Use [`provider_tool_manifest.template.json`](../../backend/modules/connectors/templates/provider_tool_manifest.template.json) as the starting point.

Use [`AION_THIRD_PARTY_TOOL_IMPLEMENTATION_CHECKLIST.md`](templates/AION_THIRD_PARTY_TOOL_IMPLEMENTATION_CHECKLIST.md) as the human implementation and release record.

### Step 5 — Implement the adapter

An adapter should expose separate phases where relevant:

1. `health_check()` confirms the connection without changing state;
2. `prepare()` validates and normalises the payload;
3. `preview()` renders exactly what AION proposes to do;
4. `execute()` performs only the named action after authority evaluation;
5. `reconcile()` reads back provider state and proves the result;
6. `revoke()` or the central kill switch disables further use.

The adapter receives a short-lived credential reference from the Vault service, not a credential from the language model.

### Step 6 — Register authority

Map the action to the Pilot authority store. The UI must show the provider, action, current mode, limits and last use. If AION lacks authority, it should naturally ask whether the owner wants to approve this instance or change standing authority. A refusal is respected; `blocked` with `ask_again=false` prevents repeated prompts.

### Step 7 — Produce and verify receipts

Before a live write, hash the exact approved payload. After execution, capture the provider's response and reconcile it. The receipt must distinguish:

- `prepared` — a safe preview exists;
- `approved` — authority exists for this exact action;
- `attempted` — the adapter made a provider request;
- `verified_complete` — provider state confirms the result;
- `failed` — no verified completion;
- `uncertain` — request outcome needs reconciliation.

### Step 8 — Test failure as seriously as success

Required tests include:

- manifest validation;
- missing and revoked credentials;
- insufficient provider scope;
- blocked and ask-each-time authority;
- dry run without side effects;
- duplicate request/idempotency protection;
- timeouts, rate limits and malformed responses;
- receipt creation and read-after-write reconciliation;
- amount, currency, recipient and allowlist limits;
- proof that the language model cannot see secrets;
- proof that AION never claims an unverified action succeeded.

### Step 9 — Promote progressively

A provider progresses through `defined`, `connected`, `read_verified`, `draft_verified`, `sandbox_write_verified` and `live_verified`. UI wording must reflect the achieved stage. “Manifest valid” and “provider connected” are not claims of live execution.

## 4. Important action separations

| Provider area | Lower-risk actions | Higher-risk actions that require separate authority |
|---|---|---|
| Email | search, read, prepare draft | send, reply, delete |
| CRM | read pipeline, prepare note | create contact, change stage, apply discount |
| Accounting | read balances, draft invoice | issue invoice, reconcile, submit tax data |
| Payments | inspect bill, prepare payment | release payment, change beneficiary |
| Publishing | prepare content, preview campaign | publish, spend advertising budget |
| Voice | draft script, select contact | place call, record audio, make commitments |
| Browser/computer | inspect page, prepare form | submit form, download sensitive data, purchase or delete |

Browser and computer use are providers in this model. They do not provide universal permission; every consequential operation remains named, scoped and governed.

## 5. The machine-readable template

The canonical template is:

`backend/modules/connectors/templates/provider_tool_manifest.template.json`

The validator is:

`backend/modules/connectors/tool_manifest.py`

It currently rejects:

- embedded credentials;
- missing connection, skill, action or governance contracts;
- invalid or duplicate IDs;
- actions referencing unknown skills;
- external writes without receipts, idempotency or fail-closed behaviour;
- financial actions without an amount-limit and currency contract;
- high-risk actions that default to unrestricted full access.

## 6. Definition of done for a new tool

A third-party tool is complete only when all of the following are true:

- its manifest passes the validator and is hash-recorded;
- credentials are stored in the Vault with least privilege;
- its connection health check works;
- every enabled action has a real adapter method;
- AION selects the action from intent rather than a hard-coded response;
- the cognitive control plane retrieves the required skills and approved company knowledge;
- per-action authority is visible and enforced;
- previews show the exact proposed payload;
- external writes are idempotent and receipt-backed;
- provider state is reconciled after execution;
- failure tests pass;
- a kill switch and revocation path work;
- the UI states the truthful capability stage.

## 7. Claim boundary

This standard and template define how third-party tools must be integrated. They do not make every listed provider operational. Each provider still needs a real credential, adapter, action registration, policy mapping, tests and verified live receipt before AION may claim it can execute that operation.
