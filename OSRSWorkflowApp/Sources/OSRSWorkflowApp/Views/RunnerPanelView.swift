import SwiftUI

struct RunnerPanelView: View {
    @ObservedObject var viewModel: AppViewModel
    @ObservedObject var runner: Runner
    @ObservedObject var permissionManager: PermissionManager
    let preset: Preset

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                statusCard
                summaryCard
                permissionCard
                logCard
            }
            .padding(20)
        }
        .background(Theme.panel)
    }

    private var statusCard: some View {
        card {
            VStack(alignment: .leading, spacing: 14) {
                Text("Run Bar")
                    .font(.system(size: 18, weight: .semibold, design: .rounded))
                    .foregroundStyle(Theme.textPrimary)

                statusRow("Preset", preset.name)
                statusRow("State", runner.state.label)
                statusRow("Current Step", runner.currentStepTitle)
                statusRow("Loop", "\(runner.currentLoop)")
                statusRow("Runtime", elapsedLabel)

                ViewThatFits(in: .horizontal) {
                    HStack {
                        runButton
                        pauseResumeButton
                        stopButton
                    }

                    VStack(spacing: 10) {
                        runButton
                        pauseResumeButton
                        stopButton
                    }
                }

                if let calibrationInstructions = viewModel.calibrationInstructions {
                    Text(calibrationInstructions)
                        .font(.system(size: 12, weight: .semibold, design: .rounded))
                        .foregroundStyle(Theme.accent)
                }

                if let transientMessage = viewModel.transientMessage {
                    Text(transientMessage)
                        .font(.system(size: 12, weight: .medium, design: .rounded))
                        .foregroundStyle(Theme.accent)
                }
            }
        }
    }

    private var summaryCard: some View {
        let enabledActions = preset.actions.filter(\.isEnabled)
        let clickCount = enabledActions.filter { $0.kind == .click }.count
        let waitCount = enabledActions.filter { $0.kind == .wait }.count

        return card {
            VStack(alignment: .leading, spacing: 12) {
                Text("Preset Summary")
                    .font(.system(size: 16, weight: .semibold, design: .rounded))
                    .foregroundStyle(Theme.textPrimary)

                summaryRow("Enabled Steps", "\(enabledActions.count)")
                summaryRow("Clicks", "\(clickCount)")
                summaryRow("Waits", "\(waitCount)")
                summaryRow("Loop Mode", loopModeLabel)
            }
        }
    }

    private var permissionCard: some View {
        card {
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    Text("Permissions")
                        .font(.system(size: 16, weight: .semibold, design: .rounded))
                        .foregroundStyle(Theme.textPrimary)
                    Spacer()
                    Circle()
                        .fill(permissionManager.isAccessibilityGranted ? Theme.success : Theme.warning)
                        .frame(width: 10, height: 10)
                }

                Text(permissionManager.isAccessibilityGranted ? "Accessibility permission granted." : "Accessibility permission required for mouse automation.")
                    .font(.system(size: 12, weight: .medium, design: .rounded))
                    .foregroundStyle(Theme.textSecondary)

                Button("Request Permission") {
                    _ = permissionManager.requestAccessibilityPrompt()
                }
                .buttonStyle(.bordered)
            }
        }
    }

    private var logCard: some View {
        card {
            VStack(alignment: .leading, spacing: 12) {
                Text("Recent Events")
                    .font(.system(size: 16, weight: .semibold, design: .rounded))
                    .foregroundStyle(Theme.textPrimary)

                if runner.logs.isEmpty {
                    Text("Runtime logs will appear here after you run a preset.")
                        .font(.system(size: 12, weight: .medium, design: .rounded))
                        .foregroundStyle(Theme.textSecondary)
                } else {
                    ScrollView {
                        VStack(alignment: .leading, spacing: 8) {
                            ForEach(runner.logs, id: \.self) { line in
                                Text(line)
                                    .font(.system(size: 11, weight: .medium, design: .monospaced))
                                    .foregroundStyle(Theme.textSecondary)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                            }
                        }
                    }
                    .frame(minHeight: 220)
                }
            }
        }
    }

    private func statusRow(_ title: String, _ value: String) -> some View {
        HStack {
            Text(title)
                .foregroundStyle(Theme.textSecondary)
            Spacer()
            Text(value)
                .foregroundStyle(Theme.textPrimary)
                .multilineTextAlignment(.trailing)
        }
        .font(.system(size: 12, weight: .semibold, design: .rounded))
    }

    private var runButton: some View {
        Button {
            viewModel.startRun(preset)
        } label: {
            Label("Run", systemImage: "play.fill")
                .frame(maxWidth: .infinity)
        }
        .buttonStyle(.borderedProminent)
        .tint(Theme.success)
        .disabled(runner.state == .running || runner.state == .paused || runner.state == .stopping)
    }

    private var stopButton: some View {
        Button {
            viewModel.stopRun()
        } label: {
            Label("Stop", systemImage: "stop.fill")
                .frame(maxWidth: .infinity)
        }
        .buttonStyle(.bordered)
        .tint(Theme.warning)
        .disabled(runner.state == .idle)
    }

    private var pauseResumeButton: some View {
        Button {
            if runner.state == .paused {
                viewModel.resumeRun()
            } else {
                viewModel.pauseRun()
            }
        } label: {
            Label(runner.state == .paused ? "Resume" : "Pause", systemImage: runner.state == .paused ? "playpause.fill" : "pause.fill")
                .frame(maxWidth: .infinity)
        }
        .buttonStyle(.bordered)
        .tint(Theme.accent)
        .disabled(!(runner.state == .running || runner.state == .paused))
    }

    private var elapsedLabel: String {
        let total = runner.elapsedSeconds
        let hours = total / 3600
        let minutes = (total % 3600) / 60
        let seconds = total % 60
        return String(format: "%02d:%02d:%02d", hours, minutes, seconds)
    }

    private var loopModeLabel: String {
        switch preset.loop.mode {
        case .once:
            return "Run Once"
        case .repeatCount:
            return "Repeat \(preset.loop.repeatCount)x"
        case .untilStopped:
            return "Until Stopped"
        }
    }

    private func summaryRow(_ title: String, _ value: String) -> some View {
        HStack {
            Text(title)
                .foregroundStyle(Theme.textSecondary)
            Spacer()
            Text(value)
                .foregroundStyle(Theme.textPrimary)
                .multilineTextAlignment(.trailing)
        }
        .font(.system(size: 12, weight: .semibold, design: .rounded))
    }

    private func card<Content: View>(@ViewBuilder content: () -> Content) -> some View {
        content()
            .padding(18)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                RoundedRectangle(cornerRadius: 20, style: .continuous)
                    .fill(Theme.panelRaised)
                    .overlay(
                        RoundedRectangle(cornerRadius: 20, style: .continuous)
                            .stroke(Theme.line, lineWidth: 1)
                    )
            )
    }
}
