# Pilot Android foundation

This is the native Android source foundation. The protocol Ed25519 key is wrapped by a
non-exportable Android Keystore AES key configured for strong-biometric or device-credential
authentication and invalidation after biometric enrollment changes. Push messages contain only an
opaque event identifier and produce a private lock-screen preview; WorkManager deduplicates refresh
work by event identifier.

The repository contains no signing keystore, FCM server credential, customer endpoint or private
mother data. Building and signing requires JDK 17, the Android SDK, Gradle, an owner-controlled app
signing key and a Firebase configuration selected by the deployer. Those tools are not installed on
the current development Mac, so no APK or physical-device qualification is claimed yet.
