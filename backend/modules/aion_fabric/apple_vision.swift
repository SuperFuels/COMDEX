import AppKit
import Foundation
import Vision

struct Label: Codable {
    let label: String
    let confidence: Double
}

struct TextObservation: Codable {
    let text: String
    let confidence: Double
    let x: Double
    let y: Double
    let width: Double
    let height: Double
}

struct Output: Codable {
    let texts: [String]
    let textObservations: [TextObservation]
    let labels: [Label]

    enum CodingKeys: String, CodingKey {
        case texts
        case textObservations = "text_observations"
        case labels
    }
}

guard CommandLine.arguments.count == 2 else {
    FileHandle.standardError.write(Data("expected one image path\n".utf8))
    exit(2)
}

let url = URL(fileURLWithPath: CommandLine.arguments[1])
guard let image = NSImage(contentsOf: url),
      let data = image.tiffRepresentation,
      let bitmap = NSBitmapImageRep(data: data),
      let cgImage = bitmap.cgImage else {
    FileHandle.standardError.write(Data("could not decode image\n".utf8))
    exit(3)
}

let textRequest = VNRecognizeTextRequest()
textRequest.recognitionLevel = .accurate
textRequest.usesLanguageCorrection = true
textRequest.recognitionLanguages = ["en-GB", "en-US", "es-ES"]

let classifyRequest = VNClassifyImageRequest()
let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])

do {
    try handler.perform([textRequest, classifyRequest])
    let texts = (textRequest.results ?? []).compactMap { observation in
        observation.topCandidates(1).first?.string
    }
    let textObservations = (textRequest.results ?? []).compactMap { observation -> TextObservation? in
        guard let candidate = observation.topCandidates(1).first else { return nil }
        let box = observation.boundingBox
        return TextObservation(
            text: candidate.string,
            confidence: Double(candidate.confidence),
            x: Double(box.origin.x),
            y: Double(box.origin.y),
            width: Double(box.size.width),
            height: Double(box.size.height)
        )
    }
    let labels = (classifyRequest.results ?? []).prefix(12).map { observation in
        Label(label: observation.identifier, confidence: Double(observation.confidence))
    }
    let encoded = try JSONEncoder().encode(Output(texts: texts, textObservations: textObservations, labels: labels))
    FileHandle.standardOutput.write(encoded)
} catch {
    FileHandle.standardError.write(Data("Vision error: \(error)\n".utf8))
    exit(4)
}
