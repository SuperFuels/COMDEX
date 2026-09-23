import SwiftUI
import UserNotifications

@main
struct PilotApp: App {
    @UIApplicationDelegateAdaptor(PilotAppDelegate.self) var delegate
    var body: some Scene { WindowGroup { PilotHomeView() } }
}

final class PilotAppDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate {
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        UNUserNotificationCenter.current().delegate = self
        PilotBackgroundInbox.shared.register()
        return true
    }

    func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken token: Data) {
        NotificationCenter.default.post(name: .pilotPushToken, object: token.map { String(format: "%02x", $0) }.joined())
    }

    func application(
        _ application: UIApplication,
        didReceiveRemoteNotification userInfo: [AnyHashable: Any],
        fetchCompletionHandler completionHandler: @escaping (UIBackgroundFetchResult) -> Void
    ) {
        guard let eventID = userInfo["event_id"] as? String else { completionHandler(.noData); return }
        PilotBackgroundInbox.shared.acceptOpaqueWake(eventID: eventID)
        completionHandler(.newData)
    }
}

extension Notification.Name { static let pilotPushToken = Notification.Name("pilot.push-token") }
