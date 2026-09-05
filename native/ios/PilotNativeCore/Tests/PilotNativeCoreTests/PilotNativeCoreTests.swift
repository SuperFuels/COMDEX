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
