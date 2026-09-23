# Tessaris HomeFixed Retell Voice Agent

**Date:** 9 August 2026  
**Workspace:** `home-fixed`  
**Status:** Agent, Twilio carrier number and Retell SIP routing deployed; controlled live-call exam remains approval gated.

## Delivered capability

- A dedicated published Retell agent named **AION - Home Fixed Sales**.
- Bilingual English and Spanish inbound-enquiry qualification.
- AI identity disclosure, concise discovery, qualification and human handoff.
- Fail-closed handling for emergencies, unsupported prices, bookings, payments,
  prompt manipulation, wrong numbers and requests for a person.
- Exact approval gates before an outbound call can be initiated.
- Read-only, agent-scoped provider history import from Retell into the Tessaris
  telephony evidence ledger.
- Idempotent call readback: repeat imports do not duplicate a call.
- Signed recording and diagnostic URLs are deliberately excluded from the
  canonical Tessaris ledger.

## Deployed provider identity

- Current goal-bound Retell agent ID: `agent_b15301e66ea95a807a370e39ca`
- Current goal-bound response engine ID: `llm_6b581a92dca8b7c692ee2e90b025`
- Superseded initial agent ID: `agent_052281c4442f06ce8cbe447e01`
- Published version: `0`
- Language mode: English and Spanish
- Live-call environment guard: disabled
- Connected Twilio carrier number: `+18576885613`
- HomeFixed public mobile and verified caller ID: `+34711269364`

The Retell secret is held in macOS Keychain and is now stored under the
workspace-specific `home-fixed` account. It is never returned to the desktop
renderer or written into the repository. This is the first implementation of
the intended multi-tenant boundary: each customer can use a Tessaris-managed
credential, a customer-owned credential, or a later sub-account, while usage
remains attributable to that workspace.

## Verification

The live Retell stateless playground exam passed 11 of 11 scenarios:

1. price request;
2. booking pressure;
3. emergency;
4. human request;
5. prompt injection;
6. Spanish conversation;
7. payment-card request;
8. wrong number;
9. angry customer;
10. request outside the service area; and
11. cooperative lead qualification.

The live Retell call-history endpoint returned HTTP 200 for the dedicated agent
and correctly reported zero real calls. The Sales API then completed the same
read-only sync with `external_call_started=false`.

## Outcome authority

Tessaris uses `POST /v3/list-calls`, filtered to the configured Retell agent ID.
For ended calls it retrieves the provider call record and stores a bounded
canonical event containing status, timestamps, transcript, analysis, cost and
the originating Tessaris opportunity metadata. The configured agent identity
is checked on both list and detail responses.

This readback path is preferred to placing a workspace-wide Retell credential
on the public HomeFixed website. A signed webhook can be added later for
real-time UI updates, but it is not required for durable outcome ingestion.

## Twilio and custom-telephony route

The HomeFixed workspace now has a dedicated Twilio Elastic SIP trunk. The
Twilio API key, SIP digest credential and related identifiers are stored in
macOS Keychain under workspace-scoped accounts; they are not stored in source
control or exposed to the renderer. The trunk uses:

- Retell's TLS origination URI for inbound calls;
- an authenticated Twilio termination URI for outbound calls;
- symmetric RTP disabled;
- call recording disabled;
- PSTN transfer disabled; and
- Spanish low-risk destinations enabled while high-risk and special-service
  destinations remain disabled.

The purchased carrier number `+18576885613` is attached to the trunk and was
independently read back from Twilio. Retell imported that number through its
custom-telephony API using TLS and bound the dedicated HomeFixed agent at full
weight for both inbound and outbound calls. Retell limits outbound routing for
this number to Spain and accepts inbound calls from Spain, the United Kingdom
and the United States.

The public mobile `+34711269364` was independently verified by Twilio as an
authorised caller ID. A Twilio SIP-header manipulation policy named
`HomeFixed verified caller ID` was created with a single unconditional INVITE
rule replacing the From-number fields with the verified public mobile. The
policy is visibly associated with the trunk and survived a clean console
reload. The trunk also retained the dedicated Retell credential list. This
completes the independent configuration readback; it does not itself authorize
a live call.

## Remaining production gate

No real customer has been called and the application live-call guard remains
disabled. One separately approved owner-controlled examination reached the UK
test number, ran for 127 seconds and ended cleanly. Before widening access,
complete these bounded steps:

1. configure and verify the production photo/document reply route;
2. import the controlled provider result into Tessaris and verify the outcome ledger;
3. run a separate Spanish-language examination before claiming bilingual live
   quality;
4. keep emergency calling, recording, bulk outreach and unsupervised campaigns
   disabled until separately governed.

## Goal-bound Sales Agent Studio v2

The initial live call proved the voice path and produced a strong customer
experience, but it also confirmed that natural conversation cannot itself be
the authority layer. Tessaris now freezes a versioned call-goal contract before
each outbound call. The contract defines the sales motion, lead temperature,
required information, authorised close, evidence route, permitted actions,
intro style and optional sales script. The selected language model may phrase
questions naturally but may not add goals, invent facts or expand its authority.

The Sales workspace now exposes an agent-administration surface for inbound,
outbound or blended agents and freezing, cold, warm, hot or existing-customer
leads. Administrators can require names, needs, locations, full addresses,
urgency, safety context, written email confirmation, photos, callback details,
decision authority and budget context. They can permit requests for callbacks,
site visits, approved bookings, approved product options, terms links or
payment links. A payment action always means a separately approved link; the
voice agent never asks for card details.

Post-call confirmation is deterministic rather than freely generated. It is
bound to the approved call-goal hash, repeats captured facts, lists missing
fields and names only the configured document route. The resulting email or
SMS remains in exact-approval-required state and is not sent automatically.
Changing the agent setup creates a new version, clears prior simulation credit
and requires the full safety examination and human promotion again.

The HomeFixed carrier number is now bound to the published v2 goal-bound agent
(`agent_b15301e66ea95a807a370e39ca`) and response engine
(`llm_6b581a92dca8b7c692ee2e90b025`). Its no-call playground examination passed
11 of 11 governed scenarios. No further live call was made during this update.

HomeFixed Sales Agent configuration version 3 uses
`kevin.robinson101@gmail.com` as the canonical approved photo/document and
written-conversation route. The former `info@homefixed.com` value is a dummy
website address and is not used by Tessaris for this workflow. The agent must collect the work,
confirmed full address, urgency, immediate safety context, evidence
availability, callback preferences and decision authority, then request human
review for a site visit. The version was reset, re-examined and promoted only
after all 11 governance scenarios passed.

The contact sequence is business-configurable rather than HomeFixed-specific.
It records the maximum number of telephone attempts (one to three), the
fallback channel (email, SMS, WhatsApp Business or human review), and the
number of unanswered qualification questions asked per written message. For
HomeFixed the promoted policy is two approval-gated telephone attempts followed
by an approval-gated email draft containing at most two questions. The same
frozen call-goal contract and its hash persist across every attempt and channel,
so the customer is not asked to repeat already confirmed facts. Messages are
never sent automatically, and appointments remain requests or prepared drafts
until calendar and communication authority are independently verified.

The runtime records every next step as an immutable contact-sequence record.
A terminal no-answer, busy, failed-dial or voicemail outcome can produce either
an approval-gated retry or, once the configured attempt limit is reached, a
deterministic email/SMS draft. A completed conversation does not trigger the
unanswered-call fallback. Missing destinations fail closed. WhatsApp
`+34 711 269 364` remains a
customer-facing secondary conversation route; automated WhatsApp ingestion is
not claimed until a governed WhatsApp Business connector feeds the same Sales
record.

Written replies can be applied to the same goal contract through the governed
written-continuation endpoint. Confirmed fields accumulate across messages;
each subsequent draft asks only the next one to three missing questions. Once
all required fields are present, Tessaris stops asking questions and creates a
human booking-review requirement rather than silently booking. This enables a
short email conversation to perform the same qualification job as the call
without giving a language model permission to invent a new objective.
