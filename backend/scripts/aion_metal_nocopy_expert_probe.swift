import Foundation
import Metal
import Darwin

struct Trial: Codable {
    let condition: String
    let sequence: Int
    let creationMilliseconds: Double
    let expertKernelMilliseconds: Double
    let totalMilliseconds: Double
    let outputFNV1a64: String
}

struct Summary: Codable {
    let samples: Int
    let creationMedianMilliseconds: Double
    let creationP95Milliseconds: Double
    let kernelMedianMilliseconds: Double
    let kernelP95Milliseconds: Double
    let totalMedianMilliseconds: Double
    let totalP95Milliseconds: Double
}

struct Report: Codable {
    let schemaVersion: String
    let path: String
    let fileBytes: Int
    let expert: Int
    let expertBytes: Int
    let inputWeightShape: [Int]
    let outputWeightShape: [Int]
    let device: String
    let inputFNV1a64: String
    let summaries: [String: Summary]
    let trials: [Trial]
    let outputsBitExact: Bool
    let claimBoundary: String
}

func ms(_ start: ContinuousClock.Instant, _ end: ContinuousClock.Instant) -> Double {
    let d = start.duration(to: end)
    return Double(d.components.seconds) * 1000 + Double(d.components.attoseconds) / 1.0e15
}
func median(_ values: [Double]) -> Double {
    let v = values.sorted(), m = v.count / 2
    return v.count % 2 == 0 ? (v[m - 1] + v[m]) / 2 : v[m]
}
func p95(_ values: [Double]) -> Double {
    let v = values.sorted(); return v[max(0, Int(ceil(Double(v.count) * 0.95)) - 1)]
}
func fnv1a(_ values: [UInt16]) -> String {
    var hash: UInt64 = 14695981039346656037
    for value in values {
        hash ^= UInt64(value & 0xff); hash &*= 1099511628211
        hash ^= UInt64(value >> 8); hash &*= 1099511628211
    }
    return String(format: "%016llx", hash)
}

guard (4...5).contains(CommandLine.arguments.count),
      let expert = Int(CommandLine.arguments[2]),
      let iterations = Int(CommandLine.arguments[3]), iterations > 0 else {
    fputs("usage: aion_metal_nocopy_expert_probe <fp16-layer-pack> <expert> <iterations> [output.json]\n", stderr)
    exit(64)
}
let path = CommandLine.arguments[1]
let fd = open(path, O_RDONLY)
guard fd >= 0 else { perror("open"); exit(1) }
defer { close(fd) }
var statInfo = stat(); guard fstat(fd, &statInfo) == 0 else { perror("fstat"); exit(1) }
let fileBytes = Int(statInfo.st_size), pageBytes = Int(getpagesize())
let mappedBytes = ((fileBytes + pageBytes - 1) / pageBytes) * pageBytes
guard let mapped = mmap(nil, mappedBytes, PROT_READ, MAP_PRIVATE, fd, 0), mapped != MAP_FAILED else {
    perror("mmap"); exit(1)
}
defer { munmap(mapped, mappedBytes) }

var headerLengthRaw: UInt64 = 0
memcpy(&headerLengthRaw, mapped, 8)
let headerLength = Int(UInt64(littleEndian: headerLengthRaw))
let headerData = Data(bytes: mapped.advanced(by: 8), count: headerLength)
guard let header = try JSONSerialization.jsonObject(with: headerData) as? [String: Any],
      let inputMeta = header["experts.\(expert).input_linear.weight"] as? [String: Any],
      let outputMeta = header["experts.\(expert).output_linear.weight"] as? [String: Any],
      inputMeta["dtype"] as? String == "F16", outputMeta["dtype"] as? String == "F16",
      let inputShape = inputMeta["shape"] as? [Int], let outputShape = outputMeta["shape"] as? [Int],
      let inputOffsets = inputMeta["data_offsets"] as? [Int],
      let outputOffsets = outputMeta["data_offsets"] as? [Int] else {
    fputs("expected F16 expert tensors were not found\n", stderr); exit(1)
}
let dataStart = 8 + headerLength
let expertStart = inputOffsets[0]
let expertEnd = outputOffsets[1]
let expertBytes = expertEnd - expertStart
let inputOffsetWithinExpert = inputOffsets[0] - expertStart
let outputOffsetWithinExpert = outputOffsets[0] - expertStart

guard let device = MTLCreateSystemDefaultDevice(), let queue = device.makeCommandQueue() else { exit(1) }
let source = """
#include <metal_stdlib>
using namespace metal;
kernel void expert_hidden(device const half *weights [[buffer(0)]], device const half *x [[buffer(1)]], device half *h [[buffer(2)]], uint i [[thread_position_in_grid]]) {
    if (i >= 512) return;
    float gate = 0.0f, value = 0.0f;
    for (uint j = 0; j < 1536; ++j) {
        gate += float(weights[i * 1536 + j]) * float(x[j]);
        value += float(weights[(i + 512) * 1536 + j]) * float(x[j]);
    }
    half gate_half = half(gate);
    half value_half = half(value);
    half activated_half = half(float(gate_half) / (1.0f + exp(-float(gate_half))));
    h[i] = activated_half * value_half;
}
kernel void expert_output(device const half *weights [[buffer(0)]], device const half *h [[buffer(1)]], device half *y [[buffer(2)]], uint i [[thread_position_in_grid]]) {
    if (i >= 1536) return;
    float value = 0.0f;
    for (uint j = 0; j < 512; ++j) value += float(weights[i * 512 + j]) * float(h[j]);
    y[i] = half(value);
}
"""
let compileOptions = MTLCompileOptions()
compileOptions.fastMathEnabled = false
let library = try device.makeLibrary(source: source, options: compileOptions)
let hiddenPipeline = try device.makeComputePipelineState(function: library.makeFunction(name: "expert_hidden")!)
let outputPipeline = try device.makeComputePipelineState(function: library.makeFunction(name: "expert_output")!)
var input = (0..<1536).map { Float16(sin(Double($0) * 0.017) * 0.125) }
let inputBuffer = input.withUnsafeBytes { device.makeBuffer(bytes: $0.baseAddress!, length: $0.count, options: .storageModeShared)! }
let hiddenBuffer = device.makeBuffer(length: 512 * 2, options: .storageModeShared)!
let outputBuffer = device.makeBuffer(length: 1536 * 2, options: .storageModeShared)!

func execute(_ weights: MTLBuffer, inputWeightOffset: Int, outputWeightOffset: Int) -> (Double, String) {
    memset(hiddenBuffer.contents(), 0, hiddenBuffer.length); memset(outputBuffer.contents(), 0, outputBuffer.length)
    let command = queue.makeCommandBuffer()!
    let first = command.makeComputeCommandEncoder()!
    first.setComputePipelineState(hiddenPipeline); first.setBuffer(weights, offset: inputWeightOffset, index: 0)
    first.setBuffer(inputBuffer, offset: 0, index: 1); first.setBuffer(hiddenBuffer, offset: 0, index: 2)
    first.dispatchThreads(MTLSize(width: 512, height: 1, depth: 1), threadsPerThreadgroup: MTLSize(width: 128, height: 1, depth: 1)); first.endEncoding()
    let second = command.makeComputeCommandEncoder()!
    second.setComputePipelineState(outputPipeline); second.setBuffer(weights, offset: outputWeightOffset, index: 0)
    second.setBuffer(hiddenBuffer, offset: 0, index: 1); second.setBuffer(outputBuffer, offset: 0, index: 2)
    second.dispatchThreads(MTLSize(width: 1536, height: 1, depth: 1), threadsPerThreadgroup: MTLSize(width: 128, height: 1, depth: 1)); second.endEncoding()
    let started = ContinuousClock.now; command.commit(); command.waitUntilCompleted()
    guard command.status == .completed else { fputs("expert kernel failed\n", stderr); exit(1) }
    let values = Array(UnsafeBufferPointer(start: outputBuffer.contents().assumingMemoryBound(to: UInt16.self), count: 1536))
    return (ms(started, ContinuousClock.now), fnv1a(values))
}

var trials: [Trial] = []
let order = Array(repeating: ["copied", "nocopy", "nocopy", "copied"], count: iterations).flatMap { $0 }
for (sequence, condition) in order.enumerated() {
    autoreleasepool {
        let started = ContinuousClock.now
        let weights: MTLBuffer?
        let inputOffset: Int, outputOffset: Int
        if condition == "nocopy" {
            weights = device.makeBuffer(bytesNoCopy: mapped, length: mappedBytes, options: .storageModeShared, deallocator: nil)
            inputOffset = dataStart + inputOffsets[0]; outputOffset = dataStart + outputOffsets[0]
        } else {
            weights = device.makeBuffer(bytes: mapped.advanced(by: dataStart + expertStart), length: expertBytes, options: .storageModeShared)
            inputOffset = inputOffsetWithinExpert; outputOffset = outputOffsetWithinExpert
        }
        let creation = ms(started, ContinuousClock.now)
        guard let weights else { fputs("weight buffer failed\n", stderr); exit(1) }
        let (kernel, hash) = execute(weights, inputWeightOffset: inputOffset, outputWeightOffset: outputOffset)
        trials.append(Trial(condition: condition, sequence: sequence, creationMilliseconds: creation,
                            expertKernelMilliseconds: kernel, totalMilliseconds: creation + kernel,
                            outputFNV1a64: hash))
    }
}
let summaries = Dictionary(uniqueKeysWithValues: ["copied", "nocopy"].map { condition in
    let selected = trials.filter { $0.condition == condition }
    let creation = selected.map { $0.creationMilliseconds }, kernel = selected.map { $0.expertKernelMilliseconds }, total = selected.map { $0.totalMilliseconds }
    return (condition, Summary(samples: selected.count,
        creationMedianMilliseconds: median(creation), creationP95Milliseconds: p95(creation),
        kernelMedianMilliseconds: median(kernel), kernelP95Milliseconds: p95(kernel),
        totalMedianMilliseconds: median(total), totalP95Milliseconds: p95(total)))
})
let report = Report(schemaVersion: "aion.metal_nocopy_expert_probe.v1", path: path,
    fileBytes: fileBytes, expert: expert, expertBytes: expertBytes,
    inputWeightShape: inputShape, outputWeightShape: outputShape, device: device.name,
    inputFNV1a64: fnv1a(input.map { $0.bitPattern }),
    summaries: summaries, trials: trials,
    outputsBitExact: Set(trials.map { $0.outputFNV1a64 }).count == 1,
    claimBoundary: "One deterministic input and one real FP16 Granite expert using custom Metal kernels. Bit-exact means copied and no-copy conditions within this kernel, not equivalence to the Transformers/MPS expert, model logits, tokens or end-to-end inference. Filesystem state is warm uncontrolled.")
let encoder = JSONEncoder(); encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
var encoded = try encoder.encode(report); encoded.append(Data("\n".utf8))
if CommandLine.arguments.count == 5 { try encoded.write(to: URL(fileURLWithPath: CommandLine.arguments[4]), options: .withoutOverwriting) }
FileHandle.standardOutput.write(encoded)
