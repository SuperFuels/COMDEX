# Pilot Unified Mobile Component and Risk Registry

Status: Stage 4 coded implementation complete; Stage 5 identity/task integration active — 3 September 2026

This registry assigns authority to existing systems. The unified mobile app consumes adapters and
versioned contracts; it does not become a new owner of Personal Pilot or Boardroom data.

| Domain | Authoritative implementation | Mobile integration | Decision |
| --- | --- | --- | --- |
| Private persona, guardian profile, trusted phone, consent and shared-TV identity | `backend/modules/aion_fabric/private_identity.py` | Read/write through a versioned Pilot adapter | Reuse and harden |
| Personal tasks, lists, reminders, contacts and agent inbox | `backend/modules/aion_fabric/pilot_inbox.py` | Project into unified Inbox and Actions | Reuse |
| Email/messaging drafts, approval and delivery receipts | `backend/modules/aion_fabric/communication.py` | Governed service cards | Reuse and provider-qualify |
| Calendar planning and Google authorization | `backend/modules/aion_fabric/calendar_planning.py`, `google_oauth.py` | Personal Actions | Reuse and provider-qualify |
| TV/device identity, capabilities and control | `backend/modules/aion_fabric` | Devices and TV surfaces | Reuse |
| Real-time chat, voice note, PTT and thread journal | `backend/modules/glyphnet` and `Glyph_Net_Browser` | Unified Inbox transport adapter | Reuse and harden |
| Organisation, departments, agents, dashboards, files and business decisions | `backend/modules/aion_business` and Boardroom runtime | Workspace Gateway | Boardroom remains owner |
| Workspace contract currently used by Boardroom | `backend/modules/aion_business/contracts/workspace.py` | Compatibility reader, followed by signed manifest | Reuse; do not broaden authority |
| Proof preview, commitment and lookup | `backend/modules/aion_gateway/glyphchain_proof_commit.py`, `backend/modules/chain_sim/aion_proof_commit_store.py` | Selective proof adapter | Reuse; no private payloads |
| PHO, PhotonPay, wallets and economic instruments | wallet, mesh, PhotonPay and GMA modules | None in initial mobile app | Preserve but hide |
| Radio bridge and offline Wave transport | `Glyph_Net_Browser/radio-node` | Optional transport capability | Preserve; disabled until hardware qualification |

## Collision and migration rules

1. Raw legacy identifiers are namespaced by type and source; a task and message with the same raw
   identifier cannot collide.
2. Existing stores remain readable and untouched. Compatibility readers produce immutable
   `pilot.unified.v1` projections.
3. No irreversible migration runs during the first implementation stages.
4. Boardroom data is queried through a Workspace Gateway and is not copied into Personal Pilot.
5. Personal data is never made visible to a Boardroom administrator merely because the person is a
   member of that organisation.
6. Every client receives authority from a current membership and capability lease, not from the
   existence of an interface control.

## Legacy and overlapping paths

- `aion_fabric/agent.py` remains the television planning store; it is not the unified personal
  task authority.
- `aion_fabric/pilot_inbox.py` is the current personal task and agent-inbox authority.
- `pilot_unified/inbox.py` is the encrypted inter-mother transport and reconciliation bridge. It
  does not replace Pilot Inbox as the personal task/list authority; a verified incoming delegation
  is imported there once and remains pending until its local recipient accepts it. Sender
  corrections and cancellations use encrypted task-update packets; recipient lifecycle changes
  use signed content-free receipts and reconcile into both mothers.
- `pilot_unified/inbox_live_service.py` is a read-only, possession-authenticated notification
  channel. It cannot mutate the Inbox and resumes from a client-supplied verified revision cursor.
- `pilot_unified/personal.py` is the persona-filtered mobile projection over Production Private
  Identity and Pilot Inbox. It does not own personal records, expose unrelated adults, or grant
  shared-screen identity merely because a phone reads its own data.
- Mobile reminders remain owned by Pilot Inbox. Their signed adapter adds durable duplicate
  suppression, defined recurrence, same-device location consent and exact lifecycle transitions;
  it does not store raw movement history or infer location permission.
- Unified Inbox attachments are encrypted per mother as owner-only blobs and remain subordinate to
  their parent message. The mixed search projection decrypts only after persona-bound phone
  authorization and creates no plaintext index or second files authority.
- Unified Inbox voice notes use the same encrypted attachment authority with additional duration,
  size and retention bounds. Push-to-talk authority is issued by the mother and bound to the exact
  persona, signed phone device, lease and conversation; browser-tab identity is not authority.
- Reminder, follow-up, calendar and document-review cards are encrypted transport projections.
  Their presence records a proposal for review and never claims that a provider action executed.
- GlyphNet browser `sessionStorage` is a temporary client cache; the server thread journal is the
  compatibility source for conversation history.
- `aion_business/contracts/workspace.py` remains a Boardroom-owned legacy contract projected
  through the new compatibility reader.
- `backend/modules/aion_unified` is an older cognitive experiment unrelated to the unified mobile
  product and must not be imported as the mobile contract package.
- Legacy approvals without a device-possession proof are projected back to awaiting approval.
  Compatibility code must never upgrade them into production authority.

## Immediate risks

| Risk | Control required before exposure |
| --- | --- |
| GlyphNet development token and static identities | Replace with Pilot phone possession, persona and expiring capability lease |
| Plain local thread/message payloads | Encrypt at rest and define export/deletion behaviour |
| Demonstration QKD/call encryption | Use audited authenticated key establishment and media encryption |
| In-memory replay protection | Persist expiry-aware idempotency state at transport boundaries |
| Boardroom role overreach | Signed manifest, field filtering and malicious-admin tests |
| Cross-space prompt injection | Treat message, file, website and Boardroom evidence as untrusted input |
| Chain privacy leakage | Allowlisted proof schema; reject plaintext and secrets before commitment |
| PHO development routes | Exclude from manifests, voice routing, agents and production server registration |
| Incomplete RF inbound reconstruction | Keep radio disabled until integrity and offline field tests pass |
| Standalone GlyphNet Browser dependency failure | Lock and reproduce the client build before reuse in production |

## Stage 0 outcome

The authoritative ownership boundary is now recorded. The new
`backend.modules.pilot_unified` package contains the first versioned contract and compatibility
boundary plus the tested encrypted Inbox transport. Secure phone pairing, authenticated polling
and resumable live subscriptions now bind that transport to the unified mobile surface. The live
socket proves phone possession on every connection, applies only newer revisions and retains the
separately authenticated HTTPS Inbox request as its recovery path.
