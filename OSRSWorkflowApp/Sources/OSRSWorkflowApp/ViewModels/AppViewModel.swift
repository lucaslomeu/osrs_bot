import Foundation
import SwiftUI
import AppKit
import Combine

enum CalibrationMode {
    case absolute
    case windowRelative

    var buttonLabel: String {
        switch self {
        case .absolute:
            return "absolute"
        case .windowRelative:
            return "RuneLite"
        }
    }

    var instructions: String {
        switch self {
        case .absolute:
            return "Calibration armed. Move the mouse to the target point and press F6 to save. Press Esc to cancel."
        case .windowRelative:
            return "RuneLite calibration armed. Move the mouse inside RuneLite and press F6 to save. Press Esc to cancel."
        }
    }
}

struct CalibrationRequest: Equatable {
    let presetID: UUID
    let stepID: UUID
    let mode: CalibrationMode
}

@MainActor
final class AppViewModel: ObservableObject {
    private static let confirmKeyCode: UInt16 = 97
    private static let cancelKeyCode: UInt16 = 53

    @Published var transientMessage: String?
    @Published private(set) var calibrationRequest: CalibrationRequest?

    let store: PresetStore
    let runner: Runner
    let captureService: CaptureService
    let permissionManager: PermissionManager
    private let windowLocator: WindowLocator
    private var cancellables = Set<AnyCancellable>()
    private var localKeyMonitor: Any?
    private var globalKeyMonitor: Any?

    init() {
        let windowLocator = WindowLocator()
        let permissionManager = PermissionManager()

        self.windowLocator = windowLocator
        self.store = PresetStore()
        self.captureService = CaptureService(windowLocator: windowLocator)
        self.permissionManager = permissionManager
        self.runner = Runner(
            permissionManager: permissionManager,
            windowLocator: windowLocator,
            inputExecutor: InputExecutor()
        )

        bindRuntimeState()
    }

    func beginAbsoluteCalibration(presetID: UUID, stepID: UUID) {
        beginCalibration(
            CalibrationRequest(
                presetID: presetID,
                stepID: stepID,
                mode: .absolute
            )
        )
    }

    func beginRelativeCalibration(presetID: UUID, stepID: UUID) {
        beginCalibration(
            CalibrationRequest(
                presetID: presetID,
                stepID: stepID,
                mode: .windowRelative
            )
        )
    }

    func isCalibrating(stepID: UUID, mode: CalibrationMode) -> Bool {
        calibrationRequest?.stepID == stepID && calibrationRequest?.mode == mode
    }

    func cancelCalibration() {
        guard calibrationRequest != nil else { return }
        teardownCalibration(message: "Calibration cancelled.")
    }

    func startRun(_ preset: Preset) {
        runner.start(preset: preset)
    }

    func stopRun() {
        runner.stop()
    }

    var calibrationInstructions: String? {
        calibrationRequest?.mode.instructions
    }

    func windowMatchSummary(for target: TargetWindow) -> String {
        guard let match = windowLocator.findWindow(target: target) else {
            return "No visible window matched \(target.filterDescription). Matching ignores case and extra spaces."
        }

        let title = match.title.trimmingCharacters(in: .whitespacesAndNewlines)
        if title.isEmpty {
            return "Matched \(match.ownerName) at \(Int(match.bounds.origin.x)), \(Int(match.bounds.origin.y)) with size \(Int(match.bounds.width)) x \(Int(match.bounds.height))."
        }

        return "Matched \(match.ownerName) - \(title) at \(Int(match.bounds.origin.x)), \(Int(match.bounds.origin.y)) with size \(Int(match.bounds.width)) x \(Int(match.bounds.height))."
    }

    func hasWindowMatch(for target: TargetWindow) -> Bool {
        windowLocator.findWindow(target: target) != nil
    }

    func testWindowMatch(for target: TargetWindow) {
        transientMessage = windowMatchSummary(for: target)
    }

    private func bindRuntimeState() {
        runner.$state
            .receive(on: DispatchQueue.main)
            .sink { [weak self] state in
                guard let self else { return }
                self.syncHotkeyMonitoring()

                switch state {
                case .running:
                    if self.transientMessage == nil {
                        self.transientMessage = "Preset running. Press Esc to stop the current run."
                    }
                case .idle:
                    break
                case .stopping:
                    self.transientMessage = "Stopping current run..."
                case .failed(let message):
                    self.transientMessage = message
                }
            }
            .store(in: &cancellables)
    }

    private func beginCalibration(_ request: CalibrationRequest) {
        guard permissionManager.refresh() else {
            transientMessage = "Accessibility permission is required before calibration. Use Request Permission once, then enable OSRSWorkflowApp in System Settings > Privacy & Security > Accessibility."
            return
        }

        calibrationRequest = request
        transientMessage = request.mode.instructions
        syncHotkeyMonitoring()
    }

    private func syncHotkeyMonitoring() {
        let shouldMonitor = calibrationRequest != nil || runner.state == .running || runner.state == .stopping
        if shouldMonitor {
            installHotkeyMonitorsIfNeeded()
        } else {
            removeHotkeyMonitors()
        }
    }

    private func installHotkeyMonitorsIfNeeded() {
        if localKeyMonitor == nil {
            localKeyMonitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { [weak self] event in
                guard let self else { return event }
                return self.handleLocalHotkeyEvent(event)
            }
        }

        if globalKeyMonitor == nil {
            globalKeyMonitor = NSEvent.addGlobalMonitorForEvents(matching: .keyDown) { [weak self] event in
                guard let self else { return }
                Task { @MainActor in
                    self.handleGlobalHotkeyEvent(event)
                }
            }
        }
    }

    private func handleLocalHotkeyEvent(_ event: NSEvent) -> NSEvent? {
        guard calibrationRequest != nil || runner.state == .running || runner.state == .stopping else {
            return event
        }

        switch event.keyCode {
        case Self.confirmKeyCode:
            if calibrationRequest != nil {
                confirmCalibration()
                return nil
            }
            return event
        case Self.cancelKeyCode:
            handleEscape()
            return nil
        default:
            return event
        }
    }

    private func handleGlobalHotkeyEvent(_ event: NSEvent) {
        guard calibrationRequest != nil || runner.state == .running || runner.state == .stopping else { return }

        switch event.keyCode {
        case Self.confirmKeyCode:
            if calibrationRequest != nil {
                confirmCalibration()
            }
        case Self.cancelKeyCode:
            handleEscape()
        default:
            break
        }
    }

    private func handleEscape() {
        if calibrationRequest != nil {
            cancelCalibration()
            return
        }

        if runner.state == .running || runner.state == .stopping {
            runner.stop()
            transientMessage = "Current run stopped with Esc."
        }
    }

    private func confirmCalibration() {
        guard let calibrationRequest else { return }
        guard let location = locateAction(for: calibrationRequest) else {
            teardownCalibration(message: "The action being calibrated no longer exists.")
            return
        }

        do {
            let point: StoredPoint
            switch calibrationRequest.mode {
            case .absolute:
                point = try captureService.captureAbsoluteMousePoint()
            case .windowRelative:
                let preset = store.presets[location.presetIndex]
                point = try captureService.captureRuneLiteRelativePoint(target: preset.targetWindow)
            }

            var click = store.presets[location.presetIndex].actions[location.stepIndex].click ?? .default
            click.coordinateMode = calibrationRequest.mode == .absolute ? .absolute : .windowRelative
            click.point = point
            store.presets[location.presetIndex].actions[location.stepIndex].click = click
            store.save()

            teardownCalibration(
                message: "Click calibrated in \(calibrationRequest.mode.buttonLabel) mode at \(Int(point.x)), \(Int(point.y))."
            )
        } catch {
            transientMessage = "\(error.localizedDescription) Reposition the mouse and press F6 again, or Esc to cancel."
        }
    }

    private func locateAction(for request: CalibrationRequest) -> (presetIndex: Int, stepIndex: Int)? {
        guard let presetIndex = store.presets.firstIndex(where: { $0.id == request.presetID }) else {
            return nil
        }
        guard let stepIndex = store.presets[presetIndex].actions.firstIndex(where: { $0.id == request.stepID }) else {
            return nil
        }
        return (presetIndex, stepIndex)
    }

    private func teardownCalibration(message: String) {
        calibrationRequest = nil
        transientMessage = message
        syncHotkeyMonitoring()
    }

    private func removeHotkeyMonitors() {
        if let localKeyMonitor {
            NSEvent.removeMonitor(localKeyMonitor)
            self.localKeyMonitor = nil
        }

        if let globalKeyMonitor {
            NSEvent.removeMonitor(globalKeyMonitor)
            self.globalKeyMonitor = nil
        }
    }
}
