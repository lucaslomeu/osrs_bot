import Foundation
import CoreGraphics

enum CaptureError: LocalizedError {
    case unavailable

    var errorDescription: String? {
        switch self {
        case .unavailable:
            return "Could not read the current mouse position."
        }
    }
}

final class CaptureService {
    private let windowLocator: WindowLocator

    init(windowLocator: WindowLocator) {
        self.windowLocator = windowLocator
    }

    func captureRelativePoint(target: TargetWindow) throws -> StoredPoint {
        guard let cursor = CGEvent(source: nil)?.location else {
            throw CaptureError.unavailable
        }
        return try windowLocator.captureRelativePoint(target: target, cursor: cursor)
    }
}
