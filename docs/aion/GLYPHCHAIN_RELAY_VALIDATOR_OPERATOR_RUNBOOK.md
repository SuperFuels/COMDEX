# GlyphChain relay and validator operator runbook

Status: pre-production operating procedure. Admission/removal and upgrade
coordination are implemented locally; organisational approval, independent
monitoring transport and representative deployment exercises remain release
gates.

## 1. Decide the role

A normal Tessaris installation stays a **light node**. Do not enable elevated
participation merely to verify a document.

- A relay accepts authenticated peers and serves bounded synchronization data.
- A validator also proposes and votes, safeguards a finality key and commits to
  an availability and incident-response duty.

Record the named operator, device purpose, storage budget and approval ticket.
A validator also needs the governance admission identifier and the exact
validator-set checkpoint approved for that admission.

## 2. Establish independent trust

Obtain the public checkpoint file and its expected checkpoint ID through
separate authenticated channels. Verify before configuration:

```text
python backend/scripts/export_glyphchain_checkpoint.py \
  --verify validator-set.glyphchain-checkpoint \
  --expected-id <independently-obtained-checkpoint-id>
```

Never use the ID embedded in the downloaded file as its own trust pin.

## 3. Protect keys

- Use distinct Ed25519 identities for P2P transport and validator finality.
- Never place private keys in documentation, tickets, logs or checkpoint files.
- Store recovery material encrypted, offline and separately from the node.
- Startup deliberately rejects reuse of the P2P private key as the finality
  private key.

## 4. Configure explicit participation

Production must set `GLYPHCHAIN_ENFORCE_EXPLICIT_PARTICIPATION=1` and place the
participation record in the protected directory selected by
`GLYPHCHAIN_PARTICIPATION_DIR`. If that variable is absent, the location is the
`participation` child of `GLYPHCHAIN_STATE_DIR`.

The local administration operation must call `NetworkParticipationStore` and
requires these exact acknowledgements:

- relay confirmation: `ENABLE GLYPHCHAIN RELAY`;
- validator confirmation: `ENABLE GLYPHCHAIN VALIDATOR`;
- relay and validator: public-connectivity acknowledgement;
- validator: availability and key-custody acknowledgements, governance approval
  ID and matching validator checkpoint ID.

The state and its hash-chained audit journal are written with owner-only
permissions. Environment variables alone cannot elevate an enforced node.

## 5. Pre-start checks

1. Confirm system time synchronization and sufficient encrypted disk space.
2. Verify the participation audit chain.
3. Verify the public validator checkpoint against its independent pin.
4. Confirm transport and finality keys are different.
5. Confirm the configured storage limit and inbound network exposure.
6. Confirm backups and operator contact details are current.
7. Start the node and inspect the reported participation role and capabilities.

Stop if the role, checkpoint, keys or network exposure differs from the approved
record.

## 6. Normal operation

- Monitor peer authentication failures, queue pressure, finalized height,
  finality lag, fork/round changes, disk use and restart catch-up.
- Treat `LEDGER_COMMITTED_AWAITING_QUORUM_FINALITY` as incomplete.
- Never claim delivery, finality or recovery success from submission alone.
- Preserve relevant logs without document contents, signer identities or raw
  private keys.

Production alert thresholds are intentionally unset until representative pilots
provide evidence. Operators must not invent thresholds and present them as
tested limits.

### Protocol-upgrade procedure

1. Obtain the approved release manifest, its SHA-256 digest, governance approval
   and the validator checkpoint through the documented release channels.
2. Install the release on representative non-voting nodes and verify its
   advertised supported protocol range.
3. Through signed desktop administration, schedule the target version far
   enough ahead of the current finalized height to satisfy the configured lead
   time. Use the exact confirmation `SCHEDULE GLYPHCHAIN PROTOCOL UPGRADE`.
4. Refresh signed HELLO sessions and monitor readiness by voting power. Do not
   count unverified peers or ordinary light nodes toward readiness.
5. If the release is withdrawn before activation, record the reason and use
   `CANCEL GLYPHCHAIN PROTOCOL UPGRADE`. Local cancellation is prohibited after
   activation.
6. At activation, treat `UPGRADE_HALT` as fail-closed: do not bypass it or alter
   finalized height. Correct the installed release or the matching validator
   plan and allow signed readiness to reach quorum.
7. After the activation height has finalized on supported software, use
   `COMPLETE GLYPHCHAIN PROTOCOL UPGRADE` to commit the new current version and
   retain the hash-chained operator history.

## 7. Incident response

For suspected key exposure, equivocation, unapproved role elevation, persistent
forking or corrupted state:

1. isolate the node from inbound and outbound peers;
2. preserve encrypted state, participation audit history and privacy-safe logs;
3. disable elevated participation with a named operator and reason;
4. do not delete or rotate evidence until the incident owner authorizes it;
5. rotate affected keys using the approved recovery procedure;
6. require governance action before validator readmission; and
7. verify catch-up and trusted checkpoint state before reconnecting.

Disabling elevated participation returns the device to the light role and does
not erase its audit record.

### Partition and conflicting-finality response

When network health reports `PARTITION_SUSPECTED`, `REJOIN_ASSESSING` or
`BLOCK_CATCHUP`, keep the node connected only to approved peers and allow the
bounded recovery process to validate certificates and materialize the exact
ledger range. Do not manually advance finalized height.

When it reports `SNAPSHOT_REQUIRED`, return the device to light mode if
necessary, obtain a snapshot from an already authenticated relay or validator,
verify it against the independently pinned checkpoint, and install it through
signed desktop administration. Consensus may adopt the snapshot height only
after the installed tip matches the retained finality certificate.

Treat `SAFETY_HALT` as a security incident:

1. preserve the recovery record, hash-chained journal and privacy-safe health
   history;
2. isolate untrusted routes while retaining the evidence needed to compare the
   valid finalized views;
3. determine the trusted history through the incident and governance process;
4. repair or restore the node to that exact verified history; and
5. only then clear the halt through signed desktop administration using the
   displayed halt identifier, a named operator, the reason, and the exact phrase
   `CLEAR GLYPHCHAIN PARTITION SAFETY HALT`.

Clearance is not an override of certificate validation. Proposals and votes
remain suppressed until the sticky halt is explicitly cleared, and the journal
retains both the conflict and the clearance event.

### Suspected malicious or compromised validator

Treat equivocation, a suspected finality-key disclosure, deliberately invalid
proposals, repeated authenticated protocol abuse or unapproved validator
operation as a validator-security incident.

1. Isolate the affected node and preserve its owner-only participation,
   governance, health and consensus records. Do not disclose Legal content or
   private key material in the incident record.
2. Record the validator identifier, observed height interval, evidence digests,
   reporter, incident owner and the reason for the assessment. An allegation is
   not itself proof and must not automatically rewrite finalized history.
3. Disable local elevated participation. This prevents that device from
   continuing locally but does not change the distributed validator set.
4. Construct a successor checkpoint that increments the epoch, advances the
   effective height and removes only the affected validator unless a separately
   approved replacement is part of another transition.
5. Propose the action as `emergency_removal`, reference the incident identifier,
   and use the exact administration confirmation
   `PROPOSE GLYPHCHAIN VALIDATOR SET CHANGE`.
6. Collect domain-separated Ed25519 approvals from unaffected current
   validators. Do not count the accused/removed validator, candidate replacement,
   ordinary nodes, transport keys or duplicated approvals. Finalize only after
   eligible current-checkpoint voting power reaches the unchanged quorum threshold,
   using `FINALIZE GLYPHCHAIN VALIDATOR SET CHANGE`.
7. Independently verify and preserve the transition proof, previous checkpoint,
   successor checkpoint and both out-of-band pins. Configure the successor only
   at its declared effective height.
8. Rotate or destroy compromised keys under the approved custody process. Never
   reuse a transport key as a finality key.
9. Review receipts finalized during the suspected exposure interval against the
   retained certificates and incident evidence. Do not retroactively invalidate
   earlier receipts merely because a validator was later removed.
10. Restore network participation only after the incident owner approves the
    disposition, the node verifies the canonical history, and the relevant
    checkpoint is independently pinned.

The response is fail-closed but not unilateral: neither the accused validator,
a joining validator nor one local administrator can appoint the successor set.
The transition proof is portable evidence of the current set's quorum decision.

The repeatable local exercise is run with:

```text
python backend/scripts/run_glyphchain_validator_removal_exercise.py \
  --output docs/aion/GLYPHCHAIN_VALIDATOR_REMOVAL_EXERCISE_REPORT.json
```

The retained report contains content-free public checkpoints, the exact
quorum-governed transition proof, verification result and explicit denial
evidence for the accused and joining validators. It contains no private key or
Legal document content. Passing this local cryptographic exercise does not
replace operational/security approval or a production incident exercise.

### Checkpoint rollover and historical evidence

For every validator-set transition, retain the old checkpoint, new checkpoint,
transition proof, governance reference, effective height and independently
published pins. Verify a receipt using the checkpoint epoch effective at the
receipt's finalized height. A successor checkpoint governs new heights only; it
must not be substituted into an older receipt merely because it is current.

If a checkpoint or pin is published incorrectly, stop rollout and publish a
versioned withdrawal notice through both release channels. Do not edit the
already published object in place. If the bad checkpoint was never effective,
retain it as withdrawn. If it became effective, use a new quorum transition and
later effective height. There is no administrative operation that erases or
rewrites finalized history.

## 8. Retirement

Export required evidence and configuration records, confirm retention duties,
disable elevated participation, remove the validator through quorum governance,
destroy private keys under the approved process
and retain a content-free destruction record. A local role change alone does
not remove a validator from a distributed validator set.
