# Pilot Sections 13–14 Qualification Register

Status: Pilot Fabric 0.47.0 — 30 August 2026

The locally enforceable identity, privacy, inbox, task, delegation and reminder logic is
complete. The following items cannot truthfully be marked field-complete without an
authorized native platform, provider account or physical deployment.

## Section 13 — Production private identity

- Native iOS and Android application signing and secure-enclave/keystore key storage.
- Hardware-backed attestation and Face ID, Touch ID or Android biometric approval.
- Production push-based lost-device revocation and recovery qualification.
- Guardian policy, age assurance, privacy review and ordinary-family usability testing.
- Consumer migration from the earlier preview `local_persona` without silently merging
  identities or private memory.

Until those are qualified, Pilot may say **signed phone possession verified** but must not
say **biometrically approved**.

## Section 14 — Tasks, lists and reminders

- User-authorized Google OAuth with the Tasks scope and a live verified insertion receipt.
- Native background notifications and operating-system geofences for arrival/departure.
- Authorized Apple CarPlay, Android Auto or vehicle adapter qualification.
- Official WhatsApp Business, email or native share handoff for non-Pilot recipients.
- Multi-household field testing of recipient acceptance, revocation and offline delivery.

Provider execution remains disabled without an authorized persona-bound credential.
External messages remain `prepared_not_sent`, and route stops remain suggestions until a
person accepts them.

## Closure evidence required

Each external item needs a dated provider/platform receipt, the active persona, exact
scope, outcome verification, revocation test and a redacted audit record. Language-model
output is never authority to send, add, share, alter a route or create an external task.
