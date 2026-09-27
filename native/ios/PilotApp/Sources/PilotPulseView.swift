import SwiftUI
import AVFoundation
import Speech
import UniformTypeIdentifiers
import PhotosUI
import EventKit

import AVFoundation
import Foundation
import Speech

/// Native, visible speech capture for Pilot chat and meeting drafting.
/// Conversation callers submit a completed spoken turn to Pilot; meeting callers
/// keep the transcript as an editable draft until the user chooses to use it.
@MainActor
final class PilotLiveDictation: NSObject, ObservableObject {
    enum State: Equatable {
        case idle
        case requestingPermission
        case listening
        case unavailable(String)

        var message: String {
            switch self {
            case .idle: return ""
            case .requestingPermission: return "Preparing microphone…"
            case .listening: return "Listening…"
            case .unavailable(let message): return message
            }
        }
    }

    @Published private(set) var state: State = .idle
    @Published private(set) var transcript = ""

    private let recognizer = SFSpeechRecognizer(locale: Locale.current)
    private let audioEngine = AVAudioEngine()
    private var request: SFSpeechAudioBufferRecognitionRequest?
    private var task: SFSpeechRecognitionTask?

    var isListening: Bool { state == .listening }

    func start(initialText: String = "") async {
        guard !isListening else { return }
        state = .requestingPermission
        transcript = initialText.trimmingCharacters(in: .whitespacesAndNewlines)

        let speechGranted = await requestSpeechPermission()
        guard speechGranted else {
            state = .unavailable("Allow Speech Recognition in iPhone Settings to use Pilot Flow.")
            return
        }
        let microphoneGranted = await requestMicrophonePermission()
        guard microphoneGranted else {
            state = .unavailable("Allow Microphone access in iPhone Settings to use Pilot Flow.")
            return
        }
        guard let recognizer, recognizer.isAvailable else {
            state = .unavailable("Speech recognition is not available on this iPhone right now.")
            return
        }

        do {
            try configureAudioSession()
            let request = SFSpeechAudioBufferRecognitionRequest()
            request.shouldReportPartialResults = true
            request.requiresOnDeviceRecognition = false
            self.request = request

            let input = audioEngine.inputNode
            input.removeTap(onBus: 0)
            input.installTap(onBus: 0, bufferSize: 1024, format: input.outputFormat(forBus: 0)) { [weak self] buffer, _ in
                self?.request?.append(buffer)
            }
            audioEngine.prepare()
            try audioEngine.start()
            state = .listening
            task = recognizer.recognitionTask(with: request) { [weak self] result, error in
                guard let self else { return }
                if let result {
                    self.transcript = result.bestTranscription.formattedString
                }
                if error != nil || result?.isFinal == true {
                    self.stop()
                }
            }
        } catch {
            stop()
            state = .unavailable("Pilot could not start the microphone. \(error.localizedDescription)")
        }
    }

    func stop() {
        if audioEngine.isRunning { audioEngine.stop() }
        audioEngine.inputNode.removeTap(onBus: 0)
        request?.endAudio()
        task?.cancel()
        request = nil
        task = nil
        if case .listening = state { state = .idle }
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
    }

    func updateTranscript(_ value: String) {
        transcript = value
    }

    func reset() {
        stop()
        transcript = ""
        state = .idle
    }

    private func configureAudioSession() throws {
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.record, mode: .measurement, options: .duckOthers)
        try session.setActive(true, options: .notifyOthersOnDeactivation)
    }

    private func requestSpeechPermission() async -> Bool {
        switch SFSpeechRecognizer.authorizationStatus() {
        case .authorized: return true
        case .denied, .restricted: return false
        case .notDetermined:
            return await withCheckedContinuation { continuation in
                SFSpeechRecognizer.requestAuthorization { status in
                    continuation.resume(returning: status == .authorized)
                }
            }
        @unknown default: return false
        }
    }

    private func requestMicrophonePermission() async -> Bool {
        let session = AVAudioSession.sharedInstance()
        if session.recordPermission == .granted { return true }
        return await withCheckedContinuation { continuation in
            session.requestRecordPermission { granted in continuation.resume(returning: granted) }
        }
    }
}

/// A private, read-only iPhone calendar action for central Pilot. Calendar
/// titles never leave this phone; only the requested availability is shown.
enum PilotCalendarAssistant {
    static func reply(for text: String) async -> String? {
        let normalized = text.lowercased()
        // The phone calendar is an optional personal source. Business requests
        // must go through the Vault-connected calendar authority instead.
        let explicitlyPersonal = normalized.contains("iphone calendar") || normalized.contains("phone calendar") || normalized.contains("personal calendar")
        guard explicitlyPersonal && (normalized.contains("calendar") || normalized.contains("diary") || normalized.contains("appointment")) else { return nil }

        let store = EKEventStore()
        do {
            let authorised: Bool
            if #available(iOS 17.0, *) {
                authorised = try await store.requestFullAccessToEvents()
            } else {
                authorised = await withCheckedContinuation { continuation in
                    store.requestAccess(to: .event) { granted, _ in continuation.resume(returning: granted) }
                }
            }
            guard authorised else {
                return "I need permission to read this iPhone’s calendar before I can check availability. Nothing has been changed."
            }

            let calendar = Calendar.current
            var day = calendar.startOfDay(for: Date())
            if normalized.contains("tomorrow") { day = calendar.date(byAdding: .day, value: 1, to: day) ?? day }
            let hour = requestedHour(in: normalized)
            let start: Date
            let end: Date
            if let hour {
                start = calendar.date(bySettingHour: hour, minute: 0, second: 0, of: day) ?? day
                end = calendar.date(byAdding: .hour, value: 1, to: start) ?? start
            } else {
                start = day
                end = calendar.date(byAdding: .day, value: 1, to: day) ?? day
            }
            let events = store.events(matching: store.predicateForEvents(withStart: start, end: end, calendars: nil))
                .sorted { $0.startDate < $1.startDate }
            let formatter = DateFormatter()
            formatter.locale = Locale.current
            formatter.dateStyle = .none
            formatter.timeStyle = .short
            let period = hour.map { "at \($0 > 12 ? $0 - 12 : $0)\($0 >= 12 ? "pm" : "am")" } ?? "for the day"
            if events.isEmpty {
                return "I checked your private calendar \(period). You have no recorded appointments in that period. Nothing has been changed."
            }
            let detail = events.prefix(4).map { "\(formatter.string(from: $0.startDate))–\(formatter.string(from: $0.endDate)): \($0.title ?? "Untitled event")" }.joined(separator: "; ")
            return "I checked your private calendar \(period). You have \(events.count) appointment\(events.count == 1 ? "" : "s"): \(detail). Nothing has been changed."
        } catch {
            return "I could not read this iPhone’s calendar. \(error.localizedDescription) Nothing has been changed."
        }
    }

    private static func requestedHour(in text: String) -> Int? {
        let pattern = #"\b([0-9]{1,2})(?::[0-9]{2})?\s?(am|pm)\b"#
        guard let regex = try? NSRegularExpression(pattern: pattern),
              let match = regex.firstMatch(in: text, range: NSRange(text.startIndex..., in: text)),
              let hourRange = Range(match.range(at: 1), in: text),
              let periodRange = Range(match.range(at: 2), in: text),
              var hour = Int(text[hourRange]) else { return nil }
        let period = text[periodRange]
        if period == "pm", hour < 12 { hour += 12 }
        if period == "am", hour == 12 { hour = 0 }
        return hour
    }
}

/// The connected founder surface. It is intentionally useful before the Node
/// has delivered live activity, and never invents approvals or receipts.
struct PilotPulseView: View {
    let connection: PilotConnection
    let replaceConnection: () -> Void

    @State private var space: PilotSpace = .pilot
    @State private var selectedTool: PilotTool?
    @State private var selectedConversation: PilotConversation?
    @State private var customTools: [PilotTool] = []
    @State private var showingDepartmentSetup = false

    private let columns = [GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())]

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    if space == .pilot {
                        PilotCentralChatView(connection: connection, openBusiness: { space = .executive })
                    } else {
                        header
                    if space == .work {
                        PilotWorkScheduleView(connection: connection)
                    } else if space.isBusiness {
                        businessChatList
                    } else if space == .personal {
                        PilotPersonalDashboardView(connection: connection) {
                            space = .executive
                        }
                    } else {
                        contextBanner
                        LazyVGrid(columns: columns, spacing: 12) {
                            ForEach(space.tools) { tool in
                                toolCard(tool)
                            }
                        }
                    }
                    }
                }
                .padding(.horizontal, 20)
                .padding(.vertical, 16)
            }
            if space.isBusiness || space == .pilot { businessTabBar }
        }
        .foregroundStyle(Color(red: 0.06, green: 0.08, blue: 0.13))
        .background(Color(red: 0.965, green: 0.965, blue: 0.985))
        .toolbarColorScheme(.light, for: .navigationBar)
        .navigationTitle("")
        .navigationBarBackButtonHidden()
        .sheet(item: $selectedTool) { tool in
            PilotToolDetailView(tool: tool, space: space) { }
        }
        .fullScreenCover(item: $selectedConversation) { conversation in
            PilotWorkspaceConversationView(connection: connection, conversation: conversation) { deletedID in
                customTools.removeAll { $0.customDepartmentID == deletedID }
            }
        }
        .sheet(isPresented: $showingDepartmentSetup) {
            CustomDepartmentSetupView(connection: connection) { tool in
                customTools.append(tool)
            }
        }
        .task(id: space) { await loadCustomDepartments() }
    }

    private var header: some View {
        HStack(alignment: .center) {
            Text(space == .work ? "Work & Schedule" : (space.isBusiness ? "Chats" : space.rawValue))
                .font(.system(size: 42, weight: .bold, design: .rounded))
            Spacer()
            profileMenu
        }
    }

    private var profileMenu: some View {
        Menu {
            Section("Space") {
                Button("Pilot") { space = .pilot }
                Button("Business") { space = .executive }
                Button("Personal") { space = .personal }
                Button("Workspace") { space = .workspace }
            }
            Divider()
            Button("Pair a different Node", action: replaceConnection)
        } label: {
            Image(systemName: "person.crop.circle.fill")
                .font(.system(size: 39))
                .foregroundStyle(Color(red: 0.1, green: 0.36, blue: 0.72))
        }
    }

    private var contextBanner: some View {
        HStack(spacing: 10) {
            Image(systemName: space == .personal ? "person.fill" : "person.2.fill")
                .foregroundStyle(Color.blue)
            Text(space == .personal ? "Personal space" : "Workspace space")
                .font(.subheadline.weight(.semibold))
            Spacer()
            Button("Back to Business") { space = .executive }
                .font(.caption.weight(.semibold))
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 11)
        .background(.white, in: Capsule())
        .overlay(Capsule().stroke(Color.black.opacity(0.07)))
    }

    private func toolCard(_ tool: PilotTool) -> some View {
        Button {
            if let conversation = tool.conversation { selectedConversation = conversation }
            else { selectedTool = tool }
        } label: {
        VStack(alignment: .leading, spacing: 12) {
            Image(systemName: tool.icon)
                .font(.title3.weight(.semibold))
                .foregroundStyle(tool.tint)
            Text(tool.title)
                .font(.caption.weight(.semibold))
                .lineLimit(2)
            Spacer(minLength: 0)
        }
        .frame(maxWidth: .infinity, minHeight: 92, alignment: .topLeading)
        .padding(12)
        .background(.white, in: RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color.black.opacity(0.06)))
        }
        .buttonStyle(.plain)
        .accessibilityHint("Open \(tool.title) in \(space.rawValue)")
    }

    private var businessChatList: some View {
        VStack(alignment: .leading, spacing: 10) {
            VStack(spacing: 0) {
                ForEach(visibleTools) { tool in
                    Button {
                        if let conversation = tool.conversation { selectedConversation = conversation }
                        else { selectedTool = tool }
                    } label: {
                        HStack(spacing: 13) {
                            Image(systemName: tool.icon)
                                .font(.title3.weight(.semibold))
                                .foregroundStyle(.white)
                                .frame(width: 46, height: 46)
                                .background(Color(red: 0.07, green: 0.09, blue: 0.15), in: Circle())
                            VStack(alignment: .leading, spacing: 4) {
                                Text(tool.title).font(.subheadline.weight(.bold)).foregroundStyle(.primary)
                                Text(chatPreview(for: tool))
                                    .font(.caption).foregroundStyle(.secondary)
                                    .lineLimit(1)
                            }
                            Spacer()
                            Image(systemName: "chevron.right")
                                .font(.caption.weight(.bold)).foregroundStyle(.tertiary)
                        }
                        .padding(.vertical, 12)
                    }
                    .buttonStyle(.plain)
                    if tool.id != visibleTools.last?.id { Divider().padding(.leading, 59) }
                }
                if space == .departments {
                    Button { showingDepartmentSetup = true } label: {
                        HStack(spacing: 13) {
                            Image(systemName: "plus")
                                .font(.title3.weight(.bold))
                                .foregroundStyle(.white)
                                .frame(width: 46, height: 46)
                                .background(Color(red: 0.07, green: 0.09, blue: 0.15), in: Circle())
                            VStack(alignment: .leading, spacing: 3) {
                                Text("New department").font(.subheadline.weight(.bold)).foregroundStyle(.primary)
                                Text("Create a custom Pilot with a mandate").font(.caption).foregroundStyle(.secondary)
                            }
                            Spacer()
                        }
                        .padding(.vertical, 12)
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private var visibleTools: [PilotTool] {
        space == .departments ? space.tools + customTools : space.tools
    }

    private func loadCustomDepartments() async {
        guard space == .departments else { return }
        do {
            let vault = PilotPossessionVault()
            let client = try PilotNodeClient(connection: connection)
            let spaces = try await client.workspaceSpaces(connection: connection, vault: vault)
            guard let first = (spaces["spaces"] as? [[String: Any]])?.first,
                  let membership = first["membership"] as? [String: Any],
                  let membershipID = membership["membership_id"] as? String else { return }
            let surface = try await client.workspaceSurface(membershipID: membershipID, surface: "departments", connection: connection, vault: vault)
            let data = surface["data"] as? [String: Any]
            let departmentRows = data?["departments"] as? [[String: Any]] ?? []
            customTools = departmentRows.compactMap { item in
                guard (item["core"] as? Bool) == false,
                      let id = item["id"] as? String,
                      let name = item["name"] as? String else { return nil }
                return PilotTool(name, "sparkles", Color(red: 0.07, green: 0.09, blue: 0.15), customDepartmentID: id)
            }
        } catch {
            // A read-only or older pairing simply does not expose custom departments.
        }
    }

    private func chatPreview(for tool: PilotTool) -> String {
        switch tool.title {
        case "Executive meeting": return "Daily round-up with your function Pilots"
        case "Executive channels": return "COO conversations with each Department Pilot"
        case "Board mandate": return "Current strategic objectives and constraints"
        case "Board meetings": return "Next formal Board meeting and evidence pack"
        case "Pilot": return "Coordinate work across the business with guarded Mission Mode"
        case "Sales": return "Pipeline, leads and the Sales Pilot"
        case "Marketing": return "Campaigns, content and the Marketing Pilot"
        case "Finance": return "Cash flow, invoices and exceptions"
        case "Support": return "Cases requiring direction"
        case "Operations": return "Work queue, risks and delivery"
        case "People": return "Authorised people and team records"
        default: return "Open this private business conversation"
        }
    }

    private var businessTabBar: some View {
        HStack(spacing: 4) {
            businessTab("Pilot", icon: "sparkles", target: .pilot)
            businessTab("Executive", icon: "person.3.fill", target: .executive)
            businessTab("Work", icon: "calendar.badge.clock", target: .work)
            businessTab("Departments", icon: "bubble.left.and.bubble.right.fill", target: .departments)
            Menu {
                Button("Business") { space = .executive }
                Button("Board") { space = .board }
                Button("Personal") { space = .personal }
                Button("Workspace") { space = .workspace }
                Divider()
                Button("Pair a different Node", action: replaceConnection)
            } label: {
                VStack(spacing: 3) {
                    Image(systemName: "person.crop.circle.fill").font(.title3)
                    Text("You").font(.caption2.weight(.semibold))
                }
                .frame(maxWidth: .infinity, minHeight: 50)
                .foregroundStyle(Color(red: 0.06, green: 0.08, blue: 0.13))
            }
        }
        .padding(.horizontal, 12)
        .padding(.top, 8)
        .padding(.bottom, 4)
        .background(.ultraThinMaterial)
        .overlay(alignment: .top) { Divider() }
    }

    private func businessTab(_ label: String, icon: String, target: PilotSpace) -> some View {
        Button { space = target } label: {
            VStack(spacing: 3) {
                Image(systemName: icon).font(.title3)
                Text(label).font(.caption2.weight(.semibold))
            }
            .frame(maxWidth: .infinity, minHeight: 50)
            .foregroundStyle(space == target ? Color.blue : Color(red: 0.06, green: 0.08, blue: 0.13))
        }
        .buttonStyle(.plain)
    }

}

private struct PilotCentralChatView: View {
    let connection: PilotConnection
    let openBusiness: () -> Void
    private let vault = PilotPossessionVault()

    @State private var membershipID = ""
    @State private var draft = ""
    @State private var messages: [PilotChatMessage] = []
    @State private var awaitingReply = false
    @State private var showSlowHint = false
    @State private var status = "Connecting to your private Pilot…"
    @StateObject private var dictation = PilotLiveDictation()
    @State private var showingMeetingCapture = false
    @State private var preparingMeetingDraft = false
    @State private var meetingDraft: PilotMeetingMinutesDraft?

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text("Pilot")
                    .font(.system(size: 34, weight: .bold, design: .rounded))
                Spacer()
                Button(action: openBusiness) {
                    Label("Business", systemImage: "building.2")
                        .font(.subheadline.weight(.semibold))
                }
                .buttonStyle(.bordered)
                Button { showingMeetingCapture = true } label: {
                    Image(systemName: "record.circle")
                }
                .buttonStyle(.bordered)
                .accessibilityLabel("Record meeting minutes")
            }
            .padding(.top, 8)

            if !status.isEmpty {
                Text(status)
                    .font(.footnote)
                    .foregroundStyle(status.hasPrefix("Pilot could") ? .red : .secondary)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.top, 8)
            }

            if messages.isEmpty {
                Spacer(minLength: 80)
                Image(systemName: "sparkles")
                    .font(.system(size: 40, weight: .bold))
                    .foregroundStyle(.indigo)
                    .frame(width: 82, height: 82)
                    .background(.white, in: Circle())
                Text("How can I help your business today?")
                    .font(.title2.weight(.bold))
                    .multilineTextAlignment(.center)
                    .padding(.top, 18)
                Text("Pilot can explain, plan and prepare work. Department Pilots and approvals remain in control of business actions.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.top, 6)
                VStack(spacing: 10) {
                    suggestion("Give me today’s business briefing")
                    suggestion("What needs attention today?")
                    suggestion("Help me prepare a plan")
                }
                .padding(.top, 24)
                Button(action: toggleDictation) {
                    Label(dictation.isListening ? "Listening — tap to stop" : "Turn on microphone", systemImage: dictation.isListening ? "stop.fill" : "mic.fill")
                        .font(.subheadline.weight(.bold))
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(dictation.isListening ? .red : .indigo)
                .padding(.top, 12)
                .accessibilityLabel(dictation.isListening ? "Stop Pilot microphone" : "Turn on Pilot microphone")
                Spacer()
            } else {
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 12) {
                        ForEach(messages) { message in
                            centralBubble(message)
                        }
                        if awaitingReply { thinkingBubble }
                    }
                    .padding(.vertical, 20)
                }
            }

            composer
        }
        .task { await connect() }
        .onChange(of: dictation.state) { previous, next in
            guard previous == .listening, next == .idle else { return }
            send()
        }
    }

    private func suggestion(_ text: String) -> some View {
        Button { draft = text; send() } label: {
            HStack { Text(text).font(.subheadline.weight(.medium)); Spacer(); Image(systemName: "arrow.up.right") }
                .padding(14)
                .background(.white, in: RoundedRectangle(cornerRadius: 16))
                .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color.black.opacity(0.07)))
        }
        .buttonStyle(.plain)
        .disabled(membershipID.isEmpty || awaitingReply)
    }

    private var composer: some View {
        HStack(spacing: 8) {
            TextField("Ask Pilot anything", text: $draft, axis: .vertical)
                .lineLimit(1...4)
                .padding(.horizontal, 15).padding(.vertical, 11)
                .background(.white, in: Capsule())
            if dictation.isListening || draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                Button(action: toggleDictation) {
                    Image(systemName: dictation.isListening ? "stop.fill" : "mic.fill")
                        .font(.headline.weight(.bold)).frame(width: 46, height: 46)
                        .foregroundStyle(.white).background(dictation.isListening ? Color.red : .indigo, in: Circle())
                }
                .accessibilityLabel(dictation.isListening ? "Stop dictation and send to Pilot" : "Start dictation")
            } else {
                Button(action: send) {
                    Image(systemName: "arrow.up")
                        .font(.headline.weight(.bold)).frame(width: 46, height: 46)
                        .foregroundStyle(.white).background(.indigo, in: Circle())
                }
                .disabled(membershipID.isEmpty || awaitingReply)
            }
        }
        .padding(.vertical, 14)
        .onChange(of: dictation.transcript) { _, value in
            if dictation.isListening || !value.isEmpty { draft = value }
        }
        .sheet(isPresented: $showingMeetingCapture) {
            PilotMeetingCaptureView(title: "Pilot meeting") { transcript in
                prepareMeetingMinutesDraft(from: transcript, title: "Pilot meeting")
            }
        }
        .sheet(item: $meetingDraft) { draft in
            PilotMeetingMinutesDraftView(draft: draft)
        }
    }

    private func toggleDictation() {
        if dictation.isListening { dictation.stop(); return }
        Task { await dictation.start(initialText: draft) }
    }

    /// Meeting capture is deliberately separate from ordinary Pilot chat. It
    /// never copies the chat composer, conversation history, or dictated turn.
    private func prepareMeetingMinutesDraft(from transcript: String, title: String) {
        let cleaned = transcript.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !cleaned.isEmpty, !preparingMeetingDraft else { return }
        meetingDraft = PilotMeetingMinutesDraft(title: title, transcript: cleaned, minutes: "Transcript captured. Pilot will add evidence-backed decisions and actions when the private workspace is available.\n\n\(cleaned)")
        guard !membershipID.isEmpty else {
            status = "Your meeting transcript is ready to review. Reconnect to Pilot to generate the assisted draft."
            return
        }
        preparingMeetingDraft = true
        let request = """
        Prepare an editable meeting-minutes draft for \(title) from the transcript below. List only decisions and actions that are explicitly evidenced. For every action, include an owner and due date only when stated; otherwise mark both ‘Unassigned’ and ‘Not stated’. Do not send, publish, assign, or execute anything. End by asking the user to review the draft, assign owners, and choose recipients before delivery.

        Transcript:
        \(cleaned)
        """
        Task {
            defer { preparingMeetingDraft = false }
            do {
                let client = try PilotNodeClient(connection: connection)
                let result = try await client.workspaceConversation(membershipID: membershipID, departmentID: "pilot", text: request, connection: connection, vault: vault)
                let turn = (result["conversation"] as? [String: Any])?["turn"] as? [String: Any]
                meetingDraft = PilotMeetingMinutesDraft(title: title, transcript: cleaned, minutes: turn?["content"] as? String ?? cleaned)
            } catch {
                meetingDraft = PilotMeetingMinutesDraft(title: title, transcript: cleaned, minutes: "Pilot could not prepare the minutes draft yet. Your transcript is preserved below for review.\n\n\(cleaned)")
            }
        }
    }

    private func centralBubble(_ message: PilotChatMessage) -> some View {
        HStack {
            if message.isMine { Spacer(minLength: 40) }
            VStack(alignment: .leading, spacing: 4) {
                Text(message.sender).font(.caption.weight(.bold)).foregroundStyle(message.isMine ? .white.opacity(0.75) : .indigo)
                Text(message.body).font(.body)
                if let details = message.details {
                    Divider().opacity(0.25)
                    Text(details).font(.caption2.weight(.semibold)).foregroundStyle(message.isMine ? .white.opacity(0.70) : .indigo.opacity(0.78))
                }
            }
            .padding(13)
            .foregroundStyle(message.isMine ? .white : Color(red: 0.06, green: 0.08, blue: 0.13))
            .background(message.isMine ? Color.indigo : .white, in: RoundedRectangle(cornerRadius: 18))
            if !message.isMine { Spacer(minLength: 40) }
        }
    }

    private var thinkingBubble: some View {
        HStack {
            HStack(spacing: 9) {
                ProgressView().tint(.indigo)
                VStack(alignment: .leading, spacing: 3) {
                    Text("Pilot is working on this…").font(.subheadline.weight(.semibold))
                    if showSlowHint { Text("A Tessaris Hub or additional home compute can make longer replies faster.").font(.caption).foregroundStyle(.secondary) }
                }
            }
            .padding(13).background(.white, in: RoundedRectangle(cornerRadius: 18))
            Spacer()
        }
    }

    private func connect() async {
        do {
            let client = try PilotNodeClient(connection: connection)
            let spaces = try await client.workspaceSpaces(connection: connection, vault: vault)
            guard let first = (spaces["spaces"] as? [[String: Any]])?.first,
                  let membership = first["membership"] as? [String: Any],
                  let id = membership["membership_id"] as? String else { return }
            membershipID = id
            status = "Pilot is ready."
        } catch { status = "Pilot could not connect yet: \(error.localizedDescription)" }
    }

    private func send() {
        let text = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !awaitingReply else { return }
        guard !membershipID.isEmpty else {
            status = "Pilot is reconnecting to your private workspace. Your message is still in the composer."
            Task { await connect() }
            return
        }
        draft = ""; awaitingReply = true; showSlowHint = false
        messages.append(PilotChatMessage(sender: "You", body: text, isMine: true))
        Task {
            try? await Task.sleep(nanoseconds: 15_000_000_000)
            if awaitingReply { showSlowHint = true }
        }
        Task {
            defer { awaitingReply = false }
            if let calendarReply = await PilotCalendarAssistant.reply(for: text) {
                messages.append(PilotChatMessage(sender: "Pilot", body: calendarReply, isMine: false))
                return
            }
            do {
                let client = try PilotNodeClient(connection: connection)
                let result = try await client.workspaceConversation(membershipID: membershipID, departmentID: "pilot", text: text, connection: connection, vault: vault)
                let turn = (result["conversation"] as? [String: Any])?["turn"] as? [String: Any]
                messages.append(PilotChatMessage(sender: "Pilot", body: turn?["content"] as? String ?? "Pilot returned no readable response.", isMine: false))
            } catch {
                messages.append(PilotChatMessage(sender: "Tessaris", body: "Pilot could not answer yet. \(error.localizedDescription)", isMine: false))
            }
        }
    }
}

private enum PilotSpace: String, CaseIterable, Identifiable {
    case pilot = "Pilot"
    case executive = "Executive"
    case work = "Work"
    case departments = "Departments"
    case board = "Board"
    case personal = "Personal"
    case workspace = "Workspace"

    var id: String { rawValue }
    static let businessCases: [PilotSpace] = [.executive, .work, .departments, .board]
    var isBusiness: Bool { Self.businessCases.contains(self) }
    var contextLabel: String { isBusiness ? "Business" : rawValue }

    var heading: String {
        switch self {
        case .pilot: "Your central Pilot"
        case .executive: "Today’s business, in view"
        case .work: "Jobs, visits and appointments"
        case .departments: "Your department team"
        case .board: "Strategy and Board mandate"
        case .personal: "Your private life, organised"
        case .workspace: "Your shared workspace"
        }
    }

    var subheading: String {
        switch self {
        case .pilot: "Your guarded business helping hand."
        case .executive: "The CEO or COO channel brings together priorities, exceptions and decisions for today."
        case .work: "Schedule work, assign it and keep the live record up to date from anywhere."
        case .departments: "Open a department’s mandate, working conversation and receipts."
        case .board: "Formal strategic meetings, signed decisions and the objectives handed to the executive team."
        case .personal: "Private tasks, calendar, people, files and personal assistant conversations."
        case .workspace: "Shared work, conversations and approved activity across your authorised spaces."
        }
    }

    var tools: [PilotTool] {
        switch self {
        case .pilot:
            []
        case .executive:
            [PilotTool("Executive meeting", "person.3.fill", .blue), PilotTool("Executive channels", "bubble.left.and.bubble.right.fill", .blue), PilotTool("Morning brief", "sun.max.fill", .orange), PilotTool("Approvals", "checkmark.seal.fill", .green), PilotTool("Work queue", "checklist", .purple), PilotTool("Escalations", "exclamationmark.triangle.fill", .red), PilotTool("Receipts", "doc.text.fill", .teal)]
        case .work:
            []
        case .departments:
            [PilotTool("Pilot", "sparkles", .indigo), PilotTool("Sales", "target", .orange), PilotTool("Marketing", "megaphone.fill", .pink), PilotTool("Finance", "sterlingsign.circle.fill", .green), PilotTool("Support", "heart.text.square.fill", .teal), PilotTool("Operations", "gearshape.2.fill", .purple), PilotTool("People", "person.2.fill", .blue)]
        case .board:
            [PilotTool("Board mandate", "checkmark.seal.fill", .blue), PilotTool("Board meetings", "person.3.sequence.fill", .purple), PilotTool("Decisions", "list.clipboard.fill", .orange), PilotTool("Strategic risks", "exclamationmark.shield.fill", .red), PilotTool("Objectives", "scope", .green), PilotTool("Escalate to Board", "arrow.up.circle.fill", .pink)]
        case .personal:
            [PilotTool("Inbox", "tray.fill", .blue), PilotTool("Calendar", "calendar", .orange), PilotTool("Contacts", "person.2.fill", .purple), PilotTool("Files", "folder.fill", .teal), PilotTool("Memory", "brain.head.profile", .indigo), PilotTool("Devices", "tv.fill", .pink)]
        case .workspace:
            [PilotTool("Shared inbox", "bubble.left.and.bubble.right.fill", .blue), PilotTool("Tasks", "checklist", .green), PilotTool("Files", "folder.fill", .orange), PilotTool("Activity", "chart.line.uptrend.xyaxis", .purple), PilotTool("Members", "person.3.fill", .teal), PilotTool("Approvals", "checkmark.seal.fill", .pink)]
        }
    }

}

private struct PilotTool: Identifiable {
    let title: String
    let icon: String
    let tint: Color
    let customDepartmentID: String?
    var conversation: PilotConversation? {
        let department: String?
        if let customDepartmentID {
            department = customDepartmentID
        } else {
            department = switch title {
            case "Executive channels": "executive_channels"
            case "Executive meeting", "Morning brief", "Approvals", "Work queue", "Escalations", "Receipts": "executive"
            case "Board meetings": "boardroom"
            case "Board mandate": "board_mandate"
            case "Decisions": "decisions"
            case "Strategic risks": "strategic_risks"
            case "Objectives": "objectives"
            case "Escalate to Board": "board_escalations"
            case "Pilot": "pilot"
            case "Sales": "sales"
            case "Marketing": "marketing"
            case "Finance": "finance"
            case "Support": "support"
            case "Operations": "operations"
            case "People": "people"
            default: nil
            }
        }
        guard let department else { return nil }
        return PilotConversation(title: title, departmentID: department, isCustom: customDepartmentID != nil)
    }
    var id: String { title }

    init(_ title: String, _ icon: String, _ tint: Color, customDepartmentID: String? = nil) {
        self.title = title
        self.icon = icon
        self.tint = tint
        self.customDepartmentID = customDepartmentID
    }
}

private struct PilotConversation: Identifiable {
    let title: String
    let departmentID: String
    let isCustom: Bool
    var id: String { "\(departmentID)-\(title)" }
}

private struct PilotSupportCase: Identifiable {
    let id: String
    let number: String
    let subject: String
    let customer: String
    let category: String
    let priority: String
    let status: String
    let updatedAt: String
    let riskFlags: [String]
    let needsHuman: Bool
    let humanRequest: String
    let timeline: [PilotSupportEvent]

    var statusLabel: String { status.replacingOccurrences(of: "_", with: " ").capitalized }
    var updatedLabel: String { updatedAt.isEmpty ? "Updated recently" : "Updated " + String(updatedAt.prefix(10)) }
}

private struct PilotSupportEvent: Identifiable {
    let id = UUID()
    let direction: String
    let channel: String
    let recordedAt: String
    let content: String
}

private struct PilotPersonRecord: Identifiable {
    let id: String
    let name: String
    let title: String
    let status: String
    let employmentType: String
    let roleNames: [String]
    let departmentNames: [String]
    let authorityScope: String
    let accessAreas: [String]
    let directReports: Int
    let projectCount: Int
    let assignedAssetCount: Int
    let hasManager: Bool
}

private struct PilotSupportPulse {
    let summary: [String: Int]
    let cases: [PilotSupportCase]

    init(surface: [String: Any]) {
        let data = surface["data"] as? [String: Any] ?? [:]
        let rawSummary = data["summary"] as? [String: Any] ?? [:]
        self.summary = rawSummary.reduce(into: [:]) { result, item in
            if let value = item.value as? Int { result[item.key] = value }
        }
        self.cases = (data["support_cases"] as? [[String: Any]] ?? []).compactMap { row in
            guard let id = row["id"] as? String, !id.isEmpty else { return nil }
            let timeline = (row["timeline"] as? [[String: Any]] ?? []).map { event in
                PilotSupportEvent(direction: event["direction"] as? String ?? "update", channel: event["channel"] as? String ?? "", recordedAt: event["recorded_at"] as? String ?? "", content: event["content"] as? String ?? "")
            }
            return PilotSupportCase(id: id, number: row["number"] as? String ?? "", subject: row["subject"] as? String ?? "Customer support request", customer: row["customer"] as? String ?? "Customer", category: row["category"] as? String ?? "unknown", priority: row["priority"] as? String ?? "normal", status: row["status"] as? String ?? "open", updatedAt: row["updated_at"] as? String ?? "", riskFlags: row["risk_flags"] as? [String] ?? [], needsHuman: row["needs_human"] as? Bool ?? false, humanRequest: row["human_request"] as? String ?? "", timeline: timeline)
        }
    }
}

private struct PilotPeoplePulse {
    let allowed: Bool
    let people: [PilotPersonRecord]

    init(surface: [String: Any]) {
        let data = surface["data"] as? [String: Any] ?? [:]
        let access = data["people_access"] as? [String: Any] ?? [:]
        self.allowed = access["allowed"] as? Bool ?? false
        self.people = (data["people"] as? [[String: Any]] ?? []).compactMap { row in
            guard let id = row["id"] as? String, !id.isEmpty else { return nil }
            return PilotPersonRecord(id: id, name: row["name"] as? String ?? "Team member", title: row["title"] as? String ?? "", status: row["status"] as? String ?? "active", employmentType: row["employment_type"] as? String ?? "employee", roleNames: row["role_names"] as? [String] ?? [], departmentNames: row["department_names"] as? [String] ?? [], authorityScope: row["authority_scope"] as? String ?? "Assigned work", accessAreas: row["access_areas"] as? [String] ?? [], directReports: row["direct_reports"] as? Int ?? 0, projectCount: row["project_count"] as? Int ?? 0, assignedAssetCount: row["assigned_asset_count"] as? Int ?? 0, hasManager: row["has_manager"] as? Bool ?? false)
        }
    }
}

private struct PilotSalesPulse {
    let date: String
    let message: String
    let metrics: [String: Int]
    let conversion: Int?
    let availability: [String: String]
    let boardActions: [PilotBoardAction]
    let queue: [(title: String, stage: String, nextAction: String)]
    let governance: String

    init(surface: [String: Any]) {
        let data = surface["data"] as? [String: Any] ?? [:]
        let briefing = data["sales_briefing"] as? [String: Any] ?? [:]
        date = briefing["date"] as? String ?? "today"
        message = briefing["message"] as? String ?? "The Sales ledger is ready to update throughout the day."
        let rawMetrics = briefing["metrics"] as? [String: Any] ?? [:]
        metrics = rawMetrics.reduce(into: [:]) { result, item in
            if let value = item.value as? Int { result[item.key] = value }
        }
        conversion = rawMetrics["conversion_closed_percent"] as? Int
        availability = briefing["availability"] as? [String: String] ?? [:]
        boardActions = (briefing["board_actions"] as? [[String: Any]] ?? []).compactMap { item in
            let id = item["id"] as? String ?? ""
            let title = item["title"] as? String ?? ""
            guard !id.isEmpty, !title.isEmpty else { return nil }
            return PilotBoardAction(id: id, title: title, department: item["department"] as? String ?? "Sales", status: item["status"] as? String ?? "delegated", dueAt: item["due_at"] as? String ?? "")
        }
        queue = (briefing["today_queue"] as? [[String: Any]] ?? []).map {
            (title: $0["title"] as? String ?? "Sales opportunity", stage: $0["stage"] as? String ?? "open", nextAction: $0["next_action"] as? String ?? "Review opportunity")
        }
        governance = briefing["governance"] as? String ?? "Changes to Board objectives are reviewed through COO or Executive."
    }
}

private struct PilotFinancePulse {
    let currency: String
    let metrics: [String: Double]
    let actions: [(title: String, recommendation: String, severity: String)]
    let availability: [String]
    let plan: String
    let receiptPolicy: String
    let verification: String

    var currencySymbol: String {
        switch currency.uppercased() {
        case "EUR", "EURO", "EUROS": return "€"
        case "GBP", "POUND", "POUNDS": return "£"
        case "USD", "DOLLAR", "DOLLARS": return "$"
        default: return currency
        }
    }

    init(surface: [String: Any]) {
        let data = surface["data"] as? [String: Any] ?? [:]
        let briefing = data["finance_briefing"] as? [String: Any] ?? [:]
        currency = briefing["currency"] as? String ?? "EUR"
        let rawMetrics = briefing["metrics"] as? [String: Any] ?? [:]
        metrics = rawMetrics.reduce(into: [:]) { result, item in
            if let number = item.value as? Double { result[item.key] = number }
            else if let integer = item.value as? Int { result[item.key] = Double(integer) }
        }
        actions = (briefing["actions"] as? [[String: Any]] ?? []).map {
            (title: $0["title"] as? String ?? "Finance review", recommendation: $0["recommendation"] as? String ?? "Review with Finance Pilot.", severity: $0["severity"] as? String ?? "normal")
        }
        availability = briefing["availability"] as? [String] ?? []
        plan = briefing["today_plan"] as? String ?? "Finance actions require exact approval."
        receiptPolicy = briefing["receipt_policy"] as? String ?? "Receipt intake is governed by the expense policy."
        verification = briefing["verification_state"] as? String ?? "unavailable"
    }
}

/// This is the native surface over the established signed Workspace Gateway.
/// The phone never selects a workspace by guessing: the Node returns only
/// memberships belonging to the paired identity.
private struct PilotWorkspaceConversationView: View {
    let connection: PilotConnection
    let conversation: PilotConversation
    let onDeleted: (String) -> Void
    private let vault = PilotPossessionVault()

    @Environment(\.dismiss) private var dismiss
    @State private var membershipID = ""
    @State private var status = "Opening your private workspace…"
    @State private var summary = ""
    @State private var boardroomPulse: PilotBoardroomPulse?
    @State private var supportPulse: PilotSupportPulse?
    @State private var peoplePulse: PilotPeoplePulse?
    @State private var salesPulse: PilotSalesPulse?
    @State private var financePulse: PilotFinancePulse?
    @State private var selectedSupportCase: PilotSupportCase?
    @State private var selectedPerson: PilotPersonRecord?
    @State private var executiveMembers: [PilotExecutiveMember] = PilotExecutiveMember.defaults
    @State private var executiveChannelMembers: [PilotExecutiveMember] = PilotExecutiveMember.channelDefaults
    @State private var selectedExecutiveChannelID = "sales"
    @State private var executiveScheduleLabel = "Daily · 08:00 · business local time"
    @State private var executiveReasoningLabel = "Vault model · role-separated departments"
    @State private var messages: [PilotChatMessage] = []
    @State private var historyCursor = ""
    @State private var hasOlderMessages = false
    @State private var loadingOlderMessages = false
    @State private var draft = ""
    @State private var loading = false
    @State private var awaitingPilotReply = false
    @State private var showSlowResponseHint = false
    @State private var showingFilePicker = false
    @State private var attachmentName: String?
    @State private var holdingToTalk = false
    @State private var selectedPhoto: PhotosPickerItem?
    @StateObject private var dictation = PilotLiveDictation()
    @State private var showingMeetingCapture = false

    @State private var preparingMeetingDraft = false
    @State private var meetingDraft: PilotMeetingMinutesDraft?
    var body: some View {
        VStack(spacing: 0) {
            chatHeader
            Divider().overlay(Color.white.opacity(0.12))
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 12) {
                    if hasOlderMessages {
                        Button(loadingOlderMessages ? "Loading earlier messages…" : "Load earlier messages") {
                            loadOlderMessages()
                        }
                        .buttonStyle(.bordered)
                        .disabled(loadingOlderMessages)
                        .frame(maxWidth: .infinity)
                    }
                    if conversation.departmentID == "boardroom", let boardroomPulse {
                        boardroomOverview(boardroomPulse)
                    } else if conversation.departmentID == "executive" {
                        executiveOverview
                    } else if conversation.departmentID == "executive_channels" {
                        executiveChannelsOverview
                    } else if conversation.departmentID == "support", let supportPulse {
                        supportOverview(supportPulse)
                    } else if conversation.departmentID == "people", let peoplePulse {
                        peopleOverview(peoplePulse)
                    } else if conversation.departmentID == "sales", let salesPulse {
                        salesOverview(salesPulse)
                    } else if conversation.departmentID == "finance", let financePulse {
                        financeOverview(financePulse)
                    } else if !summary.isEmpty {
                        pilotBubble(summary, label: "\(conversation.title) Pilot")
                    } else {
                        pilotBubble(status, label: "Tessaris")
                    }
                    if conversation.departmentID == "executive_channels" && messages.isEmpty && !loading {
                        pilotBubble(
                            "No recorded messages yet. Messages, morning minutes, decisions and evidence shared here are the same records shown in the desktop Operations Command Centre.",
                            label: "\(selectedExecutiveChannelName) Pilot"
                        )
                    }
                    ForEach(messages) { message in
                        chatBubble(message)
                    }
                    if awaitingPilotReply {
                        pilotThinkingBubble
                    }
                    if let attachmentName {
                        pilotBubble("Attached: \(attachmentName)", label: "You")
                    }
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 18)
            }
            chatComposer
        }
        .background(Color(red: 0.055, green: 0.065, blue: 0.10).ignoresSafeArea())
        .preferredColorScheme(.dark)
        .task { await openWorkspace() }
        .onChange(of: dictation.transcript) { _, value in
            if dictation.isListening || !value.isEmpty { draft = value }
        }
        .onChange(of: dictation.state) { previous, next in
            guard previous == .listening, next == .idle else { return }
            send()
        }
        .sheet(isPresented: $showingMeetingCapture) {
            PilotMeetingCaptureView(title: conversation.title) { transcript in
                prepareMeetingMinutesDraft(from: transcript)
            }
        }
        .sheet(item: $meetingDraft) { draft in
            PilotMeetingMinutesDraftView(draft: draft)
        }
        .fileImporter(isPresented: $showingFilePicker, allowedContentTypes: [.item], allowsMultipleSelection: false) { result in
            if case let .success(urls) = result, let url = urls.first { attachmentName = url.lastPathComponent }
        }
        .sheet(item: $selectedSupportCase) { supportCase in
            PilotSupportCaseDetailView(supportCase: supportCase)
        }
        .sheet(item: $selectedPerson) { person in
            PilotPersonRecordView(person: person)
        }
    }

    private var chatHeader: some View {
        HStack(spacing: 12) {
            Button(action: dismiss.callAsFunction) {
                Image(systemName: "chevron.left")
                    .font(.headline.weight(.bold))
                    .frame(width: 40, height: 40)
                    .background(Color.white.opacity(0.10), in: Circle())
            }
            Image(systemName: conversation.departmentID == "boardroom" ? "building.columns.fill" : conversation.departmentID == "executive" ? "person.3.fill" : conversation.departmentID == "executive_channels" ? "bubble.left.and.bubble.right.fill" : "sparkles")
                .font(.title3.weight(.bold))
                .foregroundStyle(.white)
                .frame(width: 44, height: 44)
                .background(conversationTint, in: Circle())
            VStack(alignment: .leading, spacing: 2) {
                Text(conversation.title).font(.headline.weight(.bold))
                Text(conversation.departmentID == "boardroom" ? "Board meeting and actions" : conversation.departmentID == "executive" ? "Daily executive meeting" : conversation.departmentID == "executive_channels" ? "COO ↔ Department Pilots" : "Private Pilot")
                    .font(.caption).foregroundStyle(.white.opacity(0.62))
            }
            Spacer()
            if conversation.departmentID == "boardroom", let boardroomPulse {
                boardAvatarStack(boardroomPulse.members)
            } else if conversation.departmentID == "executive" {
                executiveAvatarStack(executiveMembers)
            } else if conversation.departmentID == "executive_channels" {
                executiveAvatarStack(executiveChannelMembers)
            }
            Button { showingMeetingCapture = true } label: {
                Image(systemName: "record.circle")
                    .font(.headline)
                    .frame(width: 40, height: 40)
                    .background(Color.white.opacity(0.10), in: Circle())
            }
            .accessibilityLabel("Record meeting minutes")
            if conversation.isCustom {
                Menu {
                    Button("Delete department", role: .destructive, action: deleteDepartment)
                } label: {
                    Image(systemName: "ellipsis")
                        .font(.headline)
                        .frame(width: 40, height: 40)
                        .background(Color.white.opacity(0.10), in: Circle())
                }
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
        .foregroundStyle(.white)
        .background(Color(red: 0.055, green: 0.065, blue: 0.10))
    }

    private var executiveOverview: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Executive meeting")
                .font(.title2.weight(.bold))
                .foregroundStyle(.white)
            Text("Your function Pilots report here for the daily meeting. The CEO or COO holds the floor and brings only priorities, exceptions and decisions to you.")
                .font(.subheadline)
                .foregroundStyle(.white.opacity(0.70))
            VStack(alignment: .leading, spacing: 10) {
                Text("Participants")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(.white.opacity(0.58))
                    .textCase(.uppercase)
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 12) {
                        ForEach(executiveMembers) { member in
                            VStack(spacing: 6) {
                                executiveAvatar(member, size: 48)
                                Text(member.name.replacingOccurrences(of: " Pilot", with: ""))
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white)
                                    .lineLimit(1)
                            }
                            .frame(width: 68)
                        }
                    }
                }
            }
            .padding(14)
            .background(Color.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 18))

        }
        .padding(16)
        .background(Color.white.opacity(0.05), in: RoundedRectangle(cornerRadius: 22))
    }

    private var executiveChannelsOverview: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading, spacing: 3) {
                    Text("Executive channels")
                        .font(.title2.weight(.bold))
                        .foregroundStyle(.white)
                    Text(executiveScheduleLabel)
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.58))
                }
                Spacer()
                Image(systemName: "bubble.left.and.bubble.right.fill")
                    .foregroundStyle(.blue)
            }
            Text("Choose a department to open the persistent COO ↔ Department Pilot conversation.")
                .font(.subheadline)
                .foregroundStyle(.white.opacity(0.70))
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 10) {
                    ForEach(executiveChannelMembers) { member in
                        Button {
                            selectExecutiveChannel(member.id)
                        } label: {
                            VStack(spacing: 6) {
                                executiveAvatar(member, size: 44)
                                    .overlay(Circle().stroke(
                                        selectedExecutiveChannelID == member.id ? Color.blue : Color.clear,
                                        lineWidth: 3
                                    ))
                                Text(member.name.replacingOccurrences(of: " Pilot", with: ""))
                                    .font(.caption2.weight(.bold))
                                    .foregroundStyle(.white)
                                    .lineLimit(1)
                            }
                            .frame(width: 66)
                            .padding(.vertical, 8)
                            .background(
                                selectedExecutiveChannelID == member.id ? Color.blue.opacity(0.18) : Color.clear,
                                in: RoundedRectangle(cornerRadius: 14)
                            )
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel("Open \(member.name) executive channel")
                    }
                }
            }
            HStack(spacing: 6) {
                Circle().fill(Color.green).frame(width: 7, height: 7)
                Text("COO ↔ \(selectedExecutiveChannelName) Pilot")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(.white.opacity(0.78))
                Spacer()
                Text(executiveReasoningLabel)
                    .font(.caption2)
                    .foregroundStyle(.white.opacity(0.52))
                    .lineLimit(1)
            }
        }
        .padding(16)
        .background(Color.white.opacity(0.05), in: RoundedRectangle(cornerRadius: 22))
    }

    private func executiveAvatar(_ member: PilotExecutiveMember, size: CGFloat) -> some View {
        Text(member.initials)
            .font(.caption.weight(.black))
            .foregroundStyle(.white)
            .frame(width: size, height: size)
            .background(Color(red: 0.12, green: 0.14, blue: 0.18), in: Circle())
            .overlay(Circle().stroke(Color.white.opacity(0.22), lineWidth: 1))
    }

    private func executiveAvatarStack(_ members: [PilotExecutiveMember]) -> some View {
        HStack(spacing: -10) {
            ForEach(members.prefix(4)) { member in
                executiveAvatar(member, size: 30)
            }
        }
    }

    private var selectedExecutiveChannelName: String {
        executiveChannelMembers.first(where: { $0.id == selectedExecutiveChannelID })?
            .name.replacingOccurrences(of: " Pilot", with: "") ?? "Sales"
    }

    private func selectExecutiveChannel(_ departmentID: String) {
        guard selectedExecutiveChannelID != departmentID else { return }
        selectedExecutiveChannelID = departmentID
        messages = []
        historyCursor = ""
        hasOlderMessages = false
        status = "Opening the \(selectedExecutiveChannelName) executive channel…"
        loading = true
        Task {
            await loadConversationHistory()
            loading = false
        }
    }

    @ViewBuilder
    private func boardroomOverview(_ pulse: PilotBoardroomPulse) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Boardroom")
                .font(.title2.weight(.bold))
                .foregroundStyle(.white)
            Text("The founding meeting is completed on desktop. Use this private channel to follow Board records, provide a response and keep delegated work in view.")
                .font(.subheadline)
                .foregroundStyle(.white.opacity(0.70))

            VStack(alignment: .leading, spacing: 10) {
                Text("Board members")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(.white.opacity(0.58))
                    .textCase(.uppercase)
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 12) {
                        ForEach(pulse.members) { member in
                            VStack(spacing: 6) {
                                boardAvatar(member, size: 48)
                                Text(member.name)
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(.white)
                                    .lineLimit(1)
                            }
                            .frame(width: 68)
                        }
                    }
                }
            }
            .padding(14)
            .background(Color.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 18))

            VStack(alignment: .leading, spacing: 10) {
                Text("Meeting history")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(.white.opacity(0.58))
                    .textCase(.uppercase)
                if pulse.meetings.isEmpty {
                    Text("No Board meeting records are available for this business yet.")
                        .font(.subheadline)
                        .foregroundStyle(.white.opacity(0.68))
                } else {
                    ForEach(pulse.meetings) { meeting in
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Text(meeting.title).font(.subheadline.weight(.bold)).foregroundStyle(.white)
                                Spacer()
                                Text(meeting.occurredAt).font(.caption).foregroundStyle(.white.opacity(0.55))
                            }
                            Text(meeting.recordLabel)
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(meeting.isPendingSignoff ? Color.orange.opacity(0.88) : Color.green.opacity(0.88))
                            Text(meeting.summary).font(.subheadline).foregroundStyle(.white.opacity(0.72))
                        }
                        .padding(.vertical, 4)
                        if meeting.id != pulse.meetings.last?.id { Divider().overlay(Color.white.opacity(0.12)) }
                    }
                }
            }
            .padding(14)
            .background(Color.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 18))

            VStack(alignment: .leading, spacing: 10) {
                Text("Department actions")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(.white.opacity(0.58))
                    .textCase(.uppercase)
                if pulse.actions.isEmpty {
                    Text("No Board actions are currently delegated to departments.")
                        .font(.subheadline)
                        .foregroundStyle(.white.opacity(0.68))
                } else {
                    ForEach(pulse.actions) { action in
                        HStack(alignment: .top, spacing: 10) {
                            Image(systemName: "checklist")
                                .foregroundStyle(.white.opacity(0.75))
                                .frame(width: 24, height: 24)
                                .background(Color.white.opacity(0.10), in: Circle())
                            VStack(alignment: .leading, spacing: 3) {
                                Text(action.title).font(.subheadline.weight(.semibold)).foregroundStyle(.white)
                                Text("\(action.department) · \(action.status)\(action.dueAt.isEmpty ? "" : " · due \(action.dueAt)")")
                                    .font(.caption).foregroundStyle(.white.opacity(0.62))
                            }
                        }
                    }
                }
            }
            .padding(14)
            .background(Color.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 18))
        }
    }

    private func boardAvatarStack(_ members: [PilotBoardMember]) -> some View {
        HStack(spacing: -8) {
            ForEach(members.prefix(3)) { member in
                boardAvatar(member, size: 30)
                    .overlay(Circle().stroke(Color(red: 0.055, green: 0.065, blue: 0.10), lineWidth: 2))
            }
        }
    }

    private func boardAvatar(_ member: PilotBoardMember, size: CGFloat) -> some View {
        Text(member.initials)
            .font(.system(size: size * 0.34, weight: .bold, design: .rounded))
            .foregroundStyle(.white)
            .frame(width: size, height: size)
            .background(Color(red: 0.13, green: 0.15, blue: 0.20), in: Circle())
            .accessibilityLabel("\(member.name), \(member.role)")
    }

    private func supportOverview(_ pulse: PilotSupportPulse) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Support cases").font(.title2.weight(.bold)).foregroundStyle(.white)
            Text("These are the live customer cases from your Support workspace. A human-in-the-loop case needs your direction before the Pilot can proceed.")
                .font(.subheadline).foregroundStyle(.white.opacity(0.70))
            HStack(spacing: 8) {
                supportMetric("Open", value: pulse.summary["open"] ?? 0, tint: .white)
                supportMetric("Needs you", value: pulse.summary["awaiting_human"] ?? 0, tint: .orange)
                supportMetric("Resolved", value: pulse.summary["resolved"] ?? 0, tint: .green)
            }
            if pulse.cases.isEmpty {
                Text("No Support cases are recorded for this business yet.").font(.subheadline).foregroundStyle(.white.opacity(0.68))
            } else {
                ForEach(pulse.cases) { supportCase in
                    Button { selectedSupportCase = supportCase } label: {
                        VStack(alignment: .leading, spacing: 7) {
                            HStack(alignment: .firstTextBaseline) {
                                Text(supportCase.subject).font(.subheadline.weight(.bold)).foregroundStyle(.white).lineLimit(2)
                                Spacer()
                                Image(systemName: "chevron.right").font(.caption.weight(.bold)).foregroundStyle(.white.opacity(0.48))
                            }
                            Text("\(supportCase.customer) · \(supportCase.category.capitalized) · \(supportCase.updatedLabel)").font(.caption).foregroundStyle(.white.opacity(0.62)).lineLimit(1)
                            HStack(spacing: 6) {
                                statusChip(supportCase.statusLabel, tint: supportCase.needsHuman ? .orange : .blue)
                                if supportCase.needsHuman { statusChip("Needs your direction", tint: .orange) }
                            }
                        }
                        .padding(13)
                        .background(supportCase.needsHuman ? Color.orange.opacity(0.13) : Color.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 16))
                    }
                    .buttonStyle(.plain)
                }
            }
        }
        .padding(16)
        .background(Color.white.opacity(0.05), in: RoundedRectangle(cornerRadius: 22))
    }

    private func supportMetric(_ label: String, value: Int, tint: Color) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text("\(value)").font(.headline.weight(.bold)).foregroundStyle(tint)
            Text(label).font(.caption).foregroundStyle(.white.opacity(0.62))
        }
        .frame(maxWidth: .infinity, alignment: .leading).padding(10)
        .background(Color.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 12))
    }

    private func statusChip(_ label: String, tint: Color) -> some View {
        Text(label).font(.caption2.weight(.bold)).foregroundStyle(tint).padding(.horizontal, 8).padding(.vertical, 5)
            .background(tint.opacity(0.14), in: Capsule())
    }

    private func peopleOverview(_ pulse: PilotPeoplePulse) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("People").font(.title2.weight(.bold)).foregroundStyle(.white)
            Text("Employee records are available only to founders, HR, or people given this department permission. Sensitive employment detail stays outside the mobile directory.")
                .font(.subheadline).foregroundStyle(.white.opacity(0.70))
            if !pulse.allowed {
                Text("This phone has not been given People department permission.").font(.subheadline).foregroundStyle(.orange)
            } else if pulse.people.isEmpty {
                Text("No authorised employee records are available for this business yet.").font(.subheadline).foregroundStyle(.white.opacity(0.68))
            } else {
                ForEach(pulse.people) { person in
                    Button { selectedPerson = person } label: {
                        HStack(spacing: 12) {
                            Text(person.name.split(separator: " ").prefix(2).compactMap(\.first).map(String.init).joined())
                                .font(.caption.weight(.black)).foregroundStyle(.white).frame(width: 42, height: 42)
                                .background(Color.white.opacity(0.12), in: Circle())
                            VStack(alignment: .leading, spacing: 3) {
                                Text(person.name).font(.subheadline.weight(.bold)).foregroundStyle(.white)
                                Text(person.title.isEmpty ? person.status.capitalized : person.title).font(.caption).foregroundStyle(.white.opacity(0.62))
                            }
                            Spacer()
                            Image(systemName: "chevron.right").font(.caption.weight(.bold)).foregroundStyle(.white.opacity(0.48))
                        }
                        .padding(.vertical, 7)
                    }
                    .buttonStyle(.plain)
                    if person.id != pulse.people.last?.id { Divider().overlay(Color.white.opacity(0.12)).padding(.leading, 54) }
                }
            }
        }
        .padding(16)
        .background(Color.white.opacity(0.05), in: RoundedRectangle(cornerRadius: 22))
    }

    private func salesOverview(_ pulse: PilotSalesPulse) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Today’s Sales briefing").font(.title2.weight(.bold)).foregroundStyle(.white)
            Text(pulse.date).font(.caption.weight(.bold)).foregroundStyle(conversationTint).textCase(.uppercase)
            Text(pulse.message).font(.subheadline).foregroundStyle(.white.opacity(0.70))
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 8) {
                salesMetric("New leads", value: pulse.metrics["leads_today"] ?? 0)
                salesMetric("Activity today", value: pulse.metrics["activity_today"] ?? 0)
                salesMetric("Quotes today", value: pulse.metrics["quotes_today"] ?? 0)
                salesMetric("Open follow-ups", value: pulse.metrics["follow_ups_open"] ?? 0)
                salesMetric("Deposits today", value: pulse.metrics["deposits_today"] ?? 0)
                salesMetric("Won pipeline", value: pulse.metrics["won_total"] ?? 0)
            }
            if let conversion = pulse.conversion {
                Text("Closed-pipeline conversion: \(conversion)%").font(.caption.weight(.semibold)).foregroundStyle(.green)
            }
            if let salesNote = pulse.availability["sales_generated_today"] {
                salesNotice("Sales total", detail: salesNote)
            }
            VStack(alignment: .leading, spacing: 8) {
                Text("Board direction").font(.caption.weight(.bold)).foregroundStyle(.white.opacity(0.58)).textCase(.uppercase)
                if pulse.boardActions.isEmpty {
                    Text("No Sales action has been published by the Board to the mobile ledger.").font(.subheadline).foregroundStyle(.white.opacity(0.68))
                } else {
                    ForEach(pulse.boardActions) { action in
                        Text(action.title).font(.subheadline.weight(.semibold)).foregroundStyle(.white)
                        Text("\(action.status)\(action.dueAt.isEmpty ? "" : " · due \(action.dueAt)")").font(.caption).foregroundStyle(.white.opacity(0.62))
                    }
                }
            }.padding(12).background(Color.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 16))
            VStack(alignment: .leading, spacing: 8) {
                Text("Today’s queue").font(.caption.weight(.bold)).foregroundStyle(.white.opacity(0.58)).textCase(.uppercase)
                if pulse.queue.isEmpty {
                    Text("No open Sales opportunities are recorded.").font(.subheadline).foregroundStyle(.white.opacity(0.68))
                } else {
                    ForEach(Array(pulse.queue.enumerated()), id: \.offset) { _, item in
                        VStack(alignment: .leading, spacing: 2) {
                            Text(item.title).font(.subheadline.weight(.semibold)).foregroundStyle(.white)
                            Text("\(item.stage.replacingOccurrences(of: "_", with: " ").capitalized) · \(item.nextAction)").font(.caption).foregroundStyle(.white.opacity(0.62))
                        }
                    }
                }
            }.padding(12).background(Color.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 16))
            salesNotice("Executive route", detail: pulse.availability["executive_meeting"] ?? "No Executive update is available.")
            salesNotice("Objective changes", detail: pulse.governance)
        }
        .padding(16)
        .background(Color.white.opacity(0.05), in: RoundedRectangle(cornerRadius: 22))
    }

    private func salesMetric(_ label: String, value: Int) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text("\(value)").font(.headline.weight(.bold)).foregroundStyle(.white)
            Text(label).font(.caption).foregroundStyle(.white.opacity(0.62))
        }
        .frame(maxWidth: .infinity, alignment: .leading).padding(10)
        .background(Color.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 12))
    }

    private func salesNotice(_ title: String, detail: String) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(title).font(.caption.weight(.bold)).foregroundStyle(.white.opacity(0.72))
            Text(detail).font(.caption).foregroundStyle(.white.opacity(0.60))
        }.padding(11).background(Color.white.opacity(0.06), in: RoundedRectangle(cornerRadius: 14))
    }

    private func financeOverview(_ pulse: PilotFinancePulse) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Today’s Finance briefing").font(.title2.weight(.bold)).foregroundStyle(.white)
            Text("Evidence: \(pulse.verification.replacingOccurrences(of: "_", with: " "))").font(.caption.weight(.bold)).foregroundStyle(.white.opacity(0.60)).textCase(.uppercase)
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 8) {
                financeMetric("Cash in bank", key: "cash_in_bank", pulse: pulse)
                financeMetric("Outstanding invoices", key: "outstanding_invoices", pulse: pulse)
                financeMetric("Overdue invoices", key: "overdue_invoices", pulse: pulse)
                financeMetric("Revenue", key: "revenue", pulse: pulse)
                financeMetric("Operating profit", key: "operating_profit", pulse: pulse)
                financeMetric("Cash runway", key: "runway_months", pulse: pulse, suffix: " months")
            }
            if pulse.actions.isEmpty {
                Text("No Finance risks or actions have been published for review.").font(.subheadline).foregroundStyle(.white.opacity(0.68))
            } else {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Today’s attention").font(.caption.weight(.bold)).foregroundStyle(.white.opacity(0.58)).textCase(.uppercase)
                    ForEach(Array(pulse.actions.enumerated()), id: \.offset) { _, action in
                        VStack(alignment: .leading, spacing: 3) {
                            Text(action.title).font(.subheadline.weight(.semibold)).foregroundStyle(action.severity == "critical" ? .orange : .white)
                            Text(action.recommendation).font(.caption).foregroundStyle(.white.opacity(0.65))
                        }
                    }
                }.padding(12).background(Color.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 16))
            }
            ForEach(pulse.availability, id: \.self) { notice in salesNotice("Finance evidence", detail: notice) }
        }.padding(16).background(Color.white.opacity(0.05), in: RoundedRectangle(cornerRadius: 22))
    }

    private func financeMetric(_ label: String, key: String, pulse: PilotFinancePulse, suffix: String = "") -> some View {
        VStack(alignment: .leading, spacing: 2) {
            if let value = pulse.metrics[key] {
                Text(key == "runway_months" ? "\(value, specifier: "%.1f")\(suffix)" : "\(pulse.currencySymbol)\(value, specifier: "%.2f")")
                    .font(.headline.weight(.bold)).foregroundStyle(.white).lineLimit(1).minimumScaleFactor(0.7)
            } else { Text("Not connected").font(.subheadline.weight(.semibold)).foregroundStyle(.white.opacity(0.58)) }
            Text(label).font(.caption).foregroundStyle(.white.opacity(0.62))
        }.frame(maxWidth: .infinity, alignment: .leading).padding(10).background(Color.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 12))
    }

    private var chatComposer: some View {
        HStack(alignment: .center, spacing: 8) {
            Button { showingFilePicker = true } label: {
                Image(systemName: "plus")
                    .font(.title2.weight(.medium))
                    .frame(width: 42, height: 42)
                    .background(Color.white.opacity(0.10), in: Circle())
            }
            HStack(spacing: 8) {
                TextField(
                    conversation.departmentID == "executive_channels"
                        ? "Message \(selectedExecutiveChannelName) Pilot"
                        : "Message",
                    text: $draft,
                    axis: .vertical
                )
                    .lineLimit(1...4)
                    .foregroundStyle(.white)
                PhotosPicker(selection: $selectedPhoto, matching: .images) {
                    Image(systemName: "camera.fill").font(.title3)
                }
                .onChange(of: selectedPhoto) { _, item in
                    if item != nil { attachmentName = "Photo ready to send" }
                }
            }
            .padding(.leading, 14)
            .padding(.trailing, 10)
            .padding(.vertical, 9)
            .background(Color.white.opacity(0.10), in: Capsule())
            if draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                Button(action: toggleDictation) {
                    Image(systemName: dictation.isListening ? "stop.fill" : "mic.fill")
                        .font(.title3.weight(.bold))
                        .foregroundStyle(.white)
                        .frame(width: 44, height: 44)
                        .background(dictation.isListening ? Color.red : conversationTint, in: Circle())
                }
                .accessibilityLabel(dictation.isListening ? "Stop dictation" : "Start dictation")
            } else {
                Button(action: send) {
                    Image(systemName: "arrow.up")
                        .font(.headline.weight(.bold))
                        .frame(width: 44, height: 44)
                        .background(conversationTint, in: Circle())
                }
                .disabled(membershipID.isEmpty || loading)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .foregroundStyle(.white)
        .background(Color(red: 0.055, green: 0.065, blue: 0.10))
    }

    private func chatBubble(_ message: PilotChatMessage) -> some View {
        HStack {
            if message.isMine { Spacer(minLength: 46) }
            VStack(alignment: .leading, spacing: 4) {
                Text(message.sender).font(.caption.weight(.bold)).foregroundStyle(message.isMine ? .white.opacity(0.75) : conversationTint)
                Text(message.body).font(.body).foregroundStyle(.white)
                if let details = message.details {
                    Divider().overlay(Color.white.opacity(0.18))
                    Text(details).font(.caption2.weight(.semibold)).foregroundStyle(message.isMine ? .white.opacity(0.68) : conversationTint.opacity(0.90))
                }
            }
            .padding(12)
            .background(message.isMine ? Color(red: 0.08, green: 0.37, blue: 0.30) : Color.white.opacity(0.12), in: RoundedRectangle(cornerRadius: 18))
            if !message.isMine { Spacer(minLength: 46) }
        }
    }

    private func pilotBubble(_ body: String, label: String) -> some View {
        chatBubble(PilotChatMessage(sender: label, body: body, isMine: false))
    }

    private var pilotThinkingBubble: some View {
        HStack {
            VStack(alignment: .leading, spacing: 8) {
                HStack(spacing: 9) {
                    Image(systemName: "sparkles")
                        .font(.headline.weight(.bold))
                        .foregroundStyle(conversationTint)
                    ProgressView()
                        .tint(conversationTint)
                    Text("\(conversation.title) Pilot is preparing a grounded response…")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.white)
                }
                if showSlowResponseHint {
                    Text("This private model is still working. A Tessaris Hub or additional home compute can make longer replies faster.")
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.66))
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            .padding(12)
            .background(Color.white.opacity(0.12), in: RoundedRectangle(cornerRadius: 18))
            Spacer(minLength: 46)
        }
        .accessibilityLabel("Pilot is preparing a response")
    }

    private var conversationTint: Color {
        switch conversation.departmentID {
        case "sales": .orange
        case "marketing": .pink
        case "finance": .green
        case "support": .teal
        case "operations": .purple
        case "boardroom": .blue
        case "executive": .blue
        case "executive_channels": .blue
        default: .indigo
        }
    }

    private func openWorkspace() async {
        loading = true
        defer { loading = false }
        do {
            let client = try PilotNodeClient(connection: connection)
            let surface = try await client.openWorkspaceSurface(
                surface: workspaceSurfaceName, connection: connection, vault: vault
            )
            membershipID = surface["membership_id"] as? String ?? ""
            if conversation.departmentID == "boardroom" {
                boardroomPulse = PilotBoardroomPulse(surface: surface)
            } else if conversation.departmentID == "executive" {
                executiveMembers = PilotExecutiveMember.members(from: surface)
            } else if conversation.departmentID == "executive_channels" {
                executiveMembers = PilotExecutiveMember.members(from: surface)
                if let channelStatus = try? await client.executiveChannelsStatus(
                    membershipID: membershipID, connection: connection, vault: vault
                ) {
                    let executive = channelStatus["executive"] as? [String: Any] ?? [:]
                    let schedule = executive["schedule"] as? [String: Any] ?? [:]
                    let enabled = schedule["enabled"] as? Bool ?? true
                    let localTime = schedule["local_time"] as? String ?? "08:00"
                    let timezone = schedule["timezone"] as? String ?? "business local time"
                    executiveScheduleLabel = "\(enabled ? "Daily" : "Paused") · \(localTime) · \(timezone)"
                    let latest = executive["latest_briefing"] as? [String: Any] ?? [:]
                    let channels = executive["channels"] as? [[String: Any]] ?? []
                    executiveChannelMembers = PilotExecutiveMember.channels(from: channels)
                    if !executiveChannelMembers.contains(where: { $0.id == selectedExecutiveChannelID }) {
                        selectedExecutiveChannelID = executiveChannelMembers.first?.id ?? "sales"
                    }
                    let mode = latest["reasoning_mode"] as? String ?? "single_model_role_separated"
                    executiveReasoningLabel = mode == "two_model_challenge"
                        ? "Two-model executive challenge"
                        : "Vault model · role-separated departments"
                }
            } else if conversation.departmentID == "support" {
                supportPulse = PilotSupportPulse(surface: surface)
            } else if conversation.departmentID == "people" {
                peoplePulse = PilotPeoplePulse(surface: surface)
            } else if conversation.departmentID == "sales" {
                salesPulse = PilotSalesPulse(surface: surface)
            } else if conversation.departmentID == "finance" {
                financePulse = PilotFinancePulse(surface: surface)
                if messages.isEmpty, let financePulse {
                    messages.append(PilotChatMessage(
                        sender: "Finance Pilot",
                        body: financePulse.plan,
                        isMine: false
                    ))
                }
            }
            summary = Self.readableBriefing(surface, for: conversation)
            status = "Connected to your private Node. Messages are signed by this phone and checked against your workspace role."
            await loadConversationHistory()
        } catch {
            status = "This phone cannot open the authorised workspace yet: \(error.localizedDescription)"
        }
    }

    private var workspaceSurfaceName: String {
        switch conversation.departmentID {
        case "boardroom": return "briefings"
        case "support": return "support"
        case "people": return "people"
        case "sales": return "sales"
        case "finance": return "finance"
        default: return "departments"
        }
    }

    private func prepareMeetingMinutesDraft(from transcript: String) {
        let cleaned = transcript.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !cleaned.isEmpty, !preparingMeetingDraft else { return }
        meetingDraft = PilotMeetingMinutesDraft(title: conversation.title, transcript: cleaned, minutes: "Transcript captured. Pilot will add evidence-backed decisions and actions when the private workspace is available.\n\n\(cleaned)")
        guard !membershipID.isEmpty else {
            status = "Your meeting transcript is ready to review. Reconnect to Pilot to generate the assisted draft."
            return
        }
        preparingMeetingDraft = true
        let request = """
        Prepare an editable meeting-minutes draft for \(conversation.title) from the transcript below. List only decisions and actions that are explicitly evidenced. For every action, include an owner and due date only when stated; otherwise mark both ‘Unassigned’ and ‘Not stated’. Do not send, publish, assign, or execute anything. End by asking the user to review the draft, assign owners, and choose recipients before delivery.

        Transcript:
        \(cleaned)
        """
        Task {
            defer { preparingMeetingDraft = false }
            do {
                let client = try PilotNodeClient(connection: connection)
                let result = try await client.workspaceConversation(membershipID: membershipID, departmentID: conversation.departmentID, text: request, connection: connection, vault: vault)
                let turn = (result["conversation"] as? [String: Any])?["turn"] as? [String: Any]
                meetingDraft = PilotMeetingMinutesDraft(title: conversation.title, transcript: cleaned, minutes: turn?["content"] as? String ?? cleaned)
            } catch {
                meetingDraft = PilotMeetingMinutesDraft(title: conversation.title, transcript: cleaned, minutes: "Pilot could not prepare the minutes draft yet. Your transcript is preserved below for review.\n\n\(cleaned)")
            }
        }
    }

    private func send() {
        let text = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !membershipID.isEmpty else { return }
        draft = ""
        loading = true
        awaitingPilotReply = true
        showSlowResponseHint = false
        messages.append(PilotChatMessage(sender: "You", body: text, isMine: true))
        Task {
            try? await Task.sleep(nanoseconds: 15_000_000_000)
            if awaitingPilotReply {
                showSlowResponseHint = true
            }
        }
        Task {
            defer {
                loading = false
                awaitingPilotReply = false
            }
            do {
                let client = try PilotNodeClient(connection: connection)
                if conversation.departmentID == "executive_channels" {
                    let result = try await client.executiveChannelTurn(
                        membershipID: membershipID, departmentID: selectedExecutiveChannelID, text: text,
                        connection: connection, vault: vault
                    )
                    let executive = result["executive"] as? [String: Any] ?? [:]
                    let response = executive["response"] as? [String: Any] ?? [:]
                    let answer = response["content"] as? String ?? "The Department Pilot returned no readable response."
                    messages.append(PilotChatMessage(sender: response["sender"] as? String ?? "\(selectedExecutiveChannelName) Pilot", body: answer, isMine: false))
                } else {
                    let result = try await client.workspaceConversation(
                        membershipID: membershipID, departmentID: conversation.departmentID, text: text,
                        connection: connection, vault: vault
                    )
                    let conversationObject = result["conversation"] as? [String: Any]
                    let turn = conversationObject?["turn"] as? [String: Any]
                    let answer = turn?["content"] as? String ?? "Your Pilot returned no readable response."
                    messages.append(PilotChatMessage(sender: "\(conversation.title) Pilot", body: answer, isMine: false))
                }
                await loadConversationHistory()
            } catch {
                messages.append(PilotChatMessage(sender: "Tessaris", body: "Your message was not accepted by the Node. \(error.localizedDescription)", isMine: false))
            }
        }
    }

    private func loadConversationHistory(before: String = "", prepend: Bool = false) async {
        guard !membershipID.isEmpty else { return }
        do {
            let client = try PilotNodeClient(connection: connection)
            let result: [String: Any]
            if conversation.departmentID == "executive_channels" {
                result = try await client.executiveChannelHistory(
                    membershipID: membershipID, departmentID: selectedExecutiveChannelID,
                    connection: connection, vault: vault
                )
            } else {
                result = try await client.workspaceConversationHistory(
                    membershipID: membershipID, departmentID: conversation.departmentID, before: before,
                    connection: connection, vault: vault
                )
            }
            let history = result["history"] as? [String: Any] ?? [:]
            let rows = history["turns"] as? [[String: Any]] ?? []
            let loaded = rows.map(PilotChatMessage.init(historyRow:))
            if prepend { messages = loaded + messages } else if !loaded.isEmpty { messages = loaded }
            hasOlderMessages = conversation.departmentID == "executive_channels" ? false : (history["has_more"] as? Bool ?? false)
            historyCursor = conversation.departmentID == "executive_channels" ? "" : (history["next_before"] as? String ?? "")
        } catch {
            // The live conversation still works without a history page. The
            // status shown on open retains the exact Node rejection reason.
        }
    }

    private func loadOlderMessages() {
        guard !historyCursor.isEmpty, !loadingOlderMessages else { return }
        loadingOlderMessages = true
        Task {
            await loadConversationHistory(before: historyCursor, prepend: true)
            loadingOlderMessages = false
        }
    }

    private func toggleDictation() {
        if dictation.isListening { dictation.stop(); return }
        Task { await dictation.start(initialText: draft) }
    }

    private func deleteDepartment() {
        guard conversation.isCustom, !membershipID.isEmpty else { return }
        Task {
            do {
                let client = try PilotNodeClient(connection: connection)
                _ = try await client.deleteCustomDepartment(membershipID: membershipID, departmentID: conversation.departmentID, connection: connection, vault: vault)
                onDeleted(conversation.departmentID)
                dismiss()
            } catch {
                status = "This department could not be deleted: \(error.localizedDescription)"
            }
        }
    }

    private static func readableBriefing(_ surface: [String: Any], for conversation: PilotConversation) -> String {
        if conversation.departmentID == "boardroom" {
            return "The Boardroom is connected. Your phone shows the standing Board, published meeting history and actions delegated to each department. The first Board meeting remains on desktop; later meetings can be reviewed and answered here."
        }
        if conversation.departmentID == "executive" {
            return "The Executive meeting is connected. Sales, Marketing, Finance, Operations, Support and People Pilots report here through the CEO or COO."
        }
        if conversation.departmentID == "support" {
            return "Support is connected to the live case ledger. Open a case to review the evidence and any human-in-the-loop request."
        }
        if conversation.departmentID == "people" {
            return "People is connected to the authorised employee directory. Only founder, HR or explicitly delegated phone access can open a record."
        }
        if conversation.departmentID == "sales" {
            return "Sales is connected to the canonical pipeline. Today’s briefing shows recorded leads, follow-ups and Board direction; target changes are routed to COO or Executive for review."
        }
        if conversation.departmentID == "finance" {
            return "Finance is connected to the authorised Finance model and invoice ledger. It will show only recorded cash, P&L, balance-sheet and invoice figures, with payments and provider writes held for exact approval."
        }
        let data = surface["data"] as? [String: Any]
        let departments = data?["departments"] as? [[String: Any]]
        let available = departments?.contains { ($0["key"] as? String)?.lowercased() == conversation.departmentID.lowercased() } ?? false
        if available {
            return "Your \(conversation.title) Pilot is connected. New mandates, priorities and exceptions from the Executive team will appear in this conversation."
        }
        return "Your \(conversation.title) conversation is ready. It will show approved work from your Node as your department is configured."
    }
}

private struct PilotChatMessage: Identifiable {
    let id: String
    let sender: String
    let body: String
    let isMine: Bool
    let details: String?

    init(sender: String, body: String, isMine: Bool) {
        self.id = UUID().uuidString
        self.sender = sender
        self.body = body
        self.isMine = isMine
        self.details = nil
    }

    init(historyRow: [String: Any]) {
        self.id = historyRow["id"] as? String ?? UUID().uuidString
        self.sender = historyRow["sender"] as? String ?? ((historyRow["role"] as? String) == "user" ? "You" : "Pilot")
        self.body = historyRow["content"] as? String ?? ""
        self.isMine = (historyRow["role"] as? String) == "user"
        let receipt = historyRow["mission_receipt"] as? [String: Any] ?? [:]
        let proposal = historyRow["proposal"] as? [String: Any] ?? receipt["proposal"] as? [String: Any] ?? [:]
        let selection = receipt["model_selection"] as? [String: Any] ?? [:]
        let research = historyRow["research_job"] as? [String: Any] ?? receipt["research_job"] as? [String: Any] ?? [:]
        let approval = historyRow["required_approval"] as? [String: Any] ?? receipt["required_approval"] as? [String: Any] ?? [:]
        let metadata = historyRow["metadata"] as? [String: Any] ?? [:]
        let executiveSelection = metadata["model_selection"] as? [String: Any] ?? [:]
        let evidenceSources = historyRow["evidence_source_ids"] as? [Any] ?? []
        let messageType = historyRow["message_type"] as? String
        var parts: [String] = []
        if let status = receipt["status"] as? String { parts.append("Mission \(status.replacingOccurrences(of: "_", with: " "))") }
        if let provider = selection["provider"] as? String {
            let model = selection["model"] as? String
            parts.append(model.map { "\(provider) · \($0)" } ?? provider)
        }
        if let consultations = proposal["department_consultations"] as? [[String: Any]] { parts.append("\(consultations.count) department consultation(s)") }
        if let sources = proposal["sources"] as? [Any] { parts.append("\(sources.count) source reference(s)") }
        if let status = research["status"] as? String { parts.append("Research \(status.replacingOccurrences(of: "_", with: " "))") }
        if let state = approval["approval_state"] as? String { parts.append("Approval \(state.replacingOccurrences(of: "_", with: " "))") }
        if let messageType { parts.append(messageType.replacingOccurrences(of: "_", with: " ").capitalized) }
        if !evidenceSources.isEmpty { parts.append("\(evidenceSources.count) evidence source(s)") }
        if let provider = executiveSelection["provider"] as? String {
            let model = executiveSelection["model"] as? String
            parts.append(model.map { "\(provider) · \($0)" } ?? provider)
        }
        if historyRow["approval_gated"] as? Bool == true { parts.append("Approval gated") }
        self.details = parts.isEmpty ? nil : parts.joined(separator: " · ")
    }
}

private struct PilotExecutiveMember: Identifiable {
    let id: String
    let name: String
    let role: String

    var initials: String {
        let words = name.replacingOccurrences(of: " Pilot", with: "").split(separator: " ")
        return String(words.prefix(2).compactMap(\.first)).uppercased()
    }

    static let defaults = [
        PilotExecutiveMember(id: "sales", name: "Sales Pilot", role: "Revenue and pipeline"),
        PilotExecutiveMember(id: "marketing", name: "Marketing Pilot", role: "Campaigns and demand"),
        PilotExecutiveMember(id: "finance", name: "Finance Pilot", role: "Cash and invoices"),
        PilotExecutiveMember(id: "operations", name: "Operations Pilot", role: "Delivery and risks"),
        PilotExecutiveMember(id: "support", name: "Support Pilot", role: "Customer issues"),
        PilotExecutiveMember(id: "people", name: "People Pilot", role: "Team records"),
    ]

    static let channelDefaults = [
        PilotExecutiveMember(id: "sales", name: "Sales Pilot", role: "Revenue and pipeline"),
        PilotExecutiveMember(id: "marketing", name: "Marketing Pilot", role: "Campaigns and demand"),
        PilotExecutiveMember(id: "finance", name: "Finance Pilot", role: "Cash and invoices"),
        PilotExecutiveMember(id: "support", name: "Support Pilot", role: "Customer issues"),
        PilotExecutiveMember(id: "people", name: "People Pilot", role: "Team and capacity"),
    ]

    static func channels(from rows: [[String: Any]]) -> [PilotExecutiveMember] {
        let result = rows.compactMap { item -> PilotExecutiveMember? in
            guard let id = item["department_id"] as? String, !id.isEmpty else { return nil }
            let label = (item["display_name"] as? String)?.trimmingCharacters(in: .whitespacesAndNewlines)
            return PilotExecutiveMember(
                id: id,
                name: "\((label?.isEmpty == false ? label! : id.replacingOccurrences(of: "_", with: " ").capitalized)) Pilot",
                role: "COO executive channel"
            )
        }
        return result.isEmpty ? channelDefaults : result
    }

    static func members(from surface: [String: Any]) -> [PilotExecutiveMember] {
        let data = surface["data"] as? [String: Any] ?? [:]
        let result = (data["executive_members"] as? [[String: Any]] ?? []).compactMap { item -> PilotExecutiveMember? in
            guard let id = item["id"] as? String, let name = item["name"] as? String, !id.isEmpty, !name.isEmpty else { return nil }
            return PilotExecutiveMember(id: id, name: name, role: item["role"] as? String ?? "Function Pilot")
        }
        return result.isEmpty ? defaults : result
    }
}

private struct PilotBoardMember: Identifiable {
    let id: String
    let name: String
    let role: String

    var initials: String {
        let letters = name.split(separator: " ").prefix(2).compactMap { $0.first }
        return letters.isEmpty ? "AI" : String(letters).uppercased()
    }
}

private struct PilotBoardMeeting: Identifiable {
    let id: String
    let title: String
    let occurredAt: String
    let summary: String
    let status: String

    var isPendingSignoff: Bool { status == "analysis_pending_signoff" }
    var recordLabel: String { isPendingSignoff ? "Board analysis · awaiting sign-off" : "Published minutes" }
}

private struct PilotBoardAction: Identifiable {
    let id: String
    let title: String
    let department: String
    let status: String
    let dueAt: String
}

private struct PilotBoardroomPulse {
    let members: [PilotBoardMember]
    let meetings: [PilotBoardMeeting]
    let actions: [PilotBoardAction]

    init(surface: [String: Any]) {
        let data = surface["data"] as? [String: Any] ?? [:]
        self.members = (data["board_members"] as? [[String: Any]] ?? []).compactMap { item in
            let id = item["id"] as? String ?? ""
            let name = item["name"] as? String ?? ""
            guard !id.isEmpty, !name.isEmpty else { return nil }
            return PilotBoardMember(id: id, name: name, role: item["role"] as? String ?? "Board intelligence")
        }
        self.meetings = (data["meeting_history"] as? [[String: Any]] ?? []).compactMap { item in
            let id = item["id"] as? String ?? ""
            let title = item["title"] as? String ?? ""
            guard !id.isEmpty, !title.isEmpty else { return nil }
            return PilotBoardMeeting(
                id: id,
                title: title,
                occurredAt: Self.shortDate(item["occurred_at"] as? String ?? ""),
                summary: item["summary"] as? String ?? "Approved Board record",
                status: item["status"] as? String ?? "published"
            )
        }
        self.actions = (data["department_actions"] as? [[String: Any]] ?? []).compactMap { item in
            let id = item["id"] as? String ?? ""
            let title = item["title"] as? String ?? ""
            let department = item["department"] as? String ?? ""
            guard !id.isEmpty, !title.isEmpty, !department.isEmpty else { return nil }
            return PilotBoardAction(
                id: id,
                title: title,
                department: department.capitalized,
                status: item["status"] as? String ?? "delegated",
                dueAt: Self.shortDate(item["due_at"] as? String ?? "")
            )
        }
    }

    private static func shortDate(_ value: String) -> String {
        guard !value.isEmpty else { return "Published" }
        return String(value.prefix(10))
    }
}

private struct CustomDepartmentSetupView: View {
    let connection: PilotConnection
    let onCreated: (PilotTool) -> Void
    private let vault = PilotPossessionVault()
    @Environment(\.dismiss) private var dismiss
    @State private var template = "innovation"
    @State private var name = "Innovation"
    @State private var mandate = "You are the Innovation Director. Provide research, new ideas and practical opportunities for this business. Wait for instructions and keep recommendations evidence-based."
    @State private var status = ""
    @State private var saving = false

    private let templates = [
        ("innovation", "Innovation"), ("legal", "Legal"), ("compliance", "Compliance"),
        ("it", "IT"), ("technical", "Technical"), ("product", "Product"),
        ("research", "Research"), ("partnerships", "Partnerships"),
    ]

    var body: some View {
        NavigationStack {
            Form {
                Section("Department") {
                    Picker("Template", selection: $template) {
                        ForEach(templates, id: \.0) { Text($0.1).tag($0.0) }
                    }
                    TextField("Department name", text: $name)
                }
                Section("Pilot mandate") {
                    TextEditor(text: $mandate).frame(minHeight: 150)
                    Text("This is the starting instruction for this Department Pilot. You can refine it later.")
                        .font(.caption).foregroundStyle(.secondary)
                }
                if !status.isEmpty { Section { Text(status).font(.footnote).foregroundStyle(.secondary) } }
            }
            .navigationTitle("New department")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Cancel", action: dismiss.callAsFunction) }
                ToolbarItem(placement: .confirmationAction) { Button("Create", action: create).disabled(saving || name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || mandate.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty) }
            }
        }
    }

    private func create() {
        saving = true
        status = "Creating your Department Pilot…"
        Task {
            defer { saving = false }
            do {
                let client = try PilotNodeClient(connection: connection)
                let spaces = try await client.workspaceSpaces(connection: connection, vault: vault)
                guard let first = (spaces["spaces"] as? [[String: Any]])?.first,
                      let membership = first["membership"] as? [String: Any],
                      let membershipID = membership["membership_id"] as? String else { throw PilotNodeClient.ClientError.invalidResponse }
                let result = try await client.createCustomDepartment(membershipID: membershipID, name: name, template: template, mandate: mandate, connection: connection, vault: vault)
                guard let department = result["department"] as? [String: Any], let id = department["id"] as? String, let label = department["name"] as? String else { throw PilotNodeClient.ClientError.invalidResponse }
                onCreated(PilotTool(label, "sparkles", Color(red: 0.07, green: 0.09, blue: 0.15), customDepartmentID: id))
                dismiss()
            } catch {
                status = "Only a founder-authorised phone can create this department. \(error.localizedDescription)"
            }
        }
    }
}


private struct PilotToolDetailView: View {
    let tool: PilotTool
    let space: PilotSpace
    let beginRequest: () -> Void
    @Environment(\.dismiss) private var dismiss

    private var description: String {
        switch (space, tool.title) {
        case (.executive, "Executive meeting"): return "Your daily executive conversation. CEO or COO brings together department reports, open decisions and daily priorities."
        case (.executive, "Morning brief"): return "A concise daily comparison of yesterday’s results, today’s priorities and anything that needs your decision."
        case (.board, "Board mandate"): return "The current signed strategic direction. Department targets and operating constraints are derived from this record."
        case (.board, "Board meetings"): return "Formal strategic sessions. AION prepares evidence, the Board gives independent views, and the approved minutes become the operating mandate."
        case (.board, "Escalate to Board"): return "Use this only for a material risk, strategic decision or mandate change that the Executive team cannot resolve."
        case (.departments, "Pilot"): return "Your Operations Pilot coordinates cross-department work through guarded Mission Mode. It can complete authorised research and preparation, then bring you exact approvals before any external change."
        case (.departments, "Sales"): return "Sales mandate, pipeline headline and a direct conversation with the Sales Pilot."
        case (.departments, "Marketing"): return "Campaign headline, content review and a direct conversation with the Marketing Pilot."
        case (.departments, "Finance"): return "Cash position, payments, exceptions and a direct conversation with the Finance Pilot."
        case (.departments, "Support"): return "Customer risk, active cases and a direct conversation with the Support Pilot."
        case (.departments, "Operations"): return "The daily operating queue, bottlenecks and the COO/Operations Pilot."
        case (.departments, "People"): return "Search and approved profile access, subject to the founder’s business permissions."
        default: return "This private area will show live activity from your Tessaris Node as the service is connected."
        }
    }

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 22) {
                Image(systemName: tool.icon)
                    .font(.system(size: 42, weight: .semibold))
                    .foregroundStyle(tool.tint)
                    .frame(width: 78, height: 78)
                    .background(tool.tint.opacity(0.12), in: RoundedRectangle(cornerRadius: 24))
                Text(tool.title)
                    .font(.system(size: 34, weight: .bold, design: .rounded))
                Text(description)
                    .font(.body)
                    .foregroundStyle(.secondary)
                Divider()
                Label("Private Node connection retained", systemImage: "checkmark.shield.fill")
                    .foregroundStyle(.green)
                Spacer()
                Button("Ask \(tool.title)") {
                    beginRequest()
                    dismiss()
                }
                .frame(maxWidth: .infinity)
                .buttonStyle(.borderedProminent)
            }
            .padding(24)
            .navigationTitle(space.rawValue)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .topBarTrailing) { Button("Done", action: dismiss.callAsFunction) } }
        }
    }
}


/// Private controller for the shared browser/TV Pilot. Activation proves
/// possession on this phone; the browser only observes that resulting lease.
private struct PilotPersonalDashboardView: View {
    let connection: PilotConnection
    let backToBusiness: () -> Void
    private let vault = PilotPossessionVault()

    @State private var state = "loading"
    @State private var displayName = ""
    @State private var expiresAt = ""
    @State private var message = ""
    @State private var working = false
    @State private var openTasks = 0
    @State private var dueReminders = 0
    @State private var contacts = 0
    @State private var selectedSurface: PilotPersonalSurface?
    @State private var connectionNotice: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack {
                Image(systemName: "sparkles.tv.fill")
                    .font(.system(size: 30)).foregroundStyle(.indigo)
                    .frame(width: 58, height: 58)
                    .background(.white, in: Circle())
                VStack(alignment: .leading, spacing: 3) {
                    Text("Pilot Dashboard").font(.title3.weight(.bold))
                    Text(statusTitle).font(.subheadline).foregroundStyle(.secondary)
                }
                Spacer()
                Button(action: refresh) { Image(systemName: "arrow.clockwise") }
                    .buttonStyle(.bordered)
                    .disabled(working)
            }
            .padding(16)
            .background(.white, in: RoundedRectangle(cornerRadius: 22))

            VStack(alignment: .leading, spacing: 9) {
                Text(state == "you" ? "Personal is connected" : "Connect your Personal Pilot")
                    .font(.title2.weight(.bold))
                Text(state == "you"
                     ? "This iPhone is the signed controller for the Pilot dashboard. Private tiles are available only for this short session."
                     : "Connect this iPhone to make the browser Pilot dashboard your private, signed surface. It stays locked when the session expires or you lock it.")
                    .foregroundStyle(.secondary)
                if !message.isEmpty { Text(message).font(.footnote).foregroundStyle(.secondary) }
            }
            .padding(.horizontal, 4)

            if state == "you" {
                personalTiles
                HStack(spacing: 12) {
                    Button("Keep active", action: confirmPresence)
                        .buttonStyle(.borderedProminent).disabled(working)
                    Button("Lock", role: .destructive, action: release)
                        .buttonStyle(.bordered).disabled(working)
                }
                if !expiresAt.isEmpty { Text("Session expires \(expiresAt.formattedSessionTime)").font(.caption).foregroundStyle(.secondary) }
            } else if state == "another_person" {
                Text("Another household Personal session currently controls this dashboard.")
                    .font(.subheadline).foregroundStyle(.secondary)
            } else {
                Button("Connect Personal to Pilot Dashboard", action: acquire)
                    .buttonStyle(.borderedProminent)
            }

            Divider().padding(.vertical, 3)
            Label("The browser stays the shared home and TV surface. This phone holds the private signing key and confirms access with Face ID.", systemImage: "lock.shield")
                .font(.footnote).foregroundStyle(.secondary)
            Button("Back to Business", action: backToBusiness)
                .font(.subheadline.weight(.semibold))
        }
        .task { await reload() }
        .sheet(item: $selectedSurface) { surface in
            PilotPersonalSurfaceView(connection: connection, surface: surface)
        }
        .alert("Pilot Dashboard", isPresented: Binding(
            get: { connectionNotice != nil },
            set: { if !$0 { connectionNotice = nil } }
        )) {
            Button("OK", role: .cancel) { connectionNotice = nil }
        } message: {
            Text(connectionNotice ?? "")
        }
    }

    private var personalTiles: some View {
        VStack(alignment: .leading, spacing: 18) {
            VStack(alignment: .leading, spacing: 4) {
                Text("Pilot experiences").font(.title3.weight(.bold))
                Text("Control your shared home and television.").font(.subheadline).foregroundStyle(.secondary)
            }
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                personalTile("Games", value: "Open cloud gaming on the television", icon: "gamecontroller.fill", tint: .indigo, command: "games")
                personalTile("AI TV", value: "Put Pilot on the big screen", icon: "tv.fill", tint: .blue, command: "aion")
                personalTile("AI Learning", value: "Start the Spanish Learning Centre", icon: "graduationcap.fill", tint: .green, command: "education_start", arguments: ["profile_id": "explorer_a"])
                personalTile("AI Shopping", value: "Find, compare and prepare", icon: "cart.fill", tint: .orange)
            }
            VStack(alignment: .leading, spacing: 4) {
                Text("Your workspace").font(.title3.weight(.bold))
                Text("Private tiles follow your signed Pilot session.").font(.subheadline).foregroundStyle(.secondary)
            }
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                personalTile("Tasks", value: openTasks == 0 ? "Your private lists, reminders and requests" : "\(openTasks) open task\(openTasks == 1 ? "" : "s")", icon: "checkmark", tint: .blue, command: "tasks")
                personalTile("Calendar", value: "Your schedule and approved events", icon: "rectangle.grid.1x2", tint: .indigo, command: "calendar")
                personalTile("Files", value: "Your approved documents and saved assets", icon: "list.bullet.rectangle", tint: .teal, command: "files")
                personalTile("Personal Work", value: "Research, writing, study and projects", icon: "sparkle", tint: .purple, command: "work")
                personalTile("IoT & Devices", value: "Connect, inspect and manage household devices", icon: "bolt.horizontal.fill", tint: .pink, command: "iot")
            }
        }
    }

    private func personalTile(_ title: String, value: String, icon: String, tint: Color, command: String? = nil, arguments: [String: Any] = [:]) -> some View {
        Button {
            guard let command else { message = "Tell Pilot what you would like to find or compare."; return }
            selectedSurface = PilotPersonalSurface(title: title, command: command, arguments: arguments, icon: icon, tint: tint)
        } label: {
            VStack(alignment: .leading, spacing: 10) {
                Image(systemName: icon).font(.title3.weight(.semibold)).foregroundStyle(tint)
                Spacer(minLength: 6)
                Text(title).font(.subheadline.weight(.bold)).foregroundStyle(.primary)
                Text(value).font(.caption).foregroundStyle(.secondary).lineLimit(2)
            }
            .frame(maxWidth: .infinity, minHeight: 108, alignment: .topLeading)
            .padding(14)
            .background(.white, in: RoundedRectangle(cornerRadius: 18))
            .overlay(RoundedRectangle(cornerRadius: 18).stroke(Color.black.opacity(0.06)))
        }
        .buttonStyle(.plain)
    }

    private var statusTitle: String {
        switch state {
        case "you": return displayName.isEmpty ? "Connected to this iPhone" : "Connected as \(displayName)"
        case "another_person": return "In use by another Personal session"
        case "loading": return "Checking your trusted Node…"
        default: return "Private dashboard is locked"
        }
    }

    private func refresh() { Task { await reload() } }
    private func reload() async {
        working = true
        defer { working = false }
        do {
            let result = try await PilotNodeClient(connection: connection).personalDashboard(connection: connection, vault: vault)
            let dashboard = result["shared_dashboard"] as? [String: Any] ?? [:]
            state = dashboard["state"] as? String ?? "locked"
            displayName = dashboard["display_name"] as? String ?? ""
            expiresAt = dashboard["expires_at"] as? String ?? ""
            let summary = result["summary"] as? [String: Any] ?? [:]
            openTasks = summary["open_tasks"] as? Int ?? 0
            dueReminders = summary["due_reminders"] as? Int ?? 0
            contacts = summary["contacts"] as? Int ?? 0
            message = ""
        } catch { state = "locked"; message = "Your Personal dashboard could not reach the trusted Node. \(error.localizedDescription)" }
    }
    private func acquire() { Task { await changeSession("acquire") } }
    private func release() { Task { await changeSession("release") } }
    private func changeSession(_ operation: String) async {
        working = true
        defer { working = false }
        do {
            let result = try await PilotNodeClient(connection: connection).changeSharedDashboardSession(operation: operation, connection: connection, vault: vault)
            state = result["state"] as? String ?? (operation == "acquire" ? "you" : "locked")
            displayName = result["display_name"] as? String ?? ""
            expiresAt = result["expires_at"] as? String ?? ""
            message = operation == "acquire" ? "Connected. The browser dashboard will update shortly." : "Locked on the shared dashboard."
            connectionNotice = operation == "acquire"
                ? "Personal is connected. Your private dashboard is now active on this iPhone."
                : "The Pilot Dashboard is locked."
        } catch {
            message = "The dashboard session was not changed. \(error.localizedDescription)"
            connectionNotice = "Pilot could not connect this iPhone. \(error.localizedDescription)"
        }
    }
    private func confirmPresence() { Task {
        working = true; defer { working = false }
        do { let result = try await PilotNodeClient(connection: connection).confirmSharedDashboardPresence(connection: connection, vault: vault); expiresAt = result["expires_at"] as? String ?? expiresAt; message = "Your signed session remains active." }
        catch { message = "Pilot could not confirm this phone’s presence. \(error.localizedDescription)" }
    } }
}

private struct PilotPersonalSurface: Identifiable {
    let title: String
    let command: String
    let arguments: [String: Any]
    let icon: String
    let tint: Color
    var id: String { command }
}

private struct PilotPersonalSurfaceView: View {
    let connection: PilotConnection
    let surface: PilotPersonalSurface
    private let vault = PilotPossessionVault()

    @Environment(\.dismiss) private var dismiss
    @State private var status = "Preparing your signed request…"
    @State private var working = false

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 22) {
                Image(systemName: surface.icon)
                    .font(.system(size: 38, weight: .semibold))
                    .foregroundStyle(surface.tint)
                    .frame(width: 76, height: 76)
                    .background(surface.tint.opacity(0.12), in: RoundedRectangle(cornerRadius: 22))
                Text(surface.title).font(.largeTitle.weight(.bold))
                Text("Pilot will confirm this request with your phone, then open the matching shared Pilot surface.")
                    .font(.body).foregroundStyle(.secondary)
                Divider()
                Text(status).font(.body).foregroundStyle(working ? .secondary : .primary)
                Spacer()
                Button(working ? "Opening…" : "Open \(surface.title)", action: open)
                    .buttonStyle(.borderedProminent).disabled(working)
            }
            .padding(24)
            .navigationTitle("")
            .toolbar { ToolbarItem(placement: .topBarTrailing) { Button("Done") { dismiss() } } }
        }
        .task { await openSurface() }
    }

    private func open() { Task { await openSurface() } }
    private func openSurface() async {
        guard !working else { return }
        working = true
        defer { working = false }
        do {
            let client = try PilotNodeClient(connection: connection)
            let result: [String: Any]
            switch surface.command {
            case "games":
                result = try await client.controlExperience(
                    operation: "games_open", arguments: surface.arguments, connection: connection, vault: vault
                )
            case "aion":
                result = try await client.controlSharedTelevision(
                    command: "aion", arguments: surface.arguments, connection: connection, vault: vault
                )
            case "education_start":
                result = try await client.controlExperience(
                    operation: "learning_start", arguments: surface.arguments, connection: connection, vault: vault
                )
            default:
                result = try await client.openDashboardSurface(
                    command: surface.command, arguments: surface.arguments, connection: connection, vault: vault
                )
            }
            let spoken = (result["spoken_response"] as? String) ?? "Pilot completed the request."
            if surface.command == "games", result["playing_verified"] as? Bool != true {
                status = "\(spoken) Pilot will show a verified game state when the television confirms it."
            } else {
                status = spoken
            }
        } catch {
            status = "Pilot could not open \(surface.title). \(error.localizedDescription)"
        }
    }
}

private struct PilotMeetingMinutesDraft: Identifiable {
    let id = UUID()
    let title: String
    let transcript: String
    let minutes: String
}

/// Draft review remains private to this phone. Actions and recipients are
/// deliberately editable before any future publishing or delivery integration.
private struct PilotMeetingMinutesDraftView: View {
    let draft: PilotMeetingMinutesDraft
    @Environment(\.dismiss) private var dismiss
    @State private var minutes = ""
    @State private var recipients = ""
    @State private var readyForDeliveryReview = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Text("Draft minutes").font(.title2.weight(.bold))
                    Text("Review the minutes, edit actions and owners, then choose recipients. Nothing is sent, assigned or published from this draft automatically.")
                        .font(.subheadline).foregroundStyle(.secondary)
                    TextEditor(text: $minutes)
                        .font(.body).scrollContentBackground(.hidden).padding(12)
                        .background(Color.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 12))
                        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.white.opacity(0.25)))
                        .frame(minHeight: 300)
                    Text("Recipients for review").font(.headline)
                    TextField("Names or email addresses", text: $recipients, axis: .vertical)
                        .lineLimit(1...3).padding(12)
                        .background(Color.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 12))
                    if readyForDeliveryReview {
                        Label("Ready for delivery review. Nothing has been sent or assigned.", systemImage: "checkmark.circle.fill")
                            .font(.subheadline.weight(.semibold)).foregroundStyle(.green)
                    }
                    Button(readyForDeliveryReview ? "Ready for delivery review" : "Review recipients") { readyForDeliveryReview = true }
                        .frame(maxWidth: .infinity).buttonStyle(.borderedProminent).disabled(readyForDeliveryReview)
                    Text("The delivery step will send approved minutes to selected people and their Pilots only after a final confirmation. This draft has not been distributed.")
                        .font(.footnote).foregroundStyle(.secondary)
                }.padding(20)
            }
            .foregroundStyle(.white)
            .background(Color(red: 0.08, green: 0.08, blue: 0.10).ignoresSafeArea())
            .navigationTitle(draft.title)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done", action: dismiss.callAsFunction) } }
            .toolbarColorScheme(.dark, for: .navigationBar).preferredColorScheme(.dark)
            .onAppear { minutes = draft.minutes }
        }
    }
}

private struct PilotMeetingCaptureView: View {
    let title: String
    let onUseDraft: (String) -> Void
    @Environment(\.dismiss) private var dismiss
    @StateObject private var dictation = PilotLiveDictation()

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 16) {
                HStack(spacing: 10) {
                    Image(systemName: dictation.isListening ? "record.circle.fill" : "record.circle")
                        .foregroundStyle(dictation.isListening ? .red : .indigo)
                        .font(.title2)
                    Text(dictation.isListening ? "Recording meeting" : "Meeting capture")
                        .font(.headline)
                }
                Text("Make sure everyone knows the meeting is being captured. Pilot creates an editable draft; it does not publish minutes, decisions or actions automatically.")
                    .font(.subheadline).foregroundStyle(.secondary)
                TextEditor(text: Binding(get: { dictation.transcript }, set: { dictation.updateTranscript($0) }))
                    .font(.body)
                    .foregroundStyle(.white)
                    .scrollContentBackground(.hidden)
                    .padding(12)
                    .background(Color.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 12))
                    .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.white.opacity(0.25)))
                    .frame(minHeight: 260)
                    .accessibilityLabel("Editable meeting transcript")
                if !dictation.state.message.isEmpty {
                    Text(dictation.state.message).font(.footnote).foregroundStyle(.secondary)
                }
                Spacer()
                Button(dictation.isListening ? "Stop recording" : "Start recording") {
                    if dictation.isListening { dictation.stop() }
                    else { Task { await dictation.start(initialText: dictation.transcript) } }
                }
                .frame(maxWidth: .infinity)
                .buttonStyle(.borderedProminent)
                .tint(dictation.isListening ? .red : .indigo)
                Button("Use as meeting-minutes draft") {
                    let text = dictation.transcript.trimmingCharacters(in: .whitespacesAndNewlines)
                    guard !text.isEmpty else { return }
                    dismiss()
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                        onUseDraft(text)
                    }
                }
                .frame(maxWidth: .infinity)
                .buttonStyle(.bordered)
                .disabled(dictation.transcript.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }
            .padding(20)
            .foregroundStyle(.white)
            .background(Color(red: 0.08, green: 0.08, blue: 0.10).ignoresSafeArea())
            .navigationTitle("Meeting minutes")
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Done") { dictation.stop(); dismiss() } } }
            .toolbarColorScheme(.dark, for: .navigationBar)
            .preferredColorScheme(.dark)
            .onDisappear { dictation.stop() }
        }
    }
}

private extension String {
    var formattedSessionTime: String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        guard let date = formatter.date(from: self) else { return self }
        return date.formatted(date: .omitted, time: .shortened)
    }
}
import SwiftUI

/// Read-only detail sheets keep governed Support evidence and the People
/// directory usable on a phone without offering unsafe write actions.
private struct PilotSupportCaseDetailView: View {
    let supportCase: PilotSupportCase
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    Text(supportCase.number.isEmpty ? "Support case" : supportCase.number)
                        .font(.caption.weight(.bold)).foregroundStyle(.secondary)
                    Text(supportCase.subject).font(.title2.weight(.bold))
                    Text(supportCase.customer).font(.subheadline).foregroundStyle(.secondary)
                    HStack(spacing: 8) {
                        chip(supportCase.statusLabel, tint: supportCase.needsHuman ? .orange : .blue)
                        chip(supportCase.priority.capitalized, tint: supportCase.priority == "critical" || supportCase.priority == "urgent" ? .red : .secondary)
                    }
                    if supportCase.needsHuman {
                        VStack(alignment: .leading, spacing: 7) {
                            Label("Direction needed", systemImage: "person.crop.circle.badge.exclamationmark")
                                .font(.headline).foregroundStyle(.orange)
                            Text(supportCase.humanRequest.isEmpty ? "Support requires your direction before it can continue this case." : supportCase.humanRequest)
                                .font(.subheadline).foregroundStyle(.secondary)
                        }
                        .padding(14).background(Color.orange.opacity(0.12), in: RoundedRectangle(cornerRadius: 16))
                    }
                    if !supportCase.riskFlags.isEmpty {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Flags").font(.headline)
                            ForEach(supportCase.riskFlags, id: \.self) { flag in
                                chip(flag.replacingOccurrences(of: "_", with: " ").capitalized, tint: .orange)
                            }
                        }
                    }
                    Divider()
                    Text("Case timeline").font(.headline)
                    if supportCase.timeline.isEmpty {
                        Text("No readable evidence events are available for this case.").foregroundStyle(.secondary)
                    } else {
                        ForEach(supportCase.timeline) { event in
                            VStack(alignment: .leading, spacing: 5) {
                                HStack {
                                    Text(event.direction.replacingOccurrences(of: "_", with: " ").capitalized).font(.subheadline.weight(.bold))
                                    Spacer()
                                    Text(String(event.recordedAt.prefix(10))).font(.caption).foregroundStyle(.secondary)
                                }
                                Text(event.content).font(.subheadline).foregroundStyle(.secondary)
                            }
                            .padding(12).background(Color(uiColor: .secondarySystemBackground), in: RoundedRectangle(cornerRadius: 14))
                        }
                    }
                }
                .padding(20)
            }
            .navigationTitle("Support")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .topBarTrailing) { Button("Done", action: dismiss.callAsFunction) } }
        }
    }

    private func chip(_ title: String, tint: Color) -> some View {
        Text(title).font(.caption.weight(.bold)).foregroundStyle(tint).padding(.horizontal, 9).padding(.vertical, 6)
            .background(tint.opacity(0.12), in: Capsule())
    }
}

private struct PilotPersonRecordView: View {
    let person: PilotPersonRecord
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 20) {
                HStack(spacing: 14) {
                    Text(person.name.split(separator: " ").prefix(2).compactMap(\.first).map(String.init).joined())
                        .font(.title3.weight(.black)).foregroundStyle(.white).frame(width: 62, height: 62)
                        .background(Color(red: 0.07, green: 0.09, blue: 0.15), in: Circle())
                    VStack(alignment: .leading, spacing: 3) {
                        Text(person.name).font(.title2.weight(.bold))
                        Text(person.title.isEmpty ? "Team member" : person.title).foregroundStyle(.secondary)
                    }
                }
                Divider()
                recordRow("Record status", person.status.capitalized)
                recordRow("Authority", person.authorityScope)
                if !person.roleNames.isEmpty { recordRow("Role", person.roleNames.joined(separator: ", ")) }
                if !person.departmentNames.isEmpty { recordRow("Departments", person.departmentNames.joined(separator: ", ")) }
                if !person.accessAreas.isEmpty { recordRow("Authorised areas", person.accessAreas.joined(separator: " · ")) }
                HStack(spacing: 10) {
                    metric("Direct reports", person.directReports)
                    metric("Assignments", person.projectCount)
                    metric("Company assets", person.assignedAssetCount)
                }
                if person.hasManager { recordRow("Reporting line", "Manager record available to authorised People users") }
                Spacer()
                Label("This phone view excludes sensitive employment, payroll, health, performance and personal contact data.", systemImage: "lock.shield")
                    .font(.footnote).foregroundStyle(.secondary)
            }
            .padding(22)
            .navigationTitle("Employee record")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .topBarTrailing) { Button("Done", action: dismiss.callAsFunction) } }
        }
    }

    private func metric(_ label: String, _ value: Int) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text("\(value)").font(.title3.weight(.bold))
            Text(label).font(.caption).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading).padding(12)
        .background(Color(uiColor: .secondarySystemBackground), in: RoundedRectangle(cornerRadius: 14))
    }

    private func recordRow(_ label: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label).font(.caption.weight(.bold)).foregroundStyle(.secondary)
            Text(value).font(.body.weight(.medium))
        }
        .frame(maxWidth: .infinity, alignment: .leading).padding(14)
        .background(Color(uiColor: .secondarySystemBackground), in: RoundedRectangle(cornerRadius: 16))
    }
}
