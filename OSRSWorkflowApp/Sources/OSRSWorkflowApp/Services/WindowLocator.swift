import Foundation
import CoreGraphics
import AppKit
import ApplicationServices

struct WindowMatch: Equatable {
    let ownerName: String
    let title: String
    let bounds: CGRect
}

enum WindowLocatorError: LocalizedError {
    case notFound(TargetWindow)
    case cursorOutsideWindow
    case pointOutsideWindow

    var errorDescription: String? {
        switch self {
        case .notFound(let target):
            return "No window matched \(target.filterDescription)."
        case .cursorOutsideWindow:
            return "The mouse cursor is not inside the RuneLite window."
        case .pointOutsideWindow:
            return "The saved click point is outside the matched window bounds."
        }
    }
}

final class WindowLocator {
    func findWindow(target: TargetWindow) -> WindowMatch? {
        if let displayWindow = findDisplayWindow(target: target) {
            return displayWindow
        }

        return findAccessibilityWindow(target: target)
    }

    func resolvePoint(for click: MouseClickAction, target: TargetWindow) throws -> CGPoint {
        switch click.coordinateMode {
        case .absolute:
            return CGPoint(x: click.point.x, y: click.point.y)
        case .windowRelative:
            guard let window = findWindow(target: target) else {
                throw WindowLocatorError.notFound(target)
            }
            return CGPoint(
                x: window.bounds.origin.x + click.point.x,
                y: window.bounds.origin.y + click.point.y
            )
        }
    }

    func validateRelativeClick(_ click: MouseClickAction, target: TargetWindow) throws {
        guard click.coordinateMode == .windowRelative else {
            return
        }

        guard let window = findWindow(target: target) else {
            throw WindowLocatorError.notFound(target)
        }

        guard click.point.x >= 0, click.point.y >= 0 else {
            throw WindowLocatorError.pointOutsideWindow
        }

        guard click.point.x <= window.bounds.width, click.point.y <= window.bounds.height else {
            throw WindowLocatorError.pointOutsideWindow
        }
    }

    func captureRelativePoint(target: TargetWindow, cursor: CGPoint) throws -> StoredPoint {
        guard let window = findWindow(target: target) else {
            throw WindowLocatorError.notFound(target)
        }

        guard window.bounds.contains(cursor) else {
            throw WindowLocatorError.cursorOutsideWindow
        }

        return StoredPoint(
            x: cursor.x - window.bounds.origin.x,
            y: cursor.y - window.bounds.origin.y
        )
    }

    private func findDisplayWindow(target: TargetWindow) -> WindowMatch? {
        guard let windows = CGWindowListCopyWindowInfo([.optionAll], kCGNullWindowID) as? [[String: Any]] else {
            return nil
        }

        var bestMatch: WindowMatch?
        var bestArea: CGFloat = 0

        for window in windows {
            let ownerName = (window[kCGWindowOwnerName as String] as? String) ?? ""
            let title = (window[kCGWindowName as String] as? String) ?? ""
            let boundsDict = window[kCGWindowBounds as String] as? NSDictionary

            guard
                let boundsDict,
                let bounds = CGRect(dictionaryRepresentation: boundsDict),
                let score = matchScore(ownerName: ownerName, target: target),
                isActionable(bounds: bounds)
            else {
                continue
            }

            let area = (bounds.width * bounds.height) + score
            if area > bestArea {
                bestArea = area
                bestMatch = WindowMatch(ownerName: ownerName, title: title, bounds: bounds)
            }
        }

        return bestMatch
    }

    private func findAccessibilityWindow(target: TargetWindow) -> WindowMatch? {
        guard AXIsProcessTrusted() else {
            return nil
        }

        var bestMatch: WindowMatch?
        var bestArea: CGFloat = 0

        for app in NSWorkspace.shared.runningApplications {
            let ownerName = app.localizedName ?? ""

            let applicationElement = AXUIElementCreateApplication(app.processIdentifier)
            var windowsValue: CFTypeRef?
            let result = AXUIElementCopyAttributeValue(applicationElement, kAXWindowsAttribute as CFString, &windowsValue)
            guard
                result == .success,
                let windowElements = windowsValue as? [AXUIElement]
            else {
                continue
            }

            for windowElement in windowElements {
                let title = stringAttribute(kAXTitleAttribute, from: windowElement) ?? ""
                guard let score = matchScore(ownerName: ownerName, target: target) else {
                    continue
                }

                guard
                    let position = cgPointAttribute(kAXPositionAttribute, from: windowElement),
                    let size = cgSizeAttribute(kAXSizeAttribute, from: windowElement)
                else {
                    continue
                }

                let bounds = CGRect(origin: position, size: size)
                guard isActionable(bounds: bounds) else {
                    continue
                }

                let area = (bounds.width * bounds.height) + score
                if area > bestArea {
                    bestArea = area
                    bestMatch = WindowMatch(ownerName: ownerName, title: title, bounds: bounds)
                }
            }
        }

        return bestMatch
    }

    private func matchScore(ownerName: String, target: TargetWindow) -> CGFloat? {
        let ownerFilter = normalizeForSearch(target.ownerContains)
        let ownerMatches = matchesContains(ownerFilter, in: ownerName)

        if ownerFilter.isEmpty {
            return 1
        }

        guard ownerMatches else {
            return nil
        }

        return 3_000
    }

    private func matchesContains(_ normalizedNeedle: String, in rawHaystack: String) -> Bool {
        let needle = normalizedNeedle
        if needle.isEmpty {
            return true
        }

        let haystack = normalizeForSearch(rawHaystack)
        if haystack.contains(needle) {
            return true
        }

        let tokens = needle.split(separator: " ").map(String.init)
        return !tokens.isEmpty && tokens.allSatisfy { haystack.contains($0) }
    }

    private func normalizeForSearch(_ value: String) -> String {
        value
            .folding(options: [.caseInsensitive, .diacriticInsensitive, .widthInsensitive], locale: .current)
            .replacingOccurrences(of: "\\s+", with: " ", options: .regularExpression)
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()
    }

    private func isActionable(bounds: CGRect) -> Bool {
        bounds.width >= 300 && bounds.height >= 300
    }

    private func stringAttribute(_ attribute: String, from element: AXUIElement) -> String? {
        var value: CFTypeRef?
        let result = AXUIElementCopyAttributeValue(element, attribute as CFString, &value)
        guard result == .success else {
            return nil
        }
        return value as? String
    }

    private func cgPointAttribute(_ attribute: String, from element: AXUIElement) -> CGPoint? {
        var value: CFTypeRef?
        let result = AXUIElementCopyAttributeValue(element, attribute as CFString, &value)
        guard result == .success, let axValue = value else {
            return nil
        }

        let castedValue = axValue as! AXValue
        guard AXValueGetType(castedValue) == .cgPoint else {
            return nil
        }

        var point = CGPoint.zero
        return AXValueGetValue(castedValue, .cgPoint, &point) ? point : nil
    }

    private func cgSizeAttribute(_ attribute: String, from element: AXUIElement) -> CGSize? {
        var value: CFTypeRef?
        let result = AXUIElementCopyAttributeValue(element, attribute as CFString, &value)
        guard result == .success, let axValue = value else {
            return nil
        }

        let castedValue = axValue as! AXValue
        guard AXValueGetType(castedValue) == .cgSize else {
            return nil
        }

        var size = CGSize.zero
        return AXValueGetValue(castedValue, .cgSize, &size) ? size : nil
    }
}
