# GlyphChain desktop node participation

## Default boundary

A normal Tessaris installation is a **light node**. It may verify proofs and
request bounded synchronization data, but it does not accept public peers,
relay third-party traffic, propose blocks or vote. Installing Tessaris or
discovering the network never turns a customer machine into a validator.

Elevated participation is controlled by the versioned local record
`glyphchain.network-participation.v1`. Production installers must enable
`GLYPHCHAIN_ENFORCE_EXPLICIT_PARTICIPATION=1`; in that mode the record is
authoritative and a validator-shaped environment variable alone cannot enable
voting.

## Roles

| Role | Responsibilities | Explicit requirements |
|---|---|---|
| Light | Verify documents and receipts; make outbound bounded sync requests; retain only local evidence and requested proof material. | None. This is the default and is not an elevated opt-in. |
| Relay | Accept authenticated peers, relay bounded protocol messages and serve permitted synchronization data within a configured storage limit. | Exact relay confirmation, named operator and acknowledgement of public connectivity. |
| Validator | Perform relay duties, protect validator and finality keys, remain sufficiently available, propose and vote, and follow admission/removal and incident procedures. | Exact validator confirmation, named operator, connectivity, availability and key-custody acknowledgements, governance approval identifier, and a matching trusted validator-set checkpoint. |

Every role change is written atomically and appended to a hash-chained local
audit journal. Relay and validator storage is bounded by an explicit byte
limit. The present implementation records the local governance approval; it
does not yet implement distributed validator admission or removal.

## Runtime enforcement

When explicit participation enforcement is enabled:

- a missing record resolves to light-node capabilities;
- light and relay records suppress the local consensus validator identity;
- validator startup fails if its trusted checkpoint is absent or differs from
  the checkpoint approved in the participation record;
- a validator without its matching finality key cannot cast certifiable
  precommits; and
- disabling elevated participation immediately returns the local record to the
  light role while preserving an audit event.

Developer clusters remain compatible when enforcement is disabled, but that
mode is labelled `legacy_deployment` and is not the consumer-release boundary.

## Outbound-only NAT relay transport

A light, relay or validator node behind a home, office or VM firewall can use a
public relay without opening an inbound port. The node establishes an outbound
HTTPS connection, completes a signed Ed25519 HELLO, polls a bounded recipient
queue and submits each retrieved original P2P envelope through its own local
router. The ordinary sender identity, HELLO binding and lane signature are
therefore checked again at the recipient. A relay transports messages; it does
not become a validator, finality authority or source of peer trust.

Relay routes are part of the independently signed peer-discovery record. In
production, both the relay and routed peer public keys must already be present
in that trusted registry. An unknown self-signed HELLO is rejected whenever
signed discovery is enforced, and a HELLO cannot replace an already pinned peer
key. The one-way HELLO response carries the relay's signed identity, allowing an
outbound-only node to complete mutual possession checks without a callback to
its private address.

The relay service is available only to an explicitly approved relay or
validator role. PUT, PULL and ACK operations are chain-bound, timestamped,
nonce-bearing and signed by the caller's transport key. The server requires a
previously verified HELLO, rate-limits the caller, restricts targets to the
trusted peer registry, enforces per-message, per-recipient and global queue
bounds, applies short expiry, deduplicates identical envelopes and persists the
queue atomically with owner-only permissions. A recipient acknowledges a
message only after its local P2P route has accepted it or rejected it as
permanently invalid; transient and rate-limit failures remain queued.

The transport contains consensus and synchronization protocol envelopes only.
Legal documents, signer identities, private evidence archives and document
plaintext are not placed in the relay queue. HTTPS is mandatory unless an
explicit development-only insecure-network switch is enabled. The production
relay URL is configured with `GLYPHCHAIN_NAT_RELAY_URL`; signed discovery may
also provide a per-peer `relay_url`. Queue and poll limits are controlled by the
`GLYPHCHAIN_NAT_RELAY_*` settings.

## Network-partition recovery

Partition recovery is explicit and fail-closed. A node validates finality
certificates from every available peer against its independently configured
validator checkpoint before comparing views. Peer count is not voting power
and cannot replace certificate validation.

- Finality never advances merely because a peer advertises a greater height.
  The node first retrieves and validates the exact ledger blocks, transaction
  roots and tip commitment covered by the trusted certificate.
- A bounded gap is recovered by block catch-up. A gap above
  `GLYPHCHAIN_PARTITION_BLOCK_CATCHUP_MAX` enters `SNAPSHOT_REQUIRED`; a light
  node must verify and install a finality-anchored snapshot before the retained
  certificate is applied to consensus state.
- Two valid finalized views for different blocks at the same height, or a valid
  peer view conflicting with local finality, enter a durable `SAFETY_HALT`.
  While halted, the node may gather synchronization evidence but cannot propose
  or vote.
- The recovery record and bounded event journal are chain-bound, node-bound,
  atomically written with owner-only permissions and hash-chained. A safety
  halt remains sticky across restarts and ordinary synchronization.
- Clearance requires signed desktop administration, the exact phrase
  `CLEAR GLYPHCHAIN PARTITION SAFETY HALT`, the current halt identifier, a named
  operator and a recorded reason. Clearance records the decision; it does not
  conceal or delete the conflict history.

## Public validator checkpoints

The validator checkpoint contains only public validator identifiers, voting
power and Ed25519 public keys. It contains no private signing material. An
operator can export the normalized public file with:

```text
python backend/scripts/export_glyphchain_checkpoint.py --output validator-set.glyphchain-checkpoint
```

The file and its expected checkpoint ID must be distributed through separate
channels. For example, publish the file at a documented HTTPS location and
publish the expected ID in a signed release manifest. A recipient verifies the
download using the independently obtained ID:

```text
python backend/scripts/export_glyphchain_checkpoint.py \
  --verify validator-set.glyphchain-checkpoint \
  --expected-id <independently-obtained-checkpoint-id>
```

The verifier deliberately refuses a downloaded checkpoint when no independent
ID or validator-set-root pin is supplied. A receipt, peer or checkpoint file
cannot appoint its own trust anchor.

### Checkpoint rollover, compromise and historical verification

Validator membership changes use a new checkpoint with an incremented epoch and
a later effective height. The transition package must be signed by quorum voting
power from eligible current validators. A joining validator cannot approve its
own admission, and a removed or suspected validator cannot contribute approval
power to the successor set. The quorum threshold remains derived from the full
current checkpoint, so excluding the suspected validator cannot weaken the
decision threshold. Production startup for a later epoch sets all of:

- the new checkpoint and its independently obtained checkpoint-ID pin;
- the quorum transition proof;
- the independently retained previous checkpoint ID; and
- `GLYPHCHAIN_REQUIRE_VALIDATOR_GOVERNANCE=1`.

The loader fails closed if the proof does not bind the exact previous and next
checkpoint identifiers, if current-validator approval signatures are invalid,
or if signed voting power is below quorum.

Checkpoint rollover is prospective. Never delete or silently replace the old
checkpoint, transition proof or independent pin. Historical receipts are
verified against the checkpoint epoch effective at their finalized height.
Removing a validator does not retroactively invalidate sound certificates that
predate the removal height. When a finality key might have been compromised,
the incident record defines the suspected exposure interval. Receipts finalized
inside that interval require incident review until the retained chain evidence,
quorum certificates and response decision establish their disposition.

There is no mutable ``unfinalize'' operation. An emergency removal is a
quorum-governed `emergency_removal` transition to a later effective height.
Operators publish the replacement checkpoint and transition proof through the
ordinary versioned channel and publish its pin independently. A withdrawn or
superseded checkpoint remains available for historical verification but must be
labelled as not valid for new heights at or after its successor's effective
height.

## Coordinated protocol upgrades

Future protocol activation is governed by a durable local plan rather than a
software-version guess. The plan fixes the source protocol, target protocol,
activation height, release-manifest SHA-256 digest, trusted validator checkpoint
and governance approval into one canonical plan identifier. The operator state
and journal are atomically persisted with owner-only permissions; the journal
is hash-chained.

Every managed HELLO signs the node's active protocol, supported range, plan
identifier, target and activation height together with its transport identity.
A peer cannot alter that readiness advertisement without invalidating the HELLO
signature. Consensus measures readiness by validator voting power, not by node
count. Before activation, insufficient readiness is visible as an operator
warning. At the activation boundary, a node suppresses proposals and votes if
its installed software does not support the target or matching advertisements
do not reach quorum power. Corrupt or unreadable upgrade state also fails
closed.

Scheduling requires `SCHEDULE GLYPHCHAIN PROTOCOL UPGRADE`. A pre-activation
cancellation requires `CANCEL GLYPHCHAIN PROTOCOL UPGRADE`. Once the activation
height has finalized on supported software, committing the new current version
requires `COMPLETE GLYPHCHAIN PROTOCOL UPGRADE`. All three operations require a
signed desktop administrator; cancellation is deliberately unavailable after
activation.

## Work still required

The installer default, release-channel publication of the checkpoint pin,
deployment of independently operated public relays, protocol-upgrade and
emergency-removal exercises, and representative home, office, VM and
intermittent-device exercises remain production gates. Signed validator
admission/removal governance, signed peer discovery, bounded peer and ledger state,
finality-anchored checkpoint synchronization, explicit proof-preserving pruning,
transport-key rotation/recovery, privacy-safe local monitoring and the
outbound-only NAT relay transport, fail-closed partition recovery and protocol-
upgrade coordination are implemented locally.
The pre-production operating procedure is maintained in
`GLYPHCHAIN_RELAY_VALIDATOR_OPERATOR_RUNBOOK.md`.
