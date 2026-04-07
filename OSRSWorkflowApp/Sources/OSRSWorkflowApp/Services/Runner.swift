import Foundation
import CoreGraphics

enum RunnerState: Equatable {
    case idle
    case running
    case paused
    case stopping
    case failed(String)

    var label: String {
        switch self {
        case .idle:
            return "Idle"
        case .running:
            return "Running"
        case .paused:
            return "Paused"
        case .stopping:
            return "Stopping"
        case .failed(let message):
            return "Error: \(message)"
        }
    }
}

enum RunnerValidationError: LocalizedError {
    case legacyAbsoluteClick(String)

    var errorDescription: String? {
        switch self {
        case .legacyAbsoluteClick(let title):
            return "The step '\(title)' uses a legacy absolute click. Recalibrate it before running."
        }
    }
}

@MainActor
final class Runner: ObservableObject {
    @Published private(set) var state: RunnerState = .idle
    @Published private(set) var currentStepTitle: String = "No step running"
    @Published private(set) var currentLoop: Int = 0
    @Published private(set) var logs: [String] = []
    @Published private(set) var elapsedSeconds: Int = 0

    private let permissionManager: PermissionManager
    private let windowLocator: WindowLocator
    private let inputExecutor: InputExecutor
    private var task: Task<Void, Never>?
    private var startedAt: Date?
    private var accumulatedElapsedSeconds: Int = 0
    private var elapsedTask: Task<Void, Never>?

    init(
        permissionManager: PermissionManager,
        windowLocator: WindowLocator,
        inputExecutor: InputExecutor
    ) {
        self.permissionManager = permissionManager
        self.windowLocator = windowLocator
        self.inputExecutor = inputExecutor
    }

    func start(preset: Preset) {
        guard task == nil else { return }

        if !permissionManager.refresh() {
            state = .failed("Accessibility permission is required. Click Request Permission in the side panel after enabling the app in System Settings.")
            appendLog("Accessibility permission is missing.")
            return
        }

        let enabledActions = preset.actions.filter(\.isEnabled)
        guard !enabledActions.isEmpty else {
            state = .failed("Add at least one enabled action.")
            appendLog("Preset has no enabled actions.")
            return
        }

        do {
            try validatePreflight(for: preset, actions: enabledActions)
        } catch {
            state = .failed(error.localizedDescription)
            appendLog("Preflight failed: \(error.localizedDescription)")
            return
        }

        state = .running
        currentStepTitle = "Preparing preset"
        currentLoop = 0
        elapsedSeconds = 0
        accumulatedElapsedSeconds = 0
        startedAt = .now
        startElapsedTimer()
        appendLog("Started preset '\(preset.name)'.")

        task = Task {
            await runPreset(preset, actions: enabledActions)
        }
    }

    func stop() {
        guard task != nil else { return }
        freezeElapsedClock()
        state = .stopping
        appendLog("Stop requested.")
        task?.cancel()
    }

    func pause() {
        guard state == .running else { return }
        freezeElapsedClock()
        state = .paused
        appendLog("Preset paused.")
    }

    func resume() {
        guard state == .paused else { return }
        startedAt = .now
        state = .running
        appendLog("Preset resumed.")
    }

    private func runPreset(_ preset: Preset, actions: [ActionStep]) async {
        defer {
            task = nil
            startedAt = nil
            accumulatedElapsedSeconds = 0
            stopElapsedTimer(reset: true)
            if case .failed = state {
                currentStepTitle = "Run failed"
            } else {
                state = .idle
                currentStepTitle = "No step running"
            }
        }

        do {
            switch preset.loop.mode {
            case .once:
                try await runLoop(loopNumber: 1, actions: actions, target: preset.targetWindow, safety: preset.safety)
            case .repeatCount:
                for loopNumber in 1...max(1, preset.loop.repeatCount) {
                    try Task.checkCancellation()
                    try await runLoop(loopNumber: loopNumber, actions: actions, target: preset.targetWindow, safety: preset.safety)
                }
            case .untilStopped:
                var loopNumber = 1
                while !Task.isCancelled {
                    try await runLoop(loopNumber: loopNumber, actions: actions, target: preset.targetWindow, safety: preset.safety)
                    loopNumber += 1
                }
            }

            appendLog("Preset finished.")
        } catch is CancellationError {
            appendLog("Preset stopped.")
        } catch {
            freezeElapsedClock()
            state = .failed(error.localizedDescription)
            appendLog("Run failed: \(error.localizedDescription)")
        }
    }

    private func runLoop(loopNumber: Int, actions: [ActionStep], target: TargetWindow, safety: ExecutionSafety) async throws {
        try await waitIfPaused()
        try checkRuntimeLimit(maxRuntimeMinutes: safety.maxRuntimeMinutes)
        currentLoop = loopNumber
        appendLog("Loop \(loopNumber) started.")

        for step in actions {
            try Task.checkCancellation()
            try await waitIfPaused()
            try checkRuntimeLimit(maxRuntimeMinutes: safety.maxRuntimeMinutes)
            currentStepTitle = step.title

            switch step.kind {
            case .click:
                try await executeClickStep(step, target: target, safety: safety)
            case .wait:
                try await executeWaitStep(step)
            }
        }
    }

    private func executeClickStep(_ step: ActionStep, target: TargetWindow, safety: ExecutionSafety) async throws {
        guard let click = step.click else { return }
        if safety.enforceRelativePointInsideWindow {
            try windowLocator.validateRelativeClick(click, target: target)
        }
        let resolvedPoint = try windowLocator.resolvePoint(for: click, target: target)
        let finalPoint = CGPoint(
            x: resolvedPoint.x + Double.random(in: -click.jitterX...click.jitterX),
            y: resolvedPoint.y + Double.random(in: -click.jitterY...click.jitterY)
        )
        try await inputExecutor.click(at: finalPoint, button: click.button)
        appendLog("\(step.title): \(click.button.displayName) at \(Int(finalPoint.x)), \(Int(finalPoint.y)).")
        try await sleep(seconds: step.timing.sampledSeconds())
    }

    private func executeWaitStep(_ step: ActionStep) async throws {
        let seconds = step.timing.sampledSeconds()
        appendLog("\(step.title): waiting \(String(format: "%.2f", seconds))s.")
        try await sleep(seconds: seconds)
    }

    private func sleep(seconds: Double) async throws {
        let duration = max(0, seconds)
        guard duration > 0 else { return }

        var remaining = duration
        while remaining > 0 {
            try Task.checkCancellation()
            try await waitIfPaused()
            let slice = min(remaining, 0.2)
            try await Task.sleep(for: .seconds(slice))
            remaining -= slice
        }
    }

    private func appendLog(_ message: String) {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm:ss"
        let line = "[\(formatter.string(from: .now))] \(message)"
        logs.insert(line, at: 0)
        logs = Array(logs.prefix(40))
    }

    private func validatePreflight(for preset: Preset, actions: [ActionStep]) throws {
        if let legacyStep = actions.first(where: \.requiresRecalibration) {
            throw RunnerValidationError.legacyAbsoluteClick(legacyStep.title)
        }

        let hasRelativeClicks = actions.contains { step in
            step.kind == .click && step.click?.coordinateMode == .windowRelative
        }

        if preset.safety.requireWindowMatchBeforeRun && hasRelativeClicks && windowLocator.findWindow(target: preset.targetWindow) == nil {
            throw WindowLocatorError.notFound(preset.targetWindow)
        }

        if preset.safety.enforceRelativePointInsideWindow {
            for step in actions {
                guard step.kind == .click, let click = step.click else { continue }
                try windowLocator.validateRelativeClick(click, target: preset.targetWindow)
            }
        }
    }

    private func checkRuntimeLimit(maxRuntimeMinutes: Double) throws {
        guard maxRuntimeMinutes > 0 else { return }
        let elapsedMinutes = Double(currentElapsedSeconds()) / 60.0
        if elapsedMinutes >= maxRuntimeMinutes {
            throw NSError(
                domain: "OSRSWorkflowApp.Runner",
                code: 1,
                userInfo: [NSLocalizedDescriptionKey: "Preset stopped after reaching the runtime limit of \(String(format: "%.0f", maxRuntimeMinutes)) minutes."]
            )
        }
    }

    private func startElapsedTimer() {
        elapsedTask?.cancel()
        elapsedTask = Task { [weak self] in
            guard let self else { return }
            while !Task.isCancelled {
                self.elapsedSeconds = self.currentElapsedSeconds()
                try? await Task.sleep(for: .seconds(1))
            }
        }
    }

    private func stopElapsedTimer(reset: Bool) {
        elapsedTask?.cancel()
        elapsedTask = nil
        if reset {
            elapsedSeconds = 0
        }
    }

    private func currentElapsedSeconds() -> Int {
        let activeSeconds: Int
        if let startedAt {
            activeSeconds = max(0, Int(Date().timeIntervalSince(startedAt)))
        } else {
            activeSeconds = 0
        }

        return accumulatedElapsedSeconds + activeSeconds
    }

    private func freezeElapsedClock() {
        accumulatedElapsedSeconds = currentElapsedSeconds()
        startedAt = nil
        elapsedSeconds = accumulatedElapsedSeconds
    }

    private func waitIfPaused() async throws {
        while state == .paused {
            try Task.checkCancellation()
            try await Task.sleep(for: .milliseconds(150))
        }
    }
}
