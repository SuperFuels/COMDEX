# Pilot iOS foundation

`PilotNativeCore` is testable with the Swift command-line toolchain. `PilotApp` is an XcodeGen
project specification and SwiftUI shell. Generate and sign the application on a Mac with the full
Xcode iOS SDK and an authorized Apple development team. The repository deliberately contains no
team identifier, provisioning profile, APNs key or customer endpoint.

The phone's Ed25519 protocol key is encrypted by a Secure Enclave P-256 agreement key and stored
with `WhenUnlockedThisDeviceOnly` Keychain protection. Face ID/Touch ID unlocks the local key for
one exact signed approval; biometrics are not treated as identity inference.
