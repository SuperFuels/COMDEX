# Tessaris Marketing Intake, Sales-Agent Gate and Telephony Spine

**Date:** 9 August 2026  
**Status:** Implemented and locally verified  
**Canonical workspace:** Home Fixed

## Outcome

Tessaris now has one continuous commercial evidence path:

`secured website form or read-only Gmail -> canonical contact -> opportunity -> campaign attribution -> qualification -> governed Sales Agent -> exact-approved call -> signed call events -> supervised console`

The CRM remains provider-neutral. Gmail and Retell are adapters; neither becomes the system of record.

## Genuine Marketing intake

Website intake endpoints are created by a person with `sales.manage`. Each endpoint receives a cryptographically random token once; Tessaris stores only its SHA-256 digest. Incoming events require the token, an idempotency key, valid contact details and a bounded payload. The receiver also applies a honeypot and a 20-accepted-events-per-minute limit. Raw website payloads and remote addresses are not retained.

Accepted attribution fields are campaign, channel, content, landing page, referrer and the standard UTM fields. Consent records distinguish an inbound-response permission from outbound marketing permission. A repeated event is returned as the existing opportunity rather than duplicated.

The local receiver is production-shaped but not publicly hosted. A real website requires an HTTPS deployment or a controlled tunnel before it can reach the endpoint.

## Gmail intake

The existing OAuth connector now supports a deliberately narrow, read-only Sales query. Matching messages are converted into canonical opportunities using the Gmail message ID as the idempotency reference. Tessaris does not reply, mark read, label, move or delete the message.

The stale-token path was corrected: a Gmail 401 now forces an OAuth refresh even when the historical token record lacks an expiry timestamp. If Google rejects the refresh token, connector health changes to `reauthorization_required` instead of continuing to claim it is connected.

The current local Gmail grant has expired/revoked and Google rejects refresh. The connector must be re-authorized once in Tessaris before live messages can be imported. This is an external credential state, not a missing intake implementation.

## Executable Sales-Agent examination

Agent Studio no longer displays a decorative simulation count. It executes eleven frozen decision and safety scenarios:

1. cooperative customer;
2. confused customer;
3. price objection;
4. angry customer;
5. wrong number;
6. existing customer;
7. vulnerable person;
8. unsupported question;
9. explicit request for a human;
10. prompt manipulation; and
11. interruptions.

Every scenario checks the expected route, AI disclosure, absence of unsupported claims and absence of external action. Results are stored in a hash-bound simulation record. Promotion requires all required scenarios to pass and requires approval against the exact current playbook hash. Any change after review invalidates the approval.

Home Fixed passed **11/11** and the tested version is now `promoted_for_controlled_use`. This promotion covers the deterministic decision and safety policy. It does not claim that natural-language voice quality or production telephony has passed.

## Production telephony adapter

The Retell adapter implements the documented `POST /v2/create-phone-call` path. Credentials, caller number and agent ID are environment-only. A call can execute only when all of the following are true:

- the opportunity has an E.164 customer number;
- recorded permission permits the response;
- the exact playbook version is promoted;
- an authorised person prepares the call;
- a person with communication-approval authority approves the exact draft hash;
- the draft remains byte-for-byte unchanged;
- Retell credentials are configured; and
- `AION_SALES_LIVE_TELEPHONY_ENABLED` is explicitly enabled.

The provider receives only the bound workspace/opportunity metadata and approved dynamic variables. The current machine has no Retell production configuration, so execution correctly remains fail-closed.

## Signed events and live console

Retell webhook verification follows its documented HMAC-SHA256 contract: the signature timestamp must be within five minutes and the digest is calculated over the raw request body plus the original timestamp. Parsed/re-serialized JSON is never used for verification.

Only verified events enter the append-only telephony event ledger. The Sales workspace now shows prepared/approved/submitted calls, provider state, recent transcript turns, call status and disconnection evidence. The console exposes separate prepare, approve and start controls. It cannot collapse those stages into one click.

A publicly reachable HTTPS webhook remains required for production event delivery.

## Important files

- `backend/modules/aion_business/runtime/sales_revenue_service.py`
- `backend/modules/aion_business/api/sales_revenue_api.py`
- `backend/modules/local_node/local_node_runtime.py`
- `backend/desktop_app.py`
- `desktop/mac/src/aion_sales_revenue_workspace.js`
- `backend/tests/test_sales_revenue_service.py`
- `backend/tests/test_sales_revenue_api.py`
- `backend/tests/workflow_capsules/test_aion_sales_revenue_workspace_ui.py`

## Verification

- 11/11 Home Fixed Sales-Agent scenarios passed.
- The exact tested playbook was promoted for controlled use.
- Website authentication, honeypot handling, attribution and event deduplication passed.
- Gmail message conversion and deduplication passed against fixture evidence.
- Exact-hash playbook and call approvals passed.
- Live telephony remained disabled without credentials.
- Valid Retell webhook signatures passed; stale/invalid signatures failed closed.
- 30 focused Sales, Gmail and interface tests passed.
- The installed Tessaris backend reports healthy in desktop mode on CPU.

## Remaining production steps

1. Re-authorize Gmail once and perform a narrow live inbox import.
2. Deploy the website receiver and Retell webhook behind public HTTPS.
3. Configure a Retell number, agent and API key in the secure provider settings.
4. Run controlled voice-quality simulations and a single explicitly approved test call.
5. Add calendar availability and exact-approved booking execution.
6. Feed won opportunities into quotes, Operations delivery and Finance invoicing.

