# Pilot Unified Mobile App — Remaining Build Tasks

Status: remaining-only execution list, reconciled 3 September 2026  
Canonical audit source: `PILOT_UNIFIED_MOBILE_APP_MASTER_BUILD_CHECKLIST.md`  
Progress: **169 of 182 coded MOB tasks complete; 13 remain**

This is the clean working queue. It contains no completed `MOB` task. The full master checklist
retains completed implementation evidence, closure criteria and history. A task moves out of this
file only after implementation evidence, automated verification and documentation have been added
to the master record.

## Current cursor

- The first strict-order item is `MOB-0514`, which requires user-authorized live provider accounts.
- Every remaining item now requires an external account, full signed native toolchain, physical
  hardware/field participants or independent specialist review; there is no honest mock-only
  coding task left to close.
- Native application sources and platform-security contracts are prepared, but signed iOS/Android
  binaries require unavailable platform toolchains, signing identities and physical devices.
- All 14 Stage 3 coded tasks are complete. A physical Wi-Fi/mobile-data roaming exercise remains
  an explicit verification gate rather than being misreported as completed field evidence.
- Pilot and active television sessions should not be restarted merely to complete documentation or
  server-side tests.

## Active build queue

### Stage 7 — Non-Pilot delivery

- [ ] `MOB-0703` `[EXTERNAL]` Connect WhatsApp only through an officially authorized platform route.

The official SMS adapter is implemented. Provider acceptance, carrier delivery and human reading
remain separate states. Real delivery qualification requires provider credentials and receipts;
an interface or mock cannot close it.

### Stage 11 — Native phone applications

- [ ] `MOB-1101` `[BUILD]` Build and sign the native iOS application.
- [ ] `MOB-1102` `[BUILD]` Build and sign the native Android application.
- [ ] `MOB-1110` `[VERIFY]` Complete accessibility, guardian/child and representative-device testing.
- [ ] `MOB-1111` `[EXTERNAL]` Complete Apple and Google signing, privacy declarations and store review.

Biometrics confirm possession locally; they are not used to infer a person's identity. Lock-screen,
task-switcher and notification surfaces must not expose protected content.

### Stage 12 — Calls and groups

- [ ] `MOB-1201` `[HARDEN]` Replace demonstration call encryption with independently audited end-to-end encryption.

### Stage 13 — Optional Wave transport

- [ ] `MOB-1307` `[BUILD]` Add BLE and Wi-Fi Direct adapters only when genuinely implemented.
- [ ] `MOB-1308` `[EXTERNAL]` Qualify compatible ESP32, Raspberry Pi and radio hardware.
- [ ] `MOB-1309` `[EXTERNAL]` Verify regional frequency, power and duty-cycle compliance.
- [ ] `MOB-1310` `[VERIFY]` Deliver text and push-to-talk between two mothers with the internet physically disabled.

Wave remains hidden and optional until a real internet-disconnected receipt proves delivery. It
must never be advertised merely because a simulated queue or reconstructed local frame succeeds.

## Verification and external gates

These tasks are intentionally not treated as ordinary coding work:

- [ ] `MOB-0514` `[VERIFY]` Qualify at least one real task, calendar and communication provider.
- [ ] `MOB-1409` `[VERIFY]` Conduct household, freelancer, employee and Boardroom field pilots.
- [ ] `MOB-1410` `[EXTERNAL]` Complete independent security, privacy, legal and regulatory review.

External prerequisites still include Apple and Google developer signing, native background
permissions, officially authorized WhatsApp access, real OAuth/provider accounts, additional test
households and businesses, independent security assessment, legal and child-safety review, and
optional radio hardware/compliance work.

## Closure exercises still required

The following exercises validate several coded tasks at once and do not add to the 27-task count:

- [ ] Start the normal Pilot runtime with the PHO/economic layer completely disabled.
- [ ] Pair a clean mother and phone without a terminal, then revoke the phone.
- [ ] Move a paired phone from trusted Wi-Fi to mobile data and back without re-entry or duplication.
- [ ] Send text, voice-note and push-to-talk traffic across a reconnect.
- [ ] Run a real task, calendar and communication action with exact approval and provider receipt.
- [ ] Exercise two isolated household identities on one TV, including inactivity logout.
- [ ] Qualify a freelancer in two unrelated organizations and an accountant's bounded sign-off.
- [ ] Prove a non-Pilot recipient receives useful content without leaking sender or household data.
- [ ] Export, restore and migrate a mother, then verify identity and proof continuity.
- [ ] Force a failed update and verify automatic rollback.
- [ ] Complete native possession, biometric, background-delivery and privacy tests.
- [x] Run adverse-network call tests and participant-removal key rotation.
- [ ] If Wave proceeds, complete two-mother text/PTT delivery with the internet physically disabled.

## Recommended execution order

1. `MOB-0514`: qualify real task, calendar and communication providers when the user authorizes accounts.
2. `MOB-1101`, `MOB-1102`: compile and sign native applications when full toolchains and identities are available.
3. `MOB-1201`: submit the native WebRTC media construction for independent cryptographic audit.
4. `MOB-1307`--`MOB-1310`: add genuine direct-radio adapters only with hardware, then complete compliance and disconnected proof.
5. Complete the household, business, security and legal field gates above.

The next closure exercise begins with `MOB-0514` after a real provider account is authorized.
