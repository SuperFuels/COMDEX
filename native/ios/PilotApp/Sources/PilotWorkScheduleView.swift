import SwiftUI
import PhotosUI

struct PilotWorkScheduleView: View {
    let connection: PilotConnection

    @State private var membershipID = ""
    @State private var jobs: [PilotWorkJob] = []
    @State private var selectedDay = Calendar.current.startOfDay(for: Date())
    @State private var selectedJob: PilotWorkJob?
    @State private var showingNewJob = false
    @State private var loading = true
    @State private var message = ""

    private let vault = PilotPossessionVault()

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 5) {
                    Text("WORK & SCHEDULE").font(.caption.weight(.bold)).tracking(1.5).foregroundStyle(.teal)
                    Text("Jobs, visits and appointments").font(.title2.weight(.bold))
                    Text("See what is booked, update the live record and keep the office informed.")
                        .font(.subheadline).foregroundStyle(.secondary)
                }
                Spacer()
                Button { showingNewJob = true } label: {
                    Image(systemName: "plus").font(.headline).frame(width: 40, height: 40)
                }
                .buttonStyle(.borderedProminent).tint(.teal)
                .accessibilityLabel("Create job")
            }

            weekStrip

            if loading {
                ProgressView("Loading the shared schedule…").frame(maxWidth: .infinity, alignment: .leading)
            } else if !message.isEmpty {
                Label(message, systemImage: "exclamationmark.triangle.fill")
                    .font(.footnote).foregroundStyle(.orange)
            }

            HStack(spacing: 10) {
                summaryCard("Today", value: "\(jobsToday.count)", icon: "calendar")
                summaryCard("In progress", value: "\(jobs.filter { $0.status == "in_progress" }.count)", icon: "hammer.fill")
                summaryCard("To finish", value: "\(jobs.filter { $0.status != "completed" }.count)", icon: "checklist")
            }

            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Text(dayTitle).font(.headline)
                    Spacer()
                    Text("\(jobsForSelectedDay.count) booked").font(.caption.weight(.semibold)).foregroundStyle(.secondary)
                }
                if jobsForSelectedDay.isEmpty {
                    emptySchedule
                } else {
                    ForEach(jobsForSelectedDay) { job in
                        Button { selectedJob = job } label: { jobCard(job) }
                            .buttonStyle(.plain)
                    }
                }
            }

            VStack(alignment: .leading, spacing: 10) {
                Text("All open work").font(.headline)
                ForEach(jobs.filter { $0.status != "completed" }.prefix(12)) { job in
                    Button { selectedJob = job } label: { compactJobRow(job) }.buttonStyle(.plain)
                }
            }
        }
        .task { await load() }
        .refreshable { await load() }
        .sheet(isPresented: $showingNewJob) {
            PilotNewWorkJobView { fields in await create(fields) }
        }
        .sheet(item: $selectedJob) { job in
            PilotWorkJobDetailView(
                job: job,
                save: { fields in await update(jobID: job.id, fields: fields) },
                action: { operation, fields in
                    var values = fields; values["id"] = job.id
                    return await act(operation: operation, fields: values)
                },
                upload: { data, filename, contentType in await upload(jobID: job.id, data: data, filename: filename, contentType: contentType) }
            )
        }
    }

    private var weekStrip: some View {
        HStack(spacing: 6) {
            ForEach(0..<7, id: \.self) { offset in
                let date = Calendar.current.date(byAdding: .day, value: offset, to: Calendar.current.startOfDay(for: Date())) ?? Date()
                let selected = Calendar.current.isDate(date, inSameDayAs: selectedDay)
                Button { selectedDay = date } label: {
                    VStack(spacing: 4) {
                        Text(date.formatted(.dateTime.weekday(.narrow))).font(.caption2.weight(.bold))
                        Text(date.formatted(.dateTime.day())).font(.headline)
                        Circle().fill(hasJob(on: date) ? Color.teal : Color.clear).frame(width: 4, height: 4)
                    }
                    .frame(maxWidth: .infinity).padding(.vertical, 9)
                    .foregroundStyle(selected ? .white : .primary)
                    .background(selected ? Color.teal : Color.white, in: RoundedRectangle(cornerRadius: 12))
                }.buttonStyle(.plain)
            }
        }
    }

    private var emptySchedule: some View {
        Button { showingNewJob = true } label: {
            VStack(spacing: 8) {
                Image(systemName: "calendar.badge.plus").font(.title).foregroundStyle(.teal)
                Text("Nothing booked").font(.headline)
                Text("Tap to add a job or appointment").font(.caption).foregroundStyle(.secondary)
            }.frame(maxWidth: .infinity).padding(24)
                .background(Color.white, in: RoundedRectangle(cornerRadius: 16))
        }.buttonStyle(.plain)
    }

    private func summaryCard(_ label: String, value: String, icon: String) -> some View {
        VStack(alignment: .leading, spacing: 7) {
            Image(systemName: icon).foregroundStyle(.teal)
            Text(value).font(.title2.bold())
            Text(label).font(.caption2).foregroundStyle(.secondary).lineLimit(1)
        }.frame(maxWidth: .infinity, alignment: .leading).padding(12)
            .background(Color.white, in: RoundedRectangle(cornerRadius: 14))
    }

    private func jobCard(_ job: PilotWorkJob) -> some View {
        HStack(spacing: 12) {
            VStack(spacing: 2) {
                Text(job.startDate.formatted(.dateTime.hour().minute())).font(.subheadline.bold())
                Image(systemName: job.statusIcon).foregroundStyle(job.statusColor)
            }.frame(width: 62)
            Rectangle().fill(job.statusColor).frame(width: 4).clipShape(Capsule())
            VStack(alignment: .leading, spacing: 4) {
                Text(job.title).font(.headline).foregroundStyle(.primary)
                Text([job.customer, job.location].filter { !$0.isEmpty }.joined(separator: " · "))
                    .font(.caption).foregroundStyle(.secondary).lineLimit(2)
                if !job.assignee.isEmpty { Label(job.assignee, systemImage: "person.fill").font(.caption2).foregroundStyle(.secondary) }
            }
            Spacer()
            Image(systemName: "chevron.right").foregroundStyle(.tertiary)
        }.padding(14).background(Color.white, in: RoundedRectangle(cornerRadius: 16))
    }

    private func compactJobRow(_ job: PilotWorkJob) -> some View {
        HStack(spacing: 12) {
            Image(systemName: job.statusIcon).foregroundStyle(job.statusColor).frame(width: 28)
            VStack(alignment: .leading, spacing: 2) {
                Text(job.title).font(.subheadline.weight(.semibold)).foregroundStyle(.primary)
                Text(job.startDate.formatted(date: .abbreviated, time: .shortened) + (job.assignee.isEmpty ? "" : " · " + job.assignee))
                    .font(.caption).foregroundStyle(.secondary)
            }
            Spacer()
            Text(job.statusLabel).font(.caption2.weight(.bold)).foregroundStyle(job.statusColor)
        }.padding(12).background(Color.white, in: RoundedRectangle(cornerRadius: 14))
    }

    private var jobsToday: [PilotWorkJob] { jobs.filter { Calendar.current.isDateInToday($0.startDate) } }
    private var jobsForSelectedDay: [PilotWorkJob] { jobs.filter { Calendar.current.isDate($0.startDate, inSameDayAs: selectedDay) }.sorted { $0.startDate < $1.startDate } }
    private var dayTitle: String { selectedDay.formatted(.dateTime.weekday(.wide).day().month(.wide)) }
    private func hasJob(on date: Date) -> Bool { jobs.contains { Calendar.current.isDate($0.startDate, inSameDayAs: date) } }

    @MainActor private func load() async {
        loading = true; message = ""
        defer { loading = false }
        do {
            let client = try PilotNodeClient(connection: connection)
            let spaces = try await client.workspaceSpaces(connection: connection, vault: vault)
            guard let first = (spaces["spaces"] as? [[String: Any]])?.first,
                  let membership = first["membership"] as? [String: Any],
                  let id = membership["membership_id"] as? String else { throw PilotNodeClient.ClientError.invalidResponse }
            membershipID = id
            let result = try await client.workScheduleSnapshot(membershipID: id, connection: connection, vault: vault)
            accept(result)
        } catch { message = "The shared schedule is not available yet. \(error.localizedDescription)" }
    }

    @MainActor private func create(_ fields: [String: Any]) async -> Bool { await act(operation: "create", fields: fields) }
    @MainActor private func update(jobID: String, fields: [String: Any]) async -> Bool {
        var values = fields; values["id"] = jobID
        return await act(operation: "update", fields: values)
    }
    @MainActor private func upload(jobID: String, data: Data, filename: String, contentType: String) async -> Bool {
        await act(operation: "upload_evidence", fields: [
            "id": jobID, "filename": filename, "content_type": contentType,
            "data_base64": data.base64EncodedString(),
        ])
    }
    @MainActor private func act(operation: String, fields: [String: Any]) async -> Bool {
        guard !membershipID.isEmpty else { message = "Reconnect to the workspace and try again."; return false }
        do {
            let client = try PilotNodeClient(connection: connection)
            let result = try await client.workScheduleAction(membershipID: membershipID, operation: operation, fields: fields, connection: connection, vault: vault)
            accept(result); message = ""; return true
        } catch { message = "That change was not saved. \(error.localizedDescription)"; return false }
    }
    @MainActor private func accept(_ result: [String: Any]) {
        guard let schedule = result["schedule"] as? [String: Any] else { return }
        jobs = (schedule["jobs"] as? [[String: Any]] ?? []).compactMap(PilotWorkJob.init)
    }
}

private struct PilotWorkJob: Identifiable {
    let id: String
    let title: String
    let customer: String
    let location: String
    let startsAt: String
    let endsAt: String
    let assignee: String
    let status: String
    let notes: String
    let evidenceCount: Int
    let checklist: [PilotWorkChecklist]
    let materials: [PilotWorkMaterial]
    let timeEntries: [PilotWorkTimeEntry]

    init?(_ value: [String: Any]) {
        guard let id = value["id"] as? String, let title = value["title"] as? String else { return nil }
        self.id = id; self.title = title
        customer = value["customer"] as? String ?? ""; location = value["location"] as? String ?? ""
        startsAt = value["starts_at"] as? String ?? ""; endsAt = value["ends_at"] as? String ?? ""
        assignee = value["assignee"] as? String ?? ""; status = value["status"] as? String ?? "scheduled"
        notes = value["notes"] as? String ?? ""; evidenceCount = value["evidence_count"] as? Int ?? 0
        checklist = (value["checklist"] as? [[String: Any]] ?? []).compactMap(PilotWorkChecklist.init)
        materials = (value["materials"] as? [[String: Any]] ?? []).compactMap(PilotWorkMaterial.init)
        timeEntries = (value["time_entries"] as? [[String: Any]] ?? []).compactMap(PilotWorkTimeEntry.init)
    }
    var startDate: Date { ISO8601DateFormatter().date(from: startsAt) ?? Date.distantPast }
    var statusLabel: String { status.replacingOccurrences(of: "_", with: " ").capitalized }
    var statusIcon: String { status == "completed" ? "checkmark.circle.fill" : status == "in_progress" ? "hammer.fill" : status == "on_way" ? "car.fill" : "clock.fill" }
    var statusColor: Color { status == "completed" ? .green : status == "in_progress" ? .orange : status == "on_way" ? .blue : .teal }
}

private struct PilotWorkChecklist: Identifiable {
    let id: String; let label: String; let done: Bool
    init?(_ value: [String: Any]) {
        guard let id = value["id"] as? String, let label = value["label"] as? String else { return nil }
        self.id = id; self.label = label; done = value["done"] as? Bool ?? false
    }
}

private struct PilotWorkMaterial: Identifiable {
    let id: String; let name: String; let quantity: Double; let unit: String; let used: Bool
    init?(_ value: [String: Any]) {
        guard let id = value["id"] as? String, let name = value["name"] as? String else { return nil }
        self.id = id; self.name = name; quantity = (value["quantity"] as? NSNumber)?.doubleValue ?? 0
        unit = value["unit"] as? String ?? "item"; used = value["used"] as? Bool ?? false
    }
}

private struct PilotWorkTimeEntry: Identifiable {
    let id: String; let minutes: Int; let note: String
    init?(_ value: [String: Any]) {
        guard let id = value["id"] as? String else { return nil }
        self.id = id; minutes = (value["minutes"] as? NSNumber)?.intValue ?? 0; note = value["note"] as? String ?? ""
    }
}

private struct PilotNewWorkJobView: View {
    let save: ([String: Any]) async -> Bool
    @Environment(\.dismiss) private var dismiss
    @State private var title = ""; @State private var customer = ""; @State private var location = ""; @State private var assignee = ""
    @State private var startsAt = Calendar.current.date(byAdding: .hour, value: 1, to: Date()) ?? Date()
    @State private var saving = false

    var body: some View {
        NavigationStack {
            Form {
                Section("Job or appointment") {
                    TextField("What needs doing?", text: $title)
                    TextField("Customer", text: $customer)
                    TextField("Location", text: $location)
                    TextField("Assign to", text: $assignee)
                    DatePicker("Starts", selection: $startsAt)
                }
                Section { Text("You can add notes, evidence and update progress after creating the record.").font(.footnote).foregroundStyle(.secondary) }
            }
            .navigationTitle("New work")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button(saving ? "Saving…" : "Create") { Task { saving = true; if await save(fields) { dismiss() }; saving = false } }
                        .disabled(title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || saving)
                }
            }
        }
    }
    private var fields: [String: Any] { ["title": title, "customer": customer, "location": location, "assignee": assignee, "starts_at": ISO8601DateFormatter().string(from: startsAt), "status": "scheduled"] }
}

private struct PilotWorkJobDetailView: View {
    let job: PilotWorkJob
    let save: ([String: Any]) async -> Bool
    let action: (String, [String: Any]) async -> Bool
    let upload: (Data, String, String) async -> Bool
    @Environment(\.dismiss) private var dismiss
    @Environment(\.openURL) private var openURL
    @State private var notes: String
    @State private var assignee: String
    @State private var saving = false
    @State private var evidenceItem: PhotosPickerItem?
    @State private var uploadingEvidence = false
    @State private var checklistLabel = ""
    @State private var materialName = ""
    @State private var timeMinutes = ""
    @State private var timeNote = ""

    init(
        job: PilotWorkJob,
        save: @escaping ([String: Any]) async -> Bool,
        action: @escaping (String, [String: Any]) async -> Bool,
        upload: @escaping (Data, String, String) async -> Bool
    ) {
        self.job = job; self.save = save; self.action = action; self.upload = upload
        _notes = State(initialValue: job.notes); _assignee = State(initialValue: job.assignee)
    }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Text(job.title).font(.title2.bold())
                    if !job.customer.isEmpty { Label(job.customer, systemImage: "person.fill") }
                    if !job.location.isEmpty {
                        Button { openRoute() } label: { Label(job.location, systemImage: "map.fill") }
                    }
                    Label(job.startDate.formatted(date: .long, time: .shortened), systemImage: "calendar")
                }
                Section("Progress") {
                    HStack {
                        statusButton("On way", icon: "car.fill", value: "on_way")
                        statusButton("Start", icon: "hammer.fill", value: "in_progress")
                        statusButton("Complete", icon: "checkmark.circle.fill", value: "completed")
                    }
                }
                Section("Assignment") { TextField("Person or team", text: $assignee) }
                Section("Checklist") {
                    ForEach(job.checklist) { row in
                        Button {
                            Task { _ = await action("checklist", ["checklist_id": row.id, "done": !row.done]) }
                        } label: {
                            Label(row.label, systemImage: row.done ? "checkmark.circle.fill" : "circle")
                                .foregroundStyle(row.done ? .green : .primary)
                        }
                    }
                    HStack {
                        TextField("Add checklist step", text: $checklistLabel)
                        Button("Add") { Task { if await action("add_checklist", ["label": checklistLabel]) { checklistLabel = "" } } }
                            .disabled(checklistLabel.trimmingCharacters(in: .whitespaces).isEmpty)
                    }
                }
                Section("Materials") {
                    ForEach(job.materials) { row in
                        HStack {
                            Image(systemName: row.used ? "checkmark.square.fill" : "square").foregroundStyle(row.used ? .green : .secondary)
                            Text(row.name); Spacer(); Text("\(row.quantity, specifier: "%g") \(row.unit)").foregroundStyle(.secondary)
                        }
                    }
                    HStack {
                        TextField("Material", text: $materialName)
                        Button("Add") { Task { if await action("add_material", ["name": materialName, "quantity": 1, "unit": "item"]) { materialName = "" } } }
                            .disabled(materialName.trimmingCharacters(in: .whitespaces).isEmpty)
                    }
                }
                Section("Time") {
                    ForEach(job.timeEntries) { row in HStack { Text(row.note.isEmpty ? "Work time" : row.note); Spacer(); Text("\(row.minutes) min").foregroundStyle(.secondary) } }
                    TextField("Minutes", text: $timeMinutes).keyboardType(.numberPad)
                    TextField("What was the time for?", text: $timeNote)
                    Button("Add time entry") { Task { if let minutes = Int(timeMinutes), await action("add_time", ["minutes": minutes, "note": timeNote]) { timeMinutes = ""; timeNote = "" } } }
                        .disabled((Int(timeMinutes) ?? 0) <= 0)
                }
                Section("Job record") {
                    TextEditor(text: $notes).frame(minHeight: 110)
                    PhotosPicker(selection: $evidenceItem, matching: .images) {
                        Label(uploadingEvidence ? "Uploading…" : "Add photo evidence", systemImage: "camera.fill")
                    }
                    .disabled(uploadingEvidence)
                    .onChange(of: evidenceItem) { _, item in
                        guard let item else { return }
                        Task {
                            uploadingEvidence = true
                            defer { uploadingEvidence = false; evidenceItem = nil }
                            guard let data = try? await item.loadTransferable(type: Data.self) else { return }
                            _ = await upload(data, "Photo \(Date().ISO8601Format()).jpg", "image/jpeg")
                        }
                    }
                    if job.evidenceCount > 0 { Label("Evidence stored: \(job.evidenceCount)", systemImage: "checkmark.seal.fill").foregroundStyle(.green) }
                    Label("Notes, assignment, progress and photo evidence update the same record used by the office.", systemImage: "arrow.triangle.2.circlepath").font(.footnote).foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Work record").navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Close") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button(saving ? "Saving…" : "Save") { Task { saving = true; if await save(["notes": notes, "assignee": assignee]) { dismiss() }; saving = false } }.disabled(saving)
                }
            }
        }
    }

    private func statusButton(_ label: String, icon: String, value: String) -> some View {
        Button { Task { if await save(["status": value]) { dismiss() } } } label: {
            VStack(spacing: 6) { Image(systemName: icon); Text(label).font(.caption2.weight(.semibold)) }
                .frame(maxWidth: .infinity).padding(.vertical, 10)
        }.buttonStyle(.bordered).tint(value == "completed" ? .green : .teal)
    }

    private func openRoute() {
        guard let encoded = job.location.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed),
              let url = URL(string: "https://www.google.com/maps/dir/?api=1&destination=\(encoded)") else { return }
        openURL(url)
    }
}
