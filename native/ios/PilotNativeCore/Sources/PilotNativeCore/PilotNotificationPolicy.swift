import Foundation

public enum PilotNotificationPolicy {
    public static func protectedPreview() -> (title: String, body: String) {
        ("Pilot", "Open Pilot to view a private update.")
    }

    public static func backgroundWake(eventID: String, kind: String, deviceID: String) -> [String: Any] {
        [
            "schema_version": "pilot.native-background-wake.v1",
            "event_id": eventID,
            "kind": kind,
            "device_id": deviceID,
            "content_available": true,
            "private_content_included": false,
        ]
    }
}
