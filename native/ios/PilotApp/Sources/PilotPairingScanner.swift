import AVFoundation
import Foundation
import SwiftUI
import UIKit

struct PilotPairingScanner: View {
    let didVerifyInvitation: (PilotPairingInvitation) -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            ZStack(alignment: .bottom) {
                PilotQRCodeCamera { code in
                    guard errorMessage == nil else { return }
                    Task {
                        do {
                            let invitationData = try await invitationPayload(from: code)
                            didVerifyInvitation(try PilotPairingInvitation.verify(invitationData))
                        } catch let error as PilotPairingInvitation.VerificationError {
                            errorMessage = error.localizedDescription
                        } catch {
                            errorMessage = "This is not a valid Tessaris Node invitation."
                        }
                    }
                }
                .ignoresSafeArea()

                VStack(spacing: 12) {
                    Image(systemName: "qrcode.viewfinder").font(.title)
                    Text("Scan the code shown by your Tessaris Node").font(.headline)
                    Text("Tessaris checks the Node signature before it connects your phone.")
                        .font(.footnote)
                        .multilineTextAlignment(.center)
                }
                .padding()
                .frame(maxWidth: .infinity)
                .background(.regularMaterial)
            }
            .navigationTitle("Pair Tessaris Node")
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Cancel", action: dismiss.callAsFunction) } }
            .alert("Cannot use this code", isPresented: Binding(
                get: { errorMessage != nil }, set: { if !$0 { errorMessage = nil } }
            )) {
                Button("Scan another code") { errorMessage = nil }
                Button("Cancel", role: .cancel, action: dismiss.callAsFunction)
            } message: {
                Text(errorMessage ?? "")
            }
        }
    }

    /// Full signed invitations include the Node's pinned local certificate and
    /// can exceed a physical QR symbol.  A QR may therefore contain a short
    /// local invitation URL.  Its response is still verified locally before
    /// the phone trusts or contacts the Node, so this fetch grants no access.
    private func invitationPayload(from code: String) async throws -> Data {
        guard let url = URL(string: code), url.scheme == "http", let host = url.host else {
            return Data(code.utf8)
        }
        guard isLocalInvitationHost(host) else {
            throw PilotPairingInvitation.VerificationError.malformed
        }
        var components = URLComponents(url: url, resolvingAgainstBaseURL: false)
        var items = components?.queryItems ?? []
        items.append(URLQueryItem(name: "scan", value: UUID().uuidString))
        components?.queryItems = items
        guard let freshURL = components?.url else {
            throw PilotPairingInvitation.VerificationError.malformed
        }
        var request = URLRequest(url: freshURL)
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.setValue("no-cache", forHTTPHeaderField: "Cache-Control")
        let session = URLSession(configuration: .ephemeral)
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse,
              (200..<300).contains(http.statusCode),
              data.count > 0, data.count <= 20_000 else {
            throw PilotPairingInvitation.VerificationError.malformed
        }
        return data
    }

    private func isLocalInvitationHost(_ host: String) -> Bool {
        let parts = host.split(separator: ".").compactMap { UInt8($0) }
        if parts.count == 4 {
            return parts[0] == 10
                || (parts[0] == 172 && (16...31).contains(parts[1]))
                || (parts[0] == 192 && parts[1] == 168)
                || (parts[0] == 169 && parts[1] == 254)
        }
        return host == "localhost" || host.hasSuffix(".local")
    }
}

private struct PilotQRCodeCamera: UIViewControllerRepresentable {
    let didScan: (String) -> Void

    func makeCoordinator() -> Coordinator { Coordinator(didScan: didScan) }

    func makeUIViewController(context: Context) -> QRCodeCameraController {
        let controller = QRCodeCameraController()
        controller.didScan = context.coordinator.didScan
        return controller
    }

    func updateUIViewController(_ uiViewController: QRCodeCameraController, context: Context) {}

    final class Coordinator {
        let didScan: (String) -> Void
        init(didScan: @escaping (String) -> Void) { self.didScan = didScan }
    }
}

private final class QRCodeCameraController: UIViewController, AVCaptureMetadataOutputObjectsDelegate {
    var didScan: ((String) -> Void)?
    private let captureSession = AVCaptureSession()
    private var previewLayer: AVCaptureVideoPreviewLayer?
    private var hasReportedCode = false

    override func viewDidLoad() {
        super.viewDidLoad()
        guard let device = AVCaptureDevice.default(for: .video),
              let input = try? AVCaptureDeviceInput(device: device),
              captureSession.canAddInput(input) else { return }
        captureSession.addInput(input)
        let output = AVCaptureMetadataOutput()
        guard captureSession.canAddOutput(output) else { return }
        captureSession.addOutput(output)
        output.setMetadataObjectsDelegate(self, queue: .main)
        output.metadataObjectTypes = [.qr]
        let previewLayer = AVCaptureVideoPreviewLayer(session: captureSession)
        previewLayer.videoGravity = .resizeAspectFill
        view.layer.addSublayer(previewLayer)
        self.previewLayer = previewLayer
        DispatchQueue.global(qos: .userInitiated).async { [captureSession] in captureSession.startRunning() }
    }

    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        previewLayer?.frame = view.bounds
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        captureSession.stopRunning()
    }

    func metadataOutput(_ output: AVCaptureMetadataOutput, didOutput metadataObjects: [AVMetadataObject], from connection: AVCaptureConnection) {
        guard !hasReportedCode,
              let code = metadataObjects.first as? AVMetadataMachineReadableCodeObject,
              let value = code.stringValue else { return }
        hasReportedCode = true
        didScan?(value)
    }
}
