import Foundation
import CoreGraphics

enum InputExecutorError: LocalizedError {
    case unableToCreateEvent

    var errorDescription: String? {
        switch self {
        case .unableToCreateEvent:
            return "Could not create the macOS input event."
        }
    }
}

@MainActor
final class InputExecutor {
    func click(at point: CGPoint, button: MouseButton) async throws {
        try await moveCursorSmoothly(to: point)

        let eventButton: CGMouseButton = button == .left ? .left : .right
        let moveType: CGEventType = .mouseMoved
        let downType: CGEventType = button == .left ? .leftMouseDown : .rightMouseDown
        let upType: CGEventType = button == .left ? .leftMouseUp : .rightMouseUp

        guard
            let mouseMove = CGEvent(mouseEventSource: nil, mouseType: moveType, mouseCursorPosition: point, mouseButton: eventButton),
            let mouseDown = CGEvent(mouseEventSource: nil, mouseType: downType, mouseCursorPosition: point, mouseButton: eventButton),
            let mouseUp = CGEvent(mouseEventSource: nil, mouseType: upType, mouseCursorPosition: point, mouseButton: eventButton)
        else {
            throw InputExecutorError.unableToCreateEvent
        }

        mouseMove.post(tap: .cghidEventTap)
        mouseDown.post(tap: .cghidEventTap)
        mouseUp.post(tap: .cghidEventTap)
    }

    private func moveCursorSmoothly(to point: CGPoint) async throws {
        let start = CGEvent(source: nil)?.location ?? point
        let duration = Double.random(in: 0.10...0.22)
        let steps = Int.random(in: 10...18)
        let sleepNanoseconds = UInt64((duration / Double(steps)) * 1_000_000_000)

        guard
            let firstMove = CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: start, mouseButton: .left)
        else {
            throw InputExecutorError.unableToCreateEvent
        }
        firstMove.post(tap: .cghidEventTap)

        for index in 1...steps {
            let progress = Double(index) / Double(steps)
            let eased = 1.0 - pow(1.0 - progress, 2.0)
            let currentPoint = CGPoint(
                x: start.x + ((point.x - start.x) * eased),
                y: start.y + ((point.y - start.y) * eased)
            )

            guard
                let moveEvent = CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: currentPoint, mouseButton: .left)
            else {
                throw InputExecutorError.unableToCreateEvent
            }

            moveEvent.post(tap: .cghidEventTap)
            try await Task.sleep(nanoseconds: sleepNanoseconds)
        }
    }
}
