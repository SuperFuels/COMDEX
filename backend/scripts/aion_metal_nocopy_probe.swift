import Foundation
import Metal
import Darwin

struct Trial: Codable {
    let condition: String
    let sequence: Int
    let bufferCreationMilliseconds: Double
    let gpuFullScanMilliseconds: Double
    let totalMilliseconds: Double
    let checksum: UInt32
}

struct ConditionSummary: Codable {
    let samples: Int
    let creationMedianMilliseconds: Double
    let creationP95Milliseconds: Double
    let scanMedianMilliseconds: Double
    let scanP95Milliseconds: Double
    let totalMedianMilliseconds: Double
    let totalP95Milliseconds: Double
}

struct Report: Codable {
    let schemaVersion: String
    let path: String
    let fileBytes: Int
    let mappedBytes: Int
    let device: String
    let trials: [Trial]
    let summaries: [String: ConditionSummary]
    let checksumsExact: Bool
    let claimBoundary: String
}

func milliseconds(_ start: ContinuousClock.Instant, _ end: ContinuousClock.Instant) -> Double {
    let duration = start.duration(to: end)
    return Double(duration.components.seconds) * 1_000.0
        + Double(duration.components.attoseconds) / 1.0e15
}

guard (3...4).contains(CommandLine.arguments.count), let iterations = Int(CommandLine.arguments[2]), iterations > 0 else {
    fputs("usage: aion_metal_nocopy_probe <file> <iterations> [output.json]\n", stderr)
    exit(64)
}
let path = CommandLine.arguments[1]
let descriptor = open(path, O_RDONLY)
guard descriptor >= 0 else { perror("open"); exit(1) }
defer { close(descriptor) }
var info = stat()
guard fstat(descriptor, &info) == 0 else { perror("fstat"); exit(1) }
let fileBytes = Int(info.st_size)
let pageBytes = Int(getpagesize())
let mappedBytes = ((fileBytes + pageBytes - 1) / pageBytes) * pageBytes
guard let mapped = mmap(nil, mappedBytes, PROT_READ, MAP_PRIVATE, descriptor, 0), mapped != MAP_FAILED else {
    perror("mmap"); exit(1)
}
defer { munmap(mapped, mappedBytes) }

guard let device = MTLCreateSystemDefaultDevice(), let queue = device.makeCommandQueue() else {
    fputs("Metal device unavailable\n", stderr); exit(1)
}
let shader = """
#include <metal_stdlib>
using namespace metal;
kernel void xor_scan(
    device const uint *input [[buffer(0)]],
    device atomic_uint *output [[buffer(1)]],
    constant uint &word_count [[buffer(2)]],
    uint position [[thread_position_in_grid]],
    uint grid_width [[threads_per_grid]]) {
    uint local = 0;
    for (uint index = position; index < word_count; index += grid_width) {
        local ^= input[index];
    }
    atomic_fetch_xor_explicit(output, local, memory_order_relaxed);
}
"""
let library = try device.makeLibrary(source: shader, options: nil)
guard let function = library.makeFunction(name: "xor_scan") else { exit(1) }
let pipeline = try device.makeComputePipelineState(function: function)

func scan(_ buffer: MTLBuffer) -> (Double, UInt32) {
    let output = device.makeBuffer(length: MemoryLayout<UInt32>.size, options: .storageModeShared)!
    output.contents().storeBytes(of: UInt32(0), as: UInt32.self)
    var words = UInt32(fileBytes / MemoryLayout<UInt32>.size)
    let command = queue.makeCommandBuffer()!
    let encoder = command.makeComputeCommandEncoder()!
    encoder.setComputePipelineState(pipeline)
    encoder.setBuffer(buffer, offset: 0, index: 0)
    encoder.setBuffer(output, offset: 0, index: 1)
    encoder.setBytes(&words, length: MemoryLayout<UInt32>.size, index: 2)
    let grid = MTLSize(width: 8192, height: 1, depth: 1)
    let group = MTLSize(width: min(256, pipeline.maxTotalThreadsPerThreadgroup), height: 1, depth: 1)
    let started = ContinuousClock.now
    encoder.dispatchThreads(grid, threadsPerThreadgroup: group)
    encoder.endEncoding()
    command.commit()
    command.waitUntilCompleted()
    let elapsed = milliseconds(started, ContinuousClock.now)
    if command.status != .completed { fputs("Metal scan failed\n", stderr); exit(1) }
    return (elapsed, output.contents().load(as: UInt32.self))
}

var trials: [Trial] = []
let order = Array(repeating: ["copied", "nocopy", "nocopy", "copied"], count: iterations).flatMap { $0 }
for (sequence, condition) in order.enumerated() {
    autoreleasepool {
        let creationStart = ContinuousClock.now
        let buffer: MTLBuffer?
        if condition == "nocopy" {
            buffer = device.makeBuffer(
                bytesNoCopy: mapped, length: mappedBytes,
                options: .storageModeShared, deallocator: nil
            )
        } else {
            buffer = device.makeBuffer(bytes: mapped, length: fileBytes, options: .storageModeShared)
        }
        let creation = milliseconds(creationStart, ContinuousClock.now)
        guard let buffer else { fputs("Metal buffer creation failed\n", stderr); exit(1) }
        let (scanTime, checksum) = scan(buffer)
        trials.append(Trial(
            condition: condition, sequence: sequence,
            bufferCreationMilliseconds: creation, gpuFullScanMilliseconds: scanTime,
            totalMilliseconds: creation + scanTime, checksum: checksum
        ))
    }
}
func median(_ values: [Double]) -> Double {
    let values = values.sorted()
    let middle = values.count / 2
    return values.count % 2 == 0 ? (values[middle - 1] + values[middle]) / 2 : values[middle]
}
func p95(_ values: [Double]) -> Double {
    let values = values.sorted()
    return values[max(0, Int(ceil(0.95 * Double(values.count))) - 1)]
}
let summaries = Dictionary(uniqueKeysWithValues: ["copied", "nocopy"].map { condition in
    let selected = trials.filter { $0.condition == condition }
    let creation = selected.map { $0.bufferCreationMilliseconds }
    let scan = selected.map { $0.gpuFullScanMilliseconds }
    let total = selected.map { $0.totalMilliseconds }
    return (condition, ConditionSummary(
        samples: selected.count,
        creationMedianMilliseconds: median(creation), creationP95Milliseconds: p95(creation),
        scanMedianMilliseconds: median(scan), scanP95Milliseconds: p95(scan),
        totalMedianMilliseconds: median(total), totalP95Milliseconds: p95(total)
    ))
})
let report = Report(
    schemaVersion: "aion.metal_nocopy_probe.v1", path: path,
    fileBytes: fileBytes, mappedBytes: mappedBytes, device: device.name,
    trials: trials, summaries: summaries,
    checksumsExact: Set(trials.map { $0.checksum }).count == 1,
    claimBoundary: "Warm-uncontrolled single-file Metal microbenchmark. GPU scans all complete UInt32 words. It proves byte access and buffer-construction cost only, not model integration, expert-matmul speed, token equivalence, physical cold-SD bandwidth or end-to-end generation latency."
)
let encoder = JSONEncoder()
encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
var encoded = try encoder.encode(report)
encoded.append(Data("\n".utf8))
if CommandLine.arguments.count == 4 {
    try encoded.write(to: URL(fileURLWithPath: CommandLine.arguments[3]), options: .withoutOverwriting)
}
FileHandle.standardOutput.write(encoded)
