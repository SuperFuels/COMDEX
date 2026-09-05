import SwiftUI

struct PilotHomeView: View {
    @State private var mode = "Personal"
    @State private var prompt = ""

    var body: some View {
        NavigationStack {
            VStack(spacing: 16) {
                Picker("Space", selection: $mode) {
                    Text("Personal").tag("Personal")
                    Text("Workspace").tag("Workspace")
                    Text("Boardroom").tag("Boardroom")
                }.pickerStyle(.segmented)
                ScrollView(.horizontal) {
                    HStack { ForEach(["Inbox", "Tasks", "Calendar", "TV", "Files", "Devices"], id: \.self) { Text($0).padding(10).background(.thinMaterial).clipShape(Capsule()) } }
                }.scrollIndicators(.hidden)
                Spacer()
                Text("Your private Pilot connects directly to the mother you own.").multilineTextAlignment(.center)
                Spacer()
                HStack {
                    TextField("Ask Pilot…", text: $prompt).textFieldStyle(.roundedBorder)
                    Button("Send") { prompt = "" }.buttonStyle(.borderedProminent)
                }
            }
            .padding()
            .navigationTitle("Pilot")
            .privacySensitive()
        }
    }
}
