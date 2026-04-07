import Foundation
import ApplicationServices

final class PermissionManager: ObservableObject {
    @Published private(set) var isAccessibilityGranted: Bool = AXIsProcessTrusted()

    @discardableResult
    func refresh() -> Bool {
        isAccessibilityGranted = AXIsProcessTrusted()
        return isAccessibilityGranted
    }

    @discardableResult
    func requestAccessibilityPrompt() -> Bool {
        refresh()
        guard !isAccessibilityGranted else {
            return true
        }

        let options = ["AXTrustedCheckOptionPrompt": true] as CFDictionary
        isAccessibilityGranted = AXIsProcessTrustedWithOptions(options)
        return isAccessibilityGranted
    }
}
