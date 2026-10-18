# Pilot Section 7 External Qualification Register

Status: Pilot Fabric 0.45.0 — 30 August 2026

| Capability | Current safe behavior | Evidence required to close |
| --- | --- | --- |
| Netflix/Prime/Disney/YouTube entitlement | Treats catalogue results and app opening as insufficient; accepts entitlement only from signed scoped telemetry. | Authorized account/native adapters and real account field tests per provider/region. |
| Exact title launch/playback | Strict official routes and private confirmation exist; playback requires title plus playing evidence. | Field matrix across provider versions, TV models and regions. |
| Continue watching | Persists the last persona-owned verified route and requires new private confirmation. | Signed provider position/state adapter and restart/provider-change field tests. |
| Episode reminders | Requires exact provider/content/episode metadata and stores locally. | Authorized schedule metadata and signed native phone push receipt. |
| Watch together | Room handoff contract exists without claiming synchronized playback. | Provider synchronization authority, two-room devices and timing qualification. |
| Provider sign-in recovery | Opens official owner-action surface and never handles raw credentials. | Native account-state adapter and tested expired-session recovery. |
| Programme sharing | Rights-safe Moment and official-link boundary exists. | Provider-native sharing adapter and recipient opening receipts. |

No provider capability is complete because a catalogue search succeeded or an application
opened. Closure requires the exact signed account/device/provider evidence listed above.
