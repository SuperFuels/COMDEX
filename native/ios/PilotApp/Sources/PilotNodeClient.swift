import Foundation
import Security

/// HTTPS client that accepts only the CA included in the signed Node invitation.
final class PilotNodeClient: NSObject, URLSessionDelegate {
    private let anchor: SecCertificate
    private let endpoint: URL

    init(invitation: PilotPairingInvitation) throws {
        guard let anchor = Self.certificate(fromPEM: invitation.certificatePEM) else {
            throw ClientError.invalidTrustAnchor
        }
        self.anchor = anchor
        self.endpoint = invitation.endpoint
    }

    init(connection: PilotConnection) throws {
        guard let anchor = Self.certificate(fromPEM: connection.certificatePEM) else {
            throw ClientError.invalidTrustAnchor
        }
        self.anchor = anchor
        self.endpoint = connection.endpoint
    }

    /// Read the founder's private Inbox using the lease issued at pairing.
    /// This is read-only and never fabricates activity when the Node is offline.
    func inboxStream(connection: PilotConnection) async throws -> [String: Any] {
        let certificate = try Self.jsonObject(connection.certificate)
        let lease = try Self.jsonObject(connection.lease)
        return try await request(path: "/v1/inbox/stream", body: [
            "persona_id": "",
            "certificate": certificate,
            "lease": lease,
        ])
    }

    /// Every workspace request is signed by the phone possession key after
    /// local authentication.  The Node evaluates the paired-device lease,
    /// role scope and workspace membership independently.
    func signedRequest(
        path: String,
        request: [String: Any],
        connection: PilotConnection,
        vault: PilotPossessionVault,
        reason: String,
        timeout: TimeInterval = 12
    ) async throws -> [String: Any] {
        let certificate = try Self.jsonObject(connection.certificate)
        let lease = try Self.jsonObject(connection.lease)
        let signature = try await vault.signAfterLocalAuthentication(
            payload: try PilotCanonicalJSON.data(request), reason: reason
        )
        return try await self.request(path: path, body: [
            "request": request,
            "certificate": certificate,
            "lease": lease,
            "phone_signature": signature,
        ], timeout: timeout)
    }

    /// Read the caller's own Personal Pilot dashboard state. The Node does
    /// not return another person's shared-screen session details.
    func personalDashboard(connection: PilotConnection, vault: PilotPossessionVault) async throws -> [String: Any] {
        try await signedRequest(
            path: "/v1/personal/snapshot",
            request: ["persona_id": Self.personaID(connection), "purpose": "read_personal_pilot"],
            connection: connection, vault: vault,
            reason: "Open your private Pilot dashboard"
        )
    }

    /// Acquire or release the browser/TV Pilot dashboard using a separate
    /// signed possession proof. The session expires automatically.
    func changeSharedDashboardSession(
        operation: String, connection: PilotConnection, vault: PilotPossessionVault
    ) async throws -> [String: Any] {
        let nonce = UUID().uuidString
        let possession = [
            "purpose": operation == "acquire" ? "activate_shared_screen" : "release_shared_screen",
            "persona_id": Self.personaID(connection),
            "device_id": Self.deviceID(connection),
            "nonce": nonce,
        ] as [String: Any]
        let possessionSignature = try await vault.signAfterLocalAuthentication(
            payload: try PilotCanonicalJSON.data(possession),
            reason: operation == "acquire" ? "Connect Personal to the Pilot dashboard" : "Lock the Pilot dashboard"
        )
        var request = possession
        request["operation"] = operation
        request["possession_nonce"] = nonce
        request["possession_signature"] = possessionSignature
        request["idempotency_key"] = UUID().uuidString
        return try await signedRequest(
            path: "/v1/personal/tv/session", request: request,
            connection: connection, vault: vault,
            reason: operation == "acquire" ? "Confirm this Personal dashboard session" : "Confirm locking this Pilot dashboard"
        )
    }

    func confirmSharedDashboardPresence(connection: PilotConnection, vault: PilotPossessionVault) async throws -> [String: Any] {
        try await signedRequest(
            path: "/v1/personal/tv/presence",
            request: ["persona_id": Self.personaID(connection), "purpose": "confirm_local_phone_presence", "idempotency_key": UUID().uuidString],
            connection: connection, vault: vault,
            reason: "Keep your Personal Pilot dashboard active"
        )
    }

    func openDashboardSurface(
        command: String, arguments: [String: Any] = [:], connection: PilotConnection, vault: PilotPossessionVault
    ) async throws -> [String: Any] {
        try await signedRequest(
            path: "/v1/personal/dashboard/action",
            request: ["persona_id": Self.personaID(connection), "command": command,
                      "arguments": arguments, "idempotency_key": UUID().uuidString],
            connection: connection, vault: vault,
            reason: "Open \(command) in your signed Pilot dashboard"
        )
    }

    /// Sends one explicit signed television control to the paired home node.
    func controlSharedTelevision(
        command: String, arguments: [String: Any] = [:], connection: PilotConnection, vault: PilotPossessionVault
    ) async throws -> [String: Any] {
        try await signedRequest(
            path: "/v1/personal/tv/control",
            request: ["persona_id": Self.personaID(connection), "command": command,
                      "arguments": arguments, "idempotency_key": UUID().uuidString],
            connection: connection, vault: vault,
            reason: "\(command == "games" ? "Open games" : "Control the television") from this iPhone"
        )
    }

    /// Opens a signed personal experience. The Node reports an attempted launch
    /// separately from a verified playing state so the phone never implies success.
    func controlExperience(
        operation: String, arguments: [String: Any] = [:], connection: PilotConnection, vault: PilotPossessionVault
    ) async throws -> [String: Any] {
        try await signedRequest(
            path: "/v1/personal/experiences/control",
            request: ["persona_id": Self.personaID(connection), "operation": operation,
                      "arguments": arguments, "idempotency_key": UUID().uuidString],
            connection: connection, vault: vault,
            reason: operation == "games_open" ? "Open games on the television" : "Control your Pilot experience"
        )
    }

    func workspaceSpaces(connection: PilotConnection, vault: PilotPossessionVault) async throws -> [String: Any] {
        try await signedRequest(
            path: "/v1/workspaces/spaces/snapshot",
            request: ["persona_id": Self.personaID(connection), "purpose": "mobile_boardroom_spaces", "idempotency_key": UUID().uuidString],
            connection: connection, vault: vault,
            reason: "Open your authorised Tessaris workspaces"
        )
    }

    func workspaceSurface(
        membershipID: String, surface: String, connection: PilotConnection, vault: PilotPossessionVault
    ) async throws -> [String: Any] {
        try await signedRequest(
            path: "/v1/workspaces/surfaces/read",
            request: ["persona_id": Self.personaID(connection), "membership_id": membershipID, "surface": surface, "idempotency_key": UUID().uuidString],
            connection: connection, vault: vault,
            reason: "Read this private Tessaris workspace"
        )
    }

    func workScheduleSnapshot(
        membershipID: String, connection: PilotConnection, vault: PilotPossessionVault
    ) async throws -> [String: Any] {
        try await signedRequest(
            path: "/v1/workspaces/work-schedule/snapshot",
            request: ["persona_id": Self.personaID(connection), "membership_id": membershipID, "idempotency_key": UUID().uuidString],
            connection: connection, vault: vault,
            reason: "Open your private work schedule"
        )
    }

    func workScheduleAction(
        membershipID: String, operation: String, fields: [String: Any],
        connection: PilotConnection, vault: PilotPossessionVault
    ) async throws -> [String: Any] {
        try await signedRequest(
            path: "/v1/workspaces/work-schedule/action",
            request: ["persona_id": Self.personaID(connection), "membership_id": membershipID,
                      "operation": operation, "fields": fields, "idempotency_key": UUID().uuidString],
            connection: connection, vault: vault,
            reason: operation == "create" ? "Create this job" : "Update this job"
        )
    }

    /// Opens the caller's active Boardroom surface with one Face ID proof.
    /// The Node derives the membership from the signed phone certificate.
    func openWorkspaceSurface(
        surface: String, connection: PilotConnection, vault: PilotPossessionVault
    ) async throws -> [String: Any] {
        try await signedRequest(
            path: "/v1/workspaces/surfaces/open",
            request: ["persona_id": Self.personaID(connection), "surface": surface, "idempotency_key": UUID().uuidString],
            connection: connection, vault: vault,
            reason: "Open this private Tessaris workspace"
        )
    }

    func workspaceConversation(
        membershipID: String, departmentID: String, text: String, connection: PilotConnection, vault: PilotPossessionVault
    ) async throws -> [String: Any] {
        try await signedRequest(
            path: "/v1/workspaces/conversations/turn",
            request: ["persona_id": Self.personaID(connection), "membership_id": membershipID, "department_id": departmentID, "user_text": text, "idempotency_key": UUID().uuidString],
            connection: connection, vault: vault,
            reason: "Send this instruction to your Tessaris Pilot",
            timeout: 60
        )
    }

    func workspaceConversationHistory(
        membershipID: String, departmentID: String, before: String = "", limit: Int = 50,
        connection: PilotConnection, vault: PilotPossessionVault
    ) async throws -> [String: Any] {
        try await signedRequest(
            path: "/v1/workspaces/conversations/history",
            request: ["persona_id": Self.personaID(connection), "membership_id": membershipID,
                      "department_id": departmentID, "before": before, "limit": min(max(limit, 10), 75),
                      "idempotency_key": UUID().uuidString],
            connection: connection, vault: vault,
            reason: "Read your private Tessaris conversation history"
        )
    }

    func executiveChannelsStatus(
        membershipID: String, connection: PilotConnection, vault: PilotPossessionVault
    ) async throws -> [String: Any] {
        try await signedRequest(
            path: "/v1/workspaces/executive-channels/status",
            request: ["persona_id": Self.personaID(connection), "membership_id": membershipID,
                      "idempotency_key": UUID().uuidString],
            connection: connection, vault: vault,
            reason: "Read your private executive channels"
        )
    }

    func executiveChannelHistory(
        membershipID: String, departmentID: String, limit: Int = 75,
        connection: PilotConnection, vault: PilotPossessionVault
    ) async throws -> [String: Any] {
        try await signedRequest(
            path: "/v1/workspaces/executive-channels/history",
            request: ["persona_id": Self.personaID(connection), "membership_id": membershipID,
                      "department_id": departmentID, "limit": min(max(limit, 10), 100),
                      "idempotency_key": UUID().uuidString],
            connection: connection, vault: vault,
            reason: "Read this private COO department channel"
        )
    }

    func executiveChannelTurn(
        membershipID: String, departmentID: String, text: String,
        connection: PilotConnection, vault: PilotPossessionVault
    ) async throws -> [String: Any] {
        try await signedRequest(
            path: "/v1/workspaces/executive-channels/turn",
            request: ["persona_id": Self.personaID(connection), "membership_id": membershipID,
                      "department_id": departmentID, "user_text": text,
                      "idempotency_key": UUID().uuidString],
            connection: connection, vault: vault,
            reason: "Send this COO instruction to the selected Department Pilot",
            timeout: 60
        )
    }

    func createCustomDepartment(
        membershipID: String, name: String, template: String, mandate: String,
        connection: PilotConnection, vault: PilotPossessionVault
    ) async throws -> [String: Any] {
        try await signedRequest(
            path: "/v1/workspaces/custom-departments/create",
            request: ["persona_id": Self.personaID(connection), "membership_id": membershipID,
                      "department": ["name": name, "template": template, "mandate": mandate],
                      "idempotency_key": UUID().uuidString],
            connection: connection, vault: vault,
            reason: "Create this custom Tessaris department"
        )
    }

    func deleteCustomDepartment(
        membershipID: String, departmentID: String, connection: PilotConnection, vault: PilotPossessionVault
    ) async throws -> [String: Any] {
        try await signedRequest(
            path: "/v1/workspaces/custom-departments/delete",
            request: ["persona_id": Self.personaID(connection), "membership_id": membershipID,
                      "department_id": departmentID, "idempotency_key": UUID().uuidString],
            connection: connection, vault: vault,
            reason: "Delete this custom Tessaris department"
        )
    }

    func pairingChallenge(personaID: String, deviceLabel: String, phonePublicKey: String, scopes: [String]) async throws -> [String: Any] {
        try await request(path: "/v1/pairing/challenges", body: [
            "persona_id": personaID,
            "device_label": deviceLabel,
            "phone_public_key": phonePublicKey,
            "requested_scopes": scopes,
        ])
    }

    func completePairing(challenge: [String: Any], confirmationCode: String, vault: PilotPossessionVault) async throws -> [String: Any] {
        let fields = ["schema_version", "challenge_id", "mother_id", "mother_fingerprint", "mother_descriptor_hash", "persona_id", "device_id", "device_label", "requested_scopes", "nonce", "issued_at", "expires_at"]
        let signed = try Dictionary(uniqueKeysWithValues: fields.map { key in
            guard let value = challenge[key] else { throw ClientError.invalidResponse }
            return (key, value)
        })
        let signature = try await vault.signAfterLocalAuthentication(payload: try PilotCanonicalJSON.data(signed), reason: "Confirm pairing this phone with your Tessaris Node")
        return try await request(path: "/v1/pairing/complete", body: [
            "challenge_id": challenge["challenge_id"] as? String ?? "",
            "confirmation_code": confirmationCode,
            "phone_signature": signature,
        ])
    }

    private func request(path: String, body: [String: Any], timeout: TimeInterval = 12) async throws -> [String: Any] {
        guard let url = URL(string: path, relativeTo: endpoint) else { throw ClientError.invalidEndpoint }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = timeout
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        let session = URLSession(configuration: .ephemeral, delegate: self, delegateQueue: nil)
        do {
            let (data, response) = try await session.data(for: request)
            guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
                let payload = (try? JSONSerialization.jsonObject(with: data) as? [String: Any]) ?? [:]
                let detail = payload["detail"] as? String ?? payload["error"] as? String ?? "The Node rejected this request (HTTP \((response as? HTTPURLResponse)?.statusCode ?? 0))."
                throw ClientError.nodeRejected(detail)
            }
            guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { throw ClientError.invalidResponse }
            return json
        } catch {
            print("Pilot Node request failed: \(error.localizedDescription) [\(error)]")
            throw error
        }
    }

    func urlSession(_ session: URLSession, didReceive challenge: URLAuthenticationChallenge, completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        guard challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
              let trust = challenge.protectionSpace.serverTrust else {
            completionHandler(.performDefaultHandling, nil); return
        }
        // Preserve normal host verification while trusting only the signed
        // household CA embedded in the verified invitation.
        if let host = endpoint.host {
            SecTrustSetPolicies(trust, SecPolicyCreateSSL(true, host as CFString))
        }
        SecTrustSetAnchorCertificates(trust, [anchor] as CFArray)
        SecTrustSetAnchorCertificatesOnly(trust, true)
        var verificationError: CFError?
        guard SecTrustEvaluateWithError(trust, &verificationError) else {
            print("Pilot Node trust evaluation failed: \(String(describing: verificationError))")
            completionHandler(.cancelAuthenticationChallenge, nil); return
        }
        completionHandler(.useCredential, URLCredential(trust: trust))
    }

    private static func jsonObject(_ value: [String: AnyCodable]) throws -> [String: Any] {
        let data = try JSONEncoder().encode(value)
        guard let object = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw ClientError.invalidResponse
        }
        return object
    }

    private static func personaID(_ connection: PilotConnection) -> String {
        if case .string(let value)? = connection.certificate["persona_id"] { return value }
        return ""
    }

    private static func deviceID(_ connection: PilotConnection) -> String {
        if case .string(let value)? = connection.certificate["device_id"] { return value }
        return ""
    }

    private static func certificate(fromPEM pem: Data) -> SecCertificate? {
        guard let text = String(data: pem, encoding: .utf8) else { return nil }
        let body = text.replacingOccurrences(of: "-----BEGIN CERTIFICATE-----", with: "").replacingOccurrences(of: "-----END CERTIFICATE-----", with: "").components(separatedBy: .whitespacesAndNewlines).joined()
        guard let der = Data(base64Encoded: body) else { return nil }
        return SecCertificateCreateWithData(nil, der as CFData)
    }
    enum ClientError: LocalizedError { case invalidTrustAnchor, invalidEndpoint, nodeRejected(String), invalidResponse
        var errorDescription: String? {
            switch self {
            case .invalidTrustAnchor: return "The Node trust certificate is invalid."
            case .invalidEndpoint: return "The paired Node address is invalid."
            case .nodeRejected(let detail): return detail
            case .invalidResponse: return "The Node returned an unreadable response."
            }
        }
    }
}
