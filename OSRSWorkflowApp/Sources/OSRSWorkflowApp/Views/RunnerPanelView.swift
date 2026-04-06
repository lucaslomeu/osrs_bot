import SwiftUI

struct RunnerPanelView: View {
    @ObservedObject var viewModel: AppViewModel
    @ObservedObject var runner: Runner
    @ObservedObject var permissionManager: PermissionManager
    let preset: Preset

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            statusCard
            permissionCard
            logCard
            Spacer(minLength: 0)
        }
        .padding(20)
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

                HStack {
                    Button {
                        viewModel.startRun(preset)
                    } label: {
                        Label("Run", systemImage: "play.fill")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(Theme.success)

                    Button {
                        viewModel.stopRun()
                    } label: {
                        Label("Stop", systemImage: "stop.fill")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.bordered)
                    .tint(Theme.warning)
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

    private func card<Content: View>(@ViewBuilder content: () -> Content) -> some View {
        content()
            .padding(18)
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
