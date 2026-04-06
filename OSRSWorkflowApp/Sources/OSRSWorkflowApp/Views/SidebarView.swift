import SwiftUI

struct SidebarView: View {
    @ObservedObject var store: PresetStore

    var body: some View {
        VStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 8) {
                Text("OSRS Workflow")
                    .font(.system(size: 26, weight: .bold, design: .rounded))
                    .foregroundStyle(Theme.textPrimary)

                Text("Native macOS preset builder")
                    .font(.system(size: 13, weight: .medium, design: .rounded))
                    .foregroundStyle(Theme.textSecondary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(20)

            List(selection: selectedPresetBinding) {
                ForEach(store.presets) { preset in
                    VStack(alignment: .leading, spacing: 6) {
                        Text(preset.name)
                            .font(.system(size: 14, weight: .semibold, design: .rounded))
                            .foregroundStyle(Theme.textPrimary)

                        Text("\(preset.actions.count) action\(preset.actions.count == 1 ? "" : "s")")
                            .font(.system(size: 12, weight: .medium, design: .rounded))
                            .foregroundStyle(Theme.textSecondary)
                    }
                    .padding(.vertical, 6)
                    .tag(preset.id)
                }
            }
            .scrollContentBackground(.hidden)
            .background(Theme.panel)

            HStack(spacing: 10) {
                sidebarButton("New", systemImage: "plus") {
                    store.addPreset()
                }
                sidebarButton("Copy", systemImage: "doc.on.doc") {
                    store.duplicateSelectedPreset()
                }
                sidebarButton("Delete", systemImage: "trash") {
                    store.deleteSelectedPreset()
                }
            }
            .padding(16)
        }
        .background(Theme.panel)
    }

    private var selectedPresetBinding: Binding<UUID?> {
        Binding(
            get: { store.selectedPresetID },
            set: { store.select($0) }
        )
    }

    private func sidebarButton(_ title: String, systemImage: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Label(title, systemImage: systemImage)
                .font(.system(size: 12, weight: .semibold, design: .rounded))
                .frame(maxWidth: .infinity)
        }
        .buttonStyle(.bordered)
        .tint(Theme.accent)
    }
}
