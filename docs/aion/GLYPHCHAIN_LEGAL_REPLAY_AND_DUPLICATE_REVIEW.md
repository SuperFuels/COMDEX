# GlyphChain and Legal Replay, Nonce and Duplicate-Protection Review

Status: completed local implementation review, 26 September 2026

## Scope and claim boundary

This review covers the externally reachable GlyphChain and Legal route families
implemented in this repository. It verifies how repeated requests, stale signed
messages, duplicate provider callbacks and duplicate consensus operations are
handled. It does not replace the remaining independent application-security,
consensus-protocol or denial-of-service reviews, and it does not assert that an
unexercised production deployment is secure.

## Control matrix

| Boundary | Authentication and freshness | Durable duplicate control | Result |
| --- | --- | --- | --- |
| Legal and GlyphChain desktop administration | HMAC-SHA-256 binds method, exact path and query, body hash, device, person, workspace, timestamp and a random nonce. Requests have a maximum 60-second age. | A private SQLite replay store retains only `SHA-256(device_id || NUL || nonce)`, survives application restarts, deletes expired entries and fails closed when unavailable or at its configured bound. | Replays are rejected before the route operation executes. |
| Public Legal signer | A 256-bit URL-safe bearer token is stored only as a SHA-256 digest. Optional separate-channel verification codes are independently generated and stored only as digests. | Signing clears both credential digests. Decline and signing are state-gated, signing order is enforced, reminder rotation invalidates the previous token, and completed or terminal records reject another mutation. Repeated read-only views are intentionally permitted while the token is valid. | A captured mutation cannot be applied twice to the same signer state. |
| Resend delivery callback | The exact request bytes, provider event identifier and timestamp are authenticated with the configured rotating webhook secrets. Events outside the bounded timestamp window are rejected. | Provider event identifiers and payload digests are stored inside the encrypted delivery record. An identical callback is acknowledged as a duplicate after restart; reuse of an identifier with different bytes is rejected as a conflict. | Provider retries are idempotent without hiding contradictory outcomes. |
| Signed peer discovery | Ed25519 signatures bind the complete record, chain, authority, sequence and expiry. Only independently configured authority keys are accepted. | The latest sequence per authority is stored durably. Lower sequences are rejected; an exact repeat is idempotent; same-sequence equivocation is rejected. | Stale bootstrap records cannot replace newer peer state. |
| NAT relay PUT, PULL and ACK | Ed25519 signatures bind operation, chain, node, timestamp, nonce and payload, following a verified peer HELLO. | A private, bounded, restart-safe nonce journal stores only peer/nonce digests. The relay queue also uses a content-derived relay identifier, making repeated PUTs idempotent. | Signed relay-operation replay remains rejected across relay restart. |
| P2P transaction, block, consensus and synchronisation lanes | Peer identity, chain and message type are bound by the transport signature and peer handshake. Consensus messages are additionally constrained by validator identity, height, round and quorum rules. | Bounded TTL/LRU ingress deduplication, stable message identifiers, request response caching, transaction-ledger idempotency and consensus-state validation prevent repeated application. Duplicate validator votes are rejected. | Duplicate traffic is dropped, answered from the cache where safe, or rejected by durable protocol state. |
| Legal document proof submission | A stable proof identifier and transaction lookup bind submission to the exact document and evidence manifest hashes. | The durable outbox and append-only event journal recover after restart and detect an already submitted chain transaction before retrying. | Retrying proof publication cannot create a second logical proof. |

## Desktop signed-session implementation

The desktop renderer cannot read the signing secret. It asks the Electron main
process to sign only one of three explicit route families:

1. `/api/workflow-capsules/aion-flow/`;
2. `/api/aion/business/legal-signing/`;
3. `/api/aion/business/glyphchain-admin/`.

All other targets are rejected. The backend validates exact lower-case SHA-256
and HMAC encodings, bounded identity fields, a 16--128 character nonce, a
bounded absolute request target, timestamp freshness and the exact body digest
before it records the nonce. A route-inventory regression test confirms that
every private Legal and GlyphChain administration route declares the signed
session dependency. Only the public token-based signer routes are exempt.

The persistent replay database is owner-only (`0600`) inside an owner-only
directory (`0700`). It contains no raw nonce, workspace, person or device
identifier. Database corruption, an unwriteable path or capacity exhaustion
causes the request to fail closed.

## Verified restart cases

The local regression suite now proves:

- a desktop request is rejected after constructing a new authority instance
  against the same replay database;
- a NAT relay operation is rejected after constructing a new relay-store
  instance against the same state directory;
- a Resend callback is detected as a duplicate after constructing a new
  delivery-service instance;
- reusing a callback identifier with different authenticated bytes is rejected;
- signer credentials are removed or invalidated after signature, decline or
  explicit reminder rotation;
- persistent stores retain only cryptographic digests of replay secrets;
- replay stores are bounded and fail closed when their state is unavailable.

## Remaining security gates

This completed review does not close the separate resource-exhaustion review.
That review must still assess request-body loading, signature-verification cost,
file and archive expansion, queue pressure, callback floods, peer limits and
production rate-limit configuration. Independent application and consensus
reviews, sustained multi-network soak testing and production incident exercises
also remain mandatory release gates.
