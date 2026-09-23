# Pilot iOS foundation

`PilotNativeCore` is testable with the Swift command-line toolchain. `PilotApp` is an XcodeGen
project specification and SwiftUI shell. Generate and sign the application on a Mac with the full
Xcode iOS SDK and an authorized Apple development team. The repository deliberately contains no
team identifier, provisioning profile, APNs key or customer endpoint.

The phone's Ed25519 protocol key is encrypted by a Secure Enclave P-256 agreement key and stored
with `WhenUnlockedThisDeviceOnly` Keychain protection. Face ID/Touch ID unlocks the local key for
one exact signed approval; biometrics are not treated as identity inference.

## Personal Pilot boundary

The iPhone Personal profile controls only the user's private Personal Pilot and shared home or TV
surface. It must not expose the Business Dashboard, Operations Command Centre, Department Pilots,
business workflows, or business navigation aliases.

The phone holds the private signing key and establishes a short-lived Personal session for the
browser or television. Personal tiles and commands are available only while that signed session is
active. Business access remains in the Tessaris business experience and is not inferred or granted
from a Personal Pilot session.

## Executive channels

The native Executive tab lists **Executive channels** directly beneath **Executive meeting**.
Opening that separate screen provides persistent COO-to-Department-Pilot channels for Sales,
Marketing, Finance, Support, People and every founder-created Department Pilot. Products &
Services is intentionally excluded because it is a business data area rather than a Pilot. The
channel roster is loaded from the workspace, so creating or deleting a custom department updates
both desktop and mobile without a client release. Selecting a department changes the shared
conversation being read and written; it does not create a phone-only chat. The records are served
by the same Operations executive-briefing service used by the desktop Operations Command Centre,
including morning minutes, evidence references, model receipts and approval-gated state.

The phone calls the signed Workspace Gateway routes below:

- `POST /v1/workspaces/executive-channels/status`
- `POST /v1/workspaces/executive-channels/history`
- `POST /v1/workspaces/executive-channels/turn`

Every request requires the paired phone certificate, an active lease with
`workspace.conversation`, a valid phone signature and an active workspace membership. Department
history may also be restricted by an exact `workspace.department.<department>.conversation`
membership scope. The channel gateway remains read/conversation-only: if a provider claims that a
turn performed an external write, the response is rejected. Any operational action proposed in a
channel must continue through the normal approval and execution gateway.
