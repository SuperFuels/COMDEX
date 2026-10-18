import Foundation
import Security

/// The non-secret record of the Node this phone is allowed to contact.
/// Certificates and leases are stored in the Keychain rather than UserDefaults.
struct PilotConnection: Codable, Equatable {
    let motherID: String
    let endpoint: URL
    let motherFingerprint: String
    let certificateSHA256: String
    let certificatePEM: Data
    let certificate: [String: AnyCodable]
    let lease: [String: AnyCodable]
}

/// Small Codable wrapper for signed JSON objects returned by the Node.
enum AnyCodable: Codable, Equatable {
    case string(String), bool(Bool), number(Double), object([String: AnyCodable]), array([AnyCodable]), null
    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() { self = .null }
        else if let value = try? c.decode(Bool.self) { self = .bool(value) }
        else if let value = try? c.decode(Double.self) { self = .number(value) }
        else if let value = try? c.decode(String.self) { self = .string(value) }
        else if let value = try? c.decode([String: AnyCodable].self) { self = .object(value) }
        else { self = .array(try c.decode([AnyCodable].self)) }
    }
    func encode(to encoder: Encoder) throws {
        var c = encoder.singleValueContainer()
        switch self { case .string(let v): try c.encode(v); case .bool(let v): try c.encode(v); case .number(let v): try c.encode(v); case .object(let v): try c.encode(v); case .array(let v): try c.encode(v); case .null: try c.encodeNil() }
    }
}

enum PilotConnectionStore {
    private static let service = "ai.tessaris.pilot"
    private static let account = "trusted-node.v1"
    static func load() throws -> PilotConnection? {
        let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: service, kSecAttrAccount as String: account, kSecReturnData as String: true, kSecMatchLimit as String: kSecMatchLimitOne]
        var result: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess, let data = result as? Data else { throw ConnectionError.keychain(status) }
        return try JSONDecoder().decode(PilotConnection.self, from: data)
    }
    static func save(_ connection: PilotConnection) throws {
        let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: service, kSecAttrAccount as String: account]
        SecItemDelete(query as CFDictionary)
        var item = query
        item[kSecValueData as String] = try JSONEncoder().encode(connection)
        item[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        let status = SecItemAdd(item as CFDictionary, nil)
        guard status == errSecSuccess else { throw ConnectionError.keychain(status) }
    }
    static func remove() {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
        SecItemDelete(query as CFDictionary)
    }
    enum ConnectionError: Error { case keychain(OSStatus) }
}
