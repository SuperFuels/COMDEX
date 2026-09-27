import SwiftUI

struct PilotHomeView: View {
    @State private var pairingSheetIsPresented = false
    @State private var trustedInvitation: PilotPairingInvitation?
    @State private var pairingRequestIsPresented = false
    @State private var connection: PilotConnection?

    var body: some View {
        NavigationStack {
            Group {
                if let connection {
                    PilotPulseView(connection: connection) {
                        PilotConnectionStore.remove()
                        self.connection = nil
                    }
                } else if let invitation = trustedInvitation {
                    PilotPairingReview(invitation: invitation) { pairingRequestIsPresented = true }
                } else {
                    PilotWelcome { pairingSheetIsPresented = true }
                }
            }
            .navigationTitle("Tessaris")
            .task { connection = try? PilotConnectionStore.load() }
            .sheet(isPresented: $pairingSheetIsPresented) {
                PilotPairingScanner { invitation in
                    trustedInvitation = invitation
                    pairingSheetIsPresented = false
                }
            }
            .sheet(isPresented: $pairingRequestIsPresented) {
                if let invitation = trustedInvitation {
                    PilotPairingRequest(invitation: invitation, didConnect: { connected in connection = connected; pairingRequestIsPresented = false }, dismiss: { pairingRequestIsPresented = false })
                }
            }
        }
    }
}

private struct PilotWelcome: View {
    let beginPairing: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 22) {
            Spacer()
            Image(systemName: "building.2.crop.circle")
                .font(.system(size: 52))
                .foregroundStyle(.tint)
            Text("Your business, in your hands.").font(.largeTitle.bold())
            Text("Pair this phone with your Tessaris Node to see the Boardroom, approve important actions and receive private updates wherever you are.")
                .foregroundStyle(.secondary)
            Button(action: beginPairing) {
                Label("Pair your Tessaris Node", systemImage: "qrcode.viewfinder")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            Spacer()
            Text("The Node stays under your control. Scanning a code only identifies it; pairing still requires confirmation on the Node.")
                .font(.footnote)
                .foregroundStyle(.secondary)
        }
        .padding(24)
    }
}

private struct PilotPairingReview: View {
    let invitation: PilotPairingInvitation
    let continuePairing: () -> Void

    var body: some View {
        List {
            Section("Tessaris Node verified") {
                LabeledContent("Node", value: invitation.motherID)
                LabeledContent("Address", value: invitation.endpoint.host ?? invitation.endpoint.absoluteString)
                LabeledContent("Expires", value: invitation.expiresAt.formatted(date: .abbreviated, time: .shortened))
            }
            Section("This phone may request") {
                ForEach(invitation.requestedScopes, id: \.self) { scope in
                    Label(scope.replacingOccurrences(of: ".", with: " ").capitalized, systemImage: "checkmark.shield")
                }
            }
            Section {
                Button("Request pairing on this Node", action: continuePairing)
                    .frame(maxWidth: .infinity)
            } footer: {
                Text("The next step creates a one-time confirmation on your Tessaris Node. This phone is not connected yet.")
            }
        }
        .navigationTitle("Review Node")
    }
}

private struct PilotPairingRequest: View {
    let invitation: PilotPairingInvitation
    let didConnect: (PilotConnection) -> Void
    let dismiss: () -> Void
    @State private var deviceLabel = "My iPhone"
    @State private var confirmationCode = ""
    @State private var nodeStatus = "Creating this phone's private pairing key…"
    @State private var hasRequestedPairing = false
    @State private var challenge: [String: Any] = [:]

    var body: some View {
        NavigationStack {
            Form {
                Section("Request sent to your Node") {
                    Text(nodeStatus)
                    TextField("Name this phone", text: $deviceLabel)
                }
                Section("Confirm on the Node") {
                    TextField("Six-digit confirmation", text: $confirmationCode)
                        .keyboardType(.numberPad)
                    Button("Confirm with Face ID") {
                        Task { await completePairing() }
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(!hasRequestedPairing || confirmationCode.count != 6 || deviceLabel.trimmingCharacters(in: .whitespacesAndNewlines).count < 2)
                }
                Section {
                    Text("The phone's private key stays on this device. Tessaris never receives the pairing code or the Node's private key.")
                        .font(.footnote).foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Confirm Node")
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Cancel", action: dismiss) } }
            .task {
                do {
                    let vault = PilotPossessionVault()
                    let client = try PilotNodeClient(invitation: invitation)
                    challenge = try await client.pairingChallenge(personaID: invitation.personaID, deviceLabel: deviceLabel, phonePublicKey: try vault.publicKey(), scopes: invitation.requestedScopes)
                    hasRequestedPairing = true
                    nodeStatus = "A six-digit confirmation is now displayed on \(invitation.motherID)."
                } catch {
                    nodeStatus = "Could not reach this Node securely: \(error.localizedDescription)"
                }
            }
        }
    }

    private func completePairing() async {
        do {
            let vault = PilotPossessionVault()
            let client = try PilotNodeClient(invitation: invitation)
            let result = try await client.completePairing(challenge: challenge, confirmationCode: confirmationCode, vault: vault)
            let data = try JSONSerialization.data(withJSONObject: result)
            let typed = try JSONDecoder().decode([String: AnyCodable].self, from: data)
            guard let certificate = typed["certificate"]?.objectValue, let lease = typed["lease"]?.objectValue else { throw PilotNodeClient.ClientError.invalidResponse }
            let connection = PilotConnection(motherID: invitation.motherID, endpoint: invitation.endpoint, motherFingerprint: invitation.motherFingerprint, certificateSHA256: invitation.certificateSHA256, certificatePEM: invitation.certificatePEM, certificate: certificate, lease: lease)
            try PilotConnectionStore.save(connection)
            didConnect(connection)
            nodeStatus = "This phone is securely connected to \(invitation.motherID)."
        } catch {
            nodeStatus = "Pairing was not completed. Check the code on your Node and try again."
        }
    }
}

private extension AnyCodable { var objectValue: [String: AnyCodable]? { if case .object(let value) = self { value } else { nil } } }
