import CryptoKit
import Foundation
import LocalAuthentication
import Security

public final class PilotPossessionVault {
    public static let account = "ai.tessaris.pilot.phone-possession"

    public init() {}

    public func publicKey() throws -> String {
        let key = try loadOrCreateSigningKey(context: nil)
        return key.publicKey.rawRepresentation.base64EncodedString()
    }

    public func signAfterLocalAuthentication(payload: Data, reason: String) async throws -> String {
        let context = LAContext()
        context.localizedCancelTitle = "Cancel"
        let policy: LAPolicy = .deviceOwnerAuthenticationWithBiometrics
        guard try await context.evaluatePolicy(policy, localizedReason: reason) else {
            throw VaultError.authenticationFailed
        }
        let key = try loadOrCreateSigningKey(context: context)
        return try key.signature(for: payload).base64EncodedString()
    }

    private func loadOrCreateSigningKey(context: LAContext?) throws -> Curve25519.Signing.PrivateKey {
        if let encrypted = try Keychain.read(account: Self.account) {
            return try unwrap(encrypted, context: context)
        }
        let signing = Curve25519.Signing.PrivateKey()
        let wrapped = try wrap(signing.rawRepresentation)
        try Keychain.write(wrapped, account: Self.account)
        return signing
    }

    private func wrap(_ raw: Data) throws -> Data {
        guard SecureEnclave.isAvailable else {
            throw VaultError.secureEnclaveUnavailable
        }
        let access = SecAccessControlCreateWithFlags(
            nil, kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
            [.privateKeyUsage, .biometryCurrentSet], nil
        )!
        let enclave = try SecureEnclave.P256.KeyAgreement.PrivateKey(
            compactRepresentable: false, accessControl: access
        )
        let ephemeral = P256.KeyAgreement.PrivateKey()
        let shared = try enclave.sharedSecretFromKeyAgreement(with: ephemeral.publicKey)
        let key = shared.hkdfDerivedSymmetricKey(
            using: SHA256.self, salt: Data("pilot-ios-v1".utf8),
            sharedInfo: Data(), outputByteCount: 32
        )
        let sealed = try AES.GCM.seal(raw, using: key).combined!
        let envelope: [String: String] = [
            "enclave": enclave.dataRepresentation.base64EncodedString(),
            "ephemeral": ephemeral.publicKey.x963Representation.base64EncodedString(),
            "sealed": sealed.base64EncodedString(),
        ]
        return try PilotCanonicalJSON.data(envelope)
    }

    private func unwrap(_ data: Data, context: LAContext?) throws -> Curve25519.Signing.PrivateKey {
        let envelope = try JSONDecoder().decode([String: String].self, from: data)
        guard let enclaveData = Data(base64Encoded: envelope["enclave"] ?? ""),
              let ephemeralData = Data(base64Encoded: envelope["ephemeral"] ?? ""),
              let sealedData = Data(base64Encoded: envelope["sealed"] ?? "") else {
            throw VaultError.invalidEnvelope
        }
        let enclave = try SecureEnclave.P256.KeyAgreement.PrivateKey(
            dataRepresentation: enclaveData, authenticationContext: context
        )
        let ephemeral = try P256.KeyAgreement.PublicKey(x963Representation: ephemeralData)
        let shared = try enclave.sharedSecretFromKeyAgreement(with: ephemeral)
        let key = shared.hkdfDerivedSymmetricKey(
            using: SHA256.self, salt: Data("pilot-ios-v1".utf8),
            sharedInfo: Data(), outputByteCount: 32
        )
        let box = try AES.GCM.SealedBox(combined: sealedData)
        return try Curve25519.Signing.PrivateKey(rawRepresentation: AES.GCM.open(box, using: key))
    }

    public enum VaultError: Error {
        case secureEnclaveUnavailable, authenticationFailed, invalidEnvelope
    }
}

private enum Keychain {
    static func read(account: String) throws -> Data? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: "ai.tessaris.pilot",
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]
        var result: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess, let data = result as? Data else { throw OSStatusError(status) }
        return data
    }

    static func write(_ data: Data, account: String) throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: "ai.tessaris.pilot",
            kSecAttrAccount as String: account,
        ]
        SecItemDelete(query as CFDictionary)
        var item = query
        item[kSecValueData as String] = data
        item[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        let status = SecItemAdd(item as CFDictionary, nil)
        guard status == errSecSuccess else { throw OSStatusError(status) }
    }

    struct OSStatusError: Error { let status: OSStatus; init(_ status: OSStatus) { self.status = status } }
}
