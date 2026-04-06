// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "OSRSWorkflowApp",
    platforms: [
        .macOS(.v14),
    ],
    products: [
        .executable(
            name: "OSRSWorkflowApp",
            targets: ["OSRSWorkflowApp"]
        ),
    ],
    targets: [
        .executableTarget(
            name: "OSRSWorkflowApp",
            path: "Sources/OSRSWorkflowApp"
        ),
    ]
)
