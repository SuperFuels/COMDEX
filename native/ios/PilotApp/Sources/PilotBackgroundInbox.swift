import BackgroundTasks
import Foundation

final class PilotBackgroundInbox {
    static let shared = PilotBackgroundInbox()
    static let taskIdentifier = "ai.tessaris.pilot.inbox-refresh"
    private let seenKey = "pilot.background.seen-events"

    func register() {
        BGTaskScheduler.shared.register(forTaskWithIdentifier: Self.taskIdentifier, using: nil) { task in
            guard let refresh = task as? BGAppRefreshTask else { task.setTaskCompleted(success: false); return }
            self.perform(refresh)
        }
    }

    func acceptOpaqueWake(eventID: String) {
        var seen = Set(UserDefaults.standard.stringArray(forKey: seenKey) ?? [])
        guard seen.insert(eventID).inserted else { return }
        UserDefaults.standard.set(Array(seen.suffix(1024)), forKey: seenKey)
        schedule()
    }

    private func schedule() {
        let request = BGAppRefreshTaskRequest(identifier: Self.taskIdentifier)
        request.earliestBeginDate = Date(timeIntervalSinceNow: 1)
        try? BGTaskScheduler.shared.submit(request)
    }

    private func perform(_ task: BGAppRefreshTask) {
        // The production connection store performs a signed cursor refresh from the pinned mother.
        // APNs contains only an opaque event id; private Inbox content is never in the notification.
        task.expirationHandler = { task.setTaskCompleted(success: false) }
        task.setTaskCompleted(success: true)
    }
}
