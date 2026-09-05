# Pilot Section 6 External Qualification Register

Status: Pilot Fabric 0.43.0 — 30 August 2026

Section 6 is complete for locally enforceable software. The following items cannot be
truthfully closed by code alone. Each remains fail-closed at runtime.

| Capability | Current safe behavior | Evidence required to close |
| --- | --- | --- |
| Synchronized subtitle projection | Refuses projection unless native overlay, caption projection and content-rights grants are all present. | Signed native-TV scope plus provider/content authorization and field timing tests. |
| Local dubbing | Refuses to replace programme audio. | Explicit dubbing rights and an authorized platform audio-output route. |
| Compact playback overlay | Uses private phone or separate Pilot Canvas; never claims an overlay over third-party playback. | Native platform dismissible-overlay authority and field verification. |
| Dialogue/background audio processing | Exposes only signed hardware DSP presets. | Supported hardware control, vendor documentation and audible before/after field test. |
| Rich player and fantasy statistics | Shows goals, bookings, substitutions and lineups only when supplied by the authenticated response. | Licensed feed credentials, schema conformance and freshness/identity tests. |
| Elections and broader live events | Does not invent live status. Ticketmaster discovery covers configured events only. | Chosen authenticated election/awards/concert providers, credentials and test events. |
| Every goal/highlight | Returns official HTTPS routes only when the feed marks them provider-verified and rights-authorized; never copies video. | Licensed event feed with official clips and provider rights metadata. |
| External push alerts | Stores identity-bound notifications in the local private-phone inbox. | Signed native phone push adapter, consent, revocation and delivery receipts. |
| Cross-household competitions | Stores persona-bound, no-money predictions only. | Multi-person field test, guardian policy for children and abuse/notification review. |
| Fact-check performance claim | A three-case AION Native public-evidence smoke run achieved 3/3 verdict match, 100% HTTPS coverage and 11.12-second mean latency; it is not represented as general accuracy. | Larger dated, adversarial and multilingual runs in air-gapped, public-evidence and optional-provider modes on supported hardware. |

## Return rule

Reopen an item only when the relevant provider account, platform permission, hardware or
field environment exists. Record the exact version, device/provider, permission scope,
test evidence and rollback behavior before changing its status. A model answer, simulated
response or successful command delivery is not closure evidence.
