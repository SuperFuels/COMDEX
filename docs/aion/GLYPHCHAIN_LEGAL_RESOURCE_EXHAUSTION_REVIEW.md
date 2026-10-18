# GlyphChain and Legal Resource-Exhaustion Review

Status date: 26 September 2026

## Scope and conclusion

This review covers locally enforceable denial-of-service and resource-exhaustion
boundaries for the GlyphChain consensus/P2P implementation and the Tessaris Legal
signing, proof, delivery, encrypted-record and administration surfaces.

The reviewed local implementation is **bounded and fail-closed** for request
bodies, staged snapshot files, public signer lookups, Legal record enumeration,
workspace storage, proof queues and journals, consensus recovery ranges, peer
sync state, validator/vote sets and retained health/governance state. The signed
release regression suite passes after these controls were applied.

This is an engineering review, not an independent security certification or a
production capacity claim. Sustained-load, multi-network soak testing and the
independent application/protocol reviews remain separate release gates.

## Enforced boundaries

### HTTP and streamed snapshot input

- Public signer requests are limited to 64 KiB.
- Resend webhook requests are limited to 1,000,000 bytes.
- Other Legal signing requests are limited to 40 MiB.
- GlyphChain administration and P2P requests are limited to 4 MiB.
- Snapshot verification/import archives are streamed to private staging storage
  rather than buffered by the general request middleware.
- Staged snapshot storage is removed in a `finally` path after success or any
  validation, confirmation, role or import rejection.

### Public signer surface

- Public tokens must match the expected 40--128 character URL-safe format.
- Encrypted persistent token indexes provide constant-time record location;
  random token misses do not decrypt and scan every workspace envelope.
- Token comparison remains constant-time and indexes are removed when links are
  rotated, signed, declined, voided or expired.
- Read and write work is separately rate-limited by source and token. Defaults
  are 60 reads and 20 writes per source, and 20 reads and 8 writes per token,
  per 60-second window.
- The limiter retains token digests rather than raw tokens and its LRU table is
  bounded to 10,000 buckets by default.

### Legal records, documents and templates

- Each Legal component/workspace has a default ceiling of 5,000 records and
  5 GiB, with a maximum of 40,000 measured files at that default.
- Individual encrypted records are limited to 256 MiB by default; encrypted
  reads and plaintext migrations reject larger files before loading them.
- Enumeration is complete-or-fail: a list operation exceeding its record limit
  raises an error rather than silently returning an incomplete security view.
- Template instantiation is limited to 128 values, 20,000 characters per value,
  500,000 substituted characters in total and 1,000,000 rendered characters.
- Delivery attachments are limited to 50 MiB and retained delivery-event lists
  to 2,000 events.
- Legal key metadata is limited to 4 MiB and 4,096 retained key versions.

### Proof persistence and verification

- Portable proof bundles are limited to 16 MiB and Merkle proofs to 256 items.
- Durable outbox items are limited to 256 KiB and the outbox count is bounded.
- Append-only submission journals rotate at 16 MiB and stop after 64 segments
  rather than overwriting evidence or growing indefinitely.
- Retry calls process at most 250 items in one invocation.

### Consensus, P2P and retained operational state

- Finality validator and vote sets are limited to 256 entries.
- Ledger commitment inputs are limited to 10,000 transactions.
- Consensus recovery is limited to 2,048 blocks by default and rejects a larger
  range before allocating or iterating it.
- Per-peer sync policy state is LRU bounded to 10,000 entries by default and
  applies bounded inflight work, spacing and exponential backoff.
- Protocol-upgrade, partition-recovery, network-health and validator-governance
  persistence is size-checked before being loaded; their retained event or
  record collections are also bounded.
- Runtime proposal, vote, finality-evidence, equivocation and recovery tracking
  caches are pruned to configured windows or explicit limits.

## Verification evidence

- Focused resource, signer, storage and Legal service regression set:
  **93 passed**.
- Complete GlyphChain, Legal, Resend and Microsoft Graph release set:
  **242 passed**.
- The signed baseline report includes this review and all resource-control source
  files in its source manifest, so later verification detects drift.

## Residual production work

The following are intentionally not closed by this local review:

- production traffic sizing and rate-limit tuning;
- sustained-load, restart, intermittent-network and multi-network soak tests;
- deployment-level reverse-proxy, operating-system, disk and process limits;
- live-provider throttling, bounce storms and callback retry behaviour;
- independent application-security, consensus and cryptography review.

Those items remain explicit tasks in the production checklist and must pass
before production security or capacity claims are made.
