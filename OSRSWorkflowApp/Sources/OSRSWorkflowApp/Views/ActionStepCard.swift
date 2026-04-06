import SwiftUI

struct ActionStepCard: View {
    @ObservedObject var viewModel: AppViewModel
    let preset: Preset
    @Binding var step: ActionStep
    let moveUp: () -> Void
    let moveDown: () -> Void
    let delete: () -> Void
    let isFirst: Bool
    let isLast: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(alignment: .top, spacing: 12) {
                VStack(alignment: .leading, spacing: 8) {
                    HStack(spacing: 10) {
                        kindBadge

                        TextField("Action title", text: $step.title)
                            .textFieldStyle(.plain)
                            .font(.system(size: 17, weight: .semibold, design: .rounded))
                            .foregroundStyle(Theme.textPrimary)
                    }

                    Text(step.summary)
                        .font(.system(size: 12, weight: .medium, design: .rounded))
                        .foregroundStyle(Theme.textSecondary)
                }

                Spacer()

                Toggle("", isOn: $step.isEnabled)
                    .toggleStyle(.switch)
                    .labelsHidden()

                HStack(spacing: 8) {
                    iconButton("arrow.up") { moveUp() }
                        .disabled(isFirst)
                    iconButton("arrow.down") { moveDown() }
                        .disabled(isLast)
                    iconButton("trash") { delete() }
                }
            }

            switch step.kind {
            case .click:
                clickEditor
            case .wait:
                waitEditor
            }
        }
        .padding(18)
        .background(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(Theme.panelRaised)
                .overlay(
                    RoundedRectangle(cornerRadius: 18, style: .continuous)
                        .stroke(Theme.line, lineWidth: 1)
                )
        )
    }

    private var kindBadge: some View {
        Text(step.kind == .click ? "CLICK" : "WAIT")
            .font(.system(size: 10, weight: .bold, design: .rounded))
            .foregroundStyle(step.kind == .click ? Theme.accent : Theme.success)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(
                Capsule(style: .continuous)
                    .fill(Color.white.opacity(0.06))
            )
    }

    private var clickEditor: some View {
        let clickBinding = Binding<MouseClickAction>(
            get: { step.click ?? .default },
            set: { step.click = $0 }
        )

        return VStack(alignment: .leading, spacing: 14) {
            HStack {
                Picker("Button", selection: clickBinding.button) {
                    ForEach(MouseButton.allCases) { button in
                        Text(button.displayName).tag(button)
                    }
                }
                .pickerStyle(.segmented)

                Picker("Mode", selection: clickBinding.coordinateMode) {
                    ForEach(CoordinateMode.allCases) { mode in
                        Text(mode.displayName).tag(mode)
                    }
                }
                .pickerStyle(.segmented)
            }

            HStack {
                coordinateField(title: "X", value: clickBinding.point.x)
                coordinateField(title: "Y", value: clickBinding.point.y)
                coordinateField(title: "Jitter X", value: clickBinding.jitterX)
                coordinateField(title: "Jitter Y", value: clickBinding.jitterY)
            }

            HStack {
                Button {
                    viewModel.beginAbsoluteCalibration(presetID: preset.id, stepID: step.id)
                } label: {
                    Label("Calibrate Absolute", systemImage: "scope")
                }
                .buttonStyle(.bordered)

                Button {
                    viewModel.beginRelativeCalibration(presetID: preset.id, stepID: step.id)
                } label: {
                    Label("Calibrate RuneLite", systemImage: "viewfinder.circle")
                }
                .buttonStyle(.borderedProminent)
                .tint(Theme.accentSoft)
            }

            if viewModel.isCalibrating(stepID: step.id, mode: .absolute) || viewModel.isCalibrating(stepID: step.id, mode: .windowRelative) {
                Text(viewModel.calibrationInstructions ?? "Calibration armed.")
                    .font(.system(size: 12, weight: .semibold, design: .rounded))
                    .foregroundStyle(Theme.accent)
                    .padding(12)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(
                        RoundedRectangle(cornerRadius: 12, style: .continuous)
                            .fill(Color.white.opacity(0.04))
                    )
            }

            timingEditor
        }
    }

    private var waitEditor: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Wait duration")
                .font(.system(size: 13, weight: .bold, design: .rounded))
                .foregroundStyle(Theme.textPrimary)

            timingEditor
        }
    }

    private var timingEditor: some View {
        VStack(alignment: .leading, spacing: 10) {
            Picker("Timing", selection: $step.timing.mode) {
                Text("Random Range").tag(TimingMode.randomRange)
                Text("Fixed").tag(TimingMode.fixed)
            }
            .pickerStyle(.segmented)

            if step.timing.mode == .fixed {
                coordinateField(title: "Seconds", value: $step.timing.fixedSeconds)
            } else {
                HStack {
                    coordinateField(title: "Min", value: $step.timing.minSeconds)
                    coordinateField(title: "Max", value: $step.timing.maxSeconds)
                }
            }
        }
    }

    private func coordinateField(title: String, value: Binding<Double>) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.system(size: 11, weight: .bold, design: .rounded))
                .foregroundStyle(Theme.textSecondary)

            TextField(title, value: value, format: .number.precision(.fractionLength(0...2)))
                .textFieldStyle(.roundedBorder)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func iconButton(_ systemImage: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: systemImage)
                .frame(width: 28, height: 28)
        }
        .buttonStyle(.borderless)
        .foregroundStyle(Theme.textSecondary)
    }
}
