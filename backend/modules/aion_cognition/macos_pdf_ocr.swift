import AppKit
import Foundation
import PDFKit
import Vision

guard CommandLine.arguments.count >= 3,
      let document = PDFDocument(url: URL(fileURLWithPath: CommandLine.arguments[1])),
      let requestedPages = Int(CommandLine.arguments[2]) else {
    fputs("invalid_pdf_or_arguments\n", stderr)
    exit(2)
}

let pageLimit = min(document.pageCount, max(1, requestedPages))
var pages: [String] = []

for pageIndex in 0..<pageLimit {
    guard let page = document.page(at: pageIndex) else {
        pages.append("")
        continue
    }
    let bounds = page.bounds(for: .mediaBox)
    let scale = min(4.0, max(1.5, 2200.0 / max(bounds.width, 1.0)))
    let pixelSize = NSSize(width: bounds.width * scale, height: bounds.height * scale)
    let image = page.thumbnail(of: pixelSize, for: .mediaBox)
    guard let tiff = image.tiffRepresentation,
          let bitmap = NSBitmapImageRep(data: tiff),
          let cgImage = bitmap.cgImage else {
        pages.append("")
        continue
    }
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    request.recognitionLanguages = ["en-GB", "en-US"]
    do {
        try VNImageRequestHandler(cgImage: cgImage, options: [:]).perform([request])
        let observations = (request.results ?? []).sorted {
            if abs($0.boundingBox.midY - $1.boundingBox.midY) > 0.015 {
                return $0.boundingBox.midY > $1.boundingBox.midY
            }
            return $0.boundingBox.minX < $1.boundingBox.minX
        }
        pages.append(observations.compactMap { $0.topCandidates(1).first?.string }.joined(separator: "\n"))
    } catch {
        pages.append("")
    }
}

let payload: [String: Any] = ["pages": pages, "page_count": document.pageCount]
let data = try JSONSerialization.data(withJSONObject: payload, options: [])
FileHandle.standardOutput.write(data)
