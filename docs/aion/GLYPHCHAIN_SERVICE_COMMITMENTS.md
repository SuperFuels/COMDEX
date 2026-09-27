# GlyphChain and Legal service commitments

Status: pre-production policy baseline. This document defines the boundary the
software can enforce today; it is not a commercial SLA.

## Availability

- Local Legal records, signing envelopes and downloaded evidence remain usable
  without a public GlyphChain connection when the device and its keys are
  available.
- A proof may remain `PENDING` or `LEDGER_COMMITTED_AWAITING_QUORUM_FINALITY`
  during network or validator unavailability. Tessaris must not relabel either
  state as final.
- No numeric uptime, submission-latency or finality-latency commitment is made
  before representative multi-device pilots establish measured percentiles.
- Provider acceptance of an email is not delivery. A signed copy is marked
  delivered only after an authenticated provider outcome or explicit human
  confirmation is retained.

## Retention and deletion

- Document text, signer identities and private evidence packages remain in the
  encrypted workspace; the chain receives commitments only.
- A record with an active legal hold cannot be destroyed.
- Eligible destruction requires a terminal record, an expired retention
  period, a completed export and the exact record-specific confirmation.
- Destruction retains an encrypted, content-free receipt containing identifiers,
  timestamps and the digest of the destroyed record. It does not retain the
  document text or private matter narrative.
- Validator and relay storage limits are explicit configuration boundaries.
  Proof-preserving pruning is an explicit light-node maintenance operation,
  never an automatic response to storage pressure. It requires a complete
  independently verified archive and rechecks finality before atomic install.

## Recovery

- Legal encryption and proof-signing keys use versioned custody. Production
  mode requires the operating-system Keychain and fails closed if it is
  unavailable.
- Password-encrypted recovery bundles must be exported before key rotation and
  kept separately from the protected device. Tessaris does not upload these
  bundles automatically.
- Recovery is considered successful only after an imported bundle can decrypt
  a retained test record and verify a receipt created with a retired signing
  key.
- Losing every copy of an encryption key can permanently make the corresponding
  private records unreadable. A chain commitment cannot recover document text.
- No recovery-time or recovery-point SLA is claimed until backup/restore and
  lost-device exercises have produced measured evidence.
- Partition recovery never advances finality from an advertised height alone.
  Exact blocks are materialized and verified for bounded gaps; larger gaps
  require a verified finality-anchored snapshot. Conflicting valid finalized
  views trigger a restart-persistent safety halt that suppresses proposals and
  votes until an authenticated operator records an explicit clearance.
- A scheduled protocol upgrade never authorizes an unsupported release.
  Activation requires local target support and matching signed validator-plan
  advertisements with quorum voting power; otherwise consensus fails closed at
  the activation boundary. No production upgrade-success claim is made until a
  representative multi-device rollout has exercised the plan.

## Responsibility boundary

- Normal desktop installations are light nodes. Relay and validator operation
  require explicit, durable opt-in and additional operational responsibility.
- Tessaris proof evidence supports integrity and audit verification. It is not
  by itself a qualified electronic signature, legal advice or a guarantee that
  an agreement is enforceable in a particular jurisdiction.
- Production claims must cite the signed baseline, the independently pinned
  validator checkpoint and the measured deployment profile to which they apply.
