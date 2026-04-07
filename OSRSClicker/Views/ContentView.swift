import SwiftUI

private enum WorkspaceTab: Hashable {
    case builder
    case runner
}

struct ContentView: View {
    @StateObject private var viewModel = AppViewModel()

    var body: some View {
        NavigationSplitView {
            SidebarView(store: viewModel.store)
                .navigationSplitViewColumnWidth(min: 240, ideal: 280, max: 320)
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
    @State private var selectedTab: WorkspaceTab = .builder

    var body: some View {
        if let selectedIndex = store.selectedIndex {
            let preset = store.presets[selectedIndex]

            VStack(alignment: .leading, spacing: 18) {
                header(for: preset)

                TabView(selection: $selectedTab) {
                    PresetEditorView(
                        viewModel: viewModel,
                        preset: bindingForPreset(at: selectedIndex)
                    )
                    .tag(WorkspaceTab.builder)
                    .tabItem {
                        Label("Builder", systemImage: "slider.horizontal.3")
                    }

                    RunnerPanelView(
                        viewModel: viewModel,
                        runner: viewModel.runner,
                        permissionManager: viewModel.permissionManager,
                        preset: preset
                    )
                    .tag(WorkspaceTab.runner)
                    .tabItem {
                        Label("Runner", systemImage: "play.circle")
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
            .padding(20)
        } else {
            EmptySelectionView {
                store.addPreset()
            }
        }
    }

    private func header(for preset: Preset) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("OSRS Clicker")
                .font(.system(size: 13, weight: .bold, design: .rounded))
                .foregroundStyle(Theme.accent)

            Text(preset.name)
                .font(.system(size: 30, weight: .bold, design: .rounded))
                .foregroundStyle(Theme.textPrimary)
                .lineLimit(1)

            Text(preset.notes.isEmpty ? "Build and run your click preset from the tabs below." : preset.notes)
                .font(.system(size: 14, weight: .medium, design: .rounded))
                .foregroundStyle(Theme.textSecondary)
                .lineLimit(2)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
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

            Text("Create your first OSRS Clicker preset and start building click and wait actions.")
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
