from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
IOS_CORE = ROOT / "native" / "ios" / "PilotNativeCore"
IOS_APP = ROOT / "native" / "ios" / "PilotApp"
ANDROID = ROOT / "native" / "android"


def test_ios_native_project_uses_secure_enclave_keychain_and_local_authentication():
    vault = (IOS_CORE / "Sources/PilotNativeCore/PilotPossessionVault.swift").read_text()
    project = (IOS_APP / "project.yml").read_text()
    app = (IOS_APP / "Sources/PilotApp.swift").read_text()
    background = (IOS_APP / "Sources/PilotBackgroundInbox.swift").read_text()
    assert "SecureEnclave.P256.KeyAgreement.PrivateKey" in vault
    assert "Curve25519.Signing.PrivateKey" in vault
    assert "kSecAttrAccessibleWhenUnlockedThisDeviceOnly" in vault
    assert ".biometryCurrentSet" in vault
    assert ".deviceOwnerAuthenticationWithBiometrics" in vault
    assert "CODE_SIGN_STYLE: Automatic" in project
    assert 'DEVELOPMENT_TEAM: ""' in project
    assert "didRegisterForRemoteNotificationsWithDeviceToken" in app
    assert "BGAppRefreshTaskRequest" in background
    assert "guard seen.insert(eventID).inserted" in background
    assert "private Inbox content is never in the notification" in background


def test_android_native_project_uses_keystore_biometric_and_private_background_delivery():
    vault = (ANDROID / "app/src/main/java/ai/tessaris/pilot/PilotPossessionVault.kt").read_text()
    biometric = (ANDROID / "app/src/main/java/ai/tessaris/pilot/PilotBiometricApproval.kt").read_text()
    push = (ANDROID / "app/src/main/java/ai/tessaris/pilot/PilotMessagingService.kt").read_text()
    manifest = (ANDROID / "app/src/main/AndroidManifest.xml").read_text()
    assert 'KeyStore.getInstance("AndroidKeyStore")' in vault
    assert "AUTH_BIOMETRIC_STRONG" in vault
    assert ".setInvalidatedByBiometricEnrollment(true)" in vault
    assert 'KeyPairGenerator.getInstance("Ed25519")' in vault
    assert "BiometricPrompt.CryptoObject(cipher)" in biometric
    assert 'enqueueUniqueWork(' in push
    assert '"Open Pilot to view a private update."' in push
    assert "message.data[\"event_id\"]" in push
    assert 'android:usesCleartextTraffic="false"' in manifest


def test_native_projects_do_not_contain_signing_or_provider_secrets():
    allowed_text = []
    for root in (IOS_CORE, IOS_APP, ANDROID):
        for path in root.rglob("*"):
            if path.is_file() and ".build" not in path.parts:
                allowed_text.append(path.read_text(errors="ignore"))
    combined = "\n".join(allowed_text)
    for forbidden in ("BEGIN PRIVATE KEY", "google-services.json", "APNS_AUTH_KEY", "AIza"):
        assert forbidden not in combined
