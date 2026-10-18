# Tessaris Sales Completion and HomeFixed A2A

Date: 9 August 2026

## Outcome

The provider-neutral Sales revenue spine now continues through controlled booking, quotation, customer acceptance, Operations handoff, Finance invoice preparation, communications, campaign consent filtering and independent outcome experiments. The HomeFixed website has also been prepared as both a human lead source and a machine-readable agent commerce surface.

## Canonical flow

Human website request or authenticated external-agent request enters the secured Sales intake endpoint. Tessaris deduplicates the customer, creates a canonical opportunity and retains source, campaign, consent and machine-agent authority evidence. Qualification, booking, quotation and handoff then use the same record.

No public request can create a confirmed booking, approve a quote, post an invoice, send a message, take payment or dispatch work. Those transitions remain independently controlled.

## Sales completion controls

- Timezone-aware internal availability and collision-checked booking preparation.
- Hash-bound exact booking approval before the opportunity becomes booked.
- Itemised quotations with quantity, net price, tax, expiry and terms.
- Exact quote approval and separate customer-acceptance evidence.
- Accepted quotes generate a delivery-ready Operations handoff and an exact-approval Finance invoice draft.
- Email and SMS follow-ups are prepared against the customer consent record and remain unsent until external execution is separately enabled.
- Campaign preflight excludes suppressed, unauthorised and incomplete contacts.
- Appointment, won, lost, no-response and not-qualified outcomes require an independent authority reference.
- Control/challenger experiments cannot promote automatically and remain inconclusive until both arms meet the frozen sample floor.

## HomeFixed public integration

The former long quote form is now a five-stage AION-guided conversation in the opening hero: service, project and urgency, location and access, contact details, then summary and consent. It collects explicit reply permission separately from optional marketing consent, plus UTM attribution, landing page and referrer evidence. It includes a honeypot, progressive browser validation, honest error handling and accessible live status. AION is deliberately a guided intake here: it does not invent prices or availability and tells the customer that a person reviews every request. The page no longer displays a false success without a backend acceptance.

The Vercel function sanitises and validates the request, restricts browser origin and rate-limits obvious abuse. When Tessaris is online it may forward directly; otherwise it writes the event to a private Vercel Blob store-and-forward queue. The HomeFixed telephone and WhatsApp contact is `+34 711 269 364` everywhere it is displayed or linked.

## Agent-to-agent integration

HomeFixed publishes its original `/agentmap.json` and `/.well-known/agentmap.json` manifests plus the current standard A2A discovery resource at `/.well-known/agent-card.json`, all declared in the HTML head. Compatibility rewrites also resolve the older `/.well-known/agent.json` and the informal `/.well-known/aion-agent` names to the standard card. The Agent Card accurately declares the governed HomeFixed commerce API as a custom HTTPS/JSON binding rather than claiming full generic A2A task semantics. Its public skill, bearer-authentication requirement and human-review boundary contain no credentials or internal URLs.

An external agent must provide its registered partner identity, bearer key, unique request id, customer identity, customer-authority reference, requested service, location and request. The edge handler forwards a normalized `external_agent` intake record. Tessaris hashes the customer-authority reference, creates a human-review opportunity and exposes only a bounded status projection to the same authenticated agent.

The response explicitly confirms that booking, payment and dispatch did not occur.

The human intake form also carries an explicit HTML `POST /api/lead` action. JavaScript progressively renders the five-stage experience and submits JSON, while the edge handler additionally normalizes conventional form-encoded field names and can generate the idempotency event identifier server-side. Static inspection can therefore see the real destination, and the backend is not dependent on the visual JavaScript layout.

## Durable external deployment

The HomeFixed project is hosted by Vercel. A private Vercel Blob store named `homefixed-leads` now accepts human and agent requests while the local Mac is offline. Queue contents are not publicly readable. Tessaris pulls with a separate server-side bearer secret, writes each event through the canonical secured intake endpoint, and acknowledges the private object only after canonical persistence succeeds. Duplicate delivery remains safe because both website and agent events carry frozen idempotency identifiers.

Agent acknowledgements replace the pending object with a bounded private status receipt. The same authenticated requesting agent can therefore distinguish `queued_for_human_review` from `accepted_by_tessaris` without gaining access to customer records, internal notes or other agents' requests.

The encrypted deployment configuration is:

- `BLOB_READ_WRITE_TOKEN`
- `TESSARIS_PULL_KEY`
- `A2A_PARTNER_KEYS`

Optional direct-delivery variables (`TESSARIS_INTAKE_URL`, `TESSARIS_A2A_INTAKE_URL`, `TESSARIS_A2A_STATUS_URL` and `TESSARIS_INTAKE_KEY`) remain supported for a future continuously hosted Tessaris receiver, but are no longer required for honest lead acceptance. The local `.env.local` holds the queue URL, queue pull secret, canonical endpoint id and intake token; none are committed to Git or exposed to browser code.

## Principal implementation files

- `backend/modules/aion_business/runtime/sales_completion_service.py`
- `backend/modules/aion_business/api/sales_completion_api.py`
- `backend/modules/aion_business/runtime/sales_revenue_service.py`
- `backend/modules/aion_business/api/sales_revenue_api.py`
- `desktop/mac/src/aion_sales_completion_workspace.js`
- HomeFixed `agentmap.json`
- HomeFixed `.well-known/agentmap.json`
- HomeFixed `api/lead.js`
- HomeFixed `api/agent/request.js`
- HomeFixed `api/agent/status.js`
- HomeFixed `api/queue/pull.js`
- HomeFixed `api/queue/ack.js`

## Verification

Focused Sales service and API tests cover exact approvals, collision rejection, quote arithmetic, customer-evidence acceptance, Operations and Finance handoff, consent filtering, outcome experiments, authenticated machine intake, acknowledgement-after-persistence and bounded A2A status. JavaScript, JSON and repository-diff checks cover the Tessaris and HomeFixed browser/serverless surfaces. A live HTTPS examination confirmed human and agent requests return `202`, both appear in the private queue, and an authenticated agent can read its safe queued state while booking, payment and dispatch remain false.
