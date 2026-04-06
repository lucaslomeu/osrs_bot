import Foundation
import CoreGraphics

enum ActionKind: String, Codable, CaseIterable, Identifiable {
    case click
    case wait

    var id: String { rawValue }
}

enum MouseButton: String, Codable, CaseIterable, Identifiable {
    case left
    case right

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .left:
            return "Left Click"
        case .right:
            return "Right Click"
        }
    }
}

enum CoordinateMode: String, Codable, CaseIterable, Identifiable {
    case windowRelative
    case absolute

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .windowRelative:
            return "RuneLite Relative"
        case .absolute:
            return "Absolute Screen"
        }
    }
}

enum TimingMode: String, Codable, CaseIterable, Identifiable {
    case randomRange
    case fixed

    var id: String { rawValue }
}

enum LoopModeKind: String, Codable, CaseIterable, Identifiable {
    case once
    case repeatCount
    case untilStopped

    var id: String { rawValue }
}

struct TargetWindow: Codable, Equatable {
    var ownerContains: String
    var titleContains: String

    static let `default` = TargetWindow(ownerContains: "RuneLite", titleContains: "")

    var filterDescription: String {
        let owner = ownerContains.trimmingCharacters(in: .whitespacesAndNewlines)
        let title = titleContains.trimmingCharacters(in: .whitespacesAndNewlines)

        switch (owner.isEmpty, title.isEmpty) {
        case (false, false):
            return "owner '\(owner)' and title '\(title)'"
        case (false, true):
            return "owner '\(owner)'"
        case (true, false):
            return "title '\(title)'"
        case (true, true):
            return "any visible window"
        }
    }
}

struct StoredPoint: Codable, Equatable {
    var x: Double
    var y: Double

    static let zero = StoredPoint(x: 0, y: 0)

    init(x: Double, y: Double) {
        self.x = x
        self.y = y
    }

    init(_ point: CGPoint) {
        self.x = point.x
        self.y = point.y
    }

    var cgPoint: CGPoint {
        CGPoint(x: x, y: y)
    }
}

struct ActionTiming: Codable, Equatable {
    var mode: TimingMode
    var fixedSeconds: Double
    var minSeconds: Double
    var maxSeconds: Double

    static let defaultClick = ActionTiming(
        mode: .randomRange,
        fixedSeconds: 1.2,
        minSeconds: 0.9,
        maxSeconds: 1.6
    )

    static let defaultWait = ActionTiming(
        mode: .randomRange,
        fixedSeconds: 2.0,
        minSeconds: 1.5,
        maxSeconds: 2.8
    )

    func sampledSeconds() -> Double {
        switch mode {
        case .fixed:
            return max(0, fixedSeconds)
        case .randomRange:
            let lower = max(0, min(minSeconds, maxSeconds))
            let upper = max(lower, max(minSeconds, maxSeconds))
            return Double.random(in: lower...upper)
        }
    }

    var summary: String {
        switch mode {
        case .fixed:
            return String(format: "%.2fs", fixedSeconds)
        case .randomRange:
            return String(format: "%.2fs - %.2fs", minSeconds, maxSeconds)
        }
    }
}

struct MouseClickAction: Codable, Equatable {
    var button: MouseButton
    var coordinateMode: CoordinateMode
    var point: StoredPoint
    var jitterX: Double
    var jitterY: Double

    static let `default` = MouseClickAction(
        button: .left,
        coordinateMode: .windowRelative,
        point: .zero,
        jitterX: 4,
        jitterY: 4
    )
}

struct ActionStep: Identifiable, Codable, Equatable {
    var id: UUID
    var title: String
    var isEnabled: Bool
    var kind: ActionKind
    var timing: ActionTiming
    var click: MouseClickAction?

    static func clickStep() -> ActionStep {
        ActionStep(
            id: UUID(),
            title: "Click Action",
            isEnabled: true,
            kind: .click,
            timing: .defaultClick,
            click: .default
        )
    }

    static func waitStep() -> ActionStep {
        ActionStep(
            id: UUID(),
            title: "Wait",
            isEnabled: true,
            kind: .wait,
            timing: .defaultWait,
            click: nil
        )
    }

    var summary: String {
        switch kind {
        case .click:
            guard let click else { return "Click" }
            let coordinateSummary = String(format: "%.0f, %.0f", click.point.x, click.point.y)
            return "\(click.button.displayName) • \(click.coordinateMode.displayName) • \(coordinateSummary) • \(timing.summary)"
        case .wait:
            return "Wait • \(timing.summary)"
        }
    }
}

struct LoopConfiguration: Codable, Equatable {
    var mode: LoopModeKind
    var repeatCount: Int

    static let `default` = LoopConfiguration(mode: .once, repeatCount: 10)
}

struct ExecutionSafety: Codable, Equatable {
    var requireWindowMatchBeforeRun: Bool
    var enforceRelativePointInsideWindow: Bool
    var maxRuntimeMinutes: Double

    static let `default` = ExecutionSafety(
        requireWindowMatchBeforeRun: true,
        enforceRelativePointInsideWindow: true,
        maxRuntimeMinutes: 20
    )
}

struct Preset: Identifiable, Codable, Equatable {
    var id: UUID
    var name: String
    var notes: String
    var targetWindow: TargetWindow
    var loop: LoopConfiguration
    var safety: ExecutionSafety
    var actions: [ActionStep]

    private enum CodingKeys: String, CodingKey {
        case id
        case name
        case notes
        case targetWindow
        case loop
        case safety
        case actions
    }

    init(
        id: UUID,
        name: String,
        notes: String,
        targetWindow: TargetWindow,
        loop: LoopConfiguration,
        safety: ExecutionSafety = .default,
        actions: [ActionStep]
    ) {
        self.id = id
        self.name = name
        self.notes = notes
        self.targetWindow = targetWindow
        self.loop = loop
        self.safety = safety
        self.actions = actions
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(UUID.self, forKey: .id)
        name = try container.decode(String.self, forKey: .name)
        notes = try container.decodeIfPresent(String.self, forKey: .notes) ?? ""
        targetWindow = try container.decodeIfPresent(TargetWindow.self, forKey: .targetWindow) ?? .default
        loop = try container.decodeIfPresent(LoopConfiguration.self, forKey: .loop) ?? .default
        safety = try container.decodeIfPresent(ExecutionSafety.self, forKey: .safety) ?? .default
        actions = try container.decodeIfPresent([ActionStep].self, forKey: .actions) ?? []
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .id)
        try container.encode(name, forKey: .name)
        try container.encode(notes, forKey: .notes)
        try container.encode(targetWindow, forKey: .targetWindow)
        try container.encode(loop, forKey: .loop)
        try container.encode(safety, forKey: .safety)
        try container.encode(actions, forKey: .actions)
    }

    static func starter() -> Preset {
        Preset(
            id: UUID(),
            name: "Starter Preset",
            notes: "A simple OSRS workflow with a click and a wait step.",
            targetWindow: .default,
            loop: .default,
            safety: .default,
            actions: [
                .clickStep(),
                .waitStep(),
            ]
        )
    }
}
