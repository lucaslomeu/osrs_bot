import SwiftUI

struct PresetEditorView: View {
    @ObservedObject var viewModel: AppViewModel
    @Binding var preset: Preset

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                headerCard
                targetCard
                safetyCard
                actionsCard
            }
            .padding(24)
        }
        .background(Theme.background)
    }

    private var headerCard: some View {
        card {
            VStack(alignment: .leading, spacing: 16) {
                Text("Preset")
                    .font(.system(size: 13, weight: .bold, design: .rounded))
                    .foregroundStyle(Theme.accent)

                TextField("Preset name", text: $preset.name)
                    .textFieldStyle(.plain)
                    .font(.system(size: 30, weight: .bold, design: .rounded))
                    .foregroundStyle(Theme.textPrimary)

                TextField("Notes", text: $preset.notes, axis: .vertical)
                    .textFieldStyle(.roundedBorder)

                VStack(alignment: .leading, spacing: 12) {
                    Text("Loop Mode")
                        .font(.system(size: 14, weight: .semibold, design: .rounded))
                        .foregroundStyle(Theme.textPrimary)

                    Picker("Loop", selection: $preset.loop.mode) {
                        Text("Run Once").tag(LoopModeKind.once)
                        Text("Repeat").tag(LoopModeKind.repeatCount)
                        Text("Until Stopped").tag(LoopModeKind.untilStopped)
                    }
                    .pickerStyle(.segmented)

                    if preset.loop.mode == .repeatCount {
                        Stepper(value: $preset.loop.repeatCount, in: 1...999) {
                            Text("Repeat \(preset.loop.repeatCount)x")
                                .foregroundStyle(Theme.textSecondary)
                        }
                    }
                }
            }
        }
    }

    private var targetCard: some View {
        card {
            VStack(alignment: .leading, spacing: 14) {
                Text("Target Window")
                    .font(.system(size: 18, weight: .semibold, design: .rounded))
                    .foregroundStyle(Theme.textPrimary)

                HStack {
                    labeledField(title: "Owner Contains", text: $preset.targetWindow.ownerContains)
                    labeledField(title: "Title Contains", text: $preset.targetWindow.titleContains)
                }

                HStack(alignment: .top, spacing: 10) {
                    Circle()
                        .fill(viewModel.hasWindowMatch(for: preset.targetWindow) ? Theme.success : Theme.warning)
                        .frame(width: 10, height: 10)
                        .padding(.top, 4)

                    Text(viewModel.windowMatchSummary(for: preset.targetWindow))
                        .font(.system(size: 12, weight: .medium, design: .rounded))
                        .foregroundStyle(Theme.textSecondary)
                }

                HStack {
                    Button {
                        viewModel.testWindowMatch(for: preset.targetWindow)
                    } label: {
                        Label("Test Window Match", systemImage: "scope")
                    }
                    .buttonStyle(.bordered)

                    Spacer()
                }

                Text("Default owner is RuneLite. Relative capture and execution use these values to resolve the game window.")
                    .font(.system(size: 12, weight: .medium, design: .rounded))
                    .foregroundStyle(Theme.textSecondary)
            }
        }
    }

    private var safetyCard: some View {
        card {
            VStack(alignment: .leading, spacing: 14) {
                Text("Run Safety")
                    .font(.system(size: 18, weight: .semibold, design: .rounded))
                    .foregroundStyle(Theme.textPrimary)

                Toggle("Require matching window before Run", isOn: $preset.safety.requireWindowMatchBeforeRun)
                    .toggleStyle(.switch)

                Toggle("Block relative clicks outside the matched window", isOn: $preset.safety.enforceRelativePointInsideWindow)
                    .toggleStyle(.switch)

                HStack {
                    coordinateField(title: "Max Runtime (min)", value: $preset.safety.maxRuntimeMinutes)
                    VStack(alignment: .leading, spacing: 6) {
                        Text("Behavior")
                            .font(.system(size: 11, weight: .bold, design: .rounded))
                            .foregroundStyle(Theme.textSecondary)
                        Text("The runner stops with a clear message after this limit. Use `0` to disable.")
                            .font(.system(size: 12, weight: .medium, design: .rounded))
                            .foregroundStyle(Theme.textSecondary)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
    }

    private var actionsCard: some View {
        card {
            VStack(alignment: .leading, spacing: 16) {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Actions")
                            .font(.system(size: 18, weight: .semibold, design: .rounded))
                            .foregroundStyle(Theme.textPrimary)
                        Text("Build a linear workflow with click and wait steps.")
                            .font(.system(size: 12, weight: .medium, design: .rounded))
                            .foregroundStyle(Theme.textSecondary)
                    }

                    Spacer()

                    Button {
                        preset.actions.append(.clickStep())
                    } label: {
                        Label("Add Click", systemImage: "cursorarrow.click.2")
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(Theme.accent)

                    Button {
                        preset.actions.append(.waitStep())
                    } label: {
                        Label("Add Wait", systemImage: "timer")
                    }
                    .buttonStyle(.bordered)
                }

                if preset.actions.isEmpty {
                    Text("No actions yet. Add a click or wait step to start.")
                        .font(.system(size: 14, weight: .medium, design: .rounded))
                        .foregroundStyle(Theme.textSecondary)
                        .padding(.vertical, 12)
                } else {
                    ForEach(Array($preset.actions.enumerated()), id: \.element.id) { index, step in
                        ActionStepCard(
                            viewModel: viewModel,
                            preset: preset,
                            step: step,
                            moveUp: { moveAction(from: index, to: index - 1) },
                            moveDown: { moveAction(from: index, to: index + 1) },
                            delete: { preset.actions.remove(at: index) },
                            isFirst: index == 0,
                            isLast: index == preset.actions.count - 1
                        )
                    }
                }
            }
        }
    }

    private func labeledField(title: String, text: Binding<String>) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.system(size: 12, weight: .bold, design: .rounded))
                .foregroundStyle(Theme.textSecondary)
            TextField(title, text: text)
                .textFieldStyle(.roundedBorder)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func coordinateField(title: String, value: Binding<Double>) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.system(size: 12, weight: .bold, design: .rounded))
                .foregroundStyle(Theme.textSecondary)

            TextField(title, value: value, format: .number.precision(.fractionLength(0...1)))
                .textFieldStyle(.roundedBorder)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func moveAction(from source: Int, to destination: Int) {
        guard preset.actions.indices.contains(source), preset.actions.indices.contains(destination) else {
            return
        }
        let element = preset.actions.remove(at: source)
        preset.actions.insert(element, at: destination)
    }

    private func card<Content: View>(@ViewBuilder content: () -> Content) -> some View {
        content()
            .padding(20)
            .background(
                RoundedRectangle(cornerRadius: 22, style: .continuous)
                    .fill(Theme.card)
                    .overlay(
                        RoundedRectangle(cornerRadius: 22, style: .continuous)
                            .stroke(Theme.line, lineWidth: 1)
                    )
            )
    }
}
