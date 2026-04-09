import SwiftUI

struct ActionStepCard: View {
    @ObservedObject var viewModel: AppViewModel
    let preset: Preset
    @Binding var step: ActionStep
    let moveUp: () -> Void
    let moveDown: () -> Void
    let duplicate: () -> Void
    let delete: () -> Void
    let isFirst: Bool
    let isLast: Bool
    let isExpanded: Bool
    let toggleExpanded: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            header

            if isExpanded {
                Divider()
                    .overlay(Theme.line)
                    .padding(.vertical, 14)

                expandedContent
            }
        }
        .padding(18)
        .background(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(Theme.panelRaised)
                .overlay(
                    RoundedRectangle(cornerRadius: 18, style: .continuous)
                        .stroke(step.requiresRecalibration ? Theme.warning : Theme.line, lineWidth: 1)
                )
        )
    }

    private var header: some View {
        HStack(alignment: .top, spacing: 12) {
            Button(action: toggleExpanded) {
                VStack(alignment: .leading, spacing: 8) {
                    HStack(spacing: 10) {
                        kindBadge

                        Text(step.title)
                            .font(.system(size: 17, weight: .semibold, design: .rounded))
                            .foregroundStyle(Theme.textPrimary)
                            .lineLimit(1)

                        if step.requiresRecalibration {
                            Text("LEGACY")
                                .font(.system(size: 10, weight: .bold, design: .rounded))
                                .foregroundStyle(Theme.warning)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 5)
                                .background(
                                    Capsule(style: .continuous)
                                        .fill(Theme.warning.opacity(0.12))
                                )
                        }
                    }

                    Text(step.summary)
                        .font(.system(size: 12, weight: .medium, design: .rounded))
                        .foregroundStyle(step.requiresRecalibration ? Theme.warning : Theme.textSecondary)
                        .multilineTextAlignment(.leading)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)

            Toggle("", isOn: $step.isEnabled)
                .toggleStyle(.switch)
                .labelsHidden()

            HStack(spacing: 8) {
                iconButton("arrow.up") { moveUp() }
                    .disabled(isFirst)
                iconButton("arrow.down") { moveDown() }
                    .disabled(isLast)
                iconButton("plus.square.on.square") { duplicate() }
                iconButton("trash") { delete() }
                iconButton(isExpanded ? "chevron.up" : "chevron.down", action: toggleExpanded)
            }
        }
    }

    private var expandedContent: some View {
        VStack(alignment: .leading, spacing: 16) {
            VStack(alignment: .leading, spacing: 6) {
                Text("Step Name")
                    .font(.system(size: 12, weight: .bold, design: .rounded))
                    .foregroundStyle(Theme.textSecondary)

                TextField(step.kind == .click ? "Rename click action" : "Rename wait action", text: $step.title)
                    .textFieldStyle(.roundedBorder)
            }

            switch step.kind {
            case .click:
                clickEditor
            case .wait:
                waitEditor
            }
        }
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
            Picker("Button", selection: clickBinding.button) {
                ForEach(MouseButton.allCases) { button in
                    Text(button.displayName).tag(button)
                }
            }
            .pickerStyle(.segmented)

            ViewThatFits(in: .horizontal) {
                HStack {
                    coordinateField(title: "X", value: clickBinding.point.x)
                    coordinateField(title: "Y", value: clickBinding.point.y)
                    coordinateField(title: "Jitter X", value: clickBinding.jitterX)
                    coordinateField(title: "Jitter Y", value: clickBinding.jitterY)
                }

                VStack(spacing: 12) {
                    HStack {
                        coordinateField(title: "X", value: clickBinding.point.x)
                        coordinateField(title: "Y", value: clickBinding.point.y)
                    }
                    HStack {
                        coordinateField(title: "Jitter X", value: clickBinding.jitterX)
                        coordinateField(title: "Jitter Y", value: clickBinding.jitterY)
                    }
                }
            }

            HStack {
                Button {
                    viewModel.beginCalibration(presetID: preset.id, stepID: step.id)
                } label: {
                    Label("Calibrate Click", systemImage: "viewfinder.circle")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(step.requiresRecalibration ? Theme.warning : Theme.accentSoft)
            }

            if step.requiresRecalibration {
                Text("This click was saved in the old absolute mode. Recalibrate it before running.")
                    .font(.system(size: 12, weight: .semibold, design: .rounded))
                    .foregroundStyle(Theme.warning)
                    .padding(12)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(
                        RoundedRectangle(cornerRadius: 12, style: .continuous)
                            .fill(Theme.warning.opacity(0.08))
                    )
            } else if viewModel.isCalibrating(stepID: step.id) {
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
                ViewThatFits(in: .horizontal) {
                    HStack {
                        coordinateField(title: "Min", value: $step.timing.minSeconds)
                        coordinateField(title: "Max", value: $step.timing.maxSeconds)
                    }

                    VStack(spacing: 12) {
                        coordinateField(title: "Min", value: $step.timing.minSeconds)
                        coordinateField(title: "Max", value: $step.timing.maxSeconds)
                    }
                }
            }
        }
    }

    private func coordinateField(title: String, value: Binding<Double>) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.system(size: 11, weight: .bold, design: .rounded))
                .foregroundStyle(Theme.textSecondary)

            EditableDoubleField(
                title: title,
                value: value,
                maxFractionDigits: 2
            )
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
