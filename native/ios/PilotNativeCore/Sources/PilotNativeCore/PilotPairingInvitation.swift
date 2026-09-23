import CryptoKit
import Foundation
import Security

/// The public, QR-safe introduction to a Tessaris Node.
///
/// An invitation establishes *which* Node a phone may begin pairing with. It
/// never grants access: the phone still creates its own possession key and the
/// person at the Node must confirm the one-time pairing code.
public struct PilotPairingInvitation: Sendable, Equatable {
    public let motherID: String
    public let motherPublicKey: String
    public let motherFingerprint: String
    public let endpoint: URL
    public let certificateSHA256: String
    /// A signed, public trust anchor for this Node only. It contains no key.
    public let certificatePEM: Data
    public let personaID: String
    public let requestedScopes: [String]
    public let expiresAt: Date

    public enum VerificationError: LocalizedError, Equatable {
        case malformed
        case unsupportedSchema
        case expired
        case unsafeInvitation
        case invalidSignature

        public var errorDescription: String? {
            switch self {
            case .malformed: "This Tessaris Node invitation is incomplete."
            case .unsupportedSchema: "This Tessaris Node invitation uses an unsupported format."
            case .expired: "This Tessaris Node invitation has expired. Ask the owner to create a new one."
            case .unsafeInvitation: "This invitation contains an unsafe Node address or permissions."
            case .invalidSignature: "This invitation was not signed by the Tessaris Node it names."
            }
        }
    }

    /// Decodes and verifies the QR payload before any pairing network request.
    public static func verify(_ data: Data, now: Date = .now) throws -> Self {
        let root = try dictionary(from: data)
        let invitationKeys: Set<String> = [
            "schema_version", "mother_descriptor", "persona_id", "requested_scopes",
            "issued_at", "expires_at", "nonce", "contains_mother_secret",
            "contains_pairing_confirmation", "payload_hash", "mother_signature",
        ]
        guard Set(root.keys) == invitationKeys else { throw VerificationError.malformed }
        guard root["schema_version"] as? String == "pilot.phone-pairing-invitation.v1" else {
            throw VerificationError.unsupportedSchema
        }
        guard root["contains_mother_secret"] as? Bool == false,
              root["contains_pairing_confirmation"] as? Bool == false else {
            throw VerificationError.unsafeInvitation
        }
        guard let descriptor = root["mother_descriptor"] as? [String: Any],
              let invitationExpiry = date(root["expires_at"]), invitationExpiry > now,
              let personaID = root["persona_id"] as? String, identifier(personaID),
              let scopes = root["requested_scopes"] as? [String], validScopes(scopes),
              let endpoint = try endpoint(descriptor["endpoint"]),
              let certificateSHA256 = descriptor["ca_sha256"] as? String,
              certificateSHA256.range(of: "^[0-9a-f]{64}$", options: .regularExpression) != nil,
              let certificatePEMBase64 = descriptor["ca_certificate_pem_b64"] as? String,
              let certificatePEM = Data(base64Encoded: certificatePEMBase64),
              let certificateDER = certificateDER(fromPEM: certificatePEM),
              SHA256.hash(data: certificateDER).hexString == certificateSHA256,
              let motherID = descriptor["mother_id"] as? String, identifier(motherID),
              let publicKey = descriptor["mother_public_key"] as? String,
              let fingerprint = descriptor["mother_fingerprint"] as? String,
              let descriptorExpiry = date(descriptor["expires_at"]), descriptorExpiry >= invitationExpiry
        else { throw VerificationError.malformed }

        try verifyDescriptor(descriptor, publicKey: publicKey, fingerprint: fingerprint, now: now)
        try verifySigned(root, publicKey: publicKey)

        return Self(
            motherID: motherID,
            motherPublicKey: publicKey,
            motherFingerprint: fingerprint,
            endpoint: endpoint,
            certificateSHA256: certificateSHA256,
            certificatePEM: certificatePEM,
            personaID: personaID,
            requestedScopes: scopes,
            expiresAt: invitationExpiry
        )
    }

    private static func verifyDescriptor(
        _ descriptor: [String: Any], publicKey: String, fingerprint: String, now: Date
    ) throws {
        let keys: Set<String> = [
            "schema_version", "mother_id", "mother_public_key", "mother_fingerprint", "endpoint",
            "ca_sha256", "ca_certificate_pem_b64", "issued_at", "expires_at", "mother_signature",
        ]
        guard Set(descriptor.keys) == keys,
              descriptor["schema_version"] as? String == "pilot.mother-descriptor.v2",
              date(descriptor["expires_at"])! > now,
              let rawKey = Data(base64Encoded: publicKey), rawKey.count == 32,
              SHA256.hash(data: rawKey).hexString.prefix(32) == fingerprint.lowercased()
        else { throw VerificationError.invalidSignature }
        try verifySigned(descriptor, publicKey: publicKey)
    }

    private static func verifySigned(_ signed: [String: Any], publicKey: String) throws {
        guard let payloadHash = signed["payload_hash"] as? String,
              let signature = signed["mother_signature"] as? String else {
            // Mother descriptors predate the invitation hash but are still signed.
            if signed["payload_hash"] == nil, let signature = signed["mother_signature"] as? String {
                var payload = signed
                payload.removeValue(forKey: "mother_signature")
                guard let keyData = Data(base64Encoded: publicKey),
                      let signatureData = Data(base64Encoded: signature),
                      let message = try? PilotCanonicalJSON.data(payload),
                      let key = try? Curve25519.Signing.PublicKey(rawRepresentation: keyData),
                      key.isValidSignature(signatureData, for: message) else {
                    throw VerificationError.invalidSignature
                }
                return
            }
            throw VerificationError.malformed
        }
        var payload = signed
        payload.removeValue(forKey: "mother_signature")
        payload.removeValue(forKey: "payload_hash")
        guard let payloadData = try? PilotCanonicalJSON.data(payload),
              SHA256.hash(data: payloadData).hexString == payloadHash else {
            throw VerificationError.invalidSignature
        }
        payload["payload_hash"] = payloadHash
        guard let message = try? PilotCanonicalJSON.data(payload),
              let keyData = Data(base64Encoded: publicKey),
              let signatureData = Data(base64Encoded: signature),
              let key = try? Curve25519.Signing.PublicKey(rawRepresentation: keyData),
              key.isValidSignature(signatureData, for: message) else {
            throw VerificationError.invalidSignature
        }
    }

    private static func dictionary(from data: Data) throws -> [String: Any] {
        guard let object = try? JSONSerialization.jsonObject(with: data), let value = object as? [String: Any] else {
            throw VerificationError.malformed
        }
        return value
    }

    private static func date(_ value: Any?) -> Date? {
        guard let text = value as? String else { return nil }
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.date(from: text)
    }

    private static func endpoint(_ value: Any?) throws -> URL? {
        guard let text = value as? String, let url = URL(string: text), url.scheme == "https", url.host != nil else {
            throw VerificationError.unsafeInvitation
        }
        return url
    }

    private static func identifier(_ value: String) -> Bool {
        value.range(of: "^[A-Za-z0-9_.-]{1,128}$", options: .regularExpression) != nil
    }

    private static func validScopes(_ scopes: [String]) -> Bool {
        !scopes.isEmpty && scopes.count <= 96 && scopes == Array(Set(scopes)).sorted() &&
            scopes.allSatisfy { $0.range(of: "^[a-z][a-z0-9_.-]{0,63}$", options: .regularExpression) != nil }
    }

    private static func certificateDER(fromPEM pem: Data) -> Data? {
        guard let text = String(data: pem, encoding: .utf8) else { return nil }
        let body = text
            .replacingOccurrences(of: "-----BEGIN CERTIFICATE-----", with: "")
            .replacingOccurrences(of: "-----END CERTIFICATE-----", with: "")
            .components(separatedBy: .whitespacesAndNewlines)
            .joined()
        guard let der = Data(base64Encoded: body),
              SecCertificateCreateWithData(nil, der as CFData) != nil else { return nil }
        return der
    }
}

private extension SHA256.Digest {
    var hexString: String { map { String(format: "%02x", $0) }.joined() }
}
