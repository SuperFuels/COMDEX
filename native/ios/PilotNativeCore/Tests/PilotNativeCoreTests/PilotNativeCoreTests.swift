import Foundation
import Testing
@testable import PilotNativeCore

@Test func protectedPreviewContainsNoPrivateContent() {
    let preview = PilotNotificationPolicy.protectedPreview()
    #expect(preview.title == "Pilot")
    #expect(preview.body == "Open Pilot to view a private update.")
}

@Test func backgroundWakeContainsNoPrivatePayload() {
    let payload = PilotNotificationPolicy.backgroundWake(eventID: "event_1", kind: "task", deviceID: "phone_1")
    #expect(payload["private_content_included"] as? Bool == false)
    #expect(payload["content_available"] as? Bool == true)
}

@Test func legacyNodeInvitationIsRejectedBeforePairingBegins() throws {
    let beforeExpiry = ISO8601DateFormatter().date(from: "2029-12-31T23:59:59Z")!

    #expect(throws: PilotPairingInvitation.VerificationError.malformed) {
        try PilotPairingInvitation.verify(validInvitation, now: beforeExpiry)
    }
}

@Test func changedNodeInvitationIsRejectedBeforePairingBegins() throws {
    var value = try JSONSerialization.jsonObject(with: validInvitation) as! [String: Any]
    value["requested_scopes"] = ["message.send", "task.create", "tv.control"]
    let changed = try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys, .withoutEscapingSlashes])
    let beforeExpiry = ISO8601DateFormatter().date(from: "2029-12-31T23:59:59Z")!

    #expect(throws: PilotPairingInvitation.VerificationError.malformed) {
        try PilotPairingInvitation.verify(changed, now: beforeExpiry)
    }
}

private let validInvitation = Data("""
{"schema_version":"pilot.phone-pairing-invitation.v1","mother_descriptor":{"schema_version":"pilot.mother-descriptor.v1","mother_id":"node_home_mother","mother_public_key":"ebVWLo/mVPlAeLES6KmLp5AfhTrmlb7X4OORC60ElmQ=","mother_fingerprint":"65b60673d6ed884bf01c2c222d82ada0","endpoint":"https://node.example.test:8767","ca_sha256":"abababababababababababababababababababababababababababababababab","issued_at":"2030-01-01T00:00:00+00:00","expires_at":"2030-01-01T00:10:00+00:00","mother_signature":"PpI1/2R808QoMQRlcQoDX+1WLnVQ5l6dLN+GHuiDYVvni7S+ohUrjntvQFMPcs9Nj99k/HZYIJh/iT0QoVMKDw=="},"persona_id":"persona_owner","requested_scopes":["message.send","task.create"],"issued_at":"2030-01-01T00:00:00+00:00","expires_at":"2030-01-01T00:10:00+00:00","nonce":"fixtureNonce123","contains_mother_secret":false,"contains_pairing_confirmation":false,"payload_hash":"9a661e300759d707d0d1630fd2da22033f59982e632d312dccb1b799293a604e","mother_signature":"SSGAyeSc1oa0ZwYg50T5I/JBpjsYTUzpJTEX/978/HpgIm6Khles0/egdfDm4h0smgTxcQPguwXAtgsjwvYMBQ=="}
""".utf8)
