// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "PilotNativeCore",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [.library(name: "PilotNativeCore", targets: ["PilotNativeCore"])],
    targets: [
        .target(name: "PilotNativeCore"),
        .testTarget(name: "PilotNativeCoreTests", dependencies: ["PilotNativeCore"]),
    ]
)
