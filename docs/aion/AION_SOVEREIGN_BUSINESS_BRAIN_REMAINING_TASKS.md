# AION Sovereign Business Brain — Remaining Tasks

Status: canonical remaining-only register — 5 September 2026

## Immediate product delivery

- `SBB-0101B` Apple Developer ID signing, notarisation, stapling and clean Intel/Apple Silicon validation.
- `SBB-0101D` Windows signing and clean-machine installation, upgrade, rollback and removal validation.
- `SBB-0101E` Sign and natively qualify the completed Linux/server developer package and systemd registration on supported targets.
- `SBB-0101F` Complete the cross-platform clean-machine qualification matrix.

`SBB-0101A` is complete as an unsigned macOS arm64 package payload with launchd registration.
`SBB-0101C` is complete as an unsigned Windows x64 developer installer with Service Control Manager
registration. The package/service foundation of `SBB-0101E` is complete as an unsigned Linux x64
archive with a hardened systemd unit. Production signatures require the relevant publisher identities. Clean-machine claims
require representative target systems or controlled virtual/physical test infrastructure.

## Compute qualification

- `SBB-0502` Qualify one real customer-controlled private OpenAI-compatible inference endpoint.
- `SBB-0503` Qualify NVIDIA NIM deployment and NeMo evaluation without making NVIDIA authoritative.

The provider-neutral adapters and deployment contracts exist. These tasks require authorized live
compute targets and measured end-to-end results.

## Capability packages

- `SBB-0602` Add a production OS/container sandbox for arbitrary third-party capability code.
- Qualify each completed core department/industry pack against authorized real adapters and customer outcomes; add further packs only from evidenced demand.

## Operations and external assurance

- `SBB-0904` Complete independent penetration testing and software supply-chain review.
- `SBB-0905` Complete qualified privacy, employment, sector and AI-regulation assessments per launch region.
- `SBB-0906` Operationally validate service levels, disaster recovery, incident response and vulnerability disclosure.
- `SBB-0907` Complete a real small-business pilot and a real medium multi-unit pilot.

## Commercial adoption and sovereign-compute conversion

- `SBB-1003` Connect and certify a live payment provider against the completed opaque-reference, exact-approval and signed-event billing lifecycle.
- `SBB-1010` Real-customer pricing, conversion and willingness-to-pay validation.

## Production qualifications retained on completed foundations

The following implementation foundations are complete but retain deployment-specific evidence
requirements: real identity-provider integration, multi-unit/currency field validation, regional
residency and retention tests, real customer datasets/evaluators, production training artefacts,
and operational support staffing. They must remain visible in release readiness and must not be
misrepresented as internally self-certified.

## Current order

1. `SBB-1003` live certified payment-provider adapter.
2. Platform signing, notarisation and clean-machine/native-target qualification for macOS, Windows and Linux.
3. Live compute and capability-pack qualifications using authorized customer/provider environments.
4. Independent assurance, operations validation, pricing research and representative field trials.
