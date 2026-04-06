import SwiftUI

struct ContentView: View {
    @StateObject private var viewModel = AppViewModel()

    var body: some View {
        NavigationSplitView {
            SidebarView(store: viewModel.store)
        } detail: {
            DetailPaneView(viewModel: viewModel, store: viewModel.store)
                .background(
                    LinearGradient(
                        colors: [Theme.background, Theme.panel],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
        }
        .navigationSplitViewStyle(.balanced)
    }
}

private struct DetailPaneView: View {
    @ObservedObject var viewModel: AppViewModel
    @ObservedObject var store: PresetStore

    var body: some View {
        if let selectedIndex = store.selectedIndex {
            HSplitView {
                PresetEditorView(
                    viewModel: viewModel,
                    preset: bindingForPreset(at: selectedIndex)
                )
                .frame(minWidth: 760)

                RunnerPanelView(
                    viewModel: viewModel,
                    runner: viewModel.runner,
                    permissionManager: viewModel.permissionManager,
                    preset: store.presets[selectedIndex]
                )
                .frame(minWidth: 320, idealWidth: 360, maxWidth: 420)
                .background(Theme.panel)
            }
        } else {
            EmptySelectionView {
                store.addPreset()
            }
        }
    }

    private func bindingForPreset(at index: Int) -> Binding<Preset> {
        Binding(
            get: { store.presets[index] },
            set: { newValue in
                store.presets[index] = newValue
                store.save()
            }
        )
    }
}

private struct EmptySelectionView: View {
    let createAction: () -> Void

    var body: some View {
        VStack(spacing: 18) {
            Image(systemName: "sparkles.rectangle.stack")
                .font(.system(size: 42, weight: .medium))
                .foregroundStyle(Theme.accent)

            Text("No Preset Selected")
                .font(.system(size: 28, weight: .semibold, design: .rounded))
                .foregroundStyle(Theme.textPrimary)

            Text("Create your first OSRS workflow and start building click and wait actions.")
                .font(.system(size: 15, weight: .medium, design: .rounded))
                .foregroundStyle(Theme.textSecondary)
                .multilineTextAlignment(.center)
                .frame(maxWidth: 420)

            Button("Create Preset", action: createAction)
                .buttonStyle(.borderedProminent)
                .tint(Theme.accent)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
