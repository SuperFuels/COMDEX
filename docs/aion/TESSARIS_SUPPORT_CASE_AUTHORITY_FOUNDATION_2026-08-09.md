# Tessaris Support Case and Authority Foundation

Date: 9 August 2026  
Reference deployment: Home Fixed  
Status: operational controlled-use Support workspace

## Outcome

The former Support discovery shell is now backed by a canonical case-management
and resolution-authority engine. It reuses Tessaris customer identity and
organisation authority rather than duplicating the Sales CRM.

The system now supports:

- canonical support cases and case numbers;
- protected multi-channel conversation timelines;
- provider email thread/message identifiers, telephone evidence references and
  content hashes;
- idempotent source references;
- matching against Sales contacts and opportunities, bookings, Finance customers
  and invoices, and Operations handoffs where canonical identifiers exist;
- universal issue categories, sentiment, priority and risk flags;
- configurable Support Agent goals, tone, channels, languages and service levels;
- approved FAQs, terms, warranties, refund policies and consumer-law sources;
- configurable action and remedy authority;
- exact-approval response drafts;
- read-only Gmail ingestion with provider-thread continuation and message-level
  deduplication;
- exact-approved Gmail draft creation in the original thread, without sending;
- token-bound, rate-limited website Support intake with honeypot and idempotency
  controls;
- Finance, Operations, Sales, human and legal/privacy handoffs;
- SLA deadlines and overdue reporting; and
- resolution only from customer, owner or provider-backed evidence.

No external reply, refund, cancellation, replacement, revisit or telephone call
is automatically executed. An exact-approved email may be placed in Gmail as a
draft; the customer receives nothing until a person sends it.

## Canonical flow

```text
email / website / telephone / manual contact
  -> canonical support case
  -> customer and business-record match
  -> issue, priority, sentiment and risk classification
  -> applicable policy / terms / rights sources
  -> bounded response or mandatory escalation
  -> exact approval
  -> later external connector execution
  -> customer, owner or provider-backed resolution evidence
```

## Desktop workspace

The old dark generic Pilot shell has been removed from the Support route. The
Support tab now has a dedicated light Case Centre containing:

- open, urgent, human-review, overdue and resolved metrics;
- the governed case queue and complete conversation timeline;
- Support Agent Studio and approved knowledge management;
- manual, website and Gmail intake controls;
- grounded reply preparation, exact approval and Gmail draft creation;
- human, Finance, Operations, Sales and legal/privacy escalation; and
- independently evidenced resolution.

The renderer uses an explicit Support mount and the canonical business identifier
already held by the desktop application. It no longer depends on the generic
department task renderer appearing first.

## Case evidence

Every conversation event records:

- direction and channel;
- complete bounded content;
- provider thread and message identifiers;
- evidence or recording references;
- actor and timestamp;
- a separate content hash; and
- an event hash.

The case itself is hash-protected. Cross-workspace access and modified records
fail closed. Source references make repeated provider delivery idempotent.

Incoming Gmail messages preserve provider message and thread identifiers. A new
message in an existing Gmail thread appends to the existing case; a repeated
message is ignored. New inbound content is reclassified and can raise priority
or trigger mandatory intervention.

Audio recordings and large attachments are referenced rather than embedded in
the case JSON. Their protected storage and retention policy remain connector
responsibilities.

## Universal case categories

The v1 taxonomy is:

1. information;
2. order, booking, delivery or job status;
3. billing or refund;
4. cancellation or return;
5. quality or fault;
6. technical help;
7. complaint;
8. account or data rights;
9. safety, legal or emergency;
10. feedback; and
11. unknown, requiring triage.

## Mandatory intervention

The system immediately creates or recommends human intervention for:

- a customer requesting a person;
- immediate safety risk;
- vulnerability;
- legal threats or consumer-rights uncertainty;
- fraud or chargeback;
- data-rights requests;
- discrimination or abuse;
- repeat failure; and
- unknown authority.

Heated language is recorded as sentiment and raises priority. It does not give
the agent permission to argue, admit liability or promise an unverified remedy.

The third same-category case for the same normalised email address or telephone
number is marked as a repeat failure, raised to urgent and escalated.

## Website Support intake

An authorised Support manager can create a dedicated website endpoint. Tessaris
returns the bearer token once and stores only its SHA-256 digest. The receiver:

- requires the exact workspace and endpoint token;
- requires an idempotency key;
- rejects payloads over 12,000 characters;
- uses a hidden website-field honeypot;
- permits at most 20 accepted events per minute per endpoint;
- stores a hash of the remote reference rather than a raw IP address; and
- creates a case only---never a refund, booking, promise or outbound message.

The route is
`POST /api/aion/support/public-intake/{workspace_id}/{endpoint_id}` with the
token in `X-Tessaris-Intake-Key`.

## Gmail Support connector

The connector performs a deliberately narrow read-only search. It does not mark
messages read, modify labels or send replies. An approved Support response moves
through three separate states:

1. `exact_approval_required`;
2. `approved_not_sent`; and
3. `provider_draft_created`.

Creating a Gmail draft records provider draft, message and thread identifiers
and appends an `outbound_draft` event to the case. The record continues to state
`external_message_sent: false`.

## Consumer and business rights

The legal-policy contract requires both applicable consumer-law authority and
approved business terms for rights-relevant decisions. This includes refund,
cancellation, quality/fault and account/data cases. Missing or jurisdictionally
mismatched authority creates `human_intervention_required`.

Tessaris does not claim independent legal authority. A policy document added by
the business records its source, source type, jurisdiction, effective date,
approver and immutable hash. Candidate sources are attached to a response for
human verification; source attachment is not represented as automatic legal
entailment.

## Refund and remedy controls

Agent Studio supports a per-business remedy matrix. The current v1 hard boundary
forces:

- automatic refunds off;
- automatic refund limit to zero;
- refunds and compensation to exact approval or human/Finance review;
- replacements and revisits to exact approval;
- legal-liability admission to never; and
- unverified dates or outcomes to never.

Even an approved response remains `approved_not_sent`; approval does not execute
a refund or customer communication.

## Home Fixed configuration

Home Fixed Support Agent version 2 uses:

- email, website, telephone and manual channels;
- English and Spanish;
- a four-hour first-response target;
- a 48-hour resolution target;
- Spain / European Union as the declared jurisdiction;
- no automatic refund authority;
- no assumed refund ceiling; and
- Finance and human review for monetary remedies.

No Home Fixed terms, refund policy or consumer-law text was invented. Until
authoritative sources are deliberately added, rights-relevant decisions fail
closed to a person.

## Main implementation

- `backend/modules/aion_business/runtime/support_case_service.py`
- `backend/modules/aion_business/api/support_case_api.py`
- `desktop/mac/src/aion_support_case_workspace.js`
- `backend/modules/aion_business/runtime/organization_authority_service.py`
- `backend/modules/aion_business/runtime/department_pilot_profiles.py`

The API prefix is `/api/aion/support`.

## Authority roles

The Owner / Director template receives full Support management, communication
approval and remedy approval capability. Two additional role templates exist:

- Support Manager: case management, escalation, communication and bounded remedy
  authority; and
- Support Agent: case work and drafting without approval authority.

Saved template roles inherit newly introduced capabilities without overwriting
business-specific additions.

## Verification

Twenty-nine focused Support, Sales-completion and organisation-authority checks
passed. They cover:

- customer and opportunity matching;
- deduplication;
- conversation evidence hashes;
- legal, safety and human-request escalation;
- forced refund and legal boundaries;
- consumer-rights source requirements;
- cited refund response preparation;
- exact approval without sending;
- Gmail case creation, thread continuation and repeated-message deduplication;
- provider draft creation without sending;
- website token rejection, honeypot protection and idempotency;
- removal of the generic Support Pilot shell;
- independently evidenced resolution;
- tamper rejection; and
- desktop Support workspace integration.

## Live controlled verification

After installation, a narrow real Gmail poll read five matching messages and
created five canonical Support cases. A second poll read the same five messages
and deduplicated all five. Gmail was not mutated and no reply was sent.

## Production-channel completion, 10 August 2026

Support now has a restart-persistent polling service. Each business stores an
immutable polling contract containing the acting person, interval, enabled
sources, a deliberately narrow Gmail query, last result, failure count and next
due time. Home Fixed is enabled at five-minute intervals for read-only Gmail and
the public website queue. The poller starts and stops with the Tessaris backend.
It deduplicates provider message identifiers and never sends a reply.

HomeFixed now publishes a customer Support form and `POST /api/support`. The
endpoint enforces same-site origin, contact permission, a honeypot, field limits
and per-instance rate limiting. A message is delivered directly to Tessaris only
when a private intake URL and key exist; otherwise it is stored in a private
Vercel Blob queue. Tessaris alone can pull and acknowledge that queue using a
server credential. The public browser never receives the pull credential.

A controlled production submission, clearly labelled as synthetic and not a
customer, returned HTTP 202, entered the private queue, became one canonical
Support case, and was acknowledged after import. No external reply or remedy was
executed.

## WhatsApp Business boundary

The provider-neutral Support channel now includes a Twilio WhatsApp adapter. It
supports signed-by-secret endpoint binding, MessageSid deduplication, case
continuation by customer number, text and protected media evidence. Media is
accepted only from trusted HTTPS Twilio hosts, limited to 16 MB and an explicit
MIME allow-list, downloaded with server credentials, hashed and stored outside
the case display record.

Outbound WhatsApp requires an exact-approved response, a verified business
sender, a live-execution flag and a customer-initiated message inside the
24-hour session. Outside that session it fails closed because an approved
message template is required. Home Fixed has no configured WhatsApp Business
sender yet, so the UI correctly reports `configuration_required` and no message
can be sent.

## Dedicated Retell Support voice

Retell now contains a separate published agent named `AION - Home Fixed Support
v1`. It has its own LLM, prompt, version and evidence record; it is not the Sales
agent. The prompt is deterministic and restricts the agent to existing-customer
Support. It must identify the customer/reference, collect the issue and desired
outcome, check safety and vulnerability, honour requests for a person, and end
with a factual summary.

The agent may not admit liability, promise a refund or compensation, change a
booking, take payment, invent policy or dates, or represent a remedy as approved.
It is published but deliberately unbound from the shared telephone number and
live execution remains false. Retell webhook ingestion verifies the provider
signature, accepts events only from this agent, hashes recording references and
stores the transcript and outcome evidence without persisting a raw recording
URL.

Retell's publish endpoint returned a successful empty response body. The client
was hardened to accept empty 2xx receipts and to discover and recover the exact
existing Support agent before any create operation, preventing duplicate agents.
Retell's version authority confirms version 1 is published. Version 2 is an
unbound draft created by Retell's version workflow and is not treated as live.

## Authoritative legal-source candidates

Two primary references were identified for legal/human review: Spain's current
consolidated Real Decreto Legislativo 1/2007 (`BOE-A-2007-20555`) and the European
Commission's Your Europe consumer-rights guidance. They have not been promoted
into executable Support policy. Every business must still supply its actual
terms, refund/cancellation policy and applicable jurisdiction, and an authorised
person or legal adviser must approve the intended interpretation. A URL is
evidence provenance, not autonomous legal authority.

- BOE consolidated source: `https://www.boe.es/buscar/act.php?id=BOE-A-2007-20555`
- European Commission consumer-rights portal:
  `https://europa.eu/youreurope/citizens/consumers/index_en.htm`

## Current honest boundary

Scheduled Gmail and public website intake, the governed WhatsApp adapter and the
dedicated Retell Support agent are implemented. The remaining external work is
to obtain and verify a WhatsApp Business sender, decide attachment/call-recording
retention, approve the business's terms and legal interpretations, and validate
the complete workflow on genuine customer cases. The dedicated Support voice
agent must not be bound to a production number until routing and supervised call
tests are approved. Gmail continues to create drafts only; direct sending remains
closed.

The production-channel sprint passed 27 focused Support, voice, interface and
organisation-authority tests. Live readback then confirmed: backend health OK;
background polling enabled with no source errors; six Support cases including
the controlled website validation; WhatsApp correctly closed pending sender
configuration; and Retell Support agent version 1 independently published but
unbound with live execution disabled.

## Unified Support workspace layout

The Support department route now renders one ordered workspace rather than three
independent full-height surfaces. A compact 176-pixel Support Director adviser
card appears first, the retained Boardroom assignment package appears second as
a collapsed expandable instruction contract, and the operational Support Case
Centre mounts immediately beneath it. The generic Support Pilot fallback and the
660-pixel spatial room are excluded from the Support route. Regression checks
bind this ordering and prevent the old full-screen renderer from returning.
