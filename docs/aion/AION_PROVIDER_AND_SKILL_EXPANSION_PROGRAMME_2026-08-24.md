# AION Provider and Skill Expansion Programme

**Date:** 24 August 2026  
**Status:** Initial governed provider contracts and curated skill catalogue installed

## Purpose

AION should use the tools a business already relies upon while keeping credentials local, authority explicit and every consequential action independently verifiable. A provider appearing in the catalogue is not enough. It becomes releasable only after AION understands it, a real adapter exists, credentials are healthy, controlled practical tests pass and the provider confirms the result.

## Standard provider pipeline

Every provider follows the same release path:

1. **Choose the connection method.** Prefer an official MCP server when it exposes the required actions and evidence. Otherwise use OAuth 2, a scoped API key, signed webhooks or a local service.
2. **Store credentials in the local Vault.** The model receives a capability reference, never the raw secret. Grants use the least privilege necessary and can be revoked independently.
3. **Register a tool manifest.** Define atomic actions, contracts, scopes, risk, authority modes, idempotency, receipts, reconciliation and fail-closed behaviour.
4. **Train AION on the provider.** Teach its objects, identifiers, state transitions, action semantics, errors, rate limits, permissions, business policies and reconciliation rules.
5. **Test without side effects.** Contract tests, mocked failures, permission attacks and dry runs must pass.
6. **Test in a sandbox.** AION performs an unfamiliar practical task and reads the result back from the provider.
7. **Run one approved live action.** The user approves the exact payload. AION performs it and independently reads the provider state back.
8. **Test failure and revocation.** Duplicate actions, timeouts, expired credentials and the kill switch must fail safely.
9. **Release progressively.** Start with `ask_each_time`; expand to bounded automatic authority only after reliable receipts and user choice.

## Meaning of readiness labels

- **Curriculum ready:** AION has a syllabus and action vocabulary.
- **Knowledge ready:** AION passed closed-book, adversarial and retention tests about the provider.
- **Adapter ready:** Real code exists and dry-run/contract tests pass.
- **Credential ready:** A workspace grant exists and health checks pass.
- **Sandbox verified:** A controlled write and provider read-back passed.
- **Live verified:** An explicitly approved live action, provider read-back, failure test and revocation test all passed.

Only the final label permits a claim of verified live execution. Training alone never creates credentials or authority.

## Priority-six audit

| Provider | Intended capability | Current repository position | Required before live claim |
|---|---|---|---|
| Gmail | Search, draft, send and reply | Adapter foundations present | Healthy workspace OAuth grant; approved send; Gmail read-back; failure/revocation receipts |
| Microsoft Outlook | Search, draft, send and reply through Graph | Contract and curriculum ready | Mail adapter; OAuth flow; sandbox test; approved send; Graph read-back; failure/revocation receipts |
| Xero | Cash/invoice reading, draft/issue invoice, reconciliation | Read/export/handoff foundations present | True write adapter; OAuth tenant connection; sandbox invoice; approved live action and Xero read-back |
| HubSpot | Contacts, deals, notes and pipeline | OAuth and tool foundations present | Healthy workspace grant; approved write; CRM read-back; failure/revocation receipts |
| Twilio Voice | Prepare/place calls and record outcomes | Credential/webhook/call-history foundations present | Consent evidence; approved outbound call; Call SID status read-back; failure/revocation receipts |
| Stripe | Customer payment intents, capture and refund | Webhook verification and contract ready | Execution adapter; Stripe test-mode payment/refund; tightly limited approved live action; read-back and revocation receipts |

**Important:** Stripe covers customer payment collection and refunds. Paying suppliers or moving bank funds is a separate integration requiring an appropriate banking/Open-Banking provider, stronger identity controls and transaction-specific limits.

## Curated AION business skill library

The first catalogue contains 100 skills across communications; sales and CRM; finance; productivity and documents; work management; marketing and social; support and people; research and intelligence; software and automation; and operations and commerce.

It includes the major small-business tool families: Gmail, Outlook, Slack, Teams, WhatsApp Business, HubSpot, Salesforce, Pipedrive, Zoho CRM, Xero, QuickBooks, Sage, Stripe, Google Workspace, Microsoft 365, Asana, Trello, ClickUp, Monday, Jira, Notion, Airtable, Shopify, WooCommerce, Zendesk, Intercom, GitHub and governed browser/computer use.

Hermes' built-in and community lists are useful discovery sources, particularly for research, documents, debugging, inbox triage and local productivity. They are not copied wholesale. A large community catalogue contains duplicates, abandoned code, unsafe permissions and capabilities irrelevant to business users. AION therefore uses a reviewed core catalogue plus a controlled request pipeline.

## Weekly and requested expansion

New integrations are ranked by customer demand, business value, provider stability, permission risk and ability to produce a verifiable outcome. The weekly cycle is:

1. promote the highest-value requested providers into contract development;
2. complete provider curriculum and adversarial assessment;
3. implement one narrow end-to-end action before broadening scope;
4. run sandbox and approved live verification;
5. publish verified actions and authority choices in the Vault;
6. retain failed experiments and repairs as AION experience capsules.

Community skills enter quarantine first. Their source, licence, dependencies, network destinations, secret access and command surface are reviewed before installation. They never inherit business credentials automatically.

## Required release evidence

The machine gate requires all of the following before `live_verified`:

- manifest contract hash;
- provider-knowledge assessment receipt;
- adapter contract-test receipt;
- dry-run receipt;
- credential-health receipt;
- sandbox write/read-back receipt;
- exact approved live-action receipt;
- independent provider read-back receipt;
- failure-path receipt;
- credential-revocation receipt.

The governing implementation lives in:

- `backend/modules/connectors/tool_manifest.py`
- `backend/modules/connectors/priority_provider_catalog.py`
- `backend/modules/connectors/provider_release_gate.py`
- `backend/modules/connectors/aion_business_skill_catalog.py`

## Claim boundary

The manifests, curricula and catalogue are installed. They do not establish that a user has connected provider accounts, that every adapter is complete, or that any of the six providers has passed the complete live-verification gate. Those claims must be generated only from actual workspace receipts.
